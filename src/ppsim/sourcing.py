"""Sourcing: supplier master, RFQ scoring and award, should-cost, total cost of ownership.

The planning engine (M1-M5) decides *how much* to buy and *when*. Sourcing decides
*who from* and *at what cost*:

- **supplier master** (M6a): every bidder for a purchased item, with its lane,
  incoterm, risk tier and quoted terms;
- **should-cost** (M6c): a bottom-up target price built from the material cost
  (a cited commodity index where one is linked, otherwise a mock base), a conversion
  step, and the supplier's SG&A and margin. The gap to the quote is the negotiation gap;
- **RFQ scoring and award** (M6b): price, lead time, quality and supply risk, each
  normalised within the item's bid set and weighted by the sourcing policy, with a
  written award rationale;
- **total cost of ownership** (M6d): quoted price plus inbound freight and duty (by
  incoterm), the carrying cost of the supplier's minimum order quantity, and the cost
  of its defect rate. The cheapest unit price is often not the cheapest TCO.

Quotes are MOCK and simulated as a price index on the should-cost target price
(ADR 0013) so that no dollar quote is invented per supplier. Commodity prices stay
cited to FRED. No real supplier appears anywhere.
"""
from __future__ import annotations

from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from .config import INCOTERMS, ProductConfig, RFQ_CRITERIA
from .mrp import MrpRecord

PERIODS_PER_YEAR = {"W": 52.0, "M": 12.0, "Q": 4.0, "D": 365.0}
# How far under an MOQ the typical planned order may sit before it is worth a note:
# lot-size rounding leaves orders a few percent short, which is not a sourcing problem.
MOQ_TOLERANCE = 0.10


def periods_per_year(freq: str) -> float:
    """Buckets per year for a pandas offset alias (``W-SUN`` -> 52)."""
    key = freq.split("-")[0].rstrip("S").upper() or freq.upper()
    for k, v in PERIODS_PER_YEAR.items():
        if key.startswith(k):
            return v
    raise ValueError(f"unsupported frequency for annualising: {freq!r}")


# ---------------------------------------------------------------------------
# planned usage (the volume an RFQ is run for)
# ---------------------------------------------------------------------------


def planned_usage(cfg: ProductConfig, records: Mapping[str, MrpRecord]) -> pd.DataFrame:
    """Purchased volume the plan implies, per item: horizon total, per bucket, annualised."""
    ppy = periods_per_year(cfg.freq)
    rows = []
    for iid, rec in records.items():
        if cfg.items[iid].type != "purchased":
            continue
        gross = float(rec.table.loc["gross_requirements"].sum())
        released = float(rec.table.loc["planned_order_releases"].sum())
        per_bucket = gross / cfg.horizon
        rows.append({
            "item": iid,
            "uom": cfg.items[iid].uom,
            "gross_requirements": gross,
            "planned_releases": released,
            "per_bucket": per_bucket,
            "annual": per_bucket * ppy,
        })
    return pd.DataFrame(rows).set_index("item") if rows else pd.DataFrame()


# ---------------------------------------------------------------------------
# M6c should-cost
# ---------------------------------------------------------------------------


def should_cost(cfg: ProductConfig, latest_prices: Optional[Mapping[str, float]] = None) -> pd.DataFrame:
    """Bottom-up target price per quoted item (ex-works basis).

    material + conversion + (SG&A and margin) = target price. ``material`` is the
    latest value of the item's linked price index when one is available, else the
    mock base from the config. ``material_basis`` records which was used.
    """
    s = cfg.sourcing
    latest = dict(latest_prices or {})
    quoted = sorted({i for sp in cfg.suppliers.values() for i in sp.supplies})
    rows = []
    for iid in quoted:
        item = cfg.items[iid]
        if iid in latest and np.isfinite(latest[iid]):
            material = float(latest[iid])
            basis = f"cited index {item.price.series}" if item.price else "linked index"
        else:
            material = s.material_base[iid]
            basis = "mock base"
        conversion = material * s.conversion_pct
        margin = (material + conversion) * s.margin_pct
        rows.append({
            "item": iid,
            "uom": item.uom,
            "material_usd": material,
            "material_basis": basis,
            "conversion_usd": conversion,
            "margin_usd": margin,
            "target_price_usd": material + conversion + margin,
            "material_share": material / (material + conversion + margin),
        })
    return pd.DataFrame(rows).set_index("item")


# ---------------------------------------------------------------------------
# M6a/M6b supplier master, quotes and scoring
# ---------------------------------------------------------------------------


def quote_table(cfg: ProductConfig, should_cost_df: pd.DataFrame, usage: pd.DataFrame) -> pd.DataFrame:
    """One row per (item, supplier): the RFQ response and its gap to should-cost."""
    s = cfg.sourcing
    rows = []
    for sup in cfg.suppliers.values():
        q = sup.quote
        for iid in sup.supplies:
            target = float(should_cost_df.loc[iid, "target_price_usd"])
            per_bucket = float(usage.loc[iid, "per_bucket"]) if iid in usage.index else 0.0
            lt = max(1, int(round(cfg.items[iid].planning.lead_time + q.lead_time_delta)))
            price = target * q.price_index
            rows.append({
                "item": iid,
                "uom": cfg.items[iid].uom,
                "supplier": sup.id,
                "supplier_name": sup.name,
                "archetype": sup.archetype,
                "lane": sup.lane,
                "incoterm": sup.incoterm,
                "risk_tier": sup.risk_tier,
                "risk_score": s.risk_scores[sup.risk_tier],
                "quoted_usd_per_uom": price,
                "lead_time_weeks": lt,
                "lead_time_sigma": q.lead_time_sigma,
                "moq_qty": q.moq_weeks * per_bucket,
                "moq_weeks": q.moq_weeks,
                "quality_ppm": q.quality_ppm,
                "otif": q.otif,
                "short_ship_rate": q.short_ship_rate,
                "should_cost_usd": target,
                "gap_usd": price - target,
                "gap_pct": price / target - 1.0,
            })
    return pd.DataFrame(rows).sort_values(["item", "quoted_usd_per_uom"]).reset_index(drop=True)


def range_score(x: pd.Series, lower_is_better: bool) -> pd.Series:
    """Range (min-max) normalisation inside one bid set: best = 1, worst = 0.

    The standard weighted-scorecard normalisation: it puts every criterion on the same
    0-1 scale so the weights, not the units, decide the award. Consequences worth
    knowing: the worst bid scores 0 on that criterion however small the real gap is,
    and with only two bidders the loser scores 0 on everything it does not win. If all
    bids tie on a criterion, they all score 1 (the criterion cannot separate them).
    """
    x = x.astype(float)
    lo, hi = x.min(), x.max()
    if hi - lo <= 0:
        return pd.Series(1.0, index=x.index)
    return (hi - x) / (hi - lo) if lower_is_better else (x - lo) / (hi - lo)


def score_quotes(cfg: ProductConfig, quotes: pd.DataFrame) -> pd.DataFrame:
    """Add a 0-1 score per criterion (normalised within the item's bid set) and the weighted total."""
    w = cfg.sourcing.weights
    out = quotes.copy()
    for col in ("price_score", "lead_time_score", "quality_score", "risk_score_norm", "total_score"):
        out[col] = np.nan
    for iid, grp in out.groupby("item"):
        out.loc[grp.index, "price_score"] = range_score(grp["quoted_usd_per_uom"], True)
        out.loc[grp.index, "lead_time_score"] = range_score(grp["lead_time_weeks"], True)
        out.loc[grp.index, "quality_score"] = range_score(grp["quality_ppm"], True)
        out.loc[grp.index, "risk_score_norm"] = range_score(grp["risk_score"], False)
    out["total_score"] = (
        w["price"] * out["price_score"]
        + w["lead_time"] * out["lead_time_score"]
        + w["quality"] * out["quality_score"]
        + w["risk"] * out["risk_score_norm"]
    )
    out["rank"] = out.groupby("item")["total_score"].rank(ascending=False, method="first").astype(int)
    return out.sort_values(["item", "rank"]).reset_index(drop=True)


_SCORE_COL = {"price": "price_score", "lead_time": "lead_time_score", "quality": "quality_score", "risk": "risk_score_norm"}
_CRITERION_FACT = {
    "price": lambda r: f"${r['quoted_usd_per_uom']:,.4g}/{r['uom']}",
    "lead_time": lambda r: f"{int(r['lead_time_weeks'])} wk",
    "quality": lambda r: f"{r['quality_ppm']:,.0f} ppm",
    "risk": lambda r: f"{r['risk_tier']} risk",
}


def _rationale(cfg: ProductConfig, grp: pd.DataFrame) -> str:
    """Why the winner won, in one sentence, naming the criterion that decided it."""
    w = cfg.sourcing.weights
    win = grp.iloc[0]
    if len(grp) == 1:
        return (f"Single bid: {win['supplier_name']} at ${win['quoted_usd_per_uom']:,.4g}/{win['uom']}, "
                f"score {win['total_score']:.2f}. No competing quote, so no award comparison.")
    up = grp.iloc[1]
    deltas = {c: w[c] * (win[_SCORE_COL[c]] - up[_SCORE_COL[c]]) for c in RFQ_CRITERIA}
    decisive = max(deltas, key=lambda c: deltas[c])
    parts = [
        f"Awarded to {win['supplier_name']} at ${win['quoted_usd_per_uom']:,.4g}/{win['uom']}: "
        f"score {win['total_score']:.2f} vs {up['total_score']:.2f} for {up['supplier_name']} "
        f"(margin {win['total_score'] - up['total_score']:+.2f}).",
        f"{decisive.replace('_', ' ').capitalize()} decided it at weight {w[decisive]:.0%}: "
        f"{_CRITERION_FACT[decisive](win)} vs {_CRITERION_FACT[decisive](up)}.",
    ]
    cheap = grp.loc[grp["quoted_usd_per_uom"].idxmin()]
    if cheap["supplier"] != win["supplier"]:
        lost = sorted((c for c in RFQ_CRITERIA if c != "price"), key=lambda c: w[c] * (cheap[_SCORE_COL[c]] - win[_SCORE_COL[c]]))
        parts.append(
            f"The lowest bid ({cheap['supplier_name']}, ${cheap['quoted_usd_per_uom']:,.4g}, "
            f"{cheap['quoted_usd_per_uom'] / win['quoted_usd_per_uom'] - 1:+.0%}) lost on "
            f"{lost[0].replace('_', ' ')} and {lost[1].replace('_', ' ')}."
        )
    else:
        parts.append("The winner is also the lowest bid.")
    parts.append(f"Quote sits {win['gap_pct']:+.0%} against should-cost (${win['should_cost_usd']:,.4g}).")
    return " ".join(parts)


def award(cfg: ProductConfig, scored: pd.DataFrame) -> pd.DataFrame:
    """One row per item: the awarded supplier, the runner-up, and the written rationale."""
    rows = []
    for iid, grp in scored.groupby("item"):
        grp = grp.sort_values("rank")
        win = grp.iloc[0]
        up = grp.iloc[1] if len(grp) > 1 else None
        cheap = grp.loc[grp["quoted_usd_per_uom"].idxmin()]
        rows.append({
            "item": iid,
            "uom": win["uom"],
            "bids": len(grp),
            "awarded_to": win["supplier"],
            "awarded_name": win["supplier_name"],
            "awarded_usd_per_uom": win["quoted_usd_per_uom"],
            "awarded_lead_time_weeks": int(win["lead_time_weeks"]),
            "awarded_score": win["total_score"],
            "runner_up": None if up is None else up["supplier"],
            "runner_up_score": np.nan if up is None else up["total_score"],
            "score_margin": np.nan if up is None else win["total_score"] - up["total_score"],
            "lowest_bid": cheap["supplier"],
            "premium_vs_lowest_pct": win["quoted_usd_per_uom"] / cheap["quoted_usd_per_uom"] - 1.0,
            "gap_vs_should_cost_pct": win["gap_pct"],
            "rationale": _rationale(cfg, grp),
        })
    return pd.DataFrame(rows).set_index("item")


# ---------------------------------------------------------------------------
# M6d total cost of ownership
# ---------------------------------------------------------------------------


def tco(cfg: ProductConfig, quotes: pd.DataFrame, usage: pd.DataFrame) -> pd.DataFrame:
    """Landed cost plus MOQ carrying cost and quality cost, per (item, supplier) and per uom.

    Who pays inbound freight and duty follows the incoterm (``config.INCOTERMS``):
    under FOB the buyer pays both, under DAP the seller delivers but the buyer clears
    customs, under DDP the seller pays both.
    """
    s = cfg.sourcing
    rows = []
    for _, q in quotes.iterrows():
        lane = s.lanes[q["lane"]]
        seller_freight, seller_duty = INCOTERMS[q["incoterm"]]
        price = float(q["quoted_usd_per_uom"])
        freight = 0.0 if seller_freight else price * lane.freight_pct
        duty = 0.0 if seller_duty else (price + freight) * lane.duty_pct
        landed = price + freight + duty
        annual = float(usage.loc[q["item"], "annual"]) if q["item"] in usage.index else 0.0
        cycle_stock = float(q["moq_qty"]) / 2.0
        carrying = (cycle_stock * landed * s.carrying_cost_rate / annual) if annual > 0 else np.nan
        quality = landed * float(q["quality_ppm"]) / 1e6 * s.quality_cost_multiple
        total = landed + (0.0 if np.isnan(carrying) else carrying) + quality
        rows.append({
            "tco_basis": "landed + MOQ carrying + defect cost" if annual > 0
            else "landed + defect cost (no planned usage, so no MOQ carrying cost)",
            "item": q["item"],
            "uom": q["uom"],
            "supplier": q["supplier"],
            "supplier_name": q["supplier_name"],
            "incoterm": q["incoterm"],
            "lane": q["lane"],
            "unit_price_usd": price,
            "freight_usd": freight,
            "duty_usd": duty,
            "landed_usd": landed,
            "moq_carrying_usd": carrying,
            "quality_cost_usd": quality,
            "tco_usd_per_uom": total,
            "annual_qty": annual,
            "annual_tco_usd": total * annual,
        })
    out = pd.DataFrame(rows)
    out["price_rank"] = out.groupby("item")["unit_price_usd"].rank(method="first").astype(int)
    out["tco_rank"] = out.groupby("item")["tco_usd_per_uom"].rank(method="first").astype(int)
    out["tco_premium_vs_best_pct"] = out["tco_usd_per_uom"] / out.groupby("item")["tco_usd_per_uom"].transform("min") - 1.0
    return out.sort_values(["item", "tco_rank"]).reset_index(drop=True)


def tco_notes(tco_df: pd.DataFrame) -> List[str]:
    """Items where the cheapest unit price is not the cheapest total cost."""
    notes = []
    for iid, grp in tco_df.groupby("item"):
        cheap = grp.loc[grp["unit_price_usd"].idxmin()]
        best = grp.loc[grp["tco_usd_per_uom"].idxmin()]
        partial = "" if grp["moq_carrying_usd"].notna().all() else " [no planned usage, so the MOQ carrying cost is excluded]"
        if cheap["supplier"] != best["supplier"]:
            notes.append(
                f"{iid}: lowest price is {cheap['supplier_name']} "
                f"(${cheap['unit_price_usd']:,.4g}/{cheap['uom']}), but lowest total cost is "
                f"{best['supplier_name']} (${best['tco_usd_per_uom']:,.4g} vs "
                f"${cheap['tco_usd_per_uom']:,.4g} per {cheap['uom']}){partial}"
            )
    return notes


def check_moq(po_lines: pd.DataFrame, quotes: pd.DataFrame, awards: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """Flag planned PO lines that fall below the awarded supplier's minimum order quantity.

    A plan that orders weekly from a supplier quoting six weeks of cover is not a plan
    that gets the awarded price. An ERP enforces this at vendor selection: Odoo filters
    the vendor price list by the order quantity and falls through to the next vendor in
    sequence, so the award quietly stops applying (verified against Odoo 19 Community,
    2026-10-04). Either the lot-sizing policy consolidates orders up to the MOQ, or the
    award has to go to a supplier whose MOQ fits the plan.
    """
    out = po_lines.copy()
    if not len(out):
        return out, []
    moq_of = {}
    for iid, aw in awards.iterrows():
        bid = quotes[(quotes["item"] == iid) & (quotes["supplier"] == aw["awarded_to"])]
        if len(bid):
            moq_of[iid] = float(bid.iloc[0]["moq_qty"])
    out["awarded_moq_qty"] = out["item"].map(moq_of)
    out["below_awarded_moq"] = out["qty"] < out["awarded_moq_qty"] - 1e-9
    notes = []
    for iid, grp in out.groupby("item"):
        below, moq = grp[grp["below_awarded_moq"]], moq_of.get(iid)
        if not len(below) or not moq:
            continue
        typical = float(grp["qty"].median())
        if typical >= moq * (1 - MOQ_TOLERANCE):
            continue  # the typical order is at the MOQ; rounding is not a sourcing problem
        notes.append(
            f"{iid}: {len(below)} of {len(grp)} planned orders ({below['qty'].min():,.0f}-"
            f"{below['qty'].max():,.0f} {grp['uom'].iloc[0]}) are below the awarded supplier's MOQ of "
            f"{moq:,.0f} - the typical order covers {typical / moq:.0%} of it. Consolidate them "
            f"(periods-of-supply lot sizing) or the award price does not apply, because an ERP will "
            f"source from the next vendor instead"
        )
    return out, notes


def awarded_vendor_map(awards: pd.DataFrame, cfg: ProductConfig) -> Dict[str, Tuple[str, str]]:
    """item -> (supplier id, supplier name) for the awarded supplier; feeds the PO schedule."""
    return {iid: (row["awarded_to"], row["awarded_name"]) for iid, row in awards.iterrows()}

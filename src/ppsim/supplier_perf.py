"""Supplier performance and sourcing strategy (M6e, M6f).

- **scorecard** (M6e): a simulated delivery history for each awarded supplier gives
  on-time, in-full and OTIF rates, lead-time variability, fill rate and purchase price
  variance against standard cost. Frequency of lateness comes from the supplier's
  quoted OTIF, the size of a delay from its lead-time sigma (ADR 0015);
- **safety-stock cost** of lead-time variability: a supplier with an erratic lead time
  is paid for twice, once in price and once in the inventory it forces;
- **single vs dual source**: extra annual cost against the expected value of supply at
  risk, so the trade-off is priced rather than asserted;
- **forward buy vs spot**: the carrying cost of buying coverage ahead against the
  price scenarios already built from the commodity index.

Every performance number is MOCK and labelled as such. The history is synthetic and
reproducible from ``sourcing.seed``; it is not a real supplier record.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .config import ProductConfig
from .sourcing import periods_per_year

# OTIF letter grades: a common buyer convention, not a sourced figure.
GRADES: Tuple[Tuple[float, str], ...] = ((0.95, "A"), (0.90, "B"), (0.80, "C"), (0.0, "D"))


def grade(otif: float) -> str:
    for threshold, letter in GRADES:
        if otif >= threshold:
            return letter
    return GRADES[-1][1]


def delivery_history(cfg: ProductConfig, quotes: pd.DataFrame, awards: pd.DataFrame, usage: pd.DataFrame) -> pd.DataFrame:
    """Simulated past deliveries for each awarded supplier, one row per period.

    on-time frequency = OTIF / (1 - short-ship rate), so the simulated OTIF reproduces
    the quoted one; a late delivery slips by at least one week, sized by the supplier's
    lead-time sigma.
    """
    s = cfg.sourcing
    rows = []
    for n, (iid, aw) in enumerate(awards.iterrows()):
        q = quotes[(quotes["item"] == iid) & (quotes["supplier"] == aw["awarded_to"])].iloc[0]
        per_bucket = float(usage.loc[iid, "per_bucket"]) if iid in usage.index else 0.0
        if per_bucket <= 0:
            continue
        rng = np.random.default_rng([s.seed, n])
        short_rate = float(q["short_ship_rate"])
        on_time_rate = min(1.0, float(q["otif"]) / (1.0 - short_rate)) if short_rate < 1 else 0.0
        standard = float(aw["awarded_usd_per_uom"])
        promised = int(q["lead_time_weeks"])
        sigma = float(q["lead_time_sigma"])
        for t in range(s.scorecard_periods):
            on_time = bool(rng.random() < on_time_rate)
            delay = 0 if on_time else max(1, int(math.ceil(abs(rng.normal(0.0, sigma)))))
            in_full = bool(rng.random() >= short_rate)
            received = per_bucket if in_full else per_bucket * s.short_ship_fraction
            actual_price = standard * (1.0 + rng.normal(0.0, s.price_drift_cv))
            rows.append({
                "item": iid,
                "supplier": aw["awarded_to"],
                "supplier_name": aw["awarded_name"],
                "period": t,
                "ordered_qty": per_bucket,
                "received_qty": received,
                "promised_lead_time": promised,
                "actual_lead_time": promised + delay,
                "weeks_late": delay,
                "on_time": on_time,
                "in_full": in_full,
                "otif": on_time and in_full,
                "standard_usd_per_uom": standard,
                "actual_usd_per_uom": actual_price,
                "ppv_usd": (actual_price - standard) * received,
            })
    return pd.DataFrame(rows)


def scorecard(cfg: ProductConfig, history: pd.DataFrame, quotes: pd.DataFrame) -> pd.DataFrame:
    """Aggregate the delivery history into a supplier scorecard per (item, supplier)."""
    if history.empty:
        return pd.DataFrame()
    rows = []
    for (iid, sid), g in history.groupby(["item", "supplier"]):
        q = quotes[(quotes["item"] == iid) & (quotes["supplier"] == sid)].iloc[0]
        std_spend = float((g["standard_usd_per_uom"] * g["received_qty"]).sum())
        otif = float(g["otif"].mean())
        rows.append({
            "item": iid,
            "supplier": sid,
            "supplier_name": g["supplier_name"].iloc[0],
            "deliveries": len(g),
            "on_time_pct": float(g["on_time"].mean()),
            "in_full_pct": float(g["in_full"].mean()),
            "otif_pct": otif,
            "quoted_otif_pct": float(q["otif"]),
            "otif_vs_quoted": otif - float(q["otif"]),
            "avg_weeks_late": float(g.loc[~g["on_time"], "weeks_late"].mean()) if (~g["on_time"]).any() else 0.0,
            "lead_time_sigma_actual": float(g["actual_lead_time"].std(ddof=0)),
            "fill_rate": float(g["received_qty"].sum() / g["ordered_qty"].sum()),
            "standard_spend_usd": std_spend,
            "ppv_usd": float(g["ppv_usd"].sum()),
            "ppv_pct": float(g["ppv_usd"].sum() / std_spend) if std_spend else np.nan,
            "grade": grade(otif),
        })
    return pd.DataFrame(rows).set_index(["item", "supplier"])


def safety_stock_cost(cfg: ProductConfig, quotes: pd.DataFrame, tco_df: pd.DataFrame, usage: pd.DataFrame, awards: pd.DataFrame) -> pd.DataFrame:
    """What each supplier's lead-time variability costs in safety stock.

    ``safety stock = z x sigma_lead_time x demand per bucket`` (lead time variable,
    demand treated as stable); carrying cost is the annual rate on its landed value.
    """
    s = cfg.sourcing
    landed = tco_df.set_index(["item", "supplier"])["landed_usd"]
    rows = []
    for _, q in quotes.iterrows():
        iid, sid = q["item"], q["supplier"]
        per_bucket = float(usage.loc[iid, "per_bucket"]) if iid in usage.index else 0.0
        ss = s.service_level_z * float(q["lead_time_sigma"]) * per_bucket
        unit = float(landed.loc[(iid, sid)])
        rows.append({
            "item": iid,
            "uom": q["uom"],
            "supplier": sid,
            "supplier_name": q["supplier_name"],
            "awarded": bool(iid in awards.index and awards.loc[iid, "awarded_to"] == sid),
            "lead_time_weeks": int(q["lead_time_weeks"]),
            "lead_time_sigma": float(q["lead_time_sigma"]),
            "safety_stock_qty": ss,
            "landed_usd_per_uom": unit,
            "annual_carrying_usd": ss * unit * s.carrying_cost_rate,
        })
    out = pd.DataFrame(rows)
    out["carrying_vs_best_usd"] = out["annual_carrying_usd"] - out.groupby("item")["annual_carrying_usd"].transform("min")
    return out.sort_values(["item", "annual_carrying_usd"]).reset_index(drop=True)


def source_strategy(cfg: ProductConfig, quotes: pd.DataFrame, awards: pd.DataFrame, tco_df: pd.DataFrame, usage: pd.DataFrame) -> pd.DataFrame:
    """Single vs dual source per item: extra annual cost vs expected value of supply at risk.

    Expected exposure = P(disruption) x weeks of supply lost x value per bucket, where
    ``P = disruption_prob_base x (1 - risk score)``. Dual sourcing splits the volume, so
    only the disrupted supplier's share stops; no backfill from the other source is
    assumed (ADR 0015).
    """
    s = cfg.sourcing
    ppy = periods_per_year(cfg.freq)
    t = tco_df.set_index(["item", "supplier"])
    rows = []
    for iid, aw in awards.iterrows():
        if iid not in usage.index:
            continue
        per_bucket = float(usage.loc[iid, "per_bucket"])
        annual = float(usage.loc[iid, "annual"])
        win = aw["awarded_to"]
        up = aw["runner_up"]
        risk = quotes.set_index(["item", "supplier"])["risk_score"]

        def prob(sid: str) -> float:
            return s.disruption_prob_base * (1.0 - float(risk.loc[(iid, sid)]))

        awarded_landed = float(t.loc[(iid, win), "landed_usd"])

        def exposure(sid: str, share: float) -> float:
            """Expected value of supply at risk, valued at the awarded landed price.

            Valuing every share at the same price keeps the comparison about supply
            risk: a pricier second source should not look riskier just for costing more.
            """
            return prob(sid) * s.disruption_weeks * per_bucket * share * awarded_landed

        tiers = quotes.set_index(["item", "supplier"])["risk_tier"]
        single_cost = annual * float(t.loc[(iid, win), "tco_usd_per_uom"])
        single_exp = exposure(win, 1.0)
        rows.append({
            "item": iid, "strategy": "single source", "suppliers": win,
            "awarded_risk_tier": tiers.loc[(iid, win)],
            "second_risk_tier": "", "annual_cost_usd": single_cost, "expected_exposure_usd": single_exp,
            "cost_delta_usd": 0.0, "exposure_delta_usd": 0.0, "cost_per_usd_exposure_removed": np.nan,
        })
        if up is None:
            continue
        split = s.dual_source_split
        dual_cost = annual * (
            (1 - split) * float(t.loc[(iid, win), "tco_usd_per_uom"]) + split * float(t.loc[(iid, up), "tco_usd_per_uom"])
        )
        dual_exp = exposure(win, 1 - split) + exposure(up, split)
        d_cost, d_exp = dual_cost - single_cost, dual_exp - single_exp
        rows.append({
            "item": iid, "strategy": f"dual source ({1 - split:.0%}/{split:.0%})", "suppliers": f"{win} + {up}",
            "awarded_risk_tier": tiers.loc[(iid, win)], "second_risk_tier": tiers.loc[(iid, up)],
            "annual_cost_usd": dual_cost, "expected_exposure_usd": dual_exp,
            "cost_delta_usd": d_cost, "exposure_delta_usd": d_exp,
            "cost_per_usd_exposure_removed": (d_cost / -d_exp) if d_exp < 0 else np.nan,
        })
    out = pd.DataFrame(rows)
    if len(out):
        out["periods_per_year"] = ppy
    return out


def strategy_notes(strategy: pd.DataFrame) -> List[str]:
    """One line per item saying whether dual sourcing buys risk reduction cheaply."""
    notes = []
    for iid, g in strategy.groupby("item"):
        dual = g[g["strategy"].str.startswith("dual")]
        if dual.empty:
            continue
        d = dual.iloc[0]
        cost, exp = d["cost_delta_usd"], d["exposure_delta_usd"]
        cost_txt = f"saves ${-cost:,.0f}/yr" if cost < 0 else f"costs ${cost:,.0f}/yr extra"
        if exp > 1e-9:
            notes.append(
                f"{iid}: dual sourcing {cost_txt} but RAISES expected exposure ${exp:,.0f}, because the "
                f"second source is {d['second_risk_tier']} risk against {d['awarded_risk_tier']} for the "
                f"awarded supplier; stay single source"
            )
        elif exp >= -1e-9:
            notes.append(
                f"{iid}: dual sourcing {cost_txt} and leaves expected exposure unchanged (both sources "
                f"{d['awarded_risk_tier']} risk); split only if capacity or negotiation leverage justifies it"
            )
        elif cost <= 0:
            notes.append(f"{iid}: dual sourcing {cost_txt} and cuts expected exposure ${-exp:,.0f}; dual source")
        else:
            notes.append(
                f"{iid}: dual sourcing {cost_txt} to remove ${-exp:,.0f} of expected exposure "
                f"(${d['cost_per_usd_exposure_removed']:,.2f} per USD removed)"
            )
    return notes


def forward_buy(cfg: ProductConfig, awards: pd.DataFrame, should_cost_df: pd.DataFrame, usage: pd.DataFrame, price_scenarios: Optional[pd.DataFrame]) -> pd.DataFrame:
    """Forward buy vs buying weekly at spot, for items with a linked price index.

    The quote is only partly commodity: a scenario price passes the index move through
    at the material share of the should-cost build-up. Buying ``forward_buy_weeks`` of
    coverage today costs the carrying charge on the average inventory held.
    """
    if price_scenarios is None or not len(price_scenarios):
        return pd.DataFrame()
    s = cfg.sourcing
    ppy = periods_per_year(cfg.freq)
    weeks = s.forward_buy_weeks
    rows = []
    for iid, aw in awards.iterrows():
        if iid not in price_scenarios.index or iid not in usage.index:
            continue
        base_index = float(price_scenarios.loc[iid, "base"])
        if base_index <= 0:
            continue
        share = float(should_cost_df.loc[iid, "material_share"])
        price = float(aw["awarded_usd_per_uom"])
        qty = weeks * float(usage.loc[iid, "per_bucket"])
        carrying_per_uom = price * s.carrying_cost_rate * (weeks / ppy) / 2.0
        forward_per_uom = price + carrying_per_uom
        for name in [c for c in ("low_p10", "median_p50", "high_p90") if c in price_scenarios.columns]:
            idx = float(price_scenarios.loc[iid, name])
            spot_per_uom = price * (1.0 + share * (idx / base_index - 1.0))
            rows.append({
                "item": iid,
                "uom": aw["uom"],
                "scenario": name,
                "weeks_covered": weeks,
                "qty": qty,
                "forward_usd_per_uom": forward_per_uom,
                "carrying_usd_per_uom": carrying_per_uom,
                "spot_usd_per_uom": spot_per_uom,
                "forward_total_usd": forward_per_uom * qty,
                "spot_total_usd": spot_per_uom * qty,
                "saving_usd": (spot_per_uom - forward_per_uom) * qty,
                "breakeven_usd_per_uom": forward_per_uom,
                "forward_wins": spot_per_uom > forward_per_uom,
            })
    return pd.DataFrame(rows)

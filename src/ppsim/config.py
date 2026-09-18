"""Load and validate a product config (YAML).

A product config is the only place product-specific facts live. The loader enforces
the repo's sourcing rule: every process parameter must cite a declared public source.
"""
from __future__ import annotations

import ast
import math
import operator
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import yaml


class ConfigError(ValueError):
    pass


# ---------------------------------------------------------------------------
# Safe arithmetic over named parameters (used for derived values and BOM qty_per)
# ---------------------------------------------------------------------------

_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}
_UNARY = {ast.USub: operator.neg, ast.UAdd: operator.pos}
_FUNCS = {"min": min, "max": max, "ceil": math.ceil, "floor": math.floor}


def evaluate(expr: Any, names: Mapping[str, float]) -> float:
    """Evaluate a number or an arithmetic expression referencing ``names``.

    Only + - * / **, unary +/-, parentheses, numeric literals, names, and the
    functions min, max, ceil, floor are allowed.
    """
    if isinstance(expr, (int, float)) and not isinstance(expr, bool):
        return float(expr)
    if not isinstance(expr, str):
        raise ConfigError(f"expected number or expression, got {expr!r}")

    def _eval(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.Name):
            if node.id not in names:
                raise ConfigError(f"unknown name {node.id!r} in expression {expr!r}")
            return float(names[node.id])
        if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
            return _BINOPS[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
            return _UNARY[type(node.op)](_eval(node.operand))
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in _FUNCS
            and not node.keywords
        ):
            return float(_FUNCS[node.func.id](*(_eval(a) for a in node.args)))
        raise ConfigError(f"unsupported syntax in expression {expr!r}")

    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise ConfigError(f"bad expression {expr!r}: {e}") from None
    return _eval(tree)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Source:
    key: str
    citation: str
    url: str
    license: Optional[str] = None


@dataclass(frozen=True)
class Parameter:
    name: str
    value: float
    unit: str
    source: str
    locator: str
    note: Optional[str] = None


@dataclass(frozen=True)
class LotSizing:
    rule: str = "lot_for_lot"  # lot_for_lot | fixed_order_quantity | periods_of_supply
    quantity: float = 0.0  # FOQ size
    periods: int = 1  # periods of supply (POQ)
    minimum: float = 0.0
    multiple: float = 0.0


@dataclass(frozen=True)
class Planning:
    lead_time: int = 0  # in buckets
    safety_stock: float = 0.0
    on_hand: float = 0.0
    scheduled_receipts: Dict[int, float] = field(default_factory=dict)  # bucket -> qty
    lot_sizing: LotSizing = LotSizing()
    basis: str = "assumption"


@dataclass(frozen=True)
class PriceLink:
    series: str  # FRED series id
    usd_per_uom: str  # expression of `series` (the price) and parameters/derived values


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    type: str  # finished | intermediate | purchased
    uom: str
    planning: Planning
    price: Optional[PriceLink] = None


@dataclass(frozen=True)
class BomLine:
    parent: str
    component: str
    qty_per: float
    expr: str  # original expression, kept for traceability


@dataclass(frozen=True)
class DemandSpec:
    item: str
    mock: bool
    base_per_period: float
    annual_growth: float = 0.0
    seasonal_amplitude: float = 0.0
    seasonal_peak_month: int = 1
    noise_cv: float = 0.0
    seed: int = 0


@dataclass(frozen=True)
class ProductConfig:
    id: str
    name: str
    mock: bool
    freq: str
    start: str
    horizon: int
    sources: Dict[str, Source]
    parameters: Dict[str, Parameter]
    derived: Dict[str, float]
    items: Dict[str, Item]
    bom: List[BomLine]
    demand: DemandSpec
    variants: Dict[str, Dict[str, str]] = field(default_factory=dict)  # name -> {old: new}
    variant: Optional[str] = None
    path: Optional[Path] = None

    def names(self) -> Dict[str, float]:
        """All parameter and derived values, by name, for expression evaluation."""
        out = {k: p.value for k, p in self.parameters.items()}
        out.update(self.derived)
        return out


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def _req(d: Mapping[str, Any], key: str, where: str) -> Any:
    if key not in d or d[key] in (None, ""):
        raise ConfigError(f"{where}: missing required field {key!r}")
    return d[key]


def _load_planning(raw: Mapping[str, Any], where: str, names: Mapping[str, float]) -> Planning:
    ls_raw = raw.get("lot_sizing") or {}
    lot = LotSizing(
        rule=ls_raw.get("rule", "lot_for_lot"),
        quantity=float(ls_raw.get("quantity", 0)),
        periods=int(ls_raw.get("periods", 1)),
        minimum=float(ls_raw.get("minimum", 0)),
        multiple=float(ls_raw.get("multiple", 0)),
    )
    if lot.rule not in ("lot_for_lot", "fixed_order_quantity", "periods_of_supply"):
        raise ConfigError(f"{where}: unknown lot sizing rule {lot.rule!r}")
    if lot.rule == "fixed_order_quantity" and lot.quantity <= 0:
        raise ConfigError(f"{where}: fixed_order_quantity needs quantity > 0")
    if lot.periods < 1:
        raise ConfigError(f"{where}: lot sizing periods must be >= 1")
    basis = raw.get("basis", "assumption")
    if basis not in ("assumption", "derived"):
        raise ConfigError(f"{where}: basis must be 'assumption' or 'derived'")
    # lead_time may be an expression of cited parameters (basis: derived)
    lt = evaluate(raw.get("lead_time", 0), names)
    if lt != int(lt) or lt < 0:
        raise ConfigError(f"{where}: lead_time must be a non-negative whole number of buckets (got {lt})")
    lead_time = int(lt)
    return Planning(
        lead_time=lead_time,
        safety_stock=float(raw.get("safety_stock", 0)),
        on_hand=float(raw.get("on_hand", 0)),
        scheduled_receipts={int(k): float(v) for k, v in (raw.get("scheduled_receipts") or {}).items()},
        lot_sizing=lot,
        basis=basis,
    )


def load_config(path: "str | Path") -> ProductConfig:
    path = Path(path)
    with path.open() as f:
        raw = yaml.safe_load(f)
    return parse_config(raw, path=path)


def parse_config(raw: Mapping[str, Any], path: Optional[Path] = None) -> ProductConfig:
    prod = _req(raw, "product", "config")
    time = _req(raw, "time", "config")

    sources = {}
    for key, s in (raw.get("sources") or {}).items():
        where = f"sources.{key}"
        sources[key] = Source(key, _req(s, "citation", where), _req(s, "url", where), s.get("license"))

    parameters = {}
    for name, p in (raw.get("parameters") or {}).items():
        where = f"parameters.{name}"
        src = _req(p, "source", where)
        if src not in sources:
            raise ConfigError(f"{where}: source {src!r} is not declared under 'sources'")
        value = p.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ConfigError(f"{where}: value must be a number (derived values go under 'derived')")
        parameters[name] = Parameter(
            name=name,
            value=float(value),
            unit=_req(p, "unit", where),
            source=src,
            locator=_req(p, "locator", where),
            note=p.get("note"),
        )

    # Derived values: evaluated in declaration order, may reference earlier ones.
    names: Dict[str, float] = {k: v.value for k, v in parameters.items()}
    derived: Dict[str, float] = {}
    for name, d in (raw.get("derived") or {}).items():
        if name in names:
            raise ConfigError(f"derived.{name}: name already defined")
        expr = _req(d, "expr", f"derived.{name}")
        derived[name] = names[name] = evaluate(expr, names)

    items: Dict[str, Item] = {}
    for it in _req(raw, "items", "config"):
        iid = _req(it, "id", "items[]")
        where = f"items.{iid}"
        if iid in items:
            raise ConfigError(f"{where}: duplicate item id")
        typ = _req(it, "type", where)
        if typ not in ("finished", "intermediate", "purchased"):
            raise ConfigError(f"{where}: unknown type {typ!r}")
        price = None
        if it.get("price"):
            pr = it["price"]
            price = PriceLink(series=_req(pr, "series", f"{where}.price"), usd_per_uom=_req(pr, "usd_per_uom", f"{where}.price"))
            # validate expression now, with a dummy price value
            evaluate(price.usd_per_uom, {**names, price.series: 1.0})
        items[iid] = Item(
            id=iid,
            name=it.get("name", iid),
            type=typ,
            uom=_req(it, "uom", where),
            planning=_load_planning(it.get("planning") or {}, f"{where}.planning", names),
            price=price,
        )

    bom = []
    for i, line in enumerate(raw.get("bom") or []):
        where = f"bom[{i}]"
        parent, comp = _req(line, "parent", where), _req(line, "component", where)
        for ref in (parent, comp):
            if ref not in items:
                raise ConfigError(f"{where}: unknown item {ref!r}")
        expr = _req(line, "qty_per", where)
        qty = evaluate(expr, names)
        if qty <= 0:
            raise ConfigError(f"{where}: qty_per must be > 0 (got {qty})")
        bom.append(BomLine(parent, comp, qty, str(expr)))

    dm = _req(raw, "demand", "config")
    if dm.get("mock") is not True:
        raise ConfigError("demand: only mock demand is supported; set 'mock: true' explicitly")
    demand_item = _req(dm, "item", "demand")
    if demand_item not in items:
        raise ConfigError(f"demand: unknown item {demand_item!r}")
    demand = DemandSpec(
        item=demand_item,
        mock=True,
        base_per_period=float(_req(dm, "base_per_period", "demand")),
        annual_growth=float(dm.get("annual_growth", 0)),
        seasonal_amplitude=float(dm.get("seasonal_amplitude", 0)),
        seasonal_peak_month=int(dm.get("seasonal_peak_month", 1)),
        noise_cv=float(dm.get("noise_cv", 0)),
        seed=int(dm.get("seed", 0)),
    )

    variants: Dict[str, Dict[str, str]] = {}
    for vname, v in (raw.get("variants") or {}).items():
        subs = {str(k): str(val) for k, val in (_req(v, "substitute", f"variants.{vname}")).items()}
        for old, new in subs.items():
            if old not in items or new not in items:
                raise ConfigError(f"variants.{vname}: unknown item in {old!r} -> {new!r}")
        variants[vname] = subs

    return ProductConfig(
        id=_req(prod, "id", "product"),
        name=_req(prod, "name", "product"),
        mock=bool(prod.get("mock", True)),
        freq=_req(time, "freq", "time"),
        start=str(_req(time, "start", "time")),
        horizon=int(_req(time, "horizon", "time")),
        sources=sources,
        parameters=parameters,
        derived=derived,
        items=items,
        bom=bom,
        demand=demand,
        variants=variants,
        path=path,
    )


def apply_variant(cfg: ProductConfig, variant: Optional[str]) -> ProductConfig:
    """Return a copy of ``cfg`` with the variant's component substitutions applied."""
    if variant is None:
        return cfg
    if variant not in cfg.variants:
        raise ConfigError(f"unknown variant {variant!r}; known: {sorted(cfg.variants)}")
    subs = cfg.variants[variant]
    bom = [replace(b, component=subs.get(b.component, b.component)) for b in cfg.bom]
    return replace(cfg, bom=bom, variant=variant)

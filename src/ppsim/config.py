"""Load and validate a product config (YAML).

Product configs contain structure (items, BOM, policies) and *references* to the
assumptions registry (``knowledge/assumptions.csv``), never raw model numbers.
The loader enforces the repo's rules:

- process quantities (``derived`` used by the BOM, BOM ``qty_per``, price conversions)
  may only use ``cited`` assumptions;
- planning and demand numbers must be registry references (only 0 may be literal);
- the only numeric literals allowed inside expressions are 0 and 1;
- every referenced assumption lists this product in its ``used_in`` column.
"""
from __future__ import annotations

import ast
import math
import operator
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Set

import yaml

from .registry import Assumption, load_registry


class ConfigError(ValueError):
    pass


DEFAULT_REGISTRY = "../knowledge/assumptions.csv"  # relative to the product file

# ---------------------------------------------------------------------------
# Safe arithmetic over named values
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
ALLOWED_LITERALS = (0, 1)


def _parse(expr: Any) -> ast.Expression:
    if isinstance(expr, bool) or not isinstance(expr, (str, int, float)):
        raise ConfigError(f"expected number or expression, got {expr!r}")
    try:
        return ast.parse(str(expr), mode="eval")
    except SyntaxError as e:
        raise ConfigError(f"bad expression {expr!r}: {e}") from None


def evaluate(expr: Any, names: Mapping[str, float]) -> float:
    """Evaluate a number or an arithmetic expression referencing ``names``.

    Only + - * / **, unary +/-, parentheses, numeric literals, names, and the
    functions min, max, ceil, floor are allowed.
    """
    if isinstance(expr, (int, float)) and not isinstance(expr, bool):
        return float(expr)

    def _eval(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
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

    return _eval(_parse(expr))


def expr_names(expr: Any) -> Set[str]:
    """Variable names referenced by an expression (function names excluded)."""
    tree = _parse(expr)
    funcs = {id(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and id(n) not in funcs}


def expr_literals(expr: Any) -> List[float]:
    tree = _parse(expr)
    return [
        n.value
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool)
    ]


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


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


@dataclass(frozen=True)
class PriceLink:
    series: str  # FRED series id
    usd_per_uom: str  # expression of `series` (the price) and cited values


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
    orders_booked_first: Optional[float] = None  # share of week-0 forecast already booked (mock)
    orders_decay: Optional[float] = None  # booked share multiplier per week of lead time (mock)


@dataclass(frozen=True)
class SopSpec:
    strategy: str  # chase | level
    target_cover_months: float
    capacity_per_week: Optional[float] = None  # in demand-item uom


@dataclass(frozen=True)
class MpsSpec:
    demand_time_fence: int
    planning_time_fence: int


@dataclass(frozen=True)
class ProductConfig:
    id: str
    name: str
    mock: bool
    freq: str
    start: str
    horizon: int
    assumptions: Dict[str, Assumption]  # only the ones this product references
    derived: Dict[str, float]
    items: Dict[str, Item]
    bom: List[BomLine]
    demand: DemandSpec
    variants: Dict[str, Dict[str, str]] = field(default_factory=dict)  # name -> {old: new}
    variant: Optional[str] = None
    sop: Optional[SopSpec] = None
    mps: Optional[MpsSpec] = None
    sop_months: int = 0
    path: Optional[Path] = None

    def names(self) -> Dict[str, float]:
        """All referenced assumption values and derived values, by name."""
        out = {k: a.value for k, a in self.assumptions.items()}
        out.update(self.derived)
        return out


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def _req(d: Mapping[str, Any], key: str, where: str) -> Any:
    if key not in d or d[key] in (None, ""):
        raise ConfigError(f"{where}: missing required field {key!r}")
    return d[key]


class _Resolver:
    """Evaluates config expressions against the registry and records what was used."""

    def __init__(self, registry: Mapping[str, Assumption]):
        self.registry = registry
        self.derived: Dict[str, float] = {}
        self.derived_deps: Dict[str, Set[str]] = {}  # derived name -> registry ids it rests on
        self.used: Set[str] = set()

    def names(self) -> Dict[str, float]:
        out = {k: a.value for k, a in self.registry.items()}
        out.update(self.derived)
        return out

    def _deps(self, expr: Any, where: str, extra: Set[str]) -> Set[str]:
        """Registry ids an expression rests on (through derived values)."""
        bad = [v for v in expr_literals(expr) if v not in ALLOWED_LITERALS]
        if bad:
            raise ConfigError(f"{where}: numeric literal(s) {bad} in {expr!r}; reference an assumption id instead")
        deps: Set[str] = set()
        for n in expr_names(expr) - extra:
            if n in self.derived:
                deps |= self.derived_deps[n]
            elif n in self.registry:
                deps.add(n)
            else:
                raise ConfigError(f"{where}: unknown assumption id {n!r}")
        return deps

    def process(self, expr: Any, where: str, extra: Optional[Mapping[str, float]] = None) -> float:
        extra = dict(extra or {})
        deps = self._deps(expr, where, set(extra))
        uncited = sorted(d for d in deps if self.registry[d].status != "cited")
        if uncited:
            raise ConfigError(f"{where}: process quantities must rest on cited assumptions; not cited: {uncited}")
        self.used |= deps
        return evaluate(expr, {**self.names(), **extra})

    def planning(self, expr: Any, where: str) -> float:
        if expr is None:
            return 0.0
        if isinstance(expr, (int, float)) and not isinstance(expr, bool):
            if expr != 0:
                raise ConfigError(f"{where}: raw number {expr!r}; reference an assumption id instead")
            return 0.0
        self.used |= self._deps(expr, where, set())
        return evaluate(expr, self.names())

    def add_derived(self, name: str, expr: Any) -> None:
        where = f"derived.{name}"
        if name in self.registry or name in self.derived:
            raise ConfigError(f"{where}: name already defined")
        self.derived_deps[name] = self._deps(expr, where, set())
        self.derived[name] = evaluate(expr, self.names())


def _whole(v: float, where: str) -> int:
    if v != int(v) or v < 0:
        raise ConfigError(f"{where}: must be a non-negative whole number (got {v})")
    return int(v)


def _load_planning(raw: Mapping[str, Any], where: str, r: _Resolver) -> Planning:
    ls_raw = raw.get("lot_sizing") or {}
    rule = ls_raw.get("rule", "lot_for_lot")
    if rule not in ("lot_for_lot", "fixed_order_quantity", "periods_of_supply"):
        raise ConfigError(f"{where}: unknown lot sizing rule {rule!r}")
    lot = LotSizing(
        rule=rule,
        quantity=r.planning(ls_raw.get("quantity"), f"{where}.lot_sizing.quantity"),
        periods=_whole(r.planning(ls_raw.get("periods"), f"{where}.lot_sizing.periods"), where) or 1,
        minimum=r.planning(ls_raw.get("minimum"), f"{where}.lot_sizing.minimum"),
        multiple=r.planning(ls_raw.get("multiple"), f"{where}.lot_sizing.multiple"),
    )
    if lot.rule == "fixed_order_quantity" and lot.quantity <= 0:
        raise ConfigError(f"{where}: fixed_order_quantity needs quantity > 0")
    return Planning(
        lead_time=_whole(r.planning(raw.get("lead_time"), f"{where}.lead_time"), f"{where}.lead_time"),
        safety_stock=r.planning(raw.get("safety_stock"), f"{where}.safety_stock"),
        on_hand=r.planning(raw.get("on_hand"), f"{where}.on_hand"),
        scheduled_receipts={
            int(k): r.planning(v, f"{where}.scheduled_receipts[{k}]")
            for k, v in (raw.get("scheduled_receipts") or {}).items()
        },
        lot_sizing=lot,
    )


def load_config(path: "str | Path", registry: "str | Path | None" = None) -> ProductConfig:
    path = Path(path)
    with path.open() as f:
        raw = yaml.safe_load(f)
    reg_path = Path(registry) if registry else (path.parent / raw.get("registry", DEFAULT_REGISTRY))
    return parse_config(raw, load_registry(reg_path), path=path)


def parse_config(raw: Mapping[str, Any], registry: Mapping[str, Assumption], path: Optional[Path] = None) -> ProductConfig:
    prod = _req(raw, "product", "config")
    time = _req(raw, "time", "config")
    pid = _req(prod, "id", "product")
    r = _Resolver(registry)

    for name, expr in (raw.get("derived") or {}).items():
        r.add_derived(name, expr)

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
            r.process(price.usd_per_uom, f"{where}.price", extra={price.series: 1.0})
        items[iid] = Item(
            id=iid,
            name=it.get("name", iid),
            type=typ,
            uom=_req(it, "uom", where),
            planning=_load_planning(it.get("planning") or {}, f"{where}.planning", r),
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
        qty = r.process(expr, where)
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
        base_per_period=r.planning(_req(dm, "base_per_period", "demand"), "demand.base_per_period"),
        annual_growth=r.planning(dm.get("annual_growth"), "demand.annual_growth"),
        seasonal_amplitude=r.planning(dm.get("seasonal_amplitude"), "demand.seasonal_amplitude"),
        seasonal_peak_month=int(r.planning(dm.get("seasonal_peak_month"), "demand.seasonal_peak_month") or 1),
        noise_cv=r.planning(dm.get("noise_cv"), "demand.noise_cv"),
        seed=int(dm.get("seed", 0)),  # RNG seed: structural, not a model number
    )
    orders_raw = dm.get("orders")
    if orders_raw:
        demand = replace(
            demand,
            orders_booked_first=r.planning(_req(orders_raw, "booked_first", "demand.orders"), "demand.orders.booked_first"),
            orders_decay=r.planning(_req(orders_raw, "decay", "demand.orders"), "demand.orders.decay"),
        )

    sop = None
    if raw.get("sop"):
        sr = raw["sop"]
        strategy = _req(sr, "strategy", "sop")
        if strategy not in ("chase", "level"):
            raise ConfigError(f"sop: unknown strategy {strategy!r}")
        cap = sr.get("capacity_per_week")
        sop = SopSpec(
            strategy=strategy,
            target_cover_months=r.planning(_req(sr, "target_cover_months", "sop"), "sop.target_cover_months"),
            capacity_per_week=None if cap is None else r.planning(cap, "sop.capacity_per_week"),
        )

    mps = None
    if raw.get("mps"):
        mr = raw["mps"]
        dtf = _whole(r.planning(mr.get("demand_time_fence"), "mps.demand_time_fence"), "mps.demand_time_fence")
        ptf = _whole(r.planning(mr.get("planning_time_fence"), "mps.planning_time_fence"), "mps.planning_time_fence")
        if ptf < dtf:
            raise ConfigError(f"mps: planning_time_fence ({ptf}) must be >= demand_time_fence ({dtf})")
        mps = MpsSpec(dtf, ptf)
    if (sop is None) != (mps is None):
        raise ConfigError("sop and mps must be configured together")
    sop_months = int(time.get("sop_months", 0))
    if sop is not None and sop_months < 1:
        raise ConfigError("time.sop_months must be >= 1 when sop is configured")

    variants: Dict[str, Dict[str, str]] = {}
    for vname, v in (raw.get("variants") or {}).items():
        subs = {str(k): str(val) for k, val in (_req(v, "substitute", f"variants.{vname}")).items()}
        for old, new in subs.items():
            if old not in items or new not in items:
                raise ConfigError(f"variants.{vname}: unknown item in {old!r} -> {new!r}")
        variants[vname] = subs

    # derived values count as used only when something references them; record their deps too
    for deps in r.derived_deps.values():
        r.used |= deps

    missing = sorted(a for a in r.used if pid not in registry[a].used_in)
    if missing:
        raise ConfigError(f"assumptions used by {pid!r} but not listing it in used_in: {missing}")

    return ProductConfig(
        id=pid,
        name=_req(prod, "name", "product"),
        mock=bool(prod.get("mock", True)),
        freq=_req(time, "freq", "time"),
        start=str(_req(time, "start", "time")),
        horizon=int(_req(time, "horizon", "time")),
        assumptions={k: registry[k] for k in sorted(r.used)},
        derived=dict(r.derived),
        items=items,
        bom=bom,
        demand=demand,
        variants=variants,
        sop=sop,
        mps=mps,
        sop_months=sop_months,
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

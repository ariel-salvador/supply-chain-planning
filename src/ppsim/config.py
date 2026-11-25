"""Load and validate a product config (YAML).

Product configs contain structure (items, BOM, policies) and *references* to the
assumptions registry (``knowledge/assumptions.csv``), never raw model numbers.
The loader enforces the repo's rules:

- process quantities (``derived`` used by the BOM, BOM ``qty_per``, price conversions)
  may only use ``cited`` assumptions. The one exception (ADR 0008): a BOM line marked
  ``basis: mock`` whose component is a ``category: consumable`` item;
- planning and demand numbers must be registry references (only 0 and 1 may be literal);
- the only numeric literals allowed inside expressions are 0 and 1;
- every referenced assumption lists this product in its ``used_in`` column.
"""
from __future__ import annotations

import ast
import math
import operator
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Set, Tuple

import yaml

from .rccp import BorLine, Resource
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
    category: str = "process"  # process | consumable | packaging
    batch_size: Optional[float] = None  # base quantity for an ERP bill of materials


@dataclass(frozen=True)
class BomLine:
    parent: str
    component: str
    qty_per: float
    expr: str  # original expression, kept for traceability
    basis: str = "cited"  # cited | mock (mock only for consumables, ADR 0008)


@dataclass(frozen=True)
class Party:
    """A company or vendor. Must be fictional (public-safe rule)."""
    id: str
    name: str
    supplies: tuple = ()


@dataclass(frozen=True)
class Quote:
    """One supplier's RFQ response for the items it bids on (all MOCK, ADR 0013).

    ``price_index`` multiplies the item's should-cost target price; ``lead_time_delta``
    is weeks relative to the item's planning lead time (may be negative).
    """
    price_index: float
    lead_time_delta: float
    moq_weeks: float
    quality_ppm: float
    otif: float
    lead_time_sigma: float
    short_ship_rate: float


@dataclass(frozen=True)
class Supplier:
    """A bidder in the supplier master. Must be fictional (public-safe rule)."""
    id: str
    name: str
    supplies: tuple
    quote: Quote
    lane: str
    incoterm: str
    risk_tier: str
    archetype: str = ""


@dataclass(frozen=True)
class Lane:
    """An inbound lane: freight and duty as shares of ex-works cost."""
    id: str
    freight_pct: float
    duty_pct: float


@dataclass(frozen=True)
class SourcingSpec:
    """Sourcing policy: RFQ weights, should-cost build-up, landed cost and risk inputs."""
    weights: Dict[str, float]
    risk_scores: Dict[str, float]
    conversion_pct: float
    margin_pct: float
    material_base: Dict[str, float]
    lanes: Dict[str, Lane]
    carrying_cost_rate: float
    quality_cost_multiple: float
    scorecard_periods: int
    price_drift_cv: float
    short_ship_fraction: float
    dual_source_split: float
    disruption_prob_base: float
    disruption_weeks: float
    forward_buy_weeks: float
    service_level_z: float
    seed: int = 0


RFQ_CRITERIA = ("price", "lead_time", "quality", "risk")

# Incoterm -> (seller pays inbound freight, seller pays import duty). Used by the TCO
# build-up: anything the seller does not pay is a buyer cost on top of the quote.
INCOTERMS = {
    "EXW": (False, False),
    "FOB": (False, False),
    "CIF": (True, False),
    "DAP": (True, False),
    "DDP": (True, True),
}


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
class RccpSpec:
    level: bool = False
    max_pull_forward: int = 0  # buckets a lot may be pulled earlier when leveling


@dataclass(frozen=True)
class PurchasingSpec:
    price_window_years: float


@dataclass(frozen=True)
class CustomerProfile:
    """How one (fictional) customer orders and pays, for the MOCK history."""
    id: str
    share: float        # share of total demand
    every_weeks: int    # order interval
    pay_days: float     # average days from invoice to payment


@dataclass(frozen=True)
class HistoryEvent:
    """A named disruption in the MOCK history. Dates are structural, sizes are ids."""
    kind: str           # contamination | supplier_outage | demand_spike
    start: str          # ISO date inside the history window
    weeks: int = 1
    size: float = 0.0   # contamination: batches lost; demand_spike: uplift
    target: str = ""    # supplier (outage) or customer (spike) id
    item: str = ""      # outage: the item whose supply stops
    note: str = ""


HISTORY_EVENTS = ("contamination", "supplier_outage", "demand_spike")


@dataclass(frozen=True)
class HistorySpec:
    """Three years of MOCK operating history (ADR 0018)."""
    start: str
    end: str
    seed: int
    conversion_usd_per_kg: float
    gross_margin: float
    order_lead_weeks: int
    customer_terms_days: float
    vendor_terms_days: float
    pay_days_cv: float
    min_cover_weeks: float
    safety_cover_weeks: float
    customers: Dict[str, CustomerProfile]
    events: Tuple[HistoryEvent, ...] = ()


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
    company: Optional[Party] = None
    vendors: Dict[str, Party] = field(default_factory=dict)
    customers: Dict[str, Party] = field(default_factory=dict)
    resources: Dict[str, Resource] = field(default_factory=dict)
    bill_of_resources: List[BorLine] = field(default_factory=list)
    rccp: Optional[RccpSpec] = None
    purchasing: Optional[PurchasingSpec] = None
    suppliers: Dict[str, Supplier] = field(default_factory=dict)
    sourcing: Optional[SourcingSpec] = None
    history: Optional[HistorySpec] = None
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
            if expr not in ALLOWED_LITERALS:
                raise ConfigError(f"{where}: raw number {expr!r}; reference an assumption id instead")
            return float(expr)
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


def _incoterm(value: Any, where: str) -> str:
    code = str(value).upper()
    if code not in INCOTERMS:
        raise ConfigError(f"{where}: unknown incoterm {value!r}; known: {sorted(INCOTERMS)}")
    return code


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
        category = it.get("category", "process")
        if category not in ("process", "consumable", "packaging"):
            raise ConfigError(f"{where}: unknown category {category!r}")
        items[iid] = Item(
            id=iid,
            name=it.get("name", iid),
            type=typ,
            uom=_req(it, "uom", where),
            planning=_load_planning(it.get("planning") or {}, f"{where}.planning", r),
            price=price,
            category=category,
            batch_size=None if it.get("batch_size") is None else r.planning(it["batch_size"], f"{where}.batch_size"),
        )

    bom = []
    for i, line in enumerate(raw.get("bom") or []):
        where = f"bom[{i}]"
        parent, comp = _req(line, "parent", where), _req(line, "component", where)
        for ref in (parent, comp):
            if ref not in items:
                raise ConfigError(f"{where}: unknown item {ref!r}")
        expr = _req(line, "qty_per", where)
        basis = line.get("basis", "cited")
        if basis == "mock":
            if items[comp].category != "consumable":
                raise ConfigError(f"{where}: basis: mock is only allowed for consumable components (ADR 0008)")
            qty = r.planning(expr, where)
        elif basis == "cited":
            qty = r.process(expr, where)
        else:
            raise ConfigError(f"{where}: basis must be 'cited' or 'mock'")
        if qty <= 0:
            raise ConfigError(f"{where}: qty_per must be > 0 (got {qty})")
        bom.append(BomLine(parent, comp, qty, str(expr), basis))

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

    def _party(raw_p: Mapping[str, Any], where: str) -> Party:
        if raw_p.get("fictional") is not True:
            raise ConfigError(f"{where}: must be marked 'fictional: true' (public-safe rule)")
        supplies = tuple(raw_p.get("supplies") or ())
        for i in supplies:
            if i not in items or items[i].type != "purchased":
                raise ConfigError(f"{where}: supplies {i!r}, which is not a purchased item")
        return Party(_req(raw_p, "id", where), _req(raw_p, "name", where), supplies)

    company = _party(raw["company"], "company") if raw.get("company") else None
    def _parties(key: str) -> Dict[str, Party]:
        out: Dict[str, Party] = {}
        for i, v in enumerate(raw.get(key) or []):
            p = _party(v, f"{key}[{i}]")
            if p.id in out:
                raise ConfigError(f"{key}[{i}]: duplicate id {p.id!r}")
            out[p.id] = p
        return out

    vendors = _parties("vendors")
    customers = _parties("customers")

    resources: Dict[str, Resource] = {}
    for i, rr in enumerate(raw.get("resources") or []):
        where = f"resources[{i}]"
        rid = _req(rr, "id", where)
        if rid in resources:
            raise ConfigError(f"{where}: duplicate id {rid!r}")
        resources[rid] = Resource(
            id=rid,
            name=rr.get("name", rid),
            units=r.planning(_req(rr, "units", where), f"{where}.units"),
            hours_per_week=r.process(_req(rr, "hours_per_week", where), f"{where}.hours_per_week"),
            availability=r.process(_req(rr, "availability", where), f"{where}.availability"),
        )
    bor: List[BorLine] = []
    for i, bl in enumerate(raw.get("bill_of_resources") or []):
        where = f"bill_of_resources[{i}]"
        item, res_id = _req(bl, "item", where), _req(bl, "resource", where)
        if item not in items:
            raise ConfigError(f"{where}: unknown item {item!r}")
        if res_id not in resources:
            raise ConfigError(f"{where}: unknown resource {res_id!r}")
        hpu = r.process(_req(bl, "hours_per_unit", where), where)
        if hpu <= 0:
            raise ConfigError(f"{where}: hours_per_unit must be > 0")
        bor.append(BorLine(item, res_id, hpu))
    rccp = None
    if raw.get("rccp") is not None:
        rc = raw["rccp"] or {}
        if not bor:
            raise ConfigError("rccp: needs a bill_of_resources")
        rccp = RccpSpec(
            level=bool(rc.get("level", False)),
            max_pull_forward=_whole(r.planning(rc.get("max_pull_forward"), "rccp.max_pull_forward"), "rccp.max_pull_forward"),
        )

    purchasing = None
    if raw.get("purchasing"):
        pr = raw["purchasing"]
        purchasing = PurchasingSpec(
            price_window_years=r.planning(_req(pr, "price_window_years", "purchasing"), "purchasing.price_window_years"),
        )

    # ---- sourcing: supplier master + RFQ / should-cost / risk policy (M6) ----
    purchased = {i for i, it in items.items() if it.type == "purchased"}
    suppliers: Dict[str, Supplier] = {}
    for i, sp in enumerate(raw.get("suppliers") or []):
        where = f"suppliers[{i}]"
        sid = _req(sp, "id", where)
        if sid in suppliers:
            raise ConfigError(f"{where}: duplicate id {sid!r}")
        if sp.get("fictional") is not True:
            raise ConfigError(f"{where}: must be marked 'fictional: true' (public-safe rule)")
        supplies = tuple(sp.get("supplies") or ())
        if not supplies:
            raise ConfigError(f"{where}: must supply at least one purchased item")
        for iid in supplies:
            if iid not in purchased:
                raise ConfigError(f"{where}: supplies {iid!r}, which is not a purchased item")
        q = _req(sp, "quote", where)
        suppliers[sid] = Supplier(
            id=sid,
            name=_req(sp, "name", where),
            supplies=supplies,
            quote=Quote(
                price_index=r.planning(_req(q, "price_index", f"{where}.quote"), f"{where}.quote.price_index"),
                lead_time_delta=r.planning(q.get("lead_time_delta"), f"{where}.quote.lead_time_delta"),
                moq_weeks=r.planning(_req(q, "moq_weeks", f"{where}.quote"), f"{where}.quote.moq_weeks"),
                quality_ppm=r.planning(_req(q, "quality_ppm", f"{where}.quote"), f"{where}.quote.quality_ppm"),
                otif=r.planning(_req(q, "otif", f"{where}.quote"), f"{where}.quote.otif"),
                lead_time_sigma=r.planning(q.get("lead_time_sigma"), f"{where}.quote.lead_time_sigma"),
                short_ship_rate=r.planning(q.get("short_ship_rate"), f"{where}.quote.short_ship_rate"),
            ),
            lane=str(_req(sp, "lane", where)),
            incoterm=_incoterm(_req(sp, "incoterm", where), where),
            risk_tier=str(_req(sp, "risk_tier", where)),
            archetype=str(sp.get("archetype", "")),
        )

    sourcing = None
    if raw.get("sourcing"):
        sr = raw["sourcing"]
        if not suppliers:
            raise ConfigError("sourcing: needs a suppliers block")
        w_raw = _req(sr, "weights", "sourcing")
        if set(w_raw) != set(RFQ_CRITERIA):
            raise ConfigError(f"sourcing.weights: keys must be exactly {list(RFQ_CRITERIA)}, got {sorted(w_raw)}")
        weights = {k: r.planning(w_raw[k], f"sourcing.weights.{k}") for k in RFQ_CRITERIA}
        if any(v < 0 for v in weights.values()):
            raise ConfigError("sourcing.weights: weights must be >= 0")
        if abs(sum(weights.values()) - 1.0) > 1e-9:
            raise ConfigError(f"sourcing.weights: must sum to 1 (got {sum(weights.values()):g})")
        risk_scores = {
            str(k): r.planning(v, f"sourcing.risk_scores.{k}")
            for k, v in (_req(sr, "risk_scores", "sourcing")).items()
        }
        lanes: Dict[str, Lane] = {}
        for lid, lv in (_req(sr, "lanes", "sourcing")).items():
            lanes[str(lid)] = Lane(
                id=str(lid),
                freight_pct=r.planning(lv.get("freight_pct"), f"sourcing.lanes.{lid}.freight_pct"),
                duty_pct=r.planning(lv.get("duty_pct"), f"sourcing.lanes.{lid}.duty_pct"),
            )
        sc = _req(sr, "should_cost", "sourcing")
        base_raw = _req(sc, "material_base", "sourcing.should_cost")
        material_base = {}
        for iid, expr in base_raw.items():
            if iid not in purchased:
                raise ConfigError(f"sourcing.should_cost.material_base: {iid!r} is not a purchased item")
            material_base[str(iid)] = r.planning(expr, f"sourcing.should_cost.material_base.{iid}")
        quoted = sorted({i for sp in suppliers.values() for i in sp.supplies})
        no_base = [i for i in quoted if i not in material_base]
        if no_base:
            raise ConfigError(f"sourcing.should_cost.material_base: missing a base cost for quoted item(s) {no_base}")
        for sp in suppliers.values():
            if sp.lane not in lanes:
                raise ConfigError(f"suppliers.{sp.id}: unknown lane {sp.lane!r}; known: {sorted(lanes)}")
            if sp.risk_tier not in risk_scores:
                raise ConfigError(f"suppliers.{sp.id}: unknown risk_tier {sp.risk_tier!r}; known: {sorted(risk_scores)}")
        sourcing = SourcingSpec(
            weights=weights,
            risk_scores=risk_scores,
            conversion_pct=r.planning(_req(sc, "conversion_pct", "sourcing.should_cost"), "sourcing.should_cost.conversion_pct"),
            margin_pct=r.planning(_req(sc, "margin_pct", "sourcing.should_cost"), "sourcing.should_cost.margin_pct"),
            material_base=material_base,
            lanes=lanes,
            carrying_cost_rate=r.planning(_req(sr, "carrying_cost_rate", "sourcing"), "sourcing.carrying_cost_rate"),
            quality_cost_multiple=r.planning(_req(sr, "quality_cost_multiple", "sourcing"), "sourcing.quality_cost_multiple"),
            scorecard_periods=_whole(r.planning(_req(sr, "scorecard_periods", "sourcing"), "sourcing.scorecard_periods"), "sourcing.scorecard_periods"),
            price_drift_cv=r.planning(sr.get("price_drift_cv"), "sourcing.price_drift_cv"),
            short_ship_fraction=r.planning(_req(sr, "short_ship_fraction", "sourcing"), "sourcing.short_ship_fraction"),
            dual_source_split=r.planning(_req(sr, "dual_source_split", "sourcing"), "sourcing.dual_source_split"),
            disruption_prob_base=r.planning(_req(sr, "disruption_prob_base", "sourcing"), "sourcing.disruption_prob_base"),
            disruption_weeks=r.planning(_req(sr, "disruption_weeks", "sourcing"), "sourcing.disruption_weeks"),
            forward_buy_weeks=r.planning(_req(sr, "forward_buy_weeks", "sourcing"), "sourcing.forward_buy_weeks"),
            service_level_z=r.planning(_req(sr, "service_level_z", "sourcing"), "sourcing.service_level_z"),
            seed=int(sr.get("seed", 0)),  # RNG seed: structural, not a model number
        )
        if not 0.0 <= sourcing.dual_source_split <= 0.5:
            raise ConfigError("sourcing.dual_source_split: must be between 0 and 0.5")
    elif suppliers:
        raise ConfigError("suppliers: needs a sourcing block (weights, should_cost, lanes)")

    history = _load_history(raw.get("history"), r, customers, suppliers, items) if raw.get("history") else None

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
        company=company,
        vendors=vendors,
        customers=customers,
        resources=resources,
        bill_of_resources=bor,
        rccp=rccp,
        purchasing=purchasing,
        suppliers=suppliers,
        sourcing=sourcing,
        history=history,
        path=path,
    )


def _iso_date(v: Any, where: str) -> str:
    import datetime as _dt
    try:
        return _dt.date.fromisoformat(str(v)).isoformat()
    except ValueError:
        raise ConfigError(f"{where}: not an ISO date: {v!r}") from None


def _load_history(h: Mapping[str, Any], r: "_Resolver", customers: Mapping[str, Party],
                  suppliers: Mapping[str, Supplier], items: Mapping[str, Item]) -> HistorySpec:
    where = "history"
    start, end = _iso_date(_req(h, "start", where), f"{where}.start"), _iso_date(_req(h, "end", where), f"{where}.end")
    if end <= start:
        raise ConfigError(f"{where}: end must be after start")
    profiles: Dict[str, CustomerProfile] = {}
    for cid, cp in (_req(h, "customers", where)).items():
        w = f"{where}.customers.{cid}"
        if cid not in customers:
            raise ConfigError(f"{w}: unknown customer {cid!r}")
        profiles[cid] = CustomerProfile(
            id=cid,
            share=r.planning(_req(cp, "share", w), f"{w}.share"),
            every_weeks=_whole(r.planning(_req(cp, "every_weeks", w), f"{w}.every_weeks"), f"{w}.every_weeks") or 1,
            pay_days=r.planning(_req(cp, "pay_days", w), f"{w}.pay_days"),
        )
    total = sum(p.share for p in profiles.values())
    if abs(total - 1.0) > 1e-9:
        raise ConfigError(f"{where}.customers: shares must sum to 1 (got {total:g})")
    events = []
    for i, ev in enumerate(h.get("events") or []):
        w = f"{where}.events[{i}]"
        kind = _req(ev, "kind", w)
        if kind not in HISTORY_EVENTS:
            raise ConfigError(f"{w}: unknown kind {kind!r}; known: {list(HISTORY_EVENTS)}")
        e = HistoryEvent(
            kind=kind,
            start=_iso_date(_req(ev, "start", w), f"{w}.start"),
            weeks=_whole(r.planning(ev.get("weeks", 1), f"{w}.weeks"), f"{w}.weeks") or 1,
            size=r.planning(ev.get("size"), f"{w}.size"),
            target=str(ev.get("target", "")),
            item=str(ev.get("item", "")),
            note=str(ev.get("note", "")),
        )
        if not start <= e.start <= end:
            raise ConfigError(f"{w}: start {e.start} is outside the history window")
        if kind == "supplier_outage" and (e.target not in suppliers or e.item not in suppliers[e.target].supplies):
            raise ConfigError(f"{w}: outage needs a supplier 'target' that supplies 'item'")
        if kind == "demand_spike" and e.target not in profiles:
            raise ConfigError(f"{w}: spike needs a customer 'target'")
        events.append(e)
    return HistorySpec(
        start=start,
        end=end,
        seed=int(h.get("seed", 0)),  # RNG seed: structural
        conversion_usd_per_kg=r.planning(_req(h, "conversion_usd_per_kg", where), f"{where}.conversion_usd_per_kg"),
        gross_margin=r.planning(_req(h, "gross_margin", where), f"{where}.gross_margin"),
        order_lead_weeks=_whole(r.planning(_req(h, "order_lead_weeks", where), f"{where}.order_lead_weeks"), where),
        customer_terms_days=r.planning(_req(h, "customer_terms_days", where), f"{where}.customer_terms_days"),
        vendor_terms_days=r.planning(_req(h, "vendor_terms_days", where), f"{where}.vendor_terms_days"),
        pay_days_cv=r.planning(h.get("pay_days_cv"), f"{where}.pay_days_cv"),
        min_cover_weeks=r.planning(_req(h, "min_cover_weeks", where), f"{where}.min_cover_weeks"),
        safety_cover_weeks=r.planning(_req(h, "safety_cover_weeks", where), f"{where}.safety_cover_weeks"),
        customers=profiles,
        events=tuple(events),
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

# Case 1 — rBLG whey protein (mock plant): sources and derivations

**Status:** mock plant. Process parameters are cited from public literature; demand,
inventory, lot sizes, safety stock and non-process lead times are planning
assumptions (mock). Nothing here comes from any company's internal data.

## Process basis

Base process = **scenario 1** of Behm et al. (2022): *Trichoderma reesei* fed-batch
fermentation secreting rBLG, filter press, microfiltration, ultra/diafiltration, spray
drying. Glucose feed. The `sucrose` variant is their scenario 2 (same process, sucrose
feed). The paper is an ex-ante LCA design study (VTT and Fonterra, building on NREL's
cellulase process in Humbird et al. 2011). It is not operating plant data.

| Parameter | Value | Where |
|---|---|---|
| Final rBLG titre | 50 g/L | Behm 2022 §2.4 |
| rBLG share of secreted protein | 90 % | §2.4 |
| Protein yield on sugar (base case) | 0.223 g/g | §2.4 |
| Final fungal biomass | 30 g/L | §2.4 |
| Production time / offline time per batch | 120 h / 24 h | §2.4 |
| Main bioreactor volume | 300 m³ (seed 0.3 / 3 / 30 m³) | §2.4 |
| Microfiltration permeate recovery | 97.5 % | Online Resource Data 1; §2.4 |
| UF/DF protein retention | 100 % (assumed by the authors) | Online Resource Data 1 |
| rBLG content of final product | 85.8 % (90 % purity × 95 % DM) | §2.1 |

## Derivations (in `product.yaml → derived`)

- **Powder → fermentation:** `rblg_kg_per_kg_product = 0.858 / 0.975 = 0.880` kg rBLG
  secreted per kg powder. This assumes no loss in UF/DF or drying, which matches the
  paper's own assumptions.
- **Fermentation → sugar:** `sugar_kg_per_kg_rblg = 1 / (0.223 × 0.90) = 4.98` kg.
  *Interpretation:* §2.4 gives 0.223 as "g protein per gram of sugar" in the same
  paragraph as the total-protein productivity (0.46 g/L/h) and the rBLG productivity
  (0.42 g/L/h). We read it as **total** secreted protein, so we divide by the 90 % rBLG
  share. If it actually meant rBLG only, sugar use would be 4.48 kg/kg (about 10 %
  lower). We picked the conservative reading.
- **Fermentation lead time:** a 120 h + 24 h = 144 h cycle fits in one weekly bucket.
  The seed train and DSP durations aren't reported, so they're left out of this lead
  time. The powder item's 1-week lead time is an assumption.
- **Corn → glucose (pricing only):** EPA AP-42 §9.9.7.1 says a 25 kg (56 lb) bushel
  yields about 14 kg (32 lb) of starch. Hydrolysis adds water, so starch gains mass by
  M(C₆H₁₂O₆)/M(C₆H₁₀O₅) = 180.156/162.141 = 1.111. That gives
  `corn_kg_per_glucose_kg = (25/14)/1.111 = 1.607`. This is a **theoretical minimum**
  (100 % hydrolysis, no refining losses). The resulting "glucose price" counts only the
  corn. It excludes wet-milling and refining costs, and it isn't a market dextrose price.
- **Sucrose price:** FRED `PSUGAISAUSDM` is in US cents/lb. USD/kg = value / 100 /
  0.45359237 (NIST exact lb definition).

## External price series (fetched at runtime, not committed)

| Series | Title | Units | Provider |
|---|---|---|---|
| `PMAIZMTUSDM` | Global price of Corn | USD / metric ton, monthly, NSA | IMF Primary Commodity Prices via FRED |
| `PSUGAISAUSDM` | Global price of Sugar, No. 11, World | US cents / lb, monthly, NSA | IMF Primary Commodity Prices via FRED |

The data is copyrighted by the IMF and must be cited. Any chart that uses it should
read: *"Source: International Monetary Fund, retrieved from FRED, Federal Reserve Bank
of St. Louis."*

## Known gaps (not yet sourced, so not modelled)

- Bioreactor **working volume / fill fraction**. Without it we can't size batches
  (`batch_rblg_kg_at_full_volume = 15,000 kg` is an upper bound only). This blocks batch
  lot sizing and RCCP.
- Seed-train and DSP **cycle times**.
- Nitrogen source (NH₃), corn steep liquor, and other media per kg. Behm §2.4 and its
  Table 2 point to Humbird et al. (2011) for these.
- Separate yield on sucrose. The paper applies the same process to both sugars.

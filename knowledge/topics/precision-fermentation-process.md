# Precision-fermentation process: rBLG by *Trichoderma reesei* (Case 1 basis)

Case 1 is a **mock plant**. Its process numbers come mainly from one open-access, peer-reviewed
design study (note: `notes/behm-2022-rblg-lca.md`), an *ex-ante model* by VTT and
Fonterra R&D that builds on NREL's cellulase process. It isn't operating plant data.
Planning numbers (inventory, lot sizes, demand) are [mock].

## Process train (Behm 2022 scenario 1)

Seed train 0.3 → 3 → 30 m³ (10 % inoculum per step) [source: `seed_inoculum_fraction`]
→ 300 m³ fed-batch main reactors [source: `main_bioreactor_volume`], 28 °C, glucose feed
→ filter press (removes fungal biomass, which is sold as feed)
→ 0.2 µm microfiltration → 10 kDa UF/DF → spray drying (see `tff-scale-up.md`).

| Quantity | Value | Id | Tag |
|---|---|---|---|
| Final rBLG titre | 50 g/L (100 favourable case) | `final_titre_rblg` | [source] |
| rBLG share of secreted protein | 90 % | `rblg_fraction_of_secreted_protein` | [source] |
| Protein yield on sugar | 0.223 g/g | `protein_yield_on_sugar` | [source] |
| Final fungal biomass | 30 g/L (10 favourable case) | `final_fungal_biomass` | [source] |
| Production + offline time | 120 h + 24 h | `production_time`, `turnaround_time` | [source] |
| Final working volume | 80 % of vessel (fed-batch from 50 %) | `max_working_volume_fraction` | [source: Humbird 2011] |
| Offline time, reference design | 48 h (Behm uses 24 h) | `turnaround_time` high | [source: Humbird 2011] |
| Seed vessel cycle | 48 h; 4 trains of 3 for 9 reactors | `seed_vessel_cycle_time` | [source: Humbird 2011] |
| MF protein recovery | 97.5 % | `mf_permeate_recovery` | [source] |
| rBLG in final product | 85.8 % (90 % purity × 95 % DM) | `rblg_content_of_product` | [source] |

## How the BOM is derived (`products/blg_whey_protein.yaml → derived`)

- **Powder → fermentation:** 0.858 / 0.975 = **0.880 kg rBLG secreted per kg powder**
  [estimate, derived from cited values]. It assumes no UF/DF or drying loss, as the paper
  does.
- **Fermentation → sugar:** 1 / (0.223 × 0.90) = **4.98 kg sugar per kg rBLG**
  [estimate, derived]. The yield is read as total secreted protein (ADR 0004). An
  rBLG-only reading gives 4.48.
- **Per kg powder:** 0.880 × 4.98 = **4.38 kg glucose or sucrose** [estimate, derived].
- **Fermentation lead time:** a 144 h cycle is one weekly bucket [estimate, derived]. Seed
  and DSP durations aren't sourced.
- **Batch size:** 300 m³ × 80 % × 50 g/L = **12,000 kg rBLG per batch**
  [estimate, derived]. This matches Humbird's stated 12,000 kg/batch [source]. MRP plans
  fermentation in whole batches (lot multiple).
- **Sucrose variant** = Behm scenario 2: same process, with sucrose as the carbon source.
  The paper doesn't give a separate sucrose yield.

## Sensitivities worth modelling later

Behm §3.3: carbon footprint is most sensitive to final titre, fungal biomass and sugar
selectivity to CO₂, all through yield on sugar. Production time and power matter less.

## Gaps (see `backlog.md`)

- **DSP cycle times and capacity** (filter press, MF, UF/DF, dryer). Neither Behm nor
  Humbird gives them; Humbird has no DSP at all. Until sourced, RCCP treats the
  fermenters as the constraint (ADR 0006).
- Behm's 24 h vs Humbird's 48 h offline time. Both are recorded, with Behm as base.
- Media quantities per kg rBLG: Humbird Table 20 gives concentrations (note), but these
  are not in the BOM yet.

Notes: `notes/behm-2022-rblg-lca.md`, `notes/humbird-2011-nrel-biochemical-design.md`.

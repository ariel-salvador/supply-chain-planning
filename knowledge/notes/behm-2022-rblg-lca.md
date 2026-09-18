# Behm et al. 2022: rBLG by *T. reesei*, carbon and water footprint vs dairy

- **Citation:** Behm K, Nappa M, Aro N, Welman A, Ledgard S, Suomalainen M, Hill J (2022).
  Comparison of carbon footprint and water scarcity footprint of milk protein produced by
  cellular agriculture and the dairy industry. *Int J Life Cycle Assess* 27(8):1017–1034.
- **URL:** https://doi.org/10.1007/s11367-022-02087-0 (open access, CC BY 4.0)
- **Supplement:** Online Resource 1 (Data 1: DSP mass/energy details; Data 2: LCI datasets;
  Data 3: result tables)
- **Retrieved:** 2026-09-18
- **Reliability:** peer-reviewed. It is an *ex-ante design model* (VTT with Fonterra R&D,
  using NREL's cellulase process from Humbird et al. 2011), not measured plant data.
- **reviewed:** false

## Key facts (paraphrased, with locations)

- Host is *T. reesei*, fed-batch, 28 °C. Seed train of 0.3 → 3 → 30 m³ feeds 300 m³ main
  reactors, each seed step inoculated at 10 %. (§2.4)
- Each batch runs 120 h of production plus 24 h offline for draining, cleaning and
  refilling. (§2.4)
- Final titre is 50 g/L of the single target protein, conservative compared with the
  >100 g/L mixed secreted protein reported for engineered strains. rBLG is 90 % of
  secreted protein. (§2.4)
- Sugar goes 50 % to CO₂ (molar). Final biomass is 30 g/L. Total protein productivity is
  0.46 g/L/h and rBLG is 0.42 g/L/h. The base-case yield is **0.223 g protein per g
  sugar**. (§2.4)
- NH₃, SO₂ and sugar follow stoichiometry for biomass and protein. Corn steep liquor,
  other nutrients and antifoam come from Humbird 2011 (Table 2). (§2.4)
- Aeration power is about 2 kWh/kg O₂ (citing Humbird 2017). Cooling electricity is
  0.259 kW per kW of heat removed. (§2.4)
- CIP after each batch: 1 % NaOH at 75 °C, 100 L per m³ of reactor, then a hot-water
  rinse. 1 % HNO₃ every 3rd batch. (§2.4)
- DSP: filter press (biomass cake 40 % DM), then 0.2 µm microfiltration (97.5 % permeate
  recovery), then 10 kDa UF/DF (100 % protein retention, diavolume 5), then spray drying
  to 95 % DM. (§2.4, Data 1)
- The product is 90 % pure at 95 % DM, so it is 85.8 % rBLG. Scenario 4 adds SMB
  chromatography and reaches 90.3 %. (§2.1)
- Scenarios: (1) glucose, biomass sold as feed; (2) sucrose; (3) biomass as waste;
  (4) extra chromatography. Locations: NZ, DE, US-Alabama, AU-Victoria. (§2.3)
- Results: 5.5–17.6 t CO₂e per t protein. Sugar and electricity dominate. The results
  are sensitive to titre and yield on sugar. (Abstract, §3)

## Used in

`products/blg_whey_protein.yaml` via `knowledge/assumptions.csv` ids: titre, rBLG share, yield, cycle times,
reactor volume, MF recovery, product rBLG content (plus DSP rows for later milestones).

## Open questions

- Is 0.223 g/g total protein or rBLG only? We assume total (ADR 0004).
- Working volume of the 300 m³ vessel isn't stated. Check Humbird 2011.

# Humbird et al. 2011: NREL biochemical ethanol design (Area 400: on-site *T. reesei* enzyme production)

- **Citation:** Humbird D, Davis R, Tao L, Kinchin C, Hsu D, Aden A, Schoen P, Lukas J,
  Olthof B, Worley M, Sexton D, Dudgeon D (2011). *Process Design and Economics for
  Biochemical Conversion of Lignocellulosic Biomass to Ethanol: Dilute-Acid Pretreatment
  and Enzymatic Hydrolysis of Corn Stover.* NREL Technical Report NREL/TP-5100-47764.
- **URL:** https://www.nrel.gov/docs/fy11osti/47764.pdf (mirror: https://www.osti.gov/servlets/purl/1013269).
  US DOE-funded technical report, publicly available.
- **Retrieved:** 2026-09-18 (via the OSTI mirror; nrel.gov didn't resolve from the dev machine)
- **Reliability:** national-lab design report, peer reviewed as a report. Area 400 was
  designed without input from enzyme companies (the authors say so, p. 37). It's a
  rudimentary design for costing, not an operating plant. Behm et al. 2022 base their
  rBLG bioreactor design on this section.
- **reviewed:** false

## Key facts (paraphrased, with locations)

- **Vessel:** 300 m³ total, H/D 2 (11.5 m × 5.75 m), 28 °C, 1 atm, 316SS, 800 hp
  agitator (Table 19, p. 39).
- **Working volume:** fed-batch starts at **50 %** of vessel volume and ends at
  **80 %** (Table 18, p. 37; text p. 37; Table 19 "maximum working volume 80 %").
- **Titre at harvest** is 50 g/L total protein (Table 18).
- **Cycle:** 24 h cell growth + 96 h protein production = **120 h online**, plus
  **48 h offline** for draining, cleaning and refilling, making **168 h (one week)**
  (Table 18, p. 37). Behm 2022 kept the 120 h but used 24 h offline.
- **Output:** one reactor makes **12,000 kg protein per batch** (per week), i.e.
  71.4 kg/h and 0.30 g/L/h (p. 37). That's consistent with 300 m³ × 80 % × 50 g/L.
- The design needs **9 production reactors** for 490 kg/h of protein (p. 37).
- **Yield:** 0.24 kg total enzyme protein per kg glucose (Table 18). Molar selectivity
  is 31 % protein, 4 % cell mass and 65 % CO₂ (p. 38).
- **Seed train:** 4 trains of 3 seed vessels (0.3, 3 and 30 m³, each 10 % of the next).
  Each seed vessel has a **2-day cycle** including cleaning and sterilization, covering
  growth only. Four trains serve reactors on a 7-day cycle (p. 39).
- **Nutrients:** NH₃ is stoichiometric (about 7 g/L) and SO₂ about 0.6 g/L. Also CSL 1 %
  w/w, corn oil 0.1 % v/v, (NH₄)₂SO₄ 1.4 g/L, KH₂PO₄ 2.0 g/L, MgSO₄ 0.3 g/L,
  CaCl₂ 0.4 g/L, Tween 80 0.2 g/L (Table 20, p. 39, from Schell et al.).
- **Electricity:** air compressor 1,408 kW, agitators 2,326 kW, chiller share 1,587 kW
  for the whole Area 400 (Table 21, p. 40).
- **Plant availability:** 8,410 operating h/yr = 96 % uptime. This is the design basis
  for the whole biorefinery (§2.1, p. 11).
- **Downstream:** none. The enzyme broth goes straight to hydrolysis, so the report gives
  no DSP cycle times.

## Used in

`max_working_volume_fraction`, `initial_working_volume_fraction`,
`humbird_protein_per_batch` (cross-check), `seed_vessel_cycle_time`, `humbird_seed_trains`,
`humbird_production_reactors`, `plant_uptime`, `humbird_protein_yield_on_glucose`, and the
`high` bound of `turnaround_time`. Media: `nh3_conc`, `ammonium_sulfate_conc`,
`potassium_phosphate_conc`, `magnesium_sulfate_conc`, `calcium_chloride_conc` (Table 20;
applied per litre of final working volume, so kg per kg rBLG = conc / titre).

## Open questions

- Behm's 24 h offline versus Humbird's 48 h: Behm doesn't say why it's shorter. We
  keep Behm (24 h) as base, and 48 h as the high case.
- Uptime of 96 % is for an ethanol biorefinery. Food-grade protein plants may differ.

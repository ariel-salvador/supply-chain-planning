# Backlog: open questions (prioritized)

P1 blocks the next milestone, P2 improves fidelity, P3 is nice to have.

## P1
- [x] ~~Bioreactor working volume~~: 80 % final / 50 % initial (Humbird 2011). Batch = 12,000 kg rBLG.
- [x] ~~Seed-train cycle time~~: 48 h per seed vessel, 4 trains per 9 reactors (Humbird 2011).
- [ ] **DSP cycle times / throughput** (filter press, MF, UF/DF, spray dryer). Not in
  Behm or Humbird. Cunniffe et al. 2025 (FDH TEA, CC BY) was checked and has no DSP
  times. Next: open-access whey-protein UF/DF scale-up or SuperPro-based
  recombinant-protein TEAs.
- [ ] **UF/DF flux, membrane area, dryer evaporation capacity** for DSP capacity
  (see `topics/tff-scale-up.md`).

## P2
- [ ] Behm 0.223 g/g: total protein or rBLG only? (ADR 0004; total, now supported by the Humbird cross-check.)
- [ ] Offline time: Behm 24 h vs Humbird 48 h. Is there a source for modern CIP/SIP turnaround at 300 m³?
- [ ] Plant uptime for a food-grade protein plant (Humbird's 96 % is for an ethanol biorefinery).
- [ ] A public **dextrose / glucose syrup price** or a published wet-milling cost, so
  glucose isn't priced at corn content only (M3).
- [ ] Media inputs per kg: NH₃, corn steep liquor, nutrients (Humbird 2011 via Behm
  Table 2) to add purchased items to the BOM.
- [ ] Sucrose uptake by *T. reesei*: does scenario 2 imply an engineered strain or an
  invertase step? Is the yield the same?
- [ ] Unfavourable-side sensitivity values (Behm Fig. 4) for `low`/`high` ranges.

## P3
- [ ] Filter-press cake dry content (40 %) → add to the registry when the biomass side
  stream is modelled.
- [x] ~~Choose a repo license~~ (ADR 0005)
- [ ] A second product config, to prove the engine is product-agnostic.

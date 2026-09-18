# Backlog: open questions (prioritized)

P1 blocks the next milestone, P2 improves fidelity, P3 is nice to have.

## P1
- [ ] **Bioreactor working volume / fill fraction** for the 300 m³ main vessel. It blocks
  batch lot sizing and RCCP (M4). Start with Humbird et al. 2011 (NREL/TP-5100-47764).
- [ ] **Seed-train and DSP cycle times** for lead times and capacity loading.
- [ ] **UF/DF flux, membrane area, dryer evaporation capacity** for DSP capacity
  (see `topics/tff-scale-up.md`).

## P2
- [ ] Behm 0.223 g/g: total protein or rBLG only? (ADR 0004; currently total.)
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
- [ ] Choose a repo license.
- [ ] A second product config, to prove the engine is product-agnostic.

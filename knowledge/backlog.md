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

- [x] ~~RCCP at batch level (M4)~~: bill of resources + pull-forward leveling (ADR 0010); peak 119 % → 89 %.

## P2
- [ ] Behm 0.223 g/g: total protein or rBLG only? (ADR 0004; total, now supported by the Humbird cross-check.)
- [ ] Offline time: Behm 24 h vs Humbird 48 h. Is there a source for modern CIP/SIP turnaround at 300 m³?
- [ ] Plant uptime for a food-grade protein plant (Humbird's 96 % is for an ethanol biorefinery).
- [ ] A public **dextrose / glucose syrup price** or a published wet-milling cost, so
  glucose isn't priced at corn content only (M3).
- [x] ~~Media inputs per kg~~: NH₃ and salts from Humbird Table 20 are in the BOM (CSL and Tween are not yet, since CSL is given as % w/w).
- [ ] Sucrose uptake by *T. reesei*: does scenario 2 imply an engineered strain or an
  invertase step? Is the yield the same?
- [ ] Unfavourable-side sensitivity values (Behm Fig. 4) for `low`/`high` ranges.

- [ ] Compare `chase` vs `level` S&OP (inventory vs utilization trade-off) once charts exist.
- [ ] More realistic mock order book (order sizes and lumpiness, not a smooth share of forecast).

- [ ] UF/DF membrane life / replacement rate: public source needed to replace the [mock] row (ADR 0008).
- [ ] Odoo: demonstrate rolling time-phasing (short horizon + scheduler per simulated day) vs one-shot run.

- [ ] Public price series for ammonia, salts or packaging (e.g. USDA ERS fertilizer prices for NH3) to extend spend coverage.

## P3
- [ ] Filter-press cake dry content (40 %) → add to the registry when the biomass side
  stream is modelled.
- [x] ~~Choose a repo license~~ (ADR 0005)
- [ ] A second product config, to prove the engine is product-agnostic.

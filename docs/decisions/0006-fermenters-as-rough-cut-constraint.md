# 0006: Treat fermenters as the only capacity constraint until DSP is sourced

- **Status:** accepted (2026-09-18)
- **Context:** S&OP and MPS need a capacity figure. Fermenter capacity can be derived
  from cited values: 300 m³ × 80 % × 50 g/L = 12,000 kg rBLG per batch; a
  144 h cycle; 96 % uptime. Downstream processing capacity (MF, UF/DF, dryer
  throughput) has no public source yet (backlog P1).
- **Decision:** Powder capacity per week = reactors × 168 h × uptime / cycle h ×
  batch kg / (kg rBLG per kg powder). The reactor count is `mock_production_reactors`
  [mock]; the rest is cited or derived. S&OP caps monthly production at this figure,
  and the MPS catch-up fills weeks up to it. DSP is assumed not to be the bottleneck.
- **Alternatives:** invent DSP throughput numbers (breaks the citation rule); no
  capacity at all in S&OP (hides overloads until M4).
- **Consequences:** Plans can still overload downstream in reality, and the output says
  so. Whole-batch rounding in MRP can exceed fermenter capacity in individual weeks
  even when the MPS doesn't (seen in week 2027-01-11: 4 batch starts vs 3.36 available).
  RCCP (M4) must load batch starts against reactors and resolve that.

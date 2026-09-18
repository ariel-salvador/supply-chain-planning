# 0004: Read Behm 2022's 0.223 g/g yield as total secreted protein

- **Status:** accepted (2026-09-18). Revisit if the authors or a later paper clarify.
- **Context:** Behm et al. 2022 §2.4 reports "0.223 g protein per gram of sugar" in the
  same paragraph as total-protein productivity (0.46 g/L/h) and rBLG productivity
  (0.42 g/L/h), with rBLG at 90 % of secreted protein. [source]
- **Decision:** Treat 0.223 as total protein, so sugar per kg rBLG = 1/(0.223 × 0.90)
  = 4.98 kg [estimate, derived from cited values].
- **Alternatives:** treat it as rBLG only, giving 4.48 kg/kg (about 10 % less sugar).
- **Consequences:** This is the conservative reading (more sugar, higher feedstock cost).
  The alternative is a one-line change in `products/blg_whey_protein.yaml`. It's tracked
  in the backlog.

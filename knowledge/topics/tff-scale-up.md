# Downstream processing: microfiltration, UF/DF (TFF) and drying

Basis: Behm et al. 2022 Online Resource 1, Data 1 (note: `notes/behm-2022-rblg-lca.md`).
Every value is a *design assumption* from that model, not a measured plant value.

| Step | Parameter | Value | Id | Tag |
|---|---|---|---|---|
| Filter press | biomass cake dry content | 40 % | (not yet in registry) | [source] |
| Microfiltration | pore size | 0.2 µm (full fungus rejection) | `mf_pore_size` | [source] |
| | protein (permeate) recovery | 97.5 % | `mf_permeate_recovery` | [source] |
| | electricity | 2 kWh/m³ permeate | `mf_electricity` | [source] |
| UF/DF | membrane | PES, 10 kDa MWCO | `ufdf_mwco` | [source] |
| | protein retention | 100 % (assumed) | n/a | [source] |
| | water/impurity permeability | 85 % | `ufdf_impurity_permeability` | [source] |
| | diavolume | 5 m³ buffer / m³ retentate (7 after chromatography) | `ufdf_diavolume` | [source] |
| | electricity | 19.7 kWh/m³ | `ufdf_electricity` | [source] |
| Spray drying | final dry matter | 95 % | `product_dry_matter` | [source] |
| | heat | 4.9 GJ/t water evaporated | `spray_dryer_heat` | [source] |

## What's missing for capacity planning (RCCP)

The energy basis is enough for cost work. **Capacity** needs flux (L/m²/h), installed
membrane area, concentration factor and cleaning cycles for UF/DF, plus dryer
evaporation capacity. None of these are sourced yet. Candidates to check: Cheryan's
*Ultrafiltration and Microfiltration Handbook* (paywalled; cite the values only), and
open-access papers on whey-protein UF/DF flux. See `backlog.md`.

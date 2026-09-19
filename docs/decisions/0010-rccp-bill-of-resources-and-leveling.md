# 0010: RCCP with a bill of resources, and pull-forward leveling

- **Status:** accepted (2026-09-18)
- **Context:** MRP rounds fermentation up to whole 12,000 kg batches. The MPS respected
  powder capacity, but batch rounding still produced 4 batch starts in one week against
  3.36 available with 3 reactors (ADR 0006 predicted this).
- **Decision:**
  - **Bill of resources in config:** item → resource → hours per unit. For BLG-FERM
    that's the cited 144 h cycle ÷ 12,000 kg batch. Resources declare units [mock],
    hours per week and availability; availability is the 96 % uptime [source].
    `hours_per_unit`, `hours_per_week` and `availability` must rest on cited values.
  - **Load placement:** load goes in the planned order's **release** week. That's
    textbook RCCP; the 144 h cycle fits within one weekly bucket.
  - **Leveling (optional):** pull whole lots into the latest earlier week with spare
    capacity, at most `max_pull_forward` weeks back [mock: 2] and never before week 0.
    Then re-run MRP with the leveled receipts fixed, so components follow. Leveling
    never delays supply; anything it can't fix stays flagged as a warning.
- **Alternatives:** push late (causes shortages); finite-capacity scheduling (beyond
  rough-cut, and belongs to a scheduler); raise capacity silently (hides the issue).
- **Consequences:** The base case goes from 119 % peak utilization to 89 %, with one
  batch moved from week 1 to week 0 and no warnings. DSP is still unconstrained (ADR
  0006) until throughput is sourced. The same bill-of-resources mechanism can take DSP
  lines later.

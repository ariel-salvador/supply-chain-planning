# 0007: How S&OP drives the MPS

- **Status:** accepted (2026-09-18)
- **Context:** M2 adds a monthly S&OP plan and a weekly MPS. Weeks don't line up with
  months, the horizon starts and ends mid-month, and the first weeks are already
  committed.
- **Decision:**
  1. Weekly mock demand is aggregated to months by splitting straddling weeks by days.
     Months are planned on a **daily rate**, so partial edge months get proper targets
     and capacity.
  2. S&OP target ending inventory = cover (months) × next month's daily rate × average
     month length. Strategy is `chase` by default; `level` is available.
  3. S&OP opening inventory = on hand + firm receipts inside the MPS horizon.
  4. The monthly plan is split back to weeks in proportion to forecast (totals
     conserved per month).
  5. **Time fences:** before the demand time fence, projected demand = booked orders;
     after it, max(forecast, orders). Before the planning time fence no planned MPS is
     created (firm only). Volume that falls inside the fence is re-placed after it, up to
     weekly capacity. The fence defaults to cumulative lead time (powder + fermentation).
  6. The MPS drives MRP: the finished item's planned receipts are the planned MPS, and
     its gross requirements are the projected demand. Components are netted as before.
  7. ATP is discrete with look-ahead.
- **Alternatives:** net weekly demand directly in MRP (M1 behaviour, still used when a
  config has no `sop`/`mps`); assign weeks to the month they start in (simpler, but
  distorts month totals); lump frozen-zone volume into one week (creates spikes above
  capacity).
- **Consequences:** Plans are explainable top-down (month → week → materials). One
  simplification: S&OP is re-planned from scratch each run, with no rolling frozen
  history.

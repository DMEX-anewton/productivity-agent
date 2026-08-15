# Work Queue

Open analysis work, highest value first. Move items to `insights-log.md` when answered.

---

## Follow-ups from the July-2026 drop diagnosis (2026-08-14)

- [x] **v1.3.0 executed end to end against live data** — all 37 code cells run clean,
  44 Excel sheets and the PDF produced, every internal reconciliation guard passing
  (apportioned days = distinct tech-days exactly; OT apportionment gap fully explained
  by 212 technician-months on payroll with no tickets). The PDF render was exercised on
  7 representative pages rather than all ~85, so the only untested part is the loop
  count. Set `INCLUDE_VIRTUAL_WH_IN_PRODUCTIVITY=False` and `APPORTION_TECH_DAYS=False`
  for a v1.1.0-parity run if a line-by-line reconciliation is wanted.
- [ ] **Do a full ~85-page run on the analyst's machine** and skim the warehouse pages —
  small sites may have sparse overtime or lost-equipment panels worth a layout tweak.
- [ ] **Re-sync `tech_workload` (v1.35.0) with the same two fixes.** It carries the
  same `Tech_Warehouse NOT LIKE 'Z%'` exclusion and the same whole-day denominator, so
  its July figures are wrong in the same two ways. The dashboard's cells are marked
  LIFTED VERBATIM; they have now diverged until this is done.
- [ ] **Decide whether the redelivery rate denominators should be restated.** They now
  include the recovered virtual-warehouse tickets, which lowers `redel_per_100_tickets`
  for Jun-2026 onward. Correct, but it moves published numbers — flag before the next
  board pack.
- [ ] **Quantify the residual real July movers** (TXS Garland, R06 Batesville, R09
  Athens, R12 Irving, R04 Oklahoma City) once question 2 in `questions-for-cfo.md` is
  answered. If territory was absorbed from the five silent sites, normalise by census
  (ADC) or route count rather than raw tickets.
- [ ] **Add a same-day *hours* check if PLC can be joined cheaply.** "Active day" is a
  calendar day with no time component, so a half-day counts as a full day. Ticket-share
  apportionment is a proxy for time on site; payroll hours would let us test it. Note
  the PTO-contamination caveat on PLC hours before using them as a denominator.
- [ ] **Promote the reason-whitelist and virtual-warehouse checks to a standing
  pre-flight.** Diagnostic D1 catches both, but only if someone reads it. Consider a
  hard `assert` when the excluded share or virtual share moves more than N points
  month over month.

## Done 2026-08-14 (v1.3.0)

- [x] **Lost equipment source found and wired.** `ATI.Lost` is dead (NULL on all 583,530
  rows); the live register is `SERP_LOST_EQUIPMENT`. Panels populate. Remaining: the feed
  is 85 days stale (question 6 for the CFO) and four month-end spikes need classifying
  (question 7).
- [x] **Stock outs: true incidence built.** `EnRoute` rows *are* retained after
  fulfilment, so creation-month counts are genuine incidence — the old "fulfilled
  stock-outs disappear" caveat was wrong. Outcome is now three-way (fulfilled 64.7% /
  canceled 28.2% / open 7.1%) and time-to-fulfil comes from the ticket join. Warehouse and
  metro pages carry numbers for the first time (76% order-level attribution).
- [x] **Overtime section built** on de-duplicated PLC daily hours with PTO/Holiday
  excluded from the threshold. The feed's own OT columns are unusable and are now
  documented as such with a per-run diagnostic.

## Carried forward

- [ ] **Confirm the four unlisted lost-equipment spike dates** (2025-01-31, 2025-04-30,
  2025-05-31, 2026-05-15) — question 7 for the CFO. They are currently included in every
  metric; three of four fall on a month end, which smells like posting dates.
- [ ] **Investigate the 1,518 genuinely open stock-outs** (median age 115 days) and the
  6,035 canceled ones. `StockOut_Backlog` and `StockOut_Canceled` list both by site,
  product and age. Pair with question 5 for the CFO.
- [ ] **Chase the 25% of payroll records that don't tie to a technician** (9.9% of OT
  hours unattributable to a site). The name matcher already exports unmatched candidates
  in `tech_workload`; consider running the same HR-review export for payroll names.
- [ ] **`open_orders` by creation month is lumpy** — 0 for most of 2025 but 372 in
  2025-12 and 148 in 2026-03. Worth a look at whether those months genuinely never got
  tickets or whether the order numbers changed form.
- [ ] **Exchange dedup leaves 2,752 groups with more than one kept row** (Cell 10
  prints this as a WARNING every run and it is currently ignored). Either the exchange
  definition needs widening or those groups are legitimately multi-visit; decide and
  silence the warning.
- [ ] **Populate the data dictionary in `CLAUDE.md`** as extracts are onboarded. It is
  still the placeholder stub, which is how `Z CS` went unnoticed — there was no
  documented list of what warehouse codes mean.

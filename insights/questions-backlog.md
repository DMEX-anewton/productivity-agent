# Work Queue

Open analysis work, highest value first. Move items to `insights-log.md` when answered.

---

## Follow-ups from the July-2026 drop diagnosis (2026-08-14)

- [ ] **Re-run the dashboard end to end on v1.2.0 and reconcile it against v1.1.0.**
  The v1.2.0 cells were tested individually against live data (virtual-warehouse
  resolution, apportionment, the renderer) but the full 85-page PDF / 26-sheet
  workbook has not been produced yet. Set `INCLUDE_VIRTUAL_WH_IN_PRODUCTIVITY=False`
  and `APPORTION_TECH_DAYS=False` for a v1.1.0-parity run if a line-by-line
  reconciliation is wanted.
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

## Carried forward

- [ ] **Lost equipment: no data at all.** `SERP_ACTIVE_TAGGED_INV` has zero
  lost-flagged rows company-wide (probe confirmed, not a date-filter miss). Every lost
  panel is blank. Blocked on question 4 in `questions-for-cfo.md`.
- [ ] **Stock outs: get true incidence, not just open backlog.** The current query
  filters `Status='EnRoute'`, so a stock-out created in May and fulfilled in June
  disappears entirely and the "trend" is really a backlog-aging view. The table does
  retain other statuses (Canceled 2,297 orders, Reconciled 689, Completed 69), so a
  genuine incidence history may be reconstructable — worth confirming with the SERP
  team which statuses represent fulfilment.
- [ ] **Exchange dedup leaves 2,752 groups with more than one kept row** (Cell 10
  prints this as a WARNING every run and it is currently ignored). Either the exchange
  definition needs widening or those groups are legitimately multi-visit; decide and
  silence the warning.
- [ ] **Populate the data dictionary in `CLAUDE.md`** as extracts are onboarded. It is
  still the placeholder stub, which is how `Z CS` went unnoticed — there was no
  documented list of what warehouse codes mean.

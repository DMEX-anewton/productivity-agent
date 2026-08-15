# Work Queue

Open analysis work, highest value first. Move items to `insights-log.md` when answered.

---

## v1.6.1 follow-ups — trailing census pooling (2026-08-15)

- [ ] **Re-check Cell 13.5 once more against the live run.** Four pooling defects were fixed in
  v1.6.1, all in the `_t4w` columns; weekly figures were never affected. The new bracket guard
  RAISES if any trailing census ratio falls outside the range of the weekly values behind it, so
  a live run either completes clean or names the metric — there is no longer a silent mode. If it
  raises, the message says which metric and grain.
- [x] **The Cell 13.5 crash is fixed and reproduced.** `ValueError: Boolean array expected for
  the condition, not int64` came from `add_trailing` promoting a bool column to object when it
  reindexed the caller's whole frame onto the week spine. It needs an entity-week with NEITHER
  tickets NOR census, which is why 15 hostile variants missed it; the probe now carries that
  combination and reproduces the error against v1.6.0. Verified fixed under both Python 3.12 /
  pandas 2.3.2 and Python 3.14 / pandas 2.3.3 (the analyst's environment).
- [ ] **Audit the other weekly cells for the same dtype trap.** `add_trailing` no longer alters
  caller columns, so the class is closed at the root — but any other place that left-merges a
  frame against the spine can reintroduce it. `attach_spine` is the one to check first.
- [ ] **Test against Python 3.14 / pandas 2.3.3, not just 3.12.** That is the analyst's actual
  environment and it was not what the harness ran. The suite now runs under both; keep it that
  way, because a dtype-promotion defect is exactly the kind that differs across versions.
- [ ] **Extend the bracket invariant to the other metric families.** It currently guards the
  census panel only, because that is where the defects were. Overtime, lost equipment,
  redeliveries and stock outs all publish pooled trailing rates built the same way and have never
  been checked. This is the highest-value remaining item in the notebook — it is ~15 lines reusing
  `_bracket_violations`.
- [ ] **Decide whether suppressed weeks should be excluded from the trailing average everywhere,
  not just in census.** v1.6.1 made that change for the census panel on the grounds that pooling a
  week too thin to publish reintroduces the distortion the floor prevents. The same argument
  applies to the per-panel `min_denom` suppression in Cell 18, which currently withholds a plotted
  point but leaves the trailing line pooling it.

## v1.6.0 follow-ups — Cell 13.5 fixes + document deliverables (2026-08-15)
- [ ] **Check `techs_equiv` against reality on the first live run.** The apportioned headcount
  only differs from the raw distinct count to the extent technicians work more than one site.
  The synthetic run was deliberately extreme (3.8× double-count); the real figure is probably
  small, and the printed tie-out will say. If it is small, the VP-grain census restatement from
  this release is minor; if it is large, it is another moved number to flag.
- [ ] **Tune `RECS_MIN_SEVERITY_PCT` and `RECS_EFF_GAP_PCT` after the first real run.** Both were
  set from reasoning, not from looking at real VP spread. If VPs come out tightly clustered,
  5% will produce very short recommendation lists; if they are widely spread, it will produce
  five weak ones. The count per VP is printed.
- [ ] **Have someone who is not the analyst read one VP recommendations document cold.** The
  naming rules, the coaching caveat and the censoring notes are all in there, but whether a VP
  reads them *before* the technician table is a question about the document, not the data.
- [ ] **Decide whether recommendation documents should go to VPs directly or via the CFO.** They
  name individuals. That is a distribution decision, not an analysis one, and it should be made
  before the pack is circulated.
- [ ] **Add the remaining undocumented columns to `METRIC_REGISTRY` if anyone quotes them.** The
  dictionary validation prints any published column with no definition; the current list is
  intermediate working values, but that is a judgment that should be revisited when someone asks
  about one.

## v1.5.0 follow-ups — census restatement + weekly grain (2026-08-15)

- [ ] **Run the notebook (now v1.6.0) end to end against live data.** This is the blocking item: the audit's
  reconciliation table is derived from figures already in `insights-log.md`, but the four
  source-level census findings and the VP/metro equipment-rate bug are established from the code
  and their **magnitudes are unquantified**. The run prints all of them. Specifically capture:
  the `(F)`/`(IPU)`/`Contract Test` exclusion as a % of patient-days; the `Census_Coverage` sheet
  (warehouse-months where the old summed-averages shape distorted ADC); virtual-warehouse census
  by month; the VP-vs-company patient-day check in Cell 14; and the before/after on
  `lost_cost_per_1k_pt_days` at VP and metro grain.
  *Pre-release verification done instead:* 22 synthetic assertions on the spine/trailing helper,
  plus an end-to-end synthetic execution of all ten rewritten cells, the renderer and the Excel
  export. That found two real bugs; it is not a substitute for a live run.
- [ ] **Re-issue the affected pages of the last pack, or footnote them.** Two published numbers
  move materially: census per technician (down ~27–29% against the v1.4.0 basis) and VP/metro
  `lost_cost_per_1k_pt_days` (up several-fold). Decide with the CFO whether to re-issue or annotate
  before the next board pack — the census figure has already been quoted at ≈ 120.
- [ ] **Answer question 1 in `questions-for-cfo.md` before any per-technician target is set.**
  The three candidate denominators differ by ~40% end to end.
- [ ] **Skim ~85 warehouse pages on the weekly grain.** Small sites now have ~4× more points and
  much sparser weekly counts; the suppression floors (`CENSUS_MIN_ACTIVE_TECHS`,
  `CENSUS_MIN_TECHS`, and the per-panel `min_denom` values in Cell 18) were set from reasoning, not
  from looking at real small-site output. Expect to tune them.
- [ ] **Re-sync `tech_workload` (v1.35.0) — it now lags by four releases.** It still carries the
  v1.1.0 `Z%` exclusion and whole-day denominator, and it has *none* of the v1.5.0 census or
  equipment-rate fixes. Cells marked LIFTED VERBATIM have diverged further.
- [ ] **Decide whether virtual-warehouse census can be attributed to a site at all.** It is kept
  and tagged now, but a census row carries no technician, so Cell 8.1b's ticket re-attribution does
  not apply. If `Z CS` census turns out to be material, this needs a key the feed does not have —
  ties to question 1 in `questions-for-cfo.md`.
- [ ] **Reconsider whether the redelivery and stock-out panels should show a censoring shade.**
  Both are keyed to an originating/creation week, so their last few weeks are structurally
  incomplete. The panels say so in a note; a greyed region over the incomplete tail would be harder
  to misread, but needs a defensible cut-off (median time-to-event) rather than a guess.

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

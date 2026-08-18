# Work Queue

Open analysis work, highest value first. Move items to `insights-log.md` when answered.

---

## Install-time model v1.0.0 (2026-08-18) — new items

- [ ] **BLOCKING: where do current-year delivery orders live?** `SERP_ORDERS_HISTORY`
  ends 2025-11-30; the requested 2026-YTD window is empty (research item R0). Ask IT which
  table carries live/2026 orders and whether the history load is scheduled or abandoned.
  Until answered, the install-time standards are priced on Jan–Nov 2025.
- [ ] **Confirm `Arrival_Time`/`Completion_Time` semantics with ops.** 19% of tickets
  complete faster than 0.4× the modelled standard — is that genuine quick-drop work, or are
  some timestamps entered after the fact? A ride-along on 5–10 tickets settles it.
- [x] *(DONE v1.1.0, 2026-08-18)* **v1.1: median-calibrated standards + virtual-warehouse
  exclusion.** Live run: median actual/expected 0.73 → 1.00; the Z/Mailouts gate excluded
  916 tickets and accounted for most of the >8h duration tail (502 → 159).
- [ ] **Review the 10 remaining zero-boundary products (R6) with ops** — down from 20 in
  v1.0.0 (the median fit prices bed rails at 2.1 min where the mean fit said 0). Confirm
  none of the remaining zero-priced items ever drives a solo trip.
- [ ] **The median per-visit base is 4.9 min — below the scorecard's own 5-min floor.**
  Folds into the ride-along item below: either quick drops genuinely dominate, or
  completion is sometimes stamped at handoff rather than at the end of the visit.

## v1.8.0 (2026-08-18) — new items from the ADC/OT audit; many v1.7.0 items below are now closed

Closed by v1.8.0 and marked `[x]` below: bracket guard generalised, OT per-head week sets,
scorecard guard + company `ot_hours_per_tech`, pooled recovery, README pooling claim,
exchange-pair claim (removed with dead Cell 10), Cell 8.1b week boundary, stale PTO caveat,
per-technician redelivery denominators, `USER_ROOT`. Full detail:
`insights/metric-audit-v171-adc-ot-2026-08-18.md`.

- [ ] **Run v1.8.0 live and confirm the restated figures.** Expected: trailing census per
  technician ~94–95 (from ~99–100); company OT roughly −7% on the Work-only threshold; the
  08-06 payroll week flagged feed-incomplete until the PLC load catches up. Watch the new
  warn-only bracket checks on the OT/lost/redelivery/stock-out families — if the run is
  clean, **flip `BRACKET_CHECKS_RAISE = True` (Cell 3.5)** so the guard becomes a build
  failure as the 2026-08-17 audit intended.
- [ ] **Investigate Feb-2026's 373 distinct technicians** (281 Jan / 282 Mar; census/tech
  drops to 57.9 and attendance to 54.4% that month only, and the trailing window drags it
  into March). *Progress (v1.8.1):* everything real is flat — tickets/day, tech-days,
  patient-days, payroll people with hours (305) — so ~91 extra NAMES appeared with almost
  no incremental work and no payroll echo, which points at NAME-SPLITTING over a real
  surge; but Feb OT% is the window's highest (19.85%) and PLC hours/day then dipped ~25%
  in Mar–Apr, so a February disruption is not ruled out. **Run v1.8.1: Cell 16.5's
  decomposition (sheet Diag_TechName_Spike) counts the splitting signatures (shared
  matched employee ID / within one edit of a persistent name) and prints a verdict.**
  Until resolved, Feb-2026 per-technician figures are not quotable.
- [ ] **Explain the Mar–Apr 2026 PLC hours/day dip** (~1,974/day Feb → 1,484 Mar → 1,584
  Apr → recovering; PLC people 319 Mar → 261 Apr). Missing loads, or a real slowdown after
  a February surge? Surfaced by the v1.8.1 spike scan; pair with the Feb item above.
- [ ] **Reconcile the analyst's 24,190 July ADC** (questions-for-cfo Q5). It exceeds even
  the pack's unfiltered 23,433. *Update 2026-08-18:* the Warehouse Analysis workbook's own
  NetSuite ADC is 21,998 for Jun-2026 (below the pack), so that workbook is NOT the source;
  and the "five silent sites" turned out to be re-codes (see below), so if their census
  flipped to the new codes too, the census wedge shrinks — re-test after the alias map.
- [ ] **Build a SERP warehouse ALIAS MAP (v1.9.0 candidate — moves site-level numbers).**
  The 2026-08-18 finding: the five "silent" sites were re-coded (R14 San Antonio WH 2 →
  RNW San Antonio WH 2 verbatim in the ticket feed; Walker → R01 Baton Rouge per the
  finance crosswalk), and the same naming churn causes the census vocabulary gap (RNW
  College Station / RNW Lufkin / R16 Stafford). Seed the map from the `Location` sheet of
  `06 - Warehouse Analysis Monthly June 2026, 07-23-2026.xlsb` (93 SERP→NS rows), get IT
  to confirm the complete dated old→new list (the tech-flow SQL in questions-for-cfo runs
  read-only and settles Harlingen / Mailouts / T Storage), then: merge renamed series so
  site trends stop breaking at Jun/Jul-2026, and map census across name variants (closes
  most of the 0.6% vocabulary gap). Do it as its own version — it restates site pages.
- [ ] **Confirm the definition behind "266 active PCT FTE"** (Q8). Hours-capped FTE from
  the OT Week files averages 270.6 over the four July payroll weeks; name the definition so
  targets have a stated denominator.
- [ ] **Confirm the three unconfirmed lost-equipment spike dates** (2025-01-31, 2025-04-30,
  2025-05-31 — flagged `NOT EXCLUDED` on every run). Bulk events like 2025-08-01, or real
  loss? They remain in every trend until listed in `LOST_BULK_EVENT_DATES`.
- [ ] **Chase the ~10% inferred-vs-paid OT residual** in the 07-23 and 07-30 payroll weeks
  (Q7); Cell 15.6 prints it weekly whenever OT Week files are present — keep dropping the
  weekly files into `data/Financial/`.
- [ ] **Consider a feed-completeness guard for the census tail too.** OT got one in v1.8.0
  because the OT Week files proved the lag; the APC feed has its own staleness warning but
  a partially-loaded census day would still pool into ADC undetected.

---

## v1.7.1 — the one census question leadership did NOT settle (2026-08-17)

- [ ] **Decide the SITE-grain caseload denominator: apportioned headcount or raw distinct count?**
  Leadership confirmed the metric is average daily census / distinct technicians ACTIVE IN THE
  PERIOD. At company grain the pack already computes exactly that (Reconciliation 6 asserts it).
  At VP/metro/warehouse grain it divides by the **apportioned** headcount so site rows sum to the
  company row. The literal reading of the confirmed definition would use the **raw distinct
  count** at site grain, which is arguably what a site manager means by "technicians who worked
  here" — but it counts a technician working two sites at both, so the grains stop being
  additive and warehouse rows no longer aggregate to their VP.
  **Company figures are identical either way**; only VP/metro/warehouse move, and they move DOWN
  (bigger denominator) by however much cross-site working there is. Both columns already ship on
  every Census sheet, so either can be formed without a re-run. This is an analyst call, not a
  leadership one — but it is a restatement of every site figure, so it needs its own version and
  its own note rather than being folded into another release.

---

## v1.7.0 audit follow-ups (2026-08-17) — from `insights/code-audit-ops-dashboard-2026-08-17.md`

Ordered as the audit recommends. The first item prevents the next occurrence of the next three.

- [x] *(DONE v1.8.0)* **Generalise the trailing-average bracket guard out of Cell 13.5.** *(highest value in
  the audit — six lines moved.)* Reconciliation 4 tests that a pooled ratio sits inside the
  min–max range of the weekly values it spans, and raises. It is applied to five **census**
  metrics and nothing else. The next two items are live instances of the class it detects, in
  other metric families. Lift `_bracket_violations` into Cell 4.3 beside `add_trailing` and run
  it over every `(frame, rate column)` the pack publishes. This class of defect has shipped in
  three consecutive releases and been invisible every time.
- [x] *(DONE v1.8.0)* **Fix the overtime per-head trailing ratios (mixed week sets).** `Cell 15.5` passes
  `technicians` and `employees` in `rate_cols` (NaN on a quiet week, excluded from the mean)
  while `ot_hours` is in `count_cols` (zero-filled), then divides one by the other. Numerator
  over 4 weeks, denominator over 3 — the v1.6.0 defect family, unfixed here. It **understates**,
  and `ot_hours_per_tech` is lower-is-better and scored, so an intermittent site reads better
  than it is and escapes a recommendation. Move both to `count_cols`, or mask the numerator to
  the same weeks. `ot_pct_of_worked_t4w` is fine (both parts are counts).
- [x] *(DONE v1.8.0)* **Fix the scorecard guard, then decide about `ot_hours_per_tech`.** `Cell 17.5` checks
  `_col not in _vpd.columns` but never tests the **company** frame. `dash_wk_ot_co` has no
  `ot_hours_per_tech`, so the metric gets `company_value = NaN`, `NaN * -1 < 0` is `False`, and
  one of eleven scored metrics can never be adverse — silently, with a blank row per VP in the
  published `VP_Scorecard`. Make the guard fail loudly first. Then choose deliberately: emit
  `ot_hours_per_tech` on the company frame from site-attributed data (covers only the ~90% of
  hours that are attributable — say so), or drop it and score `ot_hours_per_employee`.
- [x] *(DONE v1.8.0)* **Pool `recovery_rate_pct_t4w`.** Currently a mean of four weekly recovery rates, and it
  cannot be pooled as-is because `mature_assets` is aggregated in `Cell 14` but absent from
  `count_cols`. Add `mature_assets` (and `recovered_assets` is already there) and pool it. It is
  a scored metric and its denominators are thin *by design* — cohorts ≥90 days — which is
  exactly when a mean of ratios diverges most from the pooled figure.
- [x] *(DONE v1.8.0)* **Reconcile the Excel README's pooling claim with reality.** It states flatly that rate
  trailing columns are pooled, not means of weekly rates. Four are means:
  `recovery_rate_pct_t4w`, `pct_employees_with_ot_t4w`, `leave_pct_of_total_t4w`,
  `lost_pct_of_inventory_t4w`. Pool them or label them; do not leave the blanket claim standing.
- [x] *(DONE v1.8.0)* **Decide whether exchange pairs are consolidated, then make the code and the dictionary
  agree.** The metric dictionary tells a CFO that *"exchange pairs are consolidated into one
  visit by Cell 10"*, as an assumption of the **headline** productivity numerator. `Cell 10`
  builds `df_visits` and nothing reads it; `_dash_weekly` counts distinct `order_num` off raw
  `df_tx`, and an exchange Pickup and Delivery carry different order numbers, so both count.
  Either consume `df_visits` (a restatement — every ticket count falls) or delete the sentence
  and Cell 10 together. Note the dictionary's own validation cannot catch this: it checks that
  documented **columns exist**, not that documented **claims are true**.
- [ ] **Split `total_tickets` by population.** One column name, three meanings: weekday-only on
  the productivity and technician frames, all-days on the redelivery and stock-out frames. The
  rates are internally consistent so no rate is wrong, but the dictionary defines the column
  once as "weekday tickets only", which fits one of four frames a reader will compare. Rename to
  `total_tickets_weekday` / `total_tickets_all_days` with an entry each. **Breaking change** for
  saved pivots — schedule it rather than slipping it in.
- [ ] **Promote the shared helpers into `analysis/lib/`.** `CLAUDE.md` rule 4 says to use "the
  `run_query` pattern from `analysis/templates/`" and rule 1 says to check `analysis/lib/` before
  writing new code; both directories contain only `.gitkeep`. `run_query`, `clean_numbers`,
  `week_start_of`, `build_week_spine` and `add_trailing` are the obvious tenants, and it is the
  natural home for the generalised bracket guard above. Raised as C2 in the 2026-08-14 audit and
  still open.
- [x] *(DONE v1.8.0)* **Cell 8.1b's `same_week` tier uses a Monday–Sunday week.** `dt.to_period('W')` against a
  notebook whose every published week is Sunday–Saturday. It is tier 2 of a 4-tier inference
  ladder so the impact is small — it changes which physical warehouse an inferred virtual ticket
  lands on, not whether it is counted — but it is the last place a week boundary disagrees with
  the shared spine, and the fix is `week_start_of(...)`.
- [x] *(DONE v1.8.0)* **Retire the stale PTO caveat in Cell 3.1.** The comment above `OT_WEEKLY_THRESHOLD` still
  says *"if PLC 'Hours' includes PTO/holiday pay, OT is overstated ... confirm the feed with
  payroll"*. v1.3.0 confirmed it, excluded PTO and Holiday, and sized the effect at 18%. The
  comment a future editor reads first describes the unresolved state.
- [x] *(DONE v1.8.0)* **Two per-technician redelivery rates cross their denominators.** `_dash_topbottom`
  (Cell 17) and `tech_perf_vp` (Cell 17.5) put an all-days redelivery numerator over a
  weekday-only ticket denominator. Small and consistent in direction, so ranking is barely
  affected — but the figure is printed on every page-1 table and in the named lists inside VP
  recommendation documents.
- [ ] **`_named_sites` averages weekly rates rather than pooling** (Cell 22). Defensible for a
  ranking, but it selects which sites get named in a document that goes to a VP, in a pack whose
  stated rule is pooling.
- [ ] **Dead code, all three raised in the 2026-08-14 audit and still dead.** `Cell 10` in its
  entirety (see the exchange-pair item — it costs a full `groupby.transform` over ~449k rows and
  emits a warning nobody owns); `tbl_redel_monthly` (built with a rate, never exported);
  `tbl_redel_product` (built, `display()`ed only, never exported — the last `display()` left);
  `df_apc` (queried, cleaned, never read — keep the snapshot-date probe beside it, drop the
  query). Plus `MIN_HOURS_FOR_OT_RATE` and `STOCKOUT_FROZEN_LOAD_DATE`, defined and never read.

### Repository, not the notebook — these three need an owner

- [ ] **There is no pre-commit hook.** `CLAUDE.md` rule 3 says *"the pre-commit hook strips
  them; do not bypass it"*. `.git/hooks/` is empty and 538 outputs are committed across nine
  `ops_dashboard` notebooks. v1.7.0 is committed clean, which does not fix this — the next
  executed save re-adds them. Install the hook the rule already assumes.
- [ ] **Patient-account identifiers are in git history.** *(needs a decision, not a code
  change.)* The committed outputs of v1.0.0–v1.2.0 carry the `display(df_tx.head(3))` result
  with real `order_num` / `record_id` values and technician names. v1.3.0 fixed the code; the
  data was never removed from the repository. Options are a history rewrite over those three
  paths (invalidates every clone) or a documented accepted exposure. It should not sit
  undecided — and it is why the missing hook is a blocker rather than hygiene.
- [x] *(DONE v1.8.0)* **`USER_ROOT = '$HOME'` writes every deliverable into the repo.** Python does not expand
  shell variables, so `OUT_DIR` is a *relative* path and the notebook creates
  `analysis/$HOME/OneDrive - DME Express/Reports/TechWorkload/<date>/` and fills it with the
  workbook, both PDFs, the dictionary, five per-VP recommendation documents and six PNGs. That
  folder was observed full earlier on 2026-08-17; by the end of the audit only the empty
  directory skeleton remained (cause unknown — nothing in the audit removed it). The next run
  refills it. **It is not git-ignored.** Use `os.path.expanduser('~')` and assert `OUT_DIR` is absolute
  before `makedirs` — a relative deliverable path is always a bug here. Adding the path to
  `.gitignore` is a seatbelt, not the fix.
- [ ] **`SQL_USERNAME = 'anewton-ro'` is hardcoded in a shared notebook** (Cell 4.1). No
  credential is in the repo, so rule 5 holds, but a second analyst either connects as someone
  else's read-only principal or fails. Environment variable with this value as the fallback.

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
- [x] *(DONE v1.8.0)* **Extend the bracket invariant to the other metric families.** It currently guards the
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

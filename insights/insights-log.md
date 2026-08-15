# Insights Log

Newest first. Each entry: what we found, how we know, what it changes, what it does not.

---

## 2026-08-15 — v1.6.1: the Cell 13.5 crash was in `add_trailing`, and four silent pooling defects sat behind it

`analysis/ops_dashboard_2026-08-14_v1_6_1.ipynb`. Raised by the analyst, who supplied the
traceback after two rounds of my guessing at it.

### The crash: `ValueError: Boolean array expected for the condition, not int64`

**The root cause was not in Cell 13.5.** `add_trailing` (Cell 4.3) reindexed the *caller's whole
frame* onto the week spine with a left merge, so every column the caller brought along acquired
missing values for the spine weeks that entity had no row in. A bool column cannot hold one, so
pandas silently promoted `ratio_suppressed` from `bool` to `object`, and `Series.mask()` then
refused it — reporting the dtype, confusingly, as `int64`.

Fixed at the root: only the key and target columns go through the spine reindex, and the trailing
columns are joined back onto the caller's frame, so no caller column can be altered by passing
through. `add_trailing` now asserts on exit that it changed no incoming dtype.

**Why three rounds of testing missed it, which is the lesson.** The failure needs an entity-week
with **neither tickets nor census**. A gap in one feed alone is backfilled by the outer merge with
the other, so the row still exists and the dtype survives — which is why 15 hostile variants
including whole-week census gaps *and* whole-week ticket gaps all passed. Real sites that are
absent from `SERP_APC_DAILY` **and** silent for a week hit it on the first run. The probe now
carries that exact combination and reproduces the error against v1.6.0.

Two process failures made this take three attempts. First, I asserted "no exception in any data
shape" when what I had actually shown was "no exception in the shapes I thought of" — a much
weaker claim that I should have stated as such. Second, one of my test scripts was still pointing
at the *previous* notebook version because a path-rewrite had silently failed, so a run I reported
as verifying v1.6.1 had been re-verifying v1.6.0. Both are arguments for the invariants now
embedded in the notebook itself, which cannot be pointed at the wrong file.

### Behind the crash: four silent pooling defects — one mistake in four disguises

Found by writing the invariant guard, not by reading. Each is a trailing ratio assembled from
parts that were not averaged over the same thing. All are confined to the `_t4w` columns —
**every weekly figure was correct throughout.**

**1. The trailing attendance figure was a product of means.** v1.6.0 computed
`tech_days_t4w / (techs_equiv_t4w × weekday_days_t4w)`. `mean(a) / (mean(b) × mean(c))` is not
`sum(a) / sum(b × c)`, and both denominator factors were zero-filled for a week the entity did
not work — so the denominator shrank **twice**. An entity with three worked weeks and one idle
week in the window reported **106.7% attendance, from weeks that never exceeded 80%.** A rate
above 100% was sitting in the output and nothing flagged it.

The root cause was two denominators collapsed into one. `weekday_days` is a **calendar**
property — a week an entity did not work still *has* five weekdays — so zero-filling it per
entity was wrong on its face. What attendance actually divides by is **available
technician-days** (`techs_equiv × weekday_days`), where an idle week contributes zero. That is
now its own column, computed before the trailing pass.

**2. Ratios were pooled against zero-filled denominators.** Zero-filling is right for a volume
and wrong for a ratio: a week with census and zero technicians does not make
patients-per-technician enormous, it makes it **undefined**. The headline came out at **1,240
against weekly values that never exceeded 930.**

**3. Two ratios mixed two different week sets.** `census_per_active_tech_weekday` pooled ADC over
weeks with census *and* technicians, and its denominator over weeks with technicians only.

**4. Suppressed weeks fed the trailing average** — withheld from the weekly series as too thin,
then pooled into the four-week figure anyway, reintroducing exactly what the floor prevents.

### The guard is the durable part

All four share a signature: **a pooled ratio landing outside the min–max range of the weekly
values it spans.** A mean must be bracketed by its inputs. Cell 13.5 now tests that on every run
across five metrics at company, VP and warehouse grain, and **raises rather than warns** — this
class of error shipped twice in two releases and was invisible both times.

It earned its keep immediately. It was written to catch defect 1; **it then found defects 2, 3
and 4**, each on the first run after the previous fix. A regression test pins the 106.7%-vs-80%
case numerically, so it cannot come back quietly.

### Also fixed: labels that no longer matched the code

v1.6.0 moved the headline denominator to `techs_equiv` but left `denominator_note` — which ships
on **every row of every census sheet** — saying "ADC / distinct technicians", and left the
suppression message and closing summary naming `techs_distinct`. Publishing a metric whose stated
denominator is not its actual denominator is the precise error this whole sequence of releases
exists to correct. The note is now derived from the metric names rather than retyped.

### What moves

**Company figures are unchanged** — at company grain `techs_equiv` equals `techs_distinct`, there
are no idle or suppressed weeks, and the pooled and product-of-means forms coincide. **VP, metro
and warehouse `_t4w` census columns from v1.6.0 are wrong**, by an amount that grows with how much
idle or suppressed time an entity had in the window. No weekly figure moves, and no other metric
family is touched.

### A note on how this was found

Four rounds of fixes to this cell now, each found by a different method: the unmapped-census
conflation by reading the code, the entity-grain double-count by reading the generated documents,
the four pooling defects by writing an invariant and letting it fail, and the crash only once the
analyst supplied the traceback. The census panel has carried a denominator or pooling defect in
**every version since it was introduced**, which is the actual finding here — the metric was
built on a shared denominator borrowed from a flow metric, and every subsequent fix uncovered
another consequence of that.

Two methods earned their place. The **in-notebook invariants** (apportioned days reconcile to
distinct tech-days; the apportioned headcount sums across grains; a trailing ratio sits inside the
range of its weekly inputs; `add_trailing` alters no caller dtype) found three of the six defects
and cannot be pointed at the wrong file or forgotten. The **hostile-variant probe** found none of
them until the failing combination was added by hand — synthetic data only tests the conditions
you thought of, and the one that mattered was the intersection of two feeds both missing the same
entity-week. Worth stating plainly: "no exception in 15 data shapes" was never the same claim as
"no exception".

---

## 2026-08-15 — v1.6.0: three more denominator defects in the census panel, and the pack now ships a metric dictionary, per-VP recommendations, and one publishable PDF

Built in `analysis/ops_dashboard_2026-08-14_v1_6_0.ipynb`. v1.5.0 is left on disk unchanged
so the two can be diffed.

### The defect the analyst flagged in Cell 13.5, and two more found beside it

**1. The unmapped-census warning was firing on v1.5.0's own change.** v1.5.0 started *keeping*
virtual (`Z%`) census instead of dropping it — correct, because dropping it while keeping the
technicians who serve it was the whole asymmetry being fixed. But a virtual code can never map
at that join: Cell 8.1b re-attributes virtual *tickets* to physical warehouses, so no `Z%`
value survives as a `tech_warehouse` for census to join against. So **100% of virtual census
landed in the "warehouses the ticket feed never resolved" bucket**, inflated it, and printed
*"check the warehouse vocabulary in `SERP_APC_DAILY` against `SERP_WAREHOUSES`"* — pointing the
analyst at a naming problem for something that was a deliberate design decision two cells
earlier. The two causes are now separate numbers, and only the actionable one can trip the
warning.

**2. Census trailing ratios divided a four-week numerator by a two-week denominator.**
`techs_distinct` and `avg_active_techs` were classified as *rates*, so they were averaged over
the weeks an entity happened to appear in, while `pt_days` and `census_days` were *counts* and
zero-filled across the window. A site with census in four weeks but technicians in two divided
a four-week census by a two-week headcount, so the trailing ratio read **high for exactly the
sites that had a quiet week**. Both are counts — a week with no technicians on the road
genuinely had zero — and every census trailing ratio is now rebuilt from the pooled counts.
`attendance_rate_pct` is pooled now too; v1.5.0 left that one averaged.

**3. The one that actually matters: at entity grain the census denominator double-counted
technicians.** `techs_distinct` counts a technician who works two VPs **once in each**, while
`tech_days` is apportioned between them. Dividing an apportioned numerator by a whole-count
denominator is precisely the defect v1.2.0 fixed for productivity, and it was sitting
untouched in the census denominator. In a synthetic run with heavy cross-site working,
**attendance read 42% at VP grain against 72% at company grain** — entirely an artifact of the
same person being counted twice.

Fixed with an **apportioned headcount** (`techs_equiv`): each technician is given to an entity
in proportion to the share of their own days spent there, so someone entirely at one site
counts as 1 and someone splitting 50/50 counts as 0.5 at each. It **sums to the true distinct
count company-wide**, so the company figures — and the whole 85-vs-120 restatement table this
release rests on — are unchanged, while every entity grain becomes internally consistent and
additive. The notebook asserts that sum on every run: in the synthetic check the warehouse sum
was 1,071.0 against a company 1,071.0, where the raw distinct-count sum was **4,061**.

### New deliverables

- **Editable Word metric dictionary.** Every published metric with its output column, its
  calculation, the specific source fields, its grain and denominator, its direction, and the
  assumptions needed to interpret it — plus the cross-cutting assumptions and this release's
  restatements. **It is validated against the code on every run:** a documented metric the
  notebook does not produce raises and fails the build, and undocumented published columns are
  listed. That check caught 41 columns on the first pass, which is how the intermediate values
  got separated from the quotable metrics.
- **Editable Word recommendations document per VP** — top 5 actions ranked by adverse gap
  against the company, each with the figure it rests on, why it matters, concrete steps, and,
  where the data supports it, named technicians.
- **One consolidated publishable PDF** — cover, executive summary, dictionary, company page,
  then each VP's page followed immediately by their recommendations, then metros, warehouses,
  and an appendix. Bookmarked, one page size throughout. The restatement notice is on page 2,
  not in the appendix.

The Word files and the PDF render from **one content model**, so a definition cannot say two
different things in two places.

### Two judgment calls worth recording

**Who gets named.** The request was for recommendations "up to and including specific
technicians that are dragging down their metrics either in overtime or technician
efficiencies", and those two are exactly where the data attaches to a person. Technicians are
named for **tickets per active day** (denominator-honest, presence floor applied, compared to
their **own VP's median** rather than the company's so route density is not mistaken for
effort) and for **overtime** (computed on the person from de-duplicated payroll hours, before
any site allocation). Everywhere else the documents name **sites**: lost equipment because
attribution is proximity and not fault, attendance because the feed cannot separate approved
PTO from an unfilled schedule, and stock outs because they are supply-side. `COACHING_CAVEAT`
is attached to every row of `tech_perf_vp` as well as to every list, so a name cannot be copied
out of a table without it.

**A materiality floor on recommendations.** The first generated pass produced a formal
recommendation for a VP sitting **0.03 percentage points** off the company overtime figure. A
list padded with rounding teaches the reader to ignore the list, so a gap must now be at least
5% of the company figure to become an action. Immaterial gaps stay visible in the scorecard,
and the document states how many were held back and why.

### Verification

All 15 rewritten or new cells execute end to end against synthetic feeds, in both a plain and a
deliberately hostile shape (census codes absent from tickets, a warehouse under two VPs, NaN
hierarchy, a site with tickets and no census and vice versa, one genuinely weaker VP, three
deliberately slow technicians and concentrated overtime). The recommendation engine correctly
surfaced all three planted slow technicians as its top three. The spine and trailing helper
carry 22 assertions. Generated documents and PDF pages were read and looked at, which is how
the double-count, the immaterial recommendation, the percentage-versus-percentage-point wording,
`Z CS` being listed as a site for a VP to visit, and "2th" instead of "2nd" were all caught.

**Still no live database run** — see `questions-backlog.md`. Everything above is code-level or
synthetic; the magnitudes of the census-source findings remain unquantified until v1.6.0 runs
against DMEEXPRESS.

---

## 2026-08-15 — v1.5.0: the ~120 census-per-technician figure was measuring attendance, not headcount. The productivity metric is fine; one other metric was badly broken.

**Question asked:** company ADC ≈ 25,000 over just under 300 technicians is ≈ 85 per technician,
so why does the v1.4.0 pack print ≈ 120? Full audit in
`insights/metric-audit-adc-per-tech-2026-08-15.md`; fixed in
`analysis/ops_dashboard_2026-08-14_v1_5_0.ipynb`.

**Answer: the ≈ 120 is arithmetically correct and wrong as labelled.** v1.4.0 divided ADC by
`weekday tech-days ÷ weekdays in month` — the average number of technicians *on the road on a
working day* — and titled it "Census per Active Technician". Reconciled from the notebook's own
published inputs:

| | 2026-06 | 2026-07 |
|---|---|---|
| distinct technicians on tickets | 252 | 251 |
| apportioned weekday tech-days | 4,093 | 4,112 |
| weekdays in month | 22 | 23 |
| **`avg_active_techs`** (the v1.4.0 denominator) | **186.0** | **178.8** |
| ADC | 22,815 | 23,356 |
| **ADC ÷ `avg_active_techs`** — what the pack printed | **122.6** | **130.6** |
| ADC ÷ distinct technicians | 90.5 | 93.1 |
| ADC ÷ ~300 payroll technicians | 76.0 | 77.9 |
| average weekday attendance | 73.8% | 71.2% |

The entire gap is **average weekday attendance of ~71–74%** — PTO, sick, training, part-time, and
weekend work, which the weekday filter discards. The analyst's ~85 and the pack's ~120 were both
right about different denominators.

**Why it is a definitional error and not a labelling quibble.** ADC is a **stock** — patients on
service on an average day. Tech-days are a **flow** — attendance events. A patient does not leave
service because their technician took PTO, so the caseload is carried by the whole roster every
day, and the honest caseload denominator is **headcount**. Read the other way the v1.4.0 number is
a real quantity — field *coverage* intensity — but it is not caseload and must not sit beside a
per-technician staffing target. v1.5.0 publishes all three (headline `census_per_tech_headcount`,
the retained v1.4.0 basis, and `attendance_rate_pct`) and prints the bridge on every run.

**The caveat v1.4.0 carried was pointing at the wrong effect.** Every panel warned that "ADC is a
7-day calendar average while tech-days are weekdays only". Census is a stock, so that is worth low
single digits — while the ~40% attendance wedge was documented not as a limitation but as a
deliberate design choice. A reader who trusted the caveat would have mis-sized the correction by
an order of magnitude.

### What this did NOT affect — the containment finding

`tickets_per_active_day` is **flow ÷ flow**, and its denominator is asserted every run to
reconcile to distinct (tech, date). Overtime, redeliveries and stock outs never divide by census.
The defect was contained to the census panel and to the one bug below; it did not leak into the
productivity or overtime numbers.

### The one hard bug: VP and metro equipment rates were divided by the whole company's census

Cell 14 branched on `if 'tech_warehouse' in gcols`, merging per-warehouse ADC in that branch and
the **company total** in the `else`. Both the metro and the VP grain took the `else`, so every VP
row and every metro row divided its lost cost by the entire company's patient-days.
`lost_cost_per_1k_pt_days` on a VP page was understated by roughly (company census ÷ that VP's
census) — order of **5–10× for a VP**, far more for a metro — the metric was not comparable across
grains, and warehouse rows did not aggregate to their VP. Company and warehouse grains were
correct, which is exactly why it survived review: the error is invisible unless you compare two
grains. **VP and metro equipment rates rise sharply against v1.4.0.** Established from the code;
its exact size needs a run.

### Three more defects in the census source, all in one query

- **Two definitions of census in one notebook.** The APC snapshot excluded facility `(F)`,
  inpatient-unit `(IPU)` and `Contract Test` customers; the ADC series that every census metric
  and the equipment rate actually consumed excluded **none** of them.
- **Company ADC was a sum of per-warehouse monthly averages over different day sets** — a number
  corresponding to no actual day whenever site coverage differs. Live right now for the partial
  current month and for the five sites recorded going silent after Jun-2026. Now pooled
  patient-days ÷ distinct dates at every grain.
- **Virtual (`Z%`) census was dropped from the numerator while its technicians stayed in the
  denominator** — the same asymmetry that produced the false July productivity drop, in a new
  panel. Now kept and tagged. Limit: it cannot be re-attributed to a site the way a ticket can,
  because a census row carries no technician, so it counts at company level only.

### And three found while moving everything to a weekly grain

- **`rolling_4wk_avg` rolled over rows, not weeks.** An entity with no tickets in a week had no
  row, so the window reached back five or six calendar weeks and was published as four. It bit
  small warehouses hardest and biased **upward**, because the weeks that vanished were the slow
  ones. Trailing averages are now computed on a calendar spine.
- **Trailing rates were a mean of weekly ratios**, which weights a 30-ticket holiday week like a
  700-ticket week. Tested: a window of (1/3, 40/400, 40/400, 40/400) reads 15.8 as a mean of
  ratios and **10.1** pooled. All rates are now pooled.
- **Four of the five metric panels were twin-axis charts** (bars left, rate line right), which
  have no defensible crossing point. v1.4.0's census panel already refused to do this and said why
  in its own docstring — the rule was written down and applied to one panel in five. Layout is now
  3×4 with the rates on their own single-axis panels.

### Everything is now weekly with a trailing 4-week average

Previously productivity was weekly and the other five families monthly, so two panels on one page
were two different time bases and 19 monthly points hid every single-week break. Overtime keeps
its own Thu–Wed payroll spine and is **not** alignable week-for-week with the Sun–Sat panels.
Censoring is worse to read at weekly resolution and is restated on the panels: redeliveries key to
the **originating** week and stock-out outcomes to the **creation** week, so the rightmost weeks of
both are structurally incomplete rather than improving.

### Limitations of this work

- **No live database run was made.** The reconciliation table above is derived from figures already
  published in this log, so it needs no confirmation. The four source-level findings and the VP/metro
  bug are established from the code, but their **magnitudes are unquantified** until v1.5.0 runs.
- The new spine and trailing helper carry a synthetic-data test suite (22 assertions), and all ten
  rewritten cells plus the renderer and Excel export were executed end to end against synthetic
  feeds — which caught two real bugs pre-release. That is not a substitute for a live run.
- ~300 technicians is the analyst's figure, taken as given. If it is an all-departments payroll
  count rather than field technicians, the ADC ÷ 300 row is a floor, not an estimate.

---

## 2026-08-14 — v1.3.0: stock outs, lost equipment and overtime populated. Every one of the three had a source-level defect first.

Built in `analysis/ops_dashboard_2026-08-14_v1_3_0.ipynb`, alongside a full code audit
(`code-audit-ops-dashboard-2026-08-14.md`). The pattern across all three sections: the
analytical logic was never the problem — the *source* was, and in each case the failure
was silent.

### Stock outs — 28% of stock-outs end with the order abandoned, not supplied

The dashboard read `Status='EnRoute'` as an open backlog and trended it as aging. It is
not a backlog: rows are retained after the stock-out is dealt with (19,891 of 21,438
carry a completion date), and every other status value is frozen at a single 2026-01-20
load, so "oldest open 1,021 days" was a stale row.

Reframed to incidence by creation month, and the outcome split is the finding:

| outcome | orders | share |
|---|---|---|
| **fulfilled** — completion on a live (Reconciled/Completed) ticket | 13,856 | **64.7%** |
| **canceled / abandoned** — completion only on a `Canceled` ticket | 6,035 | **28.2%** |
| **genuinely open** — no completion evidence at all | 1,518 | **7.1%** |

Nearly three in ten stock-outs end with the order dropped rather than filled. That is an
operational question, not a data one — raised in `questions-for-cfo.md`.

Time-to-fulfil for the ones that do land: **P25 3 / median 6 / P75 9 / P90 17 days**. The
genuine backlog is 1,518 orders with a median age of 115 days.

**A correction worth recording.** My first pass reported 93% fulfilment. That counted
canceled tickets as deliveries — a canceled ticket carries a `Completed_Date` too. The
93% figure was wrong and is corrected wherever it was written. Fulfilment must also be
tested against the *unfiltered* ticket feed: 1,165 stock-out orders sit under
`Priority 4 - System Update/Correction (D)`, which the analysis whitelist excludes on
purpose, and measuring against the filtered set alone left them looking open forever.

Warehouse and metro pages now carry stock-out numbers for the first time. v1.1.0 asserted
no physical warehouse existed on these rows; 5,726 EnRoute rows carry one of 65 real
warehouses, and an order-level join resolves **76.0%** of orders to a site.

### Lost equipment — the panel had been structurally empty, and it was a one-column failure

`SERP_ACTIVE_TAGGED_INV.Lost` is NULL on **all 583,530 rows**, so
`WHERE ATI.Lost IS NOT NULL` could never return anything. v1.0.1's probe found the zero
and blamed the feed; the register had in fact moved. Of five candidate sources only
**`SERP_LOST_EQUIPMENT`** is live (91,023 rows, warehouse names matching the master 71 of
72, and it adds Lost Reason, Resolution and Resolved Date).

Two traps made this a silent failure rather than a loud one: `[Lost Date]` is not a date
but an HTML fragment (`01/02/2025<br/>(147)`) that `TRY_CONVERT` fails on for **100%** of
rows, and `[Unit Cost]` is a currency string. A naive port would have produced the same
empty panel. The parse-failure rate is now asserted, not printed.

Company monthly loss runs **~2,500–4,400 assets and $200k–$370k** through the window.
Recovery is 13–25% on mature cohorts, with resolution taking **P25 21 / median 42 / P75
91 days**.

Limits, both material: the feed **ends 2026-05-20** (85 days behind the rest of the
dashboard — every page carries a banner), and the **2025-08-01 bulk event is excluded**
from all metrics and trends per the analyst's instruction — 30,902 rows, $3.06M, 99.9% of
it parked in `Z Equipment Collections` / `Z CS` rather than at physical sites, which is
what marks it as a reconciliation dump rather than operational loss. It is reported in
its own sheet. Four further month-end spikes are surfaced but **not** excluded, pending
confirmation.

### Overtime — the feed's own overtime columns are unusable, and the feed double-loads

Overtime runs **~16–19% of worked hours** company-wide and is stable month to month
(Patient Care Technicians: 3,178 OT hours in Jan-2025 rising to 8,384 in Jul-2026 as
headcount grew 127 → 308). All-departments OT is ~15–16%.

Getting there required disarming four landmines:

- **The payroll feed re-loads overlapping windows, so rows accumulate.** 12.4% of pulled
  rows are duplicates; one employee-day appeared 30 times. Un-deduplicated, Jun-2026
  reads **66% overtime**. A second de-duplication rule (newest load only) agrees to 0.1%,
  which is what gives confidence in the fix.
- **`Reg_Hrs` / `OT1_Hrs` / `OT2_Hrs` / `Paid_Hrs` / `Est_*` cannot be summed** — they are
  pay-period values repeated on every daily row (16–18× the trusted daily `Hours`),
  `OT1_Hrs` is 0 for every month from 2026-02 on, and `OT2_Hrs` is 0 throughout. OT is
  inferred FLSA-style instead, and a diagnostic re-proves this on live data every run.
- **`Pay_Type` separates PTO and Holiday**, which retires the long-standing caveat that
  inferred OT is overstated when paid leave is included. Worth **18%** in Jul-2026
  (10,264 hours including leave vs 8,384 excluding). Both figures are emitted.
- 709 rows carry NULL department/employee and 2,600–3,100 hours each (1.05M hours, more
  than every real row combined), and the feed holds future-dated rows. Both guarded.

Payroll has no usable warehouse key — only **2 of 139** `Location_Name` values match the
master — so hours reach a site through the technician name match (75.1% of payroll people
tie to an attributed technician) and are then apportioned by ticket share, the same rule
v1.2.0 introduced for active days. **9.9% of OT hours cannot be attributed to any site**
and remain in the company total only, so site rows sum to less than the company row by
design; the reconciliation is printed and self-explaining every run.

---

## 2026-08-14 — The July-2026 drop in tickets per technician is a measurement artifact, not an operations slowdown

**Question asked:** why does tickets-per-technician fall in July across nearly every
location on the ops dashboard (`analysis/ops_dashboard_2026-08-14_v1_1_0.ipynb`)?

**Answer:** two independent defects in the dashboard's own measurement, stacking in
the same month. Neither is an operational change. Corrected in
`analysis/ops_dashboard_2026-08-14_v1_2_0.ipynb`.

### Finding 1 — real field tickets were being deleted from the numerator (the main effect)

From 2026-06 a virtual warehouse code, **`Z CS`**, began carrying ordinary completed
field work. The dashboard's extraction filtered `Tech_Warehouse NOT LIKE 'Z%'`, so
those tickets were dropped — but the technician's **active day was still counted in
the denominator**, because they almost always had other, non-virtual tickets the same
day. Tickets fell, days did not, and the ratio collapsed.

`Z CS` eligible weekday tickets by month — 17 months of background, then a step:

| | 2025-01 … 2026-04 | 2026-05 | 2026-06 | 2026-07 | 2026-08 (to 13th) |
|---|---|---|---|---|---|
| `Z CS` tickets | 8–134 / mo | 10 | 1,903 | **5,874** | 2,092 |
| share of eligible weekday tickets | 1–2% | 0.7% | 9.3% | **24.3%** | 21.2% |
| tech-days mixing real + virtual work | ~0% | 0.0% | 12.9% | **27.7%** | 24.7% |

These are not administrative rows. The top `Z CS` reasons in July were Additional
Equipment (D) 1,758, New Admit (D) 845, Hospital Discharge (D) 679, Customer/Patient
Request (P) 479, Respiratory Distress (D) 343 — deliveries and discharges, i.e. the
core of the productivity metric.

**Company tickets per active tech-day, Jun → Jul 2026: −13.2% as reported vs −2.1%
corrected.** The corrected monthly series is flat all year (5.53, 5.30, 5.50, 5.41,
5.48, 5.50, 5.38, 5.44 for Jan–Aug 2026); the reported one cliffs in July only.

Three independent checks say no work was lost:
- raw ticket rows in `SERP TRANSACTIONS` **rose 6.4%** in July (29,426 → 31,315);
- census hit an all-time high — ADC 22,815 (Jun) → **23,356** (Jul);
- distinct technicians and total tech-days were flat (252 → 251 techs, 4,093 → 4,112
  tech-days), so this is not attrition or PTO either.

### Finding 2 — warehouse-grain active days were double-counted (why site pages looked far worse than the company)

Separately, and also worst in July: a technician whose day spanned several warehouses
contributed a **whole** active day to **each** of them while their tickets were split
among them. Every site's ratio was therefore deflated by its fragmentation factor.
This is why warehouse pages showed −40% to −70% while the company showed −13%.

| | 2026-05 | 2026-06 | 2026-07 |
|---|---|---|---|
| warehouses per technician per month | 1.29 | 2.22 | **2.86** |
| per-warehouse active-day sum vs distinct (tech, date) | +3.8% | +14.9% | **+34.9%** |

Historic inflation was 1.8–5.3%, so this defect was always present but immaterial
until routing changed.

Jun → Jul change in warehouse tickets-per-active-day, 50 warehouses with ≥40 Jun
tech-days (distribution, not mean — the tails are the story):

| | P25 | median | P75 | min | max | declining |
|---|---|---|---|---|---|---|
| as reported (v1.1.0) | −22.6% | **−14.2%** | −3.6% | −47.8% | +29.8% | 43/50 |
| corrected (v1.2.0) | −10.3% | **−4.3%** | +3.5% | −28.4% | +44.2% | 35/50 |

### What changed in the notebook

1. Extraction keeps virtual-warehouse rows, tagged rather than dropped.
2. New Cell 8.1b re-attributes each one to the physical warehouse that technician
   actually worked that **day**, else that **week**, else that **month**. Jul-2026:
   4,019 same-day + 1,885 same-week + 53 same-month, **2 unresolved**. Anything
   unresolved is labelled `Virtual - Unresolved`, never silently dropped.
3. Cell 13 apportions each technician-day across warehouses by that day's ticket
   share. The apportioned days reconcile **exactly** to distinct (tech, date) — the
   notebook now asserts this on every run.
4. New Cell 13.0 diagnostic (D1–D5) instruments the funnel, so the next feed change
   is visible as a funnel step instead of appearing as a productivity decline.
5. Weekly panels mark the routing change and plot the re-attributed share.

### Limitations — state these wherever these numbers are used

- **A resolved warehouse is inferred, not stamped on the ticket.** It comes from the
  technician's own route that day. Sound for site-level trend and workload; **not**
  evidence about an individual without ticket-level review, and never for discipline.
- **Company, VP and state levels are sound. Warehouse-level comparisons across
  Jun-2026 are provisional** until we know what `Z CS` is and whether the five sites
  that went silent after Jun-2026 closed or were renamed (see
  `questions-for-cfo.md`). Residual real movers after correction — TXS Garland
  −28.4%, R06 Batesville −23.0%, R09 Athens −21.3%, R12 Irving −17.2% — may be
  genuine, or may be territory absorbed from those five sites.
- Ticket dates carry no time component, so "active day" is a calendar day, not hours.
  A half-day still counts as one active day; ticket share is a proxy for time on site.
- The reason whitelist (`INCLUDED_REASONS`) is still a silent single point of failure:
  a reason renamed upstream deletes its tickets with no error. Priority 4 –
  System Update/Correction rows roughly doubled in July (329 → 783), which is
  consistent with a migration and is now tracked by diagnostic D1.
- Lost-equipment metrics remain empty for an unrelated reason: `SERP_ACTIVE_TAGGED_INV`
  has **zero** lost-flagged rows company-wide, confirmed by probe.
  **Superseded 2026-08-14 (v1.3.0):** it was not an upstream feed outage as concluded
  here — the `Lost` column is dead (NULL on all 583,530 rows) and the register had moved
  to `SERP_LOST_EQUIPMENT`, which is live. Lost equipment now reports. See the v1.3.0
  entry above.

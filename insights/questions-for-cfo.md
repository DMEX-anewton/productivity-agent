# Open Questions for Leadership

Questions analysis cannot answer from the data alone. Newest first.

---

## 2026-08-18 — from the v1.8.0 audit (census/OT reconciliation)

**Q5 — What is the source and definition of the "24,190 ADC for July" figure?**
The pack's July ADC is **23,130** under the confirmed exclusions ((F), (IPU), Contract
Test, NULL customer) and **23,433 with nothing excluded** — so 24,190 sits above even the
unfiltered figure. Candidate explanations, each checkable once the source is named: a
month-end snapshot rather than a daily average; a feed that still carries the **five sites
whose SERP_APC_DAILY census went silent after Jun-2026** (in which case the pack's ADC and
every census-normalised rate are *understated* by their census, and the feed needs fixing);
or a census definition that includes populations leadership excluded on 2026-08-17. Until
reconciled, comparisons between the pack and that source will disagree by ~3–5%.

**Q6 — Confirm the overtime treatment of On Call Hours.** Calibrating against payroll's own
OT Week reports shows Paylocity does **not** count on-call hours toward the 40-hour
overtime accrual: Work-only inference matches paid OT within ~5% (within 1 hour in the week
of 07-16), while counting on-call overstates it ~22%. v1.8.0 models what payroll pays
(on-call excluded from the threshold, still counted as worked time). If policy is ever that
on-call *should* accrue OT — FLSA "engaged to wait" time can — that is a payroll change,
and the pack's `ot_hours_incl_oncall` column already measures what it would cost.

**Q7 — For payroll: what explains the residual ~10% gap between inferred and paid OT in
the weeks of 07-23 and 07-30** (inference ≈ paid in 07-09 and 07-16)? Retro adjustments,
exempt staff, or OT paid under a code the PLC daily hours don't carry? The Cell 15.6
calibration prints the gap every run, so the answer is verifiable.

**Q8 — What is the definition behind "266 active PCT FTE" for July?** From the OT Week
files: employees on report average 289.8/week, "Payroll FTE Hours"÷40 averages 283.5, and
hours-capped FTE (Σ min(Work, 40)÷40) averages 270.6 over the four July payroll weeks. The
pack's confirmed caseload denominator is ticket-attributed distinct technicians (249 in
July). Any per-technician target needs to name which of these four populations it is set
against — they span ~16%.

---

## 2026-08-17 — ANSWERED by leadership: questions 1, 2 and 3 below are settled

Recorded here rather than deleted, so the question and its answer stay together. All three are
now reflected in notebook **v1.7.1** and in the metric dictionary, the Excel README and the
publishable PDF appendix — which previously listed them as open.

**Q1 — which denominator should a per-technician caseload target use? → ANSWERED.**
> *"ADC per technician should be calculated as total active patients on service in the period
> divided by the total active count of technicians active in the same period."*

So: **average daily census ÷ distinct technicians active in the period.** That is the middle
row of the table below (≈ 93.1 for Jul-2026), and it is what the pack already publishes at
company grain — `techs_equiv` equals `techs_distinct` there by construction. **Not** payroll
headcount (~300 → 77.9) and **not** average technicians on the road per weekday (~180 → 130.6,
the basis retired in v1.7.0).

Two consequences worth noting:

- **Q4 below is no longer blocking.** It was listed as a prerequisite only because a
  payroll-based ratio would have needed the ~300 figure reconciled. The confirmed denominator
  is the ticket-attributed count, so the payroll reconciliation is now informational.
- **v1.7.1 asserts the definition rather than assuming it** (Reconciliation 6). At company
  grain the apportioned headcount equalling the distinct count was an *incidental* property of
  how `techs_equiv` is built; it is now the published definition, so the notebook raises if a
  future change to the apportionment breaks it.

**Still an analyst decision, not a leadership one — flagged, not assumed:** at VP / metro /
warehouse grain the pack divides by the **apportioned** headcount so that site rows sum to the
company row. Read literally at site grain, the confirmed definition would use the raw distinct
count, which counts a technician working two sites at *both* and makes the grains
non-additive. **Company figures are identical either way.** Both columns ship on every Census
sheet, so either can be formed without a re-run.

**Q2 — should facility `(F)` and inpatient-unit `(IPU)` census count toward caseload? → ANSWERED: NO.**
> *"Facilities and inpatient-unit census should NOT count toward the technician caseloads."*

Already excluded since v1.5.0, so **no figure moves** — but the justification changes, and that
matters. Through v1.7.0 the exclusion was defended as *"matching the company APC snapshot
definition"*: inherited from another report rather than chosen for this one. It is now policy
with a date. `pt_days_unfiltered` / `adc_unfiltered` continue to carry the excluded population
so the size of the decision stays measurable, and `Contract Test` remains excluded on the same
basis.

**Q3 — are the NULL-`customer` census rows real patients? → ANSWERED: exclude them.**
> *"Null customer census should likewise be excluded from the technician caseload."*

The number does not move, but **this one was correct by accident and is now correct on
purpose.** Those rows were already falling out of the filtered figure only because
`customer NOT LIKE '(F)%'` evaluates to NULL for a NULL customer and `CASE WHEN NULL` takes the
`ELSE` branch. Nothing in the code said they should be excluded; three-valued logic was doing
it silently, and any rewrite of the predicate into a form where that no longer held would have
changed a published figure with no diff to explain it.

v1.7.1 adds `AND APC.customer IS NOT NULL` as a declared term of the filter, driven by a new
`CENSUS_EXCLUDE_NULL_CUSTOMER` flag. Verified against a SQL engine that the old and new
predicates select **identical rows** and produce an identical `pt_count` — the change is to the
*reason* the exclusion holds, not to the exclusion.

**Q4 — why do ~300 payroll technicians become ~250 attributed to tickets? → STILL OPEN**, but
downgraded from blocking to informational by the Q1 answer. Still worth closing: it is the
reason a per-technician figure cannot be quoted against a payroll headcount, and it is an
HR/payroll reconciliation rather than an analysis task.

---

## 2026-08-15 — raised by the census-per-technician audit *(Q1-Q3 answered 2026-08-17 — see above)*

Context: the v1.4.0 pack reported ≈ 120 patients on service per technician; ADC ÷ headcount is
≈ 85–93. Both figures are arithmetically correct — they use different denominators, and the ~40%
gap between them is average weekday attendance. The metric is restated in v1.5.0
(`insights/metric-audit-adc-per-tech-2026-08-15.md`). These four questions are what analysis
cannot settle on its own.

### 1. Which denominator should a per-technician caseload *target* use? *(blocks: any staffing target)*

Three defensible answers, and they are ~20% apart from each other and ~40% from what v1.4.0
published:

| denominator | Jul-2026 value | reads as |
|---|---|---|
| ~300 payroll technicians | **77.9** | patients per technician we pay for |
| 251 distinct technicians on tickets | **93.1** | patients per technician who did field work |
| 178.8 average technicians on the road per weekday | **130.6** | patients per technician actually deployed (v1.4.0) |

v1.5.0 publishes the middle one as the headline and carries the third for reconciliation. If
leadership intends the first — a payroll-based ratio — we need question 4 answered before it can
be produced reliably. **Please confirm which one any target or benchmark is stated against.**

### 2. Should facility `(F)` and inpatient-unit `(IPU)` census count toward technician caseload?

The APC snapshot excludes them; the ADC series every metric consumed did not. Both readings are
defensible — a facility patient may generate very different field work from a home patient — but
having both in use inside one notebook is not. v1.5.0 applies the APC exclusion everywhere and
prints what it is worth. **Confirm the exclusion is the right call**, or tell us the two
populations should be reported separately rather than netted.

### 3. Are the NULL-`customer` census rows real patients?

`NOT LIKE` is NULL-unsafe, so a census row with no customer value falls out of the filtered figure
silently. This behaviour is inherited from the v1.4.0 APC snapshot definition, not introduced by
the fix, and its volume is now printed on every run. If those are real patients on service the
filter needs an explicit `IS NULL` branch.

### 4. Why do ~300 technicians on payroll become ~250 attributed to tickets?

Part is known — 75.1% of payroll people tie to an attributed technician via the name match, and
some payroll rows are genuinely non-field roles. The remainder is not accounted for. Until it is,
**no per-technician metric can be quoted against a payroll headcount without naming its
denominator**, which is precisely the ambiguity that produced the 85-versus-120 question. This is
an HR/payroll reconciliation, not an analysis task.

---

## 2026-08-14 — raised while diagnosing the "July productivity drop"

Context: the July drop turned out to be a measurement artifact, now corrected
(`insights/insights-log.md`, notebook v1.2.0). Answering these would let us close the
remaining uncertainty and stop carrying a provisional caveat on warehouse pages.

### 1. What is the `Z CS` warehouse code, and who owns it? *(blocks: warehouse-level reporting)*

From 2026-06 a warehouse code `Z CS` began appearing on completed field tickets —
1,903 in June, 5,874 in July, 2,092 in the first 13 days of August, against a
background of 8–134 per month for the previous 17 months. The tickets are ordinary
deliveries and discharges, so this looks like a routing, dispatch or system change
rather than a new line of business.

- Was something changed in June — a dispatch process, a SERP configuration, a new
  intake or call-centre workflow ("CS" suggests customer service)?
- Should `Z CS` tickets carry a physical warehouse, and can the upstream feed be fixed
  to stamp one? We currently **infer** it from the technician's own route that day,
  which works (99.9% of July resolves) but is an inference we would rather not carry.
- Is the same code affecting other reporting — payroll allocation, billing, or the
  warehouse P&Ls the CFO sees?

### 2. Did five warehouses close at the end of June 2026, or were they renamed?

These had steady volume through June and then exactly zero in July:

| warehouse | 2026-04 | 2026-05 | 2026-06 | 2026-07 |
|---|---|---|---|---|
| R14 San Antonio WH 2 | 690 | 574 | 543 | 0 |
| R14 Harlingen | 123 | 140 | 91 | 0 |
| Mailouts - Texas | 124 | 114 | 76 | 0 |
| R15 T Storage | 76 | 69 | 58 | 0 |
| R01 Walker | 65 | 116 | 26 | 0 |

A closure and a rename look identical in the data but mean opposite things for a
trend: a closure ends a series legitimately and pushes work onto neighbours, while a
rename breaks the series and makes both the old and new site look wrong. This matters
for the few warehouses still showing a real July decline after correction (TXS Garland
−28.4%, R06 Batesville −23.0%, R09 Athens −21.3%, R12 Irving −17.2%) — we cannot yet
say whether that is absorbed territory or a genuine productivity change.

### 3. Should technicians who work multiple sites be credited to one warehouse or split?

Technicians now average **2.86 distinct warehouses per month** (was 1.29 in May-2026).
The dashboard splits a technician's day across sites by that day's ticket share, so
site totals add up to the company total. That is arithmetically honest, but if
operations considers a technician to "belong" to a home site regardless of where they
run, the site pages should be built that way instead. This is a reporting-definition
decision, not a data question — we need the owner's preference.

### 4. ~~`SERP_ACTIVE_TAGGED_INV` has zero lost-flagged rows~~ — ANSWERED 2026-08-14

Resolved by the v1.3.0 source audit: the column is dead (NULL on all 583,530 rows) but
the register had simply moved to `SERP_LOST_EQUIPMENT`, which is live and richer. Lost
equipment now reports. Two follow-ups below (questions 6 and 7) came out of it.

### 5. Nearly 3 in 10 stock-outs end with the order abandoned, not supplied *(new, highest value)*

Of 21,409 stock-out events in the window, **6,035 (28.2%)** have no completion on a live
ticket — their only completion evidence sits on a **canceled** ticket. Another 1,518
(7.1%) have no completion evidence at all and are genuinely open, at a median age of 115
days. Only **64.7%** were filled, typically in 6 days.

- Is a ~28% abandonment rate expected? If the patient's need was met another way (a
  substitute product, another branch, a purchase), the order being canceled is fine and
  we should measure "need met" rather than "this order filled".
- If it is not expected, this is the largest single operational finding in the dashboard,
  and the `StockOut_Canceled` sheet lists every one by site, product and age.
- Either way: **who owns the stock-out queue?** The 1,518 genuinely open orders have a
  median age of 115 days, which suggests nobody is working the list.

### 6. Who owns the lost-equipment feed, and can it be brought current? *(new)*

`SERP_LOST_EQUIPMENT` is live and now drives the dashboard, but it **stops at
2026-05-20** — 85 days behind every other metric. Every lost-equipment panel carries a
staleness banner as a result, and the last month must not be read as an improvement. Who
refreshes this, and on what cadence?

### 7. Are these four month-end lost-equipment spikes real losses or batch postings? *(new)*

The dashboard now surveils for bulk events. Beyond the confirmed 2025-08-01 discard
(excluded), four dates exceed 8× the daily median and are **still counted** in every
metric and trend:

| date | rows | pattern |
|---|---|---|
| 2025-01-31 | 1,588 | month end |
| 2025-04-30 | 1,504 | month end |
| 2025-05-31 | 920 | month end |
| 2026-05-15 | 1,854 | mid-month |

Three of the four are the last day of a month, which looks like a posting-date artifact
rather than 1,500 assets going missing in a day. If they are batch postings, the losses
are real but the *dates* are not, which flattens any within-month trend. Confirm and we
will either re-date them or add them to the exclusion list.

### 8. Payroll: confirm the de-duplication rule and how on-call is paid *(new)*

Before any overtime **dollar** figure is circulated, two payroll confirmations:

- `PLC_EMPLOYEE_HOURS` re-loads overlapping date windows rather than replacing them, so
  **12.4%** of rows are duplicates (one employee-day appeared 30 times). We de-duplicate
  on the full business tuple; an alternative rule (keep only the newest load) agrees to
  0.1%, so we are confident — but payroll should confirm which is correct.
- We count **On Call Hours as worked time** toward the 40-hour threshold and exclude PTO
  and Holiday. If on-call is paid but not hours-worked for FLSA purposes, overtime is
  slightly overstated and we will change it.

Also worth knowing: **25% of Patient Care Technician payroll records don't tie to any
technician on a ticket**, and 9.9% of overtime hours therefore cannot be attributed to a
site. Are those techs at locations we aren't mapping, or people whose ticket activity is
recorded under a different name?

### 9. Can we get notified when a reason code or status value changes upstream?

The dashboard filters tickets to a whitelist of 30 reason codes. If a code is renamed
upstream, its tickets vanish from every report with no error — the same class of
silent failure as `Z CS`, just via a different column. Diagnostic D1 now tracks the
excluded share each run, but a heads-up from whoever changes these values would let us
fix the whitelist before a board pack goes out rather than after.

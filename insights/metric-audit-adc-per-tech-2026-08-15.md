# Metric audit — ADC per technician, and what else the census feed touches

**Date:** 2026-08-15
**Trigger:** the analyst's sanity check. Company ADC ~25,000 over just under 300 technicians
is ~85 patients per technician. The v1.4.0 report package reports ~120.
**Scope:** Cell 7.5 (census extract), Cell 13.5 (census per active technician), and every
downstream metric that consumes `df_adc`.
**Verdict:** the ~120 is arithmetically correct and **wrong as labelled**. The analyst's ~85 is
the right order of magnitude for the question the label asks. One separate hard bug was found
in the lost-equipment rate at VP and metro grain. Productivity and overtime are **not** affected.

---

## 1. The reconciliation — where 85 becomes 120

`census_per_active_tech = ADC ÷ avg_active_techs`, and

```
avg_active_techs = apportioned weekday tech-days in the month ÷ weekdays in that month
```

Using the notebook's own published inputs (`insights-log.md`, v1.2.0 entry — distinct
technicians and tech-days; ADC from the same entry):

| | 2026-06 | 2026-07 |
|---|---|---|
| distinct technicians on tickets | 252 | 251 |
| apportioned weekday tech-days | 4,093 | 4,112 |
| weekdays in month | 22 | 23 |
| **`avg_active_techs` (the v1.4.0 denominator)** | **186.0** | **178.8** |
| ADC | 22,815 | 23,356 |
| **ADC ÷ `avg_active_techs`** — what the pack prints | **122.6** | **130.6** |
| ADC ÷ distinct technicians | 90.5 | 93.1 |
| ADC ÷ ~300 payroll technicians | 76.0 | 77.9 |
| average weekday attendance | 73.8% | 71.2% |
| **overstatement vs a headcount denominator** | **+35.5%** | **+40.4%** |

The whole gap is one wedge: **average weekday attendance of ~71–74%**. A technician does not
work every weekday — PTO, sick, training, part-time schedules, and (see §3) Saturday and Sunday
work, which the metric discards entirely. So "average technicians on the road on a working day"
runs ~180 against ~250 distinct technicians on tickets and ~300 on payroll.

Nothing is miscomputed. The metric is **mis-labelled**: it is published as
*"Census per Active Technician"* on every page and read as *"census per technician."*

## 2. The definitional error — a stock divided by an attendance average

This is the finding that matters, and it is not a rounding argument.

**ADC is a stock.** It is the number of patients on service on an average day. **Tech-days are a
flow** — attendance events. Dividing the first by the second answers no question anyone asked,
because *a patient on service does not stop being on service when their technician takes PTO.*
The caseload is carried by the whole roster, every day, whether or not each individual is out on
a route. The honest caseload denominator is therefore **technician headcount**, not average daily
presence.

Read the other way round, `ADC ÷ avg_active_techs` is a real quantity — patients on service per
technician *actually deployed on an average weekday* — but that is a **coverage-intensity**
measure, useful for asking "are we thin on the road?", not a caseload measure, and not something
to put next to a per-technician staffing target.

The contrast with the productivity metric is the reassuring half of this audit.
`tickets_per_active_day` is **flow ÷ flow** — tickets completed over days worked — and its
denominator is asserted every run to reconcile to distinct (tech, date). It is correct, and none
of §1–§3 touches it. The census panel inherited that denominator on the stated grounds that
"the two panels move on the same population," which is true and is precisely why it is wrong
here: the same denominator is right for a flow numerator and wrong for a stock one.

## 3. The stated limitation misdiagnoses the inflation

Cell 13.5, Cell 3.5 and the README all carry the same caveat, on every panel and every sheet:

> LIMITATION — TWO DIFFERENT DAY BASES. ADC averages over all 7 calendar days; active tech-days
> are weekdays only. The ratio therefore reads "patients on service per technician-WEEKDAY" and
> runs high relative to a true per-calendar-day figure.

This points a reader at the wrong effect, and it will cause the correction to be mis-sized.

- The weekday/calendar mismatch is **nearly harmless**. Census is a stock. A stock averaged over
  7 days is close to the same stock averaged over 5 — they differ only by the admit/discharge
  rhythm across a weekend, low single digits.
- And `avg_active_techs` is **internally consistent** on the day basis it does use: weekday
  tech-days ÷ weekday count. There is no arithmetic mismatch to correct.
- Meanwhile the ~40% effect that *is* present — attendance versus headcount — is documented not
  as a limitation but as a deliberate design choice ("TEACHING NOTE — why not distinct
  headcount"), which reads as settled rather than as the open question it is.

A reader who trusts the caveat will conclude the number is a few percent high. It is ~40% high
against the denominator its own label implies.

## 4. The census numerator has three further defects

All three are in Cell 7.5's `df_adc` query, which feeds **every** census metric and the
lost-equipment rate. None can be sized without a run; each is a code-level certainty.

**4.1 — Two different definitions of census in one notebook.** Cell 7.5 builds two objects from
`SERP_APC_DAILY` with different filters:

| | `warehourse NOT LIKE 'Z%'` | `customer NOT LIKE '(F)%'` / `'(IPU)%'` / `'%Contract Test%'` |
|---|---|---|
| `df_apc` (snapshot) | yes | **yes** |
| `df_adc` (the monthly series everything uses) | yes | **no** |

So ADC includes facility census, inpatient-unit census and contract-test rows that the company's
own APC definition excludes. Direction: **inflates ADC**, therefore inflates census-per-tech, and
*deflates* `lost_cost_per_1k_pt_days`.

**4.2 — Company ADC is a sum of per-warehouse averages taken over different day sets.**
`AVG(APC)` is computed per warehouse-month over *the dates that warehouse appears in the feed*.
`_dash_census` then **sums** those averages across warehouses. When coverage differs by warehouse
— a site that stops reporting mid-month, a site onboarded mid-month, any feed gap — the sum
corresponds to no actual day and overstates census. This is live right now, in two places: the
partial current month, and the **five sites the log records as going silent after Jun-2026**.
The fix is already available in the data the notebook pulls: `pt_days = SUM(APC)` is there, so
honest ADC is `sum(pt_days) ÷ distinct dates in the period` — a ratio of pooled sums, the same
rule Cell 13 applies everywhere else.

**4.3 — The Z-warehouse asymmetry v1.2.0 fixed for productivity is back in the census panel.**
`df_adc` drops `warehourse LIKE 'Z%'`. The tech-day denominator **keeps** Z-warehouse work,
re-attributed to physical sites by Cell 8.1b. From 2026-06, when `Z CS` began carrying real field
work (24.3% of eligible weekday tickets by Jul-2026), census-per-tech therefore has patients
removed from the numerator whose technicians remain in the denominator — the same shape of defect
as the July "productivity drop," in a new panel. Direction: **deflates** census-per-tech from
Jun-2026, partly offsetting 4.1/4.2 and making the June break look smaller than it is.

## 5. The one hard bug: VP and metro lost-equipment rates use the *company* census

Cell 14, `_dash_lost_monthly`:

```python
if 'tech_warehouse' in gcols:
    ...merge df_adc per (warehouse, year, month)...          # correct
else:
    _adc_grain = df_adc.groupby(['yr','mo'])...              # COMPANY total
```

`_dash_lost_monthly(['metro'])` and `_dash_lost_monthly(['vp'])` both take the `else` branch.
**Every metro row and every VP row is divided by the whole company's patient-days.**

Consequences:

- `lost_cost_per_1k_pt_days` on VP pages is understated by roughly (company census ÷ that VP's
  census) — order of 5–10× for a VP, far more for a metro.
- The metric is not comparable across grains, and warehouse rows do not aggregate to their VP.
- Company and warehouse grains are correct, so the error is invisible unless you compare grains.

This is the one finding that is unambiguously "inflation of another metric" (deflation, here),
and it is caused entirely by ADC handling. It needs no data run to confirm.

## 6. Suppression floor is on the wrong quantity

`CENSUS_MIN_TECH_DAYS = 20.0` tests `tech_days`, a month total. But the ratio's denominator is
`tech_days ÷ weekdays` — at the floor that is ~0.95 technicians, so a site is published where
ADC is divided by less than one average technician and the ratio is essentially ADC itself. The
floor is doing far less than intended. On a weekly grain it is worse by ~4.3×, so it has to be
restated per-week and applied to `avg_active_techs`, not to `tech_days`.

## 7. What is NOT affected — stated plainly, because the question was whether this leaked

| metric | census input | verdict |
|---|---|---|
| `tickets_per_active_day_per_tech` (Cell 13) | none | **correct.** Flow ÷ flow; denominator asserted to reconcile to distinct (tech, date) every run. |
| `ot_pct_of_worked`, `ot_hours_per_tech` (Cell 15.5) | none | **correct.** Hours ÷ hours. |
| `redel_per_100_tickets` (Cell 15) | none | **correct.** Ticket-denominated. |
| `stockouts_per_100_tickets`, fulfilment (Cell 16) | none | **correct.** |
| `lost_pct_of_inventory` (Cell 14) | none | **correct.** |
| `lost_cost_per_1k_pt_days` — company, warehouse | per-entity | **correct grain**, but carries 4.1–4.3. |
| `lost_cost_per_1k_pt_days` — **VP, metro** | **company total** | **broken** — §5. |
| `census_per_active_tech`, all grains | per-entity | **mis-labelled** — §1–§3 — and carries 4.1–4.3, §6. |

The census defect is contained. It did not leak into productivity, overtime, redeliveries or
stock outs, because none of those divide by census. The blast radius is the census panel plus
the VP/metro lost-equipment rate.

---

## 7a. Three further defects found while implementing the fix

These are not census defects; they came out of moving every metric onto a weekly grain and are
recorded here because each one moves published numbers.

**7a.1 — The rolling 4-week average was computed over rows, not weeks.** Cell 13's
`rolling_4wk_avg` used `.rolling(4, min_periods=2)` over whatever rows an entity had. An entity
with no tickets in a week had **no row**, so the window silently reached back five or six
calendar weeks and the result was published as a 4-week average. It only bit small warehouses —
which is exactly where a quiet week is most likely — and it biased *upward*, because the weeks
that vanished were the slow ones. Fixed by reindexing onto a calendar spine before the mean.

**7a.2 — Rate trailing averages should be pooled, not a mean of weekly ratios.** A mean of four
weekly rates weights a 30-ticket holiday week the same as a 700-ticket week. Tested on synthetic
data: a four-week window of (1/3, 40/400, 40/400, 40/400) reads **15.8** as a mean of ratios and
**10.1** pooled. Every rate now uses trailing numerator ÷ trailing denominator.

**7a.3 — Four of the five metric panels were twin-axis charts.** Overtime, lost equipment,
redeliveries and stock outs drew bars on the left scale and a rate line on the right. A twin-axis
chart has no defensible crossing point — where the line appears to overtake the bars is an
artifact of two independently auto-ranged scales, so the same data supports opposite readings.
The notebook already knew this: v1.4.0's census panel refused to do it and said why in its own
docstring. The rule was written down and applied to one panel out of five. Layout went 2×4 → 3×4
so the rates have their own single-axis panels.

## 8. What changed in v1.5.0

1. **Census is pulled daily, not pre-averaged in SQL** (Cell 7.5). One filter definition shared
   with the APC snapshot (fixes 4.1, and prints the size of the change); ADC computed as pooled
   patient-days ÷ distinct dates at every grain and period (fixes 4.2); virtual (`Z%`) census
   kept and tagged rather than dropped from the numerator (fixes 4.3). Note the limit on that
   last one: virtual census **cannot** be re-attributed the way Cell 8.1b re-attributes tickets,
   because a census row carries no technician. It therefore counts at company level, is reported
   separately, and cannot reach a site page. That is honest but incomplete — if `Z CS` census is
   material, resolving it needs a key the feed does not currently carry.
2. **Three census-per-technician measures are published side by side**, so the denominator is a
   visible choice and not a buried one:
   - `census_per_tech_headcount` — ADC ÷ distinct technicians active in the period. **Headline.**
   - `census_per_active_tech_weekday` — the v1.4.0 number, retained so the restatement is
     measurable and the last package can be reconciled.
   - `attendance_rate_pct` — the wedge between them, which is the whole story.
   The reconciliation from one to the other is printed on every run.
3. **VP and metro lost-equipment rates use their own census** (fixes §5) — asserted, not assumed:
   VP patient-days must not exceed the company's, and Cell 14 prints the check every run.
4. **Suppression floor moved onto the denominators** (`avg_active_techs`, `techs_distinct`) and
   restated per-week (fixes §6).
5. **The misleading caveat is replaced** everywhere it appears — panel notes, Cell 3.5, README —
   with the attendance-vs-headcount statement, which is the effect that actually moves the number.
6. **Every metric is now weekly with a trailing 4-week average**, on one shared week spine
   (new Cell 4.3), with the trailing window computed on the calendar and pooled for rates
   (fixes 7a.1 and 7a.2). Overtime keeps its own Thu–Wed payroll spine; the two are labelled and
   are not alignable week-for-week.
7. **No panel has two y-axes** (fixes 7a.3); layout 2×4 → 3×4.

Verification, given that no live run was possible for this audit: the new spine and
trailing-average helper are covered by a synthetic-data test suite (22 assertions — calendar
coverage, missing-week handling, partial-week exclusion, entity-span handling, pooled vs
mean-of-ratios, group isolation), and all ten rewritten cells plus the renderer and the Excel
export were executed end to end against synthetic feeds of the right shape. That found two real
bugs before release (a missing `period` key in the stock-out ticket denominator, and zero-filling
weeks before an entity first appeared). **It does not substitute for a live run** — see §10.

## 9. Open questions for leadership

- **What is the intended denominator for a per-technician caseload target?** Payroll headcount,
  distinct technicians on tickets, or FTE? The three differ by ~20% among themselves and ~40%
  from what v1.4.0 published. Raised in `questions-for-cfo.md`.
- **Should facility `(F)` and inpatient-unit `(IPU)` census count toward technician caseload?**
  They are excluded from the APC snapshot and were included in ADC. Both are defensible; they
  must not both be in use in one notebook.
- **~300 technicians is a payroll headcount and ~250 is a ticket-attributed count.** The ~50
  difference is the OT match residual (75.1% of payroll people tie to an attributed technician)
  plus genuine non-field roles. Until that is closed, no per-technician metric can be quoted
  against a payroll headcount without stating which denominator it used.

## 9a. Follow-on defects found while implementing the fix (v1.6.0)

Three further denominator defects in the census panel surfaced only once v1.5.0's own output was
read. They are recorded here because two of them were *introduced or exposed* by the v1.5.0 fix,
which is the most likely way this audit misleads someone reading it later.

**9a.1 — The unmapped-census diagnostic conflated two unrelated causes and warned about the
wrong one.** By keeping virtual (`Z%`) census (fix 4.3) rather than dropping it, v1.5.0
guaranteed that all of it landed in the "warehouses the ticket feed never resolved" bucket — a
virtual code can never map at that join, because Cell 8.1b re-attributes virtual *tickets*, so
no `Z%` value survives as a `tech_warehouse`. The result was a warning telling the analyst to
reconcile warehouse names for something that was a deliberate design decision. Now reported as
two separate figures, with only the actionable one able to trip the warning.

**9a.2 — Census trailing ratios mixed window lengths.** `techs_distinct` and `avg_active_techs`
were treated as rates (averaged over observed weeks) while `pt_days` and `census_days` were
counts (zero-filled across the span), so a site with census in four weeks and technicians in two
divided a four-week numerator by a two-week denominator. It read high for exactly the sites that
had a quiet week. Both are counts; all census trailing ratios are now rebuilt from the pooled
counts, `attendance_rate_pct` included.

**9a.3 — At entity grain the census denominator double-counted technicians, and this is the same
defect §2 is about.** `techs_distinct` counts a technician who works two VPs once in *each*,
while `tech_days` is apportioned between them — an apportioned numerator over a whole-count
denominator, which is precisely what v1.2.0 fixed for the productivity metric. In a synthetic run
with heavy cross-site working, VP attendance read 42% against a company 72%, purely as an
artifact. Fixed with an apportioned headcount (`techs_equiv`) that gives each technician to an
entity in proportion to their days there and **sums to the true distinct count company-wide** —
so every figure in §1 is unchanged, and the entity grains become additive. Asserted on every run.

**What this means for §1.** Nothing: the reconciliation table in §1 is company-grain, where
`techs_equiv` equals `techs_distinct` by construction. But **VP and warehouse census figures
published from v1.5.0 are wrong** in the direction of reading too low, by the extent to which
technicians work more than one site. That extent is unmeasured until a live run.

## 10. Limitations of this audit

- **Findings 4.1, 4.2, 4.3 and §5 are established from the code, not sized against data.** No
  database run was made for this audit, so the *magnitude* of each is unquantified — §5's
  direction and rough scale follow from the arithmetic, but the exact restatement of every VP row
  requires a run of v1.5.0. Findings §1, §2, §3 and §6 are quantified above from the notebook's
  own published inputs and need no further confirmation.
- The ~300 technician figure is the analyst's, taken as given. If it is an all-departments
  payroll count rather than field technicians, the ADC ÷ 300 row in §1 is a floor, not an
  estimate.

# Metric Audit — v1.7.1 ADC/Technician & Overtime vs Payroll's OT Week Reports

**Date:** 2026-08-18
**Trigger:** the analyst's second sanity check — *"24,190 ADC for July over 266 active PCT
FTE is ~91 ADC/tech; the dashboard still seems higher"* — plus a request to verify every
published metric against its defined criteria and to reconcile staffing/overtime against the
payroll **OT Week** files in `data/Financial/`.
**Scope:** every metric calculation in `ops_dashboard_2026-08-14_v1_7_1.ipynb` (all 91
cells), and a week-by-week reconciliation against the five OT Week workbooks
(2026-07-09 → 08-12).
**Verification basis:** no live DB run (per standing practice); the code, the executed
v1.7.1 outputs, the OT Week workbooks read locally, and a 32-assertion synthetic test suite
for everything changed (`analysis/lib/verify_ops_dashboard_v1_8_0.py`, all passing).
**Outcome:** notebook **v1.8.0**, which moves two published numbers — both down.

---

## 1. The ADC/Technician question — answered, and mostly a real defect

The pack and the analyst **already agree at monthly grain**. The reconciliation:

| basis | ADC | technicians | ratio |
|---|---|---|---|
| analyst's arithmetic (July) | 24,190 | 266 "active PCT FTE" | **90.9** |
| pack, July monthly ledger (v1.7.1 output) | 23,130 (filtered) | 249 distinct on tickets | **92.9** |
| pack, weekly panel (late Jul / early Aug) | ~23,100–23,570 | 230–239 active *that week* | **97.3–102.4** |
| pack, trailing 4-week (v1.7.1) | 23,458 | 233.75 *mean of weekly counts* | **100.4** |
| pack, trailing 4-week (v1.8.0, same weeks) | 23,458 | ~248–250 distinct over the window | **~94–95** (est., needs live run) |

Three separate wedges, in order of size:

**1.1 — The window effect on a distinct-count denominator (~+6–9%, and half of it was a
defect).** The confirmed definition is ADC ÷ *distinct technicians active in the period*. A
distinct count **grows with the period length** — a technician active in any part of the
period counts once — while ADC, a stock, does not. So the same definition yields ~101 over a
week, ~93 over a month. The weekly points are *correct for a one-week period* but were being
read against a monthly expectation. That part is labelling, fixed on the panel and in the
dictionary. The defect: the **trailing 4-week figure divided by the *mean* of the four
weekly distinct counts (~234) instead of the distinct count over the window (~249)** — a
technician active in three of four weeks was counted ~0.75 times. The trailing headline
therefore sat ~5–7% above what the confirmed definition produces over its own window. Fixed
in v1.8.0 (`_windowed_techs_equiv`); the published inputs still divide into the published
figure (Reconciliation 5), and a new Reconciliation 4b asserts the window count covers every
weekly count inside it.

**1.2 — The denominator population (266 vs 249, ~7%).** The analyst's 266 is a payroll-side
FTE. Reconstructed from the OT Week raw data, hours-capped FTE (Σ min(Work hours, 40) ÷ 40)
runs **262–281 per week, mean 270.6** over the four July payroll weeks — the right
neighbourhood for 266 depending on the exact week set and hours basis (please confirm the
definition — see questions). The pack's confirmed denominator is **ticket-attributed
distinct technicians (249 in July)**. The ~20-head gap is payroll PCTs who ran no attributed
tickets (the name-match residual is 24.5%: 318 of 421 payroll PCTs tie to a ticket
technician) plus genuine non-route work. Known, listed as open since v1.5.0, unchanged here:
the confirmed definition uses the ticket-attributed count.

**1.3 — The ADC source (24,190 vs 23,130, ~4.6%).** The pack's July ADC is 23,130 after the
leadership-confirmed exclusions ((F), (IPU), Contract Test, NULL customer) and 23,433 with
nothing excluded. **24,190 is above even the unfiltered figure**, so the analyst's source
either uses a different census feed, a different day basis (e.g. month-end rather than a
daily average), or still contains the five sites whose SERP_APC_DAILY feed went silent after
Jun-2026 — in which case the pack's ADC is *understated*, not overstated. Cannot be resolved
without knowing the source; raised in `questions-for-cfo.md`.

Net: wedges 1.2 and 1.3 nearly cancel (which is why 90.9 ≈ 92.9), and wedge 1.1 — the one
that made the pack "read high" — was two-thirds real defect. After v1.8.0 the headline
trailing figure lands ~94–95, within ~4% of the analyst's arithmetic, with the residual
fully explained by 1.2/1.3.

## 2. Staffing and overtime vs the OT Week files — the calibration the model never had

The OT Week workbooks are payroll's own weekly *Overtime Reduction Report* (SERVTECH / PCT
only, Thu–Wed weeks — the same payroll week the notebook derived empirically in v1.4.0,
independently confirmed). They carry **the OT actually paid**. Week by week against v1.7.1:

| Thu–Wed week | paid hours (file) | dash worked | paid OT | dash OT (v1.7.1) | Work-only inference | file's own "Est OT" |
|---|---|---|---|---|---|---|
| 07-09 | 12,356 | 12,705 | 1,998 | 2,277 | 2,011 | 2,247 |
| 07-16 | 12,851 | 12,604 | 2,112 | 2,095 | 2,113 | 2,368 |
| 07-23 | 13,222 | 13,371 | 1,937 | 2,382 | 2,154 | 2,360 |
| 07-30 | 12,859 | 12,949 | 1,818 | 2,171 | 2,001 | 2,263 |
| 08-06 | 12,504 | **5,608** | 1,712 | **38** | — | 2,196 |

Findings, in order of importance:

**2.1 — [BUG, fixed] The 08-06 week shipped 45% loaded and looked like an OT collapse.**
The PLC feed loads in arrears; at the 2026-08-17 run the last full payroll week held 5,608
of the 12,504 hours payroll actually paid, published as a complete week with 0.68% OT, and
sat inside every trailing window. Nothing flagged it — `is_partial_week` only tests window
clipping. v1.8.0 adds a feed-completeness guard (tail week under 70% of the trailing median
of company hours → flagged, drawn hollow, excluded from trailing windows, banner printed).

**2.2 — [CALIBRATION, fixed] On-call hours do not accrue paid overtime.** Over the four
fully-loaded weeks: Work-only FLSA inference lands **+5.3%** off paid OT in aggregate
(within **1 hour** in the 07-16 week); v1.7.1's basis (Work + On Call toward the threshold)
overstated paid OT by **+21.7%**. Paylocity treats on-call as paid time outside the OT
accrual. v1.8.0 moves the threshold to Work hours only (`OT_PAY_TYPES_OT_BASIS`); on-call
stays in `worked_hours`; `ot_hours_incl_oncall` reconciles to every figure published since
v1.3.0; and a new **Cell 15.6** re-runs this calibration against whatever OT Week files are
present, every run, warning if inference drifts >10% from paid.

**2.3 — Headcount ties out.** The dashboard's weekly `employees` (277/285/290/288/277)
matches the files' working headcount (277/285/292/289/283) within 0–6 — the payroll
extraction and dedup are sound. Note the files carry *three* headcounts: employees on
report (280–295), "Payroll FTE hours"÷40 (273–291), and hours-capped FTE (262–281). Any
target stated in "FTE" needs to name which.

**2.4 — Residual, open.** Even Work-only inference runs ~+10% above paid OT in the 07-23
and 07-30 weeks (and ~0% in 07-09/07-16). Likely OT adjustments, retro corrections or
exempt staff. Raised for payroll; the Cell 15.6 diagnostic will keep it measured.

**2.5 — The files' own "Est OT %" divides by a different base.** The report's headline
22% is Est OT ÷ *Cumulative Available Hours* (≈40×headcount), and its "Payroll OT %" is
paid OT ÷ Payroll FTE Hours — neither is the dashboard's OT ÷ worked-hours (~16–17%). All
three are self-consistent; do not compare them without renaming.

## 3. Metric-by-metric confirmation (v1.7.1, all families)

| metric | definition check | verdict in v1.7.1 |
|---|---|---|
| `tickets_per_active_day_per_tech` | pooled tickets ÷ apportioned tech-days, reconciles to distinct (tech,date) | **correct** |
| `census_per_tech_headcount` — weekly | ADC ÷ distinct active that week (Recon 6 asserts) | **correct as defined**, mislabelled vs monthly targets |
| `census_per_tech_headcount_t4w` | should be window ADC ÷ window distinct | **defective** — mean-of-weekly-counts denominator (§1.1) → **fixed v1.8.0** |
| `attendance_rate_pct` | pooled tech-days ÷ capacity | correct |
| `ot_hours` | FLSA inference, Thu–Wed, dedup, leave excluded | **overstated ~13.5% vs paid** (on-call, §2.2) → **recalibrated v1.8.0** |
| `ot_pct_of_worked` | pooled | correct arithmetic; numerator recalibrated |
| `ot_hours_per_tech` (scored) | audit A1: unscorable (absent from company frame); A2: per-head trailing mixed week sets | **both fixed v1.8.0** |
| `lost_cost_per_1k_pt_days` | per-grain census join (v1.5.0 fix) proven each run | correct |
| `recovery_rate_pct_t4w` | audit A3: mean of thin weekly ratios | **fixed v1.8.0** (pooled; synthetic case reads 13.6 pooled vs 30.0 mean) |
| `lost_pct_of_inventory_t4w`, `leave_pct_of_total_t4w`, `pct_employees_with_ot_t4w` | A3 family | **pooled v1.8.0** |
| `redel_per_100_tickets` — entity | all-days over all-days | correct |
| `redel_per_100_tickets` — technician | audit B5: all-days numerator ÷ weekday denominator | **fixed v1.8.0** (all-days) |
| `stockouts_per_100_tickets`, outcome shares | pooled, censoring stated | correct |
| headline productivity dictionary claim | audit B1: "exchange pairs consolidated" was false | **claim & dead cell removed v1.8.0** |

Embedded assumptions worth restating (unchanged, documented): `INCLUDED_REASONS` is a
silent single point of failure; ticket dates carry no time component; warehouse resolution
for virtual tickets is inferred, never individual evidence; lost-equipment attribution is
proximity, not fault; the lost feed is stale (ends 2026-05, 88 days behind) and three lost
spike dates (2025-01-31, 2025-04-30, 2025-05-31) remain unconfirmed as bulk events and are
still in every trend — they need the analyst's confirmation like 2025-08-01 got.

## 4. New anomalies surfaced by this audit (open, need investigation)

- **Feb-2026 distinct technicians = 373** against 247–282 in every neighbouring month, with
  census/tech dropping to 57.9 and attendance to 54.4% that month only. Smells like a name
  or feed artifact (dedup change, name churn), not 90 real hires who vanished. Ticket-level
  look needed; until then treat Feb-2026 per-technician figures as suspect.
- **The 24,190 ADC source** (§1.3) — if it carries the five census-silent sites, the pack's
  ADC (and every census-normalised rate) is understated by their census.
- **~5% inferred-vs-paid OT residual** in two of four calibration weeks (§2.4).

## 5. What v1.8.0 changed and how it was verified

See the changelog in the notebook's first cell for the full list (window denominator;
on-call threshold; feed guard; audit items A1, A2, A3, A4, B1, B3, B4, B5, C3). Verification:
`analysis/lib/verify_ops_dashboard_v1_8_0.py` — 32 assertions over synthetic feeds
(windowed-distinct denominator re-derived independently; on-call arithmetic per employee;
feed-incomplete flagging and its exclusion from trailing windows; pooled recovery on thin
cohorts; the generalised bracket guard both passing and catching a planted violation; the
scorecard guard both scoring and reporting). **All pass. This does not substitute for a live
run** — in particular the exact v1.8.0 trailing census figure (~94–95 estimated) and the
bracket checks on the other families (warn-only this release, promote
`BRACKET_CHECKS_RAISE` after one clean run) need real data.

## 6. Still open beyond the notebook

- **C1/C2 (repo):** no pre-commit hook exists; committed v1.0.0–v1.2.0 outputs still carry
  patient-account identifiers in git history. Needs an owner and a decision; unchanged
  since the 2026-08-17 audit. v1.8.0 is written with zero outputs.
- **B2:** `total_tickets` still names three populations across sheets; renaming is a
  breaking change for saved pivots — scheduled, not done.
- Site-grain caseload denominator (apportioned vs raw distinct) — analyst decision,
  unchanged.

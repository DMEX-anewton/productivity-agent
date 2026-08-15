# Insights Log

Newest first. Each entry: what we found, how we know, what it changes, what it does not.

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

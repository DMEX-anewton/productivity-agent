# Insights Log

Newest first. Each entry: what we found, how we know, what it changes, what it does not.

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
  has **zero** lost-flagged rows company-wide, confirmed by probe. That is an upstream
  feed issue, not a filter bug.

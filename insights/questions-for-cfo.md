# Open Questions for Leadership

Questions analysis cannot answer from the data alone. Newest first.

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

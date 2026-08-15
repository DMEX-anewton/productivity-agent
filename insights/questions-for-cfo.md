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

### 4. `SERP_ACTIVE_TAGGED_INV` has zero lost-flagged rows company-wide

Unrelated to the July issue, but it means every lost-equipment panel on the dashboard
is blank and has been for at least the 2025-01 → 2026-08 window. The probe confirms
zero lost-flagged rows exist at all, so this is not a date-filter bug. Were the Lost
flags cleared or purged, or has the process for marking equipment lost changed? Until
answered, we have no lost-equipment visibility at any level.

### 5. Can we get notified when a reason code or status value changes upstream?

The dashboard filters tickets to a whitelist of 30 reason codes. If a code is renamed
upstream, its tickets vanish from every report with no error — the same class of
silent failure as `Z CS`, just via a different column. Diagnostic D1 now tracks the
excluded share each run, but a heads-up from whoever changes these values would let us
fix the whitelist before a board pack goes out rather than after.

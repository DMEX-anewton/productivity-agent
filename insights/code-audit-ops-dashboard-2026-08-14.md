# Code Audit — `analysis/ops_dashboard_2026-08-14_v1_2_0.ipynb`

Audited 2026-08-14 against the live DMEEXPRESS warehouse (read-only). Every claim
below was checked against data, not just read off the source. Severity order.

Legend: **[BLOCKER]** stops a v1.3.0 section from being correct ·
**[BUG]** wrong output today · **[RULE]** conflicts with `CLAUDE.md` ·
**[DEAD]** unused work · **[NIT]** cosmetic / hygiene

---

## A. Blockers for the three v1.3.0 sections

### A1 [BLOCKER] The lost-equipment source is dead, and the diagnostic stopped one step short
`Cell 7.4` filters `WHERE ATI.Lost IS NOT NULL`. **`SERP_ACTIVE_TAGGED_INV.Lost` is
NULL on all 583,530 rows** — zero distinct non-null values. So the panel cannot ever
populate. v1.0.1's probe correctly reported "0 lost-flagged rows exist" but concluded
"upstream feed issue" and stopped; the data had in fact moved:

| candidate source | rows | coverage | verdict |
|---|---|---|---|
| `SERP_ACTIVE_TAGGED_INV.Lost` | 0 | — | dead column |
| `SERP_ACTIVE_TAGGED_INV.Lost_Date` (ignoring `Lost`) | 188,912 | 2019 → 2026 | 96% are `Status='Rented'`; not a lost register |
| `SERP_ACTIVE_TAGGED_INV_HISTORY` | 537,335 lost rows | 2019-03 → **2025-03-30** | froze 17 months ago |
| `SERP_LOST_EQUIPMENT_MANUAL` | 53,424 | 2024 → 2025 | stale |
| `Quarterly_Lost_Equipment` | 3,047 | 2024-06 only, 1 warehouse, 1 asset repeated | abandoned |
| **`SERP_LOST_EQUIPMENT`** | **91,023** | **2025-01 → 2026-05** | **live source** |

`SERP_LOST_EQUIPMENT` also carries what the current panel lacks: `Lost Reason`,
`Resolution` (No resolution 79,717 / Recover no bill 10,695 / Discard no bill 610 /
Recover and bill 1), `Resolved Date`, `Unit Cost`, `Product Name`, `Asset Tag`,
delivery + pickup order IDs, and `Discharged Days`. Its `Warehouse` values match
`SERP_WAREHOUSES` **71 of 72** — far cleaner than the ticket feed.

Two traps in it:
- `Lost Date` is **not a date** — values look like `01/02/2025<br/>(147)`, an HTML
  fragment with a trailing counter. `TRY_CONVERT` fails on **100%** of 91,023 rows,
  which is why a naive port would silently produce an empty panel *again*.
  `LEFT([Lost Date],10)` with style 101 parses 100%.
- `Unit Cost` is a currency string (`'$11.88'`) — needs `clean_numbers`.

### A2 [BLOCKER] The stock-out "no physical warehouse exists" premise is false
`Cell 3.5` and `Cell 16` both state: *"Every stock-out row sits in the virtual
warehouse 'Z Equipment Needed', so no physical warehouse/metro exists on the data."*
Warehouse and metro pages therefore print an n/a notice instead of numbers. Measured:

- `EnRoute` rows: 244,326 in `Z%` **but 5,726 across 65 real warehouses**.
- `Territory` is populated with real site names too (R05 Birmingham (Hoover), R16
  Temple, R09 Marietta …), not only `Equipment Needed`.
- Decisively: joining `[Order]` to `SERP TRANSACTIONS` matches **20,230 of 21,438**
  EnRoute orders, and the resolution ladder built in v1.3.0 (order join on the analysis
  ticket set → order join widened to any reason → the row's own non-virtual warehouse →
  `Territory` on an exact master match) attributes **76.0%** of orders to a real site.

So three-quarters of the backlog *can* be attributed to a physical site. The notice is
suppressing available signal.

### A3 [BLOCKER] `Status='EnRoute'` is not an open backlog
The notebook reports "21,438 orders open, oldest open 1,021 days" and frames the trend
as backlog aging. But **19,891 of those 21,438 orders already carry a completion date**,
so the rows are plainly retained after the stock-out is dealt with.

`Status` simply is not maintained. Every other status value is frozen at a single load
date of 2026-01-20 (Completed, Approval Needed, Received, Next Stop, Pending Review all
created that day; Canceled and Reconciled stop there too).

**But "has a completion date" is not the same as "was fulfilled"** — and this is where I
first got it wrong. Splitting the completion evidence by the *ticket's* status:

| evidence on the order's tickets | orders | share |
|---|---|---|
| completion on a **live** ticket (Reconciled 13,771 / Completed 21 / EnRoute 65) | **13,857** | 64.6% |
| completion **only on a `Canceled` ticket** — abandoned, not delivered | **6,038** | 28.2% |
| a ticket exists but no completion date | 335 | 1.6% |
| no ticket at all | 1,208 | 5.6% |

A canceled ticket carries a `Completed_Date` too, so the naive test returns 93%
fulfilment. The honest read is a **three-way outcome**: fulfilled 64.6%,
canceled/abandoned 28.2%, genuinely open 7.2% — and the abandoned group is the most
operationally interesting of the three, since nearly three in ten stock-outs end with
the order dropped rather than supplied.

Consequences:

- "Oldest open 1,021 days" is a stale row, not an aging crisis; the genuine backlog is
  ~1,518 orders (in-window) with a median age of 115 days.
- The notebook's stated limitation — *"a stock-out created in May and fulfilled in June
  disappears from this query entirely"* — is **also wrong**: rows are retained. So
  `EnRoute` by creation month **is** true incidence, and time-to-fulfil is computable
  from the ticket join (P25 3 / median 6 / P75 9 / P90 17 days). The section can be much
  stronger than the aging view it currently offers.
- Fulfilment must be tested against the **unfiltered** ticket feed. Measuring it against
  `df_tx` understates it, because 1,165 stock-out orders sit under
  `Priority 4 - System Update/Correction (D)`, a reason `INCLUDED_REASONS` excludes on
  purpose — their delivery would otherwise look like an open backlog item forever.

### A4 [BLOCKER] The payroll feed cannot be used as `tech_workload` v1.34.0 uses it
Two independent problems, both of which would silently corrupt an overtime panel:

**(a) `PLC_EMPLOYEE_HOURS` re-loads overlapping windows, so rows accumulate.**
`SystemUpdatedDate` shows loads on 2026-08-11, 08-12 and 08-14 each covering the same
`WorkDate` range 2026-08-06→08-19. Effect on Patient Care Technician rows:

| month | raw rows | distinct (employee, workday) | raw hours | hours after dedup |
|---|---|---|---|---|
| 2026-05 | 5,975 | 5,693 | 51,614 | 58,077 * |
| **2026-06** | **13,697** | **5,729** | **123,710** | **47,850** |
| 2026-07 | 9,463 | 6,561 | 83,900 | 53,480 |
| 2026-08 (13 d) | 5,892 | 1,662 | 49,384 | 27,190 |

\* the dedup column is computed over Sun–Sat weeks assigned to the month of their
Saturday, so it is not a like-for-like row total — the point is the *scale* correction.

Worst case found: 30 duplicate rows for a single employee on 2026-06-22. Un-deduplicated,
inferred June overtime is **77,957 hours on 118,747 total (66% OT)** — obviously false.
After dedup it is 7,383 hours, in line with every other month.

**(b) The recorded overtime columns are unusable.** `PLC_EMPLOYEE_HOURS` has
`Reg_Hrs`, `OT1_Hrs`, `OT2_Hrs`, `Paid_Hrs`, `Est_*` — tempting, but:
- scale is wrong by ~14× (`Pay_Type='Work'`: `Hours` 958,685 vs `Reg_Hrs` 13,626,530),
  i.e. they are pay-period values repeated on every daily row, not daily hours;
- `OT1_Hrs` is **0 for every month from 2026-02 onward** (one −29 outlier in May);
- `OT2_Hrs` is 0 everywhere.

So FLSA inference from daily `Hours` — v1.34.0's approach — is right after all. But
there is now a genuine improvement available: **`Pay_Type` separates PTO and Holiday**
(Work / On Call Hours / PTO / Holiday), which retires the standing caveat *"if PLC
Hours includes PTO, OT is overstated."* It is worth real money: Jul-2026 inferred OT is
10,264 hours including PTO/holiday vs **8,384** excluding them — an 18% overstatement.

**(c)** 709 rows carry `Department_Name IS NULL`, `Employee_Name IS NULL` and
2,600–3,100 hours each — 1,051,659 hours total, more than every real row combined.
These are aggregate/garbage rows. The existing `Department_Name='Patient Care
Technician'` filter excludes them incidentally; it should be an explicit guard.

**(d)** `PLC_EMPLOYEE_HOURS` contains **future-dated rows** (through 2026-08-19 against
an `AS_OF_DATE` of 2026-08-13). v1.34.0's `WorkDate < DATEADD(day,1,FILTER_END)` bound
handles this correctly — preserve it.

**(e)** Payroll cannot be tied to a warehouse directly: only **2 of 139** distinct
`Location_Name` values match `SERP_WAREHOUSES`. The values are recognisable but
free-form and inconsistent (`San Antonio TX` / `San Antonio, TX`, `W Houston TX`,
`Lafayette (Scott), LA`). Warehouse attribution must come through the technician
name-match route, or from a curated crosswalk.

---

## B. Correctness bugs in the current dashboard

- **B1 [BUG] A claimed audit artifact is never produced.** `Cell 11.2` prints
  *"exported to Redel_Unlinked_Monthly"* and builds `tbl_redel_unlinked_monthly`, but
  the Excel export never writes that sheet. The 10,476 excluded redelivery events are
  therefore undocumented in the deliverable, contrary to the comment that exists
  specifically to make the exclusion auditable.
- **B2 [BUG] Two different denominators for the same rate.** `tbl_redel_monthly`
  (Cell 11.2) divides by **all** tickets from `df_tx`; `_dash_redel_monthly`
  (Cell 15) divides by **attributed** tickets (`_txa`). Both are labelled as a
  redelivery rate per ticket. The two will not reconcile.
- **B3 [BUG] Stock-out VP series can plot two points per month.**
  `dash_mo_stockout_vp` is grouped by `['vp','shared_state', …]`. A VP serving both a
  shared state (TX) and an exclusive one yields two rows per period; the renderer maps
  period → x position, so both are drawn at the same x and the line zig-zags. Group to
  one row per (vp, period) and carry `shared_state` as a max/flag.
- **B4 [BUG] Key Vault login discards the working server string.** `Cell 3.1` sets
  `SERVER_NAME = 'tcp:dmeexpress.database.windows.net,1433'`; `Cell 4.1` then
  overwrites it with the bare hostname from the vault. I hit
  `[08001] TCP Provider: Timeout error [258]` with the bare form and connected
  first try with `tcp:…,1433`. Wrap it: `f'tcp:{kv_hostname},1433'`.
- **B5 [BUG] `resolve_state_series` is documented as vectorized but is not.** Its
  docstring says *"Vectorized 3-layer state resolution"*; the body is a per-row Python
  loop with `.loc` assignment, running ~21,000 iterations on the live data (8,743
  sibling + 12,204 override resolutions). Correct, but the docstring misleads a future
  editor into assuming it is cheap.
- **B6 [BUG] A validation warning is printed and ignored.** `Cell 10` reports
  `WARNING: 2,752 groups >1 kept row` on every run. Nothing acts on it — and see D1:
  nothing downstream consumes that cell's output at all.

## C. `CLAUDE.md` rule conflicts

- **C1 [RULE 2] Patient-identifiable data is rendered into notebook output.**
  `Cell 7.1` ends with `display(df_tx.head(3))`, which prints `record_id` and
  `order_num` — record/account-level patient references — into a cell output. Rule 2
  forbids raw patient IDs or account numbers in notebook outputs. Replace with a
  shape/dtype/null summary. (`Patient_Token` is the only permitted patient reference,
  and this feed does not use it.)
- **C2 [RULE 4] `run_query` does not enforce read-only.** Rule 4 says to *"use the
  `run_query` pattern from `analysis/templates/` which enforces this in-process"* —
  but `analysis/templates/` contains only `.gitkeep`, and this notebook's `run_query`
  executes whatever string it is handed. The guarantee is documentary, not enforced.
- **C3 [RULE 3] The renderer inlines every page.** `plt.show()` sits inside
  `_entity_page`, which runs once per entity — 110 figures embedded in the executed
  notebook, which is why v1_1_0 is 33 MB. Rule 3 says outputs are never committed;
  don't rely on the hook to undo 33 MB. Show only the company/VP pages, or none.

## D. Dead code and configuration drift

- **D1 [DEAD] The visit-deduplication cell is entirely unused.** `Cell 10` builds
  `df_visits`, `visit_type` and `_is_exchange_pair`; nothing downstream reads any of
  them (productivity deliberately uses raw `df_tx`). It is lifted from
  `tech_workload`, where it *is* used. Either consume it or drop it — it costs a full
  pass over 449k rows and emits a warning nobody owns.
- **D2 [DEAD] Extracted-and-never-used frames:** `df_master` (1,117 rows),
  `df_apc` (63 rows, cleaned then abandoned), `df_inventory_total` (85 rows, cast and
  abandoned), `tbl_lost_by_wh` (built with an ADC merge and cost-per-patient-day
  columns), `_lost_patient_ids`, `tbl_redel_product` (displayed only),
  `tbl_redel_monthly`, `tbl_redel_unlinked_monthly` (see B1). Also
  `df_tx['reason_category']`, `df_tx['priority_level']` and `_matched_eid` are computed
  and never read.
- **D3 [DEAD] Unused configuration and imports.** `STATE_PREFIX_LEN` (self-labelled
  deprecated), `OUTLIER_Z_THRESH`, `DATA_FRESHNESS_THRESHOLD`, `MIN_HOURS_MONTH`,
  `MIN_HOURS_FOR_OT_RATE`, `PCT_DEPT`, `OT_WEEKLY_THRESHOLD` are all defined and never
  used; `scipy.stats` and `statsmodels` are imported (with a `_SM_OK` guard) and never
  called. The OT constants become live in v1.3.0; the rest should go.
- **D4 [NIT] Duplicated constant.** `MIN_ACTIVE_DAYS_RANK = 30` (Cell 3.1) and
  `DASH_MIN_ACTIVE_DAYS = 30` (Cell 3.5) mean the same thing, with a comment promising
  they match. One will drift.
- **D5 [NIT] The header contradicts the code.** Cell 0 states *"Payroll (PLC) and APC
  census are deliberately NOT pulled"*, but `Cell 7.5` pulls both `df_apc` and
  `df_adc`, and `Cell 12` merges ADC into `tbl_lost_by_wh`.
- **D6 [NIT] The H3 probe scans the whole table.** The unparseable-date probe in
  Cell 7.1 has no date window, so it scans all of `SERP TRANSACTIONS` on every run to
  return one number.
- **D7 [NIT] Fragile path and redundant naming.** `USER_ROOT = '/./Users/aenew'` is an
  unusual form that happens to resolve; and `save_fig` appends `RUN_DATE` to filenames
  inside `OUT_DIR`, which is already a `RUN_DATE` directory.

---

## What is genuinely sound

Worth stating, because most of the notebook is careful work: the Sun–Sat FLSA week
alignment, the deterministic `DATEDIFF % 7` day-of-week (immune to `@@DATEFIRST`), the
`TRY_CONVERT`-in-both-SELECT-and-WHERE date discipline (H3), the four-layer state
resolution with a loud unresolved audit, the ratio-of-pooled-sums grain rule, the
partial-week hollow markers, the disjoint top/bottom lists, the PII-minimised stock-out
select (patient, caregiver, phone, email and notes columns are all correctly avoided,
and the address is reduced to a state code then dropped), and the v1.2.0 apportionment
reconciliation assert. The defects above are concentrated in **source selection** and
in **cells lifted verbatim from a notebook with different needs** — not in the
analytical core.

# Code & Metric Audit — `analysis/ops_dashboard_2026-08-14_v1_7_0.ipynb`

**Audited** 2026-08-17, all 91 cells, code and metric definitions.
**Baseline** v1.6.2. **Scope** every cell; every published metric; `CLAUDE.md` rule compliance;
the repository around the notebook.

**Verification basis, stated first because it bounds everything below.** No database run was
possible for this audit — there is no reachable DMEEXPRESS connection from the environment it
was performed in. So:

- Findings marked **[CODE]** are established from the source and need no run: they are things
  the code does or does not do.
- Findings marked **[REPO]** were verified directly against the working tree and git history.
- **No finding below is sized against live data.** Where a direction of error is claimed it is
  derived from the arithmetic, not measured. Every "moves published numbers" claim states
  which way and why.
- The v1.7.0 changes were exercised against synthetic feeds (51 assertions, §0) covering the
  cases the last three releases broke on. That is not a substitute for a live run.

Legend: **[BLOCKER]** wrong number reaching a VP today · **[BUG]** wrong or unreachable
output · **[RULE]** conflicts with `CLAUDE.md` · **[DOC]** the pack says something the code
does not do · **[DEAD]** unused work · **[NIT]** hygiene.

---

## 0. What v1.7.0 changed, and how it was verified

The three requested changes, plus six defects found while making them.

| | change | verified by |
|---|---|---|
| R1 | `census_per_active_tech_weekday` (the v1.4.0 basis) and `restatement_vs_v140_pct` retired from every output | absence asserted at 4 grains + monthly bridge; no page text mentions it |
| R2 | one entity page → two 2×3 pages (six labour / six equipment-redelivery-stock-out) | 8 entities × 2 pages rendered; every panel title found in the extracted PDF text; Cell 23 assembly walks the page list and bookmarks the first page of each entity |
| R3 | the census ratio publishes the ADC and technician count it is computed from | Reconciliation 5 (new, raises) + an independent re-derivation in the harness at all four grains |
| F1 | `t4w_weeks_observed` does not measure what v1.6.2's comment claimed | new `ratio_weeks_observed_t4w` proven strictly lower where the census feed lagged |
| F2 | `add_trailing` gained `sum_cols` (additive, default-empty) | trailing sum of an alternating 1/0 series = 2; mean of the same = 0.5; collision guard raises; pre-span weeks excluded; the v1.6.1 dtype contract still holds |
| F3 | Reconciliation 4's bracket guard never covered **metro** grain | metro added, plus 3 more metrics |
| F4 | panel notes and titles were single unwrapped lines and **had been overflowing into the neighbouring panel since v1.5.0** | wrapped to the panel measure; title pad derived from the wrapped line count |
| F5 | the top/bottom table was sized by a scale factor and left a small block of text in a large box; its coaching caveat existed only in the Word document | explicit bbox; caveat now on the page |
| F6 | the Excel README still described the superseded 2×4→3×4 layout as current | marked superseded |

Reconciliations 1–5 inside Cell 13.5 all raise rather than warn, and all five passed against
the synthetic feeds. **No metric that remains published changes value in v1.7.0.**

### On R1 — why retiring beat retaining

The basis was kept from v1.5.0 so the ~40% restatement could be reconciled line by line
against the v1.4.0 pack. Three arguments for ending that:

1. **The reason expired.** The restatement has been circulated since v1.5.0, three releases
   and two months ago.
2. **A retired metric that is still published is still quoted.** Its own dictionary entry had
   to say *"never put it beside a per-technician staffing target"* — and it was drawn on every
   census panel, at every grain, directly beside the per-technician figure.
3. **It was the expensive part of the last two releases.** Of the four pooling defects fixed
   in v1.6.0 and the one in v1.6.2, **three were in this ratio or in the wedge column that
   existed to explain it**, and it is what made Reconciliation 4 fire on live data.

Nothing is lost: both inputs (`adc`, `avg_active_techs`) remain published at every grain and
on the monthly bridge, so the field-coverage figure is still computable. `attendance_rate_pct`
— the informative half — is promoted from a shaded fill to a panel with its own axis.

### On R3 — the part that is not a two-line change

For a **weekly** point the inputs are on the row and their quotient is the plotted value. For
the **trailing** point they were not available. `adc_t4w` is pooled over the weeks census was
*observed*; `techs_equiv_t4w` is a spine mean with quiet weeks zero-filled. **Their quotient
is not the published trailing ratio** — that is precisely the v1.6.2 defect, and the two
columns sit on the same row looking like the obvious pair to print. Cell 13.5 now publishes
`ratio_adc_t4w` / `ratio_techs_equiv_t4w` / `ratio_weeks_observed_t4w`, pooled over the same
mask-D weeks, and Reconciliation 5 raises if their quotient is not the published figure or if
an input survives on a row whose ratio was suppressed. A printed input that does not reproduce
the printed figure is worse than no input.

---

## A. Open findings that move published numbers

**These were found, not fixed.** Each belongs in its own release with its own verification;
folding a numbers-moving fix into a layout change is how a restatement becomes untraceable.
They are ordered by how far the wrong number travels.

### A1 [BLOCKER] `ot_hours_per_tech` can never produce a recommendation, and nothing says so
`Cell 17.5`. The scorecard guard tests the **VP** frame and not the **company** frame:

```python
if _vpd is None or _cod is None or _vpd.empty or _col not in _vpd.columns:
    _missing_metrics.append(_col); continue
```

`dash_wk_ot_vp` has `ot_hours_per_tech`; `dash_wk_ot_co` does **not** — the company frame is
built by `_ot_weekly_company`, which emits `ot_hours_per_employee` instead. So the metric
passes the guard, `_window_mean(_cod, ...)` returns an empty frame, `_co_val` is `NaN`,
`gap_vs_company` is `NaN`, and `NaN * -1 < 0` is `False`.

**Consequence:** one of eleven scored metrics — the only per-technician overtime measure —
is silently incapable of being adverse. It occupies a row per VP in the published
`VP_Scorecard` sheet with a blank company value, is absent from the executive summary's
company table (which skips NaN), and can never enter a VP's recommendation list however bad
it is. `_missing_metrics` prints nothing, because the guard it would have to fail does not
look at the company frame.

**Disposition:** extend the guard to `_col not in _cod.columns`, then decide deliberately
whether to (a) emit `ot_hours_per_tech` on the company frame from the site-attributed data —
noting that it would then cover only attributable hours, ~90% of the total — or (b) drop it
from `_SCORE_METRICS` and score `ot_hours_per_employee` instead. Either way the guard must
fail loudly first, so the next mismatch of this shape cannot ship.

### A2 [BUG] The overtime per-head trailing ratios mix two week sets — the v1.6.0 defect family, unfixed
`Cell 15.5`. `technicians` and `employees` are passed in `rate_cols`, so a week an entity had
no rows is left **NaN and excluded from the mean**. `ot_hours` is in `count_cols`, so the same
week is **zero-filled**. The pooled override then divides one by the other:

```python
agg['ot_hours_per_tech' + _s] = agg['ot_hours' + _s] / agg['technicians' + _s]
```

Over a 4-week window with one quiet week the numerator is `(0+a+b+c)/4` and the denominator is
the mean of **three** technician counts. This is exactly what Cell 13.5's own header calls
"a numerator pooled over four weeks against a denominator averaged over two", and what the
v1.6.0 changelog fixed for census — in the census cell only.

**Direction: it UNDERSTATES.** `ot_hours_per_tech` is a *lower-is-better* scored metric, so a
site or VP with intermittent weeks reads **better than it is** and escapes a recommendation it
has earned. `ot_hours_per_employee_t4w` on the company frame carries the identical construction;
at company grain payroll runs every week so it is probably inert in practice, but it is the
same latent defect the census headline was carrying when v1.6.2 found it.

`ot_pct_of_worked_t4w` is **fine** — both parts are counts, both zero-filled, consistent.

**Disposition:** move `technicians` and `employees` to `count_cols` (a week with nobody there
genuinely had zero), or mask the numerator to the same weeks. The census cell's mask-based
pooling is the pattern; the point of A4 is that this should not need finding by hand.

### A3 [BUG] `recovery_rate_pct_t4w` is a mean of ratios, and its denominator is not trailed at all
`Cell 14`. `recovery_rate_pct` is in `rate_cols` with **no pooled override**, so its trailing
value is the mean of four weekly recovery rates — a week with two mature assets weighing the
same as a week with two hundred. It cannot currently be pooled either: `mature_assets` is
aggregated into the frame but is **absent from `count_cols`**, so no `mature_assets_t4w`
exists to divide by.

This matters more than the other unpooled rates because `recovery_rate_pct` is in
`_SCORE_METRICS` and drives VP recommendations, and because recovery is *deliberately censored*
to cohorts ≥90 days old — so weekly denominators are thin by design, which is the condition
under which a mean of ratios diverges most from the pooled figure.

**Also unpooled**, lower stakes: `pct_employees_with_ot_t4w`, `leave_pct_of_total_t4w`,
`lost_pct_of_inventory_t4w`. The Excel README states flatly that *"Rate trailing columns are
POOLED (trailing numerator / trailing denominator), not a mean of four weekly rates"* — that
is true of most rates and **not** of these, and the README does not distinguish them.

**Disposition:** add `mature_assets` and `recovered_assets` to `count_cols` and pool it; pool
the other three or label them in the dictionary as means of weekly rates. Do not leave the
README's blanket claim standing either way.

### A4 [BUG] The bracket guard that catches this whole family exists for census only
`Cell 13.5` Reconciliation 4 tests that a pooled ratio sits inside the min–max range of the
weekly values it spans, raises on failure, and — by the changelog's own account — "earned its
keep immediately: it found defects 2, 3 and 4 after being written to catch 1."

It is applied to **five census metrics and nothing else.** A2 and A3 are both live instances
of the class it detects, in the overtime and lost-equipment families, and both would be caught
on the first run by the same six-line test.

**Disposition:** lift `_bracket_violations` out of Cell 13.5 into Cell 4.3 beside
`add_trailing`, and run it over every `(frame, rate column)` pair the pack publishes.
This is the highest-value item in this audit: it converts a class of defect that has shipped
in three consecutive releases and been invisible every time into a build failure.

---

## B. Open findings where the pack says something the code does not do

### B1 [DOC] The metric dictionary claims exchange pairs are consolidated. They are not.
`Cell 21` publishes, as an assumption of the headline productivity numerator:

> *"Exchange pairs (a Pickup and a Delivery for the same patient, technician and day) are
> consolidated into one visit by Cell 10."*

`Cell 10` builds `df_visits`, `visit_type` and `_keep` — and **nothing downstream reads any of
them.** `_dash_weekly` counts `order_num.nunique()` off raw `df_tx`. The consolidation the
dictionary describes to a CFO does not happen, and since an exchange Pickup and Delivery carry
different `Order_Num` values, both are counted.

Whether they *should* be consolidated is a business question. What is not a question is that
the dictionary describes behaviour the notebook does not have, on the pack's headline metric.
Note that the dictionary's own validation cannot catch this: it checks that every documented
**column exists**, not that any documented **claim is true**.

**Disposition:** either consume `df_visits` in the productivity numerator (a restatement —
it would lower every ticket count) or delete the sentence and Cell 10 together. Do not leave
the claim standing.

### B2 [DOC] `total_tickets` names three different populations across four published frames
| frame | `total_tickets` is | weekend work? |
|---|---|---|
| `dash_wk_prod_*` | attributed, **weekday-only**, whitelisted reasons | excluded |
| `dash_wk_redel_*` | attributed, **all days** | included |
| `dash_wk_stockout_*` | attributed, **all days** | included |
| `dash_tb_*` / `tech_perf_vp` | attributed, weekday-only (per technician) | excluded |

The dictionary documents `total_tickets` once, under Technician productivity, as *"Weekday
tickets only — Saturday and Sunday work is excluded from every productivity figure"*. That is
true of one of the four. The redelivery and stock-out rates are internally consistent (their
numerators are also all-days), so the **rates are correct**; what is wrong is that one column
name carries three meanings across sheets a reader will compare, under a single definition
that fits one of them.

v1.7.0 mitigated this on the page — both page-2 rate panels now state that their denominator
is wider than page 1's — but the column name, the sheets and the dictionary are unchanged.

**Disposition:** rename to `total_tickets_weekday` / `total_tickets_all_days` and give each its
own dictionary entry. Renaming a published column is a breaking change for saved pivots, which
is why it is proposed rather than done here.

### B3 [BUG] Cell 8.1b's `same_week` fallback uses a different week than the whole notebook
`Cell 8.1b` builds its week-level modal-warehouse map with `dt.to_period('W')`, which is
**Monday–Sunday**. Every published week in the pack is **Sunday–Saturday** (`week_start_of`,
`PROD_WEEK_START_DOW=6`), and Cell 4.3 exists specifically so that "each metric family invented
its own time bucket" cannot happen again.

Impact is genuinely small — it is tier 2 of a 4-tier inference ladder, reached only when a
virtual ticket has no same-day evidence, and it changes *which* physical warehouse an inferred
ticket lands on, not whether it is counted. But it is the one place in the notebook where a
week boundary still disagrees with the shared spine, and the fix is `week_start_of(...)`.

### B4 [DOC] Cell 3.1 still carries the PTO caveat that v1.3.0 retired
The comment above `OT_WEEKLY_THRESHOLD` reads: *"CAVEAT: if PLC 'Hours' includes PTO/holiday
pay, OT is overstated (PTO does not count toward the 40-hr threshold). Confirm the feed with
payroll."* v1.3.0 confirmed the feed, found `Pay_Type` separates PTO and Holiday, excluded
them, and sized the effect at 18% — and the Excel README says so. The comment a future editor
reads first still describes the unresolved state.

### B5 [NIT] Two per-technician redelivery rates cross their own denominators
`Cell 17`'s `_dash_topbottom` and `Cell 17.5`'s `tech_perf_vp` both compute
`redel_per_100_tickets` with an **all-days** numerator (from `redel_linked`) over a
**weekday-only** denominator (from `_techday_wk`). Same family as B2, at technician grain —
and this one is printed on the top/bottom table on every page 1 and in the named lists inside
VP recommendation documents. The bias is small (weekend work is a minority of tickets) and
consistent in direction across technicians, so ranking is barely affected; the absolute rate
reads slightly high.

### B6 [NIT] `_named_sites` averages weekly rates
`Cell 22` ranks the worst sites inside a VP with `value=('_v','mean')` over weekly rate values.
For a *ranking* this is defensible, but it is a mean of ratios in a pack whose stated rule is
pooling, and it selects which sites get named in a document that goes to a VP.

---

## C. `CLAUDE.md` rule compliance — three real violations, all [REPO]-verified

### C1 [RULE 3] [BLOCKER] There is no pre-commit hook. 538 outputs are committed.
`CLAUDE.md` rule 3: *"Notebook outputs are never committed. **The pre-commit hook strips
them**; do not bypass it."*

**`.git/hooks/` contains nothing but the samples git ships.** There is no pre-commit hook, and
there is no evidence one ever ran. Outputs in the committed (HEAD) notebooks:

| notebook | committed outputs |
|---|---|
| `ops_dashboard_v1_0_0` | 28 |
| `ops_dashboard_v1_1_0` | 141 |
| `ops_dashboard_v1_2_0` | 144 |
| `ops_dashboard_v1_3_0` | 41 |
| `ops_dashboard_v1_4_0` | 42 |
| `ops_dashboard_v1_5_0` | 31 |
| `ops_dashboard_v1_6_0` | 32 |
| `ops_dashboard_v1_6_1` | 31 |
| `ops_dashboard_v1_6_2` | 48 |
| `sql_explorer`, `tech_workload` | 0 |

The rule is documentary, not enforced — and every prior audit's mitigation for the
33 MB / 110-inline-figure problem was written on the assumption that the hook was the backstop.
The `.claude/hooks/guard.py` PreToolUse hook that protects `data/` and `audit/` **does** exist
and works (it blocked a shell command during this audit); the *git* hook does not.

**v1.7.0 was written with zero outputs and should be committed that way.** That does not fix
C1: the next executed save re-adds them.

### C2 [RULE 2] Patient-account identifiers are in git history, with real values
`CLAUDE.md` rule 2 forbids *"raw patient IDs, MRNs, or account numbers — in code, comments,
notebook outputs, or markdown."*

The committed outputs of `v1_0_0`, `v1_1_0` and `v1_2_0` contain the `display(df_tx.head(3))`
result, with actual values:

```
  order_num record_id           tech_warehouse techfirstname techlastname
0   3133624    646029           R15 Chesapeake          Yale       Pinnix
1   3133625    642111  Z Equipment Collections        Kassie        Rider
2   3133627    647678               R12 Irving         James       Hudson
```

`Record_ID` is the patient service-record key and `Order_Num` the order key — account-level
patient references, plus named technicians. The v1.2.0 audit raised this as finding C1 and
v1.3.0 fixed the *code* (the `display` is gone; no v1.3.0+ notebook has such an output). **The
data itself was never removed from the repository.** It is in three committed notebooks and in
every commit that touched them.

**Disposition:** this needs a decision from IT/whoever owns the repo, not a notebook change.
Removing it means rewriting history (`git filter-repo` over those three paths) and
force-pushing, which invalidates every clone. The alternative is a documented accepted
exposure. It should not sit undecided, and it is the reason C1 is a blocker rather than
hygiene: the hook that was believed to prevent this is what did not exist.

### C3 [BUG] `USER_ROOT = '$HOME'` never expands — every deliverable is written into the repo
`Cell 3.1` sets `USER_ROOT = '$HOME'` as a Python string. Python does not expand shell
variables, so:

```
REPORT_ROOT = '$HOME/OneDrive - DME Express/Reports/TechWorkload'
OUT_DIR     = '$HOME/OneDrive - DME Express/Reports/TechWorkload/<RUN_DATE>'   # RELATIVE
```

`os.makedirs` then creates a literal directory named `$HOME` under the notebook's working
directory, and every deliverable is written inside it.

**Observed directly, and the state changed mid-audit — both observations are reported because
the second does not retract the first:**

- **Earlier on 2026-08-17**, `analysis/$HOME/OneDrive - DME Express/Reports/TechWorkload/2026-08-17/`
  held a full deliverable set — the Excel workbook, the publishable PDF, the dashboard PDF, the
  metric dictionary, five per-VP recommendation documents and six dashboard PNGs — and
  `git status` listed `?? analysis/$HOME/` as untracked.
- **At the close of this audit** the dated folder and its files are gone and only the empty
  directory skeleton `analysis/$HOME/OneDrive - DME Express/Reports/TechWorkload/` remains. Git
  does not track empty directories, so `git status` no longer mentions it. **I do not know what
  removed them** — nothing in this audit did, and it may have been the analyst moving them to
  the real OneDrive folder. The path was never committed (`git log -- 'analysis/$HOME'` is
  empty), so no deliverable ever reached history by this route.

**The defect is unchanged and still live.** The path is **not** git-ignored — `.gitignore`
covers `data/`, `audit/` and `outputs/`, not this — and `git check-ignore` confirms no match.
The next run of the notebook recreates the dated folder and refills it, and at that point a
single `git add -A` commits a workbook of data rows and Word documents naming technicians into
a shared repository. That is the exact failure rule 3 exists to prevent, arriving by a route the
rule does not describe. The empty skeleton sitting in the working tree is the evidence that it
already happened once today.

Two things are wrong and both should be fixed: `USER_ROOT` should be
`os.path.expanduser('~')` (or `os.environ['USERPROFILE']`), and `OUT_DIR` should be asserted
absolute before `makedirs` — a relative deliverable path is always a bug here. Adding
`$HOME/` and `analysis/$HOME/` to `.gitignore` is a seatbelt, not the fix.

### C4 [RULE 4] `analysis/templates/` is empty, so rule 4 points at nothing
Rule 4: *"Use the `run_query` pattern from `analysis/templates/` which enforces this
in-process."* `analysis/templates/` and `analysis/lib/` each contain only `.gitkeep`. The
enforcement itself is real and good — `Cell 4.2`'s `run_query` rejects anything that is not a
single SELECT/WITH, strips comments before testing, and blocks a DDL/DML keyword list — but it
is re-implemented per notebook rather than shared from the location the rule names. Rule 1's
instruction to *"check `analysis/lib/` and `analysis/templates/` before writing new analysis
code"* is likewise unactionable.

The v1.2.0 audit raised this (C2) fifteen months of releases ago. Promoting `run_query`,
`clean_numbers`, `week_start_of`, `build_week_spine` and `add_trailing` into `analysis/lib/`
would make both rules real and is the natural home for A4's generalised bracket guard.

### C5 [NIT] A named analyst login is hardcoded in a shared notebook
`Cell 4.1`: `SQL_USERNAME = 'anewton-ro'`, used both as the connection UID and as the Key
Vault secret name. No credential is in the repo — rule 5 is not violated — but this is a
version-controlled file that "every analyst's agent reads", and a second analyst either
connects as someone else's read-only principal or fails. It belongs in an environment variable
with this value as the fallback.

---

## D. Dead code — all three were raised in the 2026-08-14 audit and are still dead

- **D1 [DEAD] `Cell 10` in its entirety.** `df_visits`, `visit_type`, `_is_exchange_pair` and
  `_keep` are built and read nowhere else — see B1, which is the same finding with a published
  consequence. It costs a full `groupby.transform` pass over ~449k rows and emits a
  `WARNING: N groups >1 kept row` that nobody owns.
- **D2 [DEAD] `tbl_redel_monthly`** is built, given a `redel_pct_of_attributed_tickets` column,
  and never exported. The comment above it explains a v1.3.0 fix to a metric no reader sees.
- **D3 [DEAD] `tbl_redel_product`** is built and `display()`ed only — never exported. It is the
  last remaining `display()` in the notebook (no PII: product names and counts).
- **D4 [DEAD] `df_apc`** — the APC snapshot — is queried, `clean_numbers`-ed and never read.
  Its only role now is that the snapshot-date probe beside it produces the staleness warning,
  which is worth keeping; the `df_apc` query itself is not.
- **D5 [NIT] Defined and never read:** `MIN_HOURS_FOR_OT_RATE` (the v1.2.0 audit predicted it
  would become live in v1.3.0; it did not), `STOCKOUT_FROZEN_LOAD_DATE` (its comment says
  "reconciliation only" — there is no reconciliation).

---

## What is sound

Worth stating plainly, because the findings above are concentrated in a few places and most of
this notebook is unusually careful work.

**The analytical core is right and it is defended.** The ratio-of-pooled-sums rule; the
apportioned technician-day denominator with an assert that it reconciles to distinct
(technician, date); the apportioned headcount with an assert that it sums across grains; the
calendar week spine that makes a missing week visible instead of skipped; the partial-week
exclusion applied to counts and rates alike with the hollow/hatched marks that keep them
visible; the census/productivity population tie-out; the overtime apportionment check that
quantifies its own legitimate leak instead of warning and leaving it; the per-grain census
join that fixed the VP/metro lost-equipment rate and then *proves* it every run rather than
asserting it.

**The single-axis rule is real and enforced.** No panel has two y-axes, the reason is written
down where a future editor will read it, and v1.7.0's census input readout was designed around
it rather than through it.

**The data-quality work is the strongest part.** The stock-out three-way outcome (rather than
the false 93% fulfilment a naive completion-date test returns); the payroll de-duplication with
a *cross-check against an alternative rule* that warns if the two disagree; the recorded-OT
diagnostic that re-proves on every run why those columns stay retired; the lost-date parse
assert that exists because a silent parse failure kept a panel empty for a year; the spike
surveillance that reports an unlisted spike loudly and refuses to exclude it automatically;
the censoring discipline on recovery rate and stock-out outcomes.

**And the guards raise rather than warn** where the failure would be invisible — Cell 13.5's
five reconciliations, the lost-date parse rate, `add_trailing`'s dtype contract. Reconciliation
4's history is the argument for A4: it was written to catch one defect and immediately found
three more. The same test applied to the other five metric families is the cheapest correctness
work available in this codebase.

**The defects cluster in three recognisable places**, and none of them is the analysis:
sections lifted from `tech_workload` and never re-consumed (D1, D2, D3, D4); the metric
families that never received the pooling discipline the census cell was rewritten twice to get
right (A2, A3, A4); and the repository around the notebook rather than the notebook itself
(C1, C2, C3, C4).

---

## Recommended order of work

1. **A4** — generalise the bracket guard. It is six lines moved, it catches A2 and A3 on the
   first run, and it is the only item here that prevents the *next* one.
2. **C1 + C2** — install the pre-commit hook the rules already assume, then get a decision on
   the identifiers already in history. C2 is not a code change and needs an owner.
3. **C3** — `USER_ROOT`, plus an absolute-path assert on `OUT_DIR`. Currently one `git add -A`
   away from committing a workbook of data rows.
4. **A1, A2, A3** — one release, one restatement note, since all three move VP-facing numbers.
5. **B1** — decide whether exchange pairs are consolidated, then make the dictionary and the
   code agree. Do not ship another pack where they disagree about the headline metric.
6. **B2** — split `total_tickets` by population. Breaking change; schedule it.
7. **C4** — promote the shared helpers into `analysis/lib/`, which is where A4's guard belongs.
8. **B3, B4, B5, B6, C5, D1–D5** — hygiene, batchable.

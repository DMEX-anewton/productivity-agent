"""Synthetic verification for install_time_model v1.1.0.

The model cells are executed against a synthetic order-line feed with KNOWN ground truth
(base visit time 12 min; concentrator 25, bed 40, wheelchair 15, tubing 0 min/unit) under
RIGHT-SKEWED noise whose median is zero — the shape the v1.1.0 median fit exists for —
plus every planted defect the QC/anomaly machinery exists for:

  * duplicate (order, address, asset) line echoes         (dedup must count 25)
  * a 30-delivery identical-completion-timestamp cluster  (bulk close-out -> excluded, R5)
  * negative durations, > 8h durations                    (gated, R2/R3)
  * split deliveries (completion spread > 60 min)         (gated, R4)
  * multi-warehouse orders                                (gated, R4)
  * 40 virtual-warehouse tickets with huge durations      (v1.1.0 gate -> excluded, R4v)
  * 8 rare products below the support floor               (folded into OTHER, R7)
  * a zero-install-time product                           (boundary -> R6 flag)
  * 20 tickets ~4x slower than their product mix warrants (R9-slow)

v1.1.0-specific assertions: the MEDIAN fit recovers the true install times under the skew
while the NNLS mean fit sits visibly above them, and the published actual/expected ratio
re-centres on 1.

Cells executed (v1.1.0 indices): 10 (run_query guard, no connection), 16, 18, 20, 22,
24, 26, 28, 30, 32, 34.

Run from the repository root:

    python analysis/lib/verify_install_time_model_v1_1_0.py

Exits non-zero on any failure. Needs no database connection, reads only the notebook, and
writes its scratch files to a temp directory.
"""
import json, os, sys, re, time, tempfile
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import sparse
from scipy.optimize import nnls, linprog

NB = 'analysis/install_time_model_2026-08-18_v1_1_0.ipynb'
OUT = os.path.join(tempfile.gettempdir(), 'install_time_verify_v110')
os.makedirs(OUT, exist_ok=True)

_nb = json.load(open(NB, encoding='utf-8'))
CELL = {i: ''.join(c['source']) for i, c in enumerate(_nb['cells'])}

FAILS, PASSES = [], []


def check(cond, label):
    (PASSES if cond else FAILS).append(label)
    print(('  PASS  ' if cond else '  FAIL  ') + label)


# ═══════════════════════════════════════════════════════════════════════════════
# Ground truth and synthetic order lines
# ═══════════════════════════════════════════════════════════════════════════════
TRUE_BASE = 12.0
TRUE_T = {'OXYGEN CONCENTRATOR': 25.0, 'HOSPITAL BED': 40.0,
          'WHEELCHAIR': 15.0, 'TUBING': 0.0}
RARE = [f'RARE DEVICE {i}' for i in range(1, 9)]   # 5 deliveries each < floor of 30
rng = np.random.default_rng(7)

lines, dkey = [], 0


def _mk(products, duration, wh='WH_A', arrival=None, comp_spread=0.0,
        second_wh=None, force_comp=None):
    """One delivery: products is a list of product names (repeats = quantity)."""
    global dkey
    dkey += 1
    order, addr = f'ORD{dkey:05d}', f'ADDR{dkey:05d}'
    arr = arrival if arrival is not None else (
        pd.Timestamp('2026-02-01 08:00') + pd.Timedelta(minutes=int(rng.integers(0, 200000))))
    comp = force_comp if force_comp is not None else arr + pd.Timedelta(minutes=float(duration))
    for j, p in enumerate(products):
        c = comp + pd.Timedelta(minutes=comp_spread) if (comp_spread and j == len(products) - 1) else comp
        w = second_wh if (second_wh and j == len(products) - 1) else wh
        lines.append(dict(order_num=order, addr_token=addr, asset_tag=f'AT{dkey:05d}{j}',
                          product_name=p.title() + ' ', warehouse=w,
                          arrival_dt=arr, completion_dt=c))
    return order


def _dur(products, noise=True):
    d = TRUE_BASE + sum(TRUE_T.get(p, 10.0) for p in products)
    if noise:
        # right-skewed, MEDIAN ZERO: exp(N(1.2, 0.9)) - exp(1.2). Left tail bounded at
        # -exp(1.2) = -3.3 min so no clipping distorts the median; mean(noise) ~ +1.7 and
        # the heavy right tail is what pushes a mean fit above a median fit.
        d += float(np.exp(rng.normal(1.2, 0.9)) - np.exp(1.2))
    return max(d, 4.0)


ALL = list(TRUE_T)
for _ in range(2600):
    k = int(rng.integers(1, 4))
    prods = list(rng.choice(ALL, size=k, replace=True))
    _mk(prods, _dur(prods), wh=str(rng.choice(['WH_A', 'WH_B', 'WH_C'])))
for p in RARE:                                            # 5 deliveries each, below floor
    for _ in range(5):
        _mk([p, 'TUBING'], _dur([p, 'TUBING']))
for _ in range(20):                                       # R9-slow: ~4x the standard
    _mk(['OXYGEN CONCENTRATOR'], 150.0, wh='WH_B')
_bulk_ts = pd.Timestamp('2026-03-15 17:00')               # 30-delivery bulk close-out
for _ in range(30):
    _mk(['WHEELCHAIR'], 0, arrival=_bulk_ts - pd.Timedelta(minutes=30), force_comp=_bulk_ts)
for _ in range(15):                                       # negative durations
    _mk(['HOSPITAL BED'], -45.0)
for _ in range(10):                                       # above the 8h cap
    _mk(['HOSPITAL BED'], 600.0)
for _ in range(12):                                       # split deliveries (spread 90 min)
    _mk(['WHEELCHAIR', 'TUBING'], _dur(['WHEELCHAIR', 'TUBING']), comp_spread=90.0)
for _ in range(8):                                        # multi-warehouse orders
    _mk(['WHEELCHAIR', 'TUBING'], _dur(['WHEELCHAIR', 'TUBING']), second_wh='WH_Z')
for _ in range(40):                                       # v1.1.0: virtual-warehouse rows
    _mk(['WHEELCHAIR'], 420.0, wh='Z Collections')        # a process, not a visit

df_lines = pd.DataFrame(lines)
df_lines = pd.concat([df_lines, df_lines.iloc[:25]], ignore_index=True)   # 25 dup echoes

# ═══════════════════════════════════════════════════════════════════════════════
# Namespace: the config the tested cells read, at the values Cell 3 sets.
# ═══════════════════════════════════════════════════════════════════════════════
G = dict(
    np=np, pd=pd, plt=plt, os=os, re=re, time=time, nnls=nnls,
    df_lines=df_lines.copy(), UNPARSEABLE_COMPLETION_ROWS=0, WINDOW_FELL_BACK=False,
    FILTER_START='2026-01-01', FILTER_END='2026-08-17', RUN_DATE='2026-08-18',
    EFFECTIVE_START='2026-01-01', EFFECTIVE_END='2026-08-17',
    OUT_DIR=OUT, CHART_DPI=80,
    MIN_DURATION_MIN=3.0, MAX_DURATION_MIN=480.0, SPLIT_TOLERANCE_MIN=60.0,
    BULK_TS_MIN_DELIVERIES=12, MIN_DELIVERIES_PER_PRODUCT=30,
    VIRTUAL_WH_PATTERNS=('Z ', 'MAILOUTS', 'DISTRIBUTION CENTER'),
    OTHER_LABEL='OTHER (below support floor)', TAU=0.5,
    N_BOOT=60, N_BOOT_MEDIAN=8, BOOT_SEED=20260818,
    sparse=sparse, linprog=linprog,
    SLOW_RATIO=2.5, FAST_RATIO=0.4,
    XCHECK_DIVERGENCE_PCT=50.0, XCHECK_DIVERGENCE_MIN=15.0, TOP_N_RESEARCH=200,
    PALETTE={'primary': '#1f77b4', 'muted': '#9467bd', 'ink': '#000000'},
    save_fig=lambda fig, name: None,
)

print('\n=== Cell 5 (=10) — run_query read-only guard (no connection) ==================')
G10 = dict(G, sql_conn=None)
exec(CELL[10], G10)
try:
    G10['run_query']('DROP TABLE x')
    check(False, 'run_query refuses a non-SELECT statement')
except ValueError:
    check(True, 'run_query refuses a non-SELECT statement')
try:
    G10['run_query']("SELECT 1; DELETE FROM t")
    check(False, 'run_query refuses multi-statement input')
except ValueError:
    check(True, 'run_query refuses multi-statement input')

print('\n=== Cell 7 (=16) — normalisation & dedup ======================================')
exec(CELL[16], G)
check(G['DUP_LINES_REMOVED'] == 25, f"dedup removed exactly the 25 planted echoes "
                                    f"(got {G['DUP_LINES_REMOVED']})")
check('OXYGEN CONCENTRATOR' in set(G['df_lines']['product_norm']),
      'trailing-space product names normalise onto one key')

print('\n=== Cell 8 (=18) — consolidation ==============================================')
exec(CELL[18], G)
df_dlv = G['df_dlv']
check(len(df_dlv) == dkey, f'one row per (order, address) delivery ({len(df_dlv)} vs {dkey})')
check(not G['TIME_ONLY_MODE'], 'real dates -> no midnight wrap engaged')

print('\n=== Cell 9 (=20) — quality gates & bulk detection =============================')
exec(CELL[20], G)
df_dlv = G['df_dlv']
_vc = df_dlv['qc'].value_counts()
check(int(_vc.get('virtual_or_mailout_wh', 0)) == 40,
      f"virtual-warehouse tickets gated out of the fit "
      f"(got {int(_vc.get('virtual_or_mailout_wh', 0))}/40)")
check(int(_vc.get('bulk_timestamp_cluster', 0)) == 30,
      f"bulk cluster fully excluded (got {int(_vc.get('bulk_timestamp_cluster', 0))}/30)")
check(int(_vc.get('nonpositive_duration', 0)) == 15,
      f"negative durations gated (got {int(_vc.get('nonpositive_duration', 0))}/15)")
check(int(_vc.get('above_max_duration', 0)) == 10,
      f"cap gated (got {int(_vc.get('above_max_duration', 0))}/10)")
check(int(_vc.get('split_delivery', 0)) == 12,
      f"split deliveries gated (got {int(_vc.get('split_delivery', 0))}/12)")
check(int(_vc.get('multi_warehouse', 0)) == 8,
      f"multi-warehouse gated (got {int(_vc.get('multi_warehouse', 0))}/8)")

print('\n=== Cells 10-11 (=22, 24) — features & NNLS fit ===============================')
exec(CELL[22], G)
check(sorted(G['rare_products']) == sorted(p.upper() for p in RARE) or
      len(G['rare_products']) == len(RARE),
      f"exactly the 8 rare products fall below the support floor (got {len(G['rare_products'])})")
exec(CELL[24], G)
coef, names = G['coef'], G['feature_names']
est = dict(zip(names, coef[1:]))
check(abs(G['BASE_MIN'] - TRUE_BASE) <= 3.0,
      f"base visit time recovered ({G['BASE_MIN']:.1f} vs true {TRUE_BASE})")
for p, t in [('OXYGEN CONCENTRATOR', 25.0), ('HOSPITAL BED', 40.0), ('WHEELCHAIR', 15.0)]:
    check(abs(est[p] - t) <= 3.0, f"{p.title()} recovered ({est[p]:.1f} vs true {t})")
check(est['TUBING'] <= 1.0, f"zero-cost product sits at the boundary ({est['TUBING']:.2f})")
check(G['R2'] > 0.5, f"mean fit explains the synthetic variance (R2={G['R2']:.3f})")
# THE POINT OF v1.1.0: under median-zero right-skewed noise the median fit tracks the
# truth while the mean fit is pulled up by the heavy tail (plus the planted slow tickets).
check(G['BASE_MIN_MEAN'] > G['BASE_MIN'] + 0.8,
      f"mean-fit base sits visibly above the median-fit base under skew "
      f"({G['BASE_MIN_MEAN']:.1f} vs {G['BASE_MIN']:.1f})")
_err_med = np.mean([abs(est[p] - t) for p, t in
                    [('OXYGEN CONCENTRATOR', 25.0), ('HOSPITAL BED', 40.0), ('WHEELCHAIR', 15.0)]])
_est_m = dict(zip(names, G['coef_mean'][1:]))
_err_mean = np.mean([abs(_est_m[p] - t) for p, t in
                     [('OXYGEN CONCENTRATOR', 25.0), ('HOSPITAL BED', 40.0), ('WHEELCHAIR', 15.0)]])
check(_err_med <= _err_mean + 0.5,
      f"median fit at least as close to truth as the mean fit "
      f"(median err {_err_med:.2f} vs mean err {_err_mean:.2f})")

print('\n=== Cell 12 (=26) — standards table & cross-check =============================')
exec(CELL[26], G)
tbl = G['tbl_products']
check(bool(tbl.loc[tbl['product_norm'] == 'TUBING', 'flag_zero_boundary'].iloc[0]),
      'zero-boundary product carries the R6 flag')
_conc = tbl[tbl['product_norm'] == 'OXYGEN CONCENTRATOR'].iloc[0]
check(_conc['single_n'] > 30 and abs(_conc['single_median_total'] - 37.0) < 6.0,
      f"single-delivery cross-check lands near base+install "
      f"({_conc['single_median_total']:.1f} vs 37, n={_conc['single_n']})")

print('\n=== Cells 13-14 (=28, 30) — expected times & reasonableness ===================')
exec(CELL[28], G)
df_dlv = G['df_dlv']
_has_lines = df_dlv['delivery_key'].isin(G['df_lines']['delivery_key'])
check(df_dlv.loc[_has_lines, 'expected_min'].notna().all(),
      'every delivery gets an expected time (including QC-excluded, for the export)')
_ok = df_dlv[df_dlv['qc'] == 'ok']
check(0.95 <= _ok['ratio'].median() <= 1.05,
      f"median actual/expected RE-CENTRED on 1 by the median standard "
      f"({_ok['ratio'].median():.2f})")
check((df_dlv['expected_min_mean'].notna() & (df_dlv['expected_min_mean']
      >= df_dlv['expected_min'] - 0.5)).all(),
      'mean-lens expected time ships beside the median standard, never below it')
exec(CELL[30], G)
check(G['N_LOOK'] <= 1, f"reasonableness checks pass on clean synthetic data "
                        f"(LOOK count {G['N_LOOK']})")

print('\n=== Cell 15 (=32) — research queue ============================================')
exec(CELL[32], G)
dr = G['df_research']
_cats = set(dr['category'])
for c in ('R2', 'R3', 'R4', 'R4v', 'R5', 'R6', 'R7', 'R9-slow'):
    check(c in _cats, f'research queue populated for {c}')
check(len(dr[dr['category'] == 'R4v']) == 40,
      f"R4v lists the virtual-warehouse tickets ({len(dr[dr['category'] == 'R4v'])}/40)")
check(len(dr[dr['category'] == 'R7']) == len(RARE),
      f"R7 lists each below-floor product once ({len(dr[dr['category'] == 'R7'])})")
check(len(dr[dr['category'] == 'R9-slow']) >= 15,
      f"R9-slow catches the planted 4x tickets ({len(dr[dr['category'] == 'R9-slow'])}/20)")
check((dr['status'] == 'open').all() and {'hypothesis', 'owner', 'next_step'} <= set(dr.columns),
      'queue carries the research-tracking columns, all open')

print('\n=== Cell 16 (=34) — export ====================================================')
exec(CELL[34], G)
_xlsx = os.path.join(OUT, 'install_time_model_2026-08-18.xlsx')
check(os.path.exists(_xlsx), 'workbook written to OUT_DIR')

print('\n' + '=' * 80)
print(f'{len(PASSES)} passed, {len(FAILS)} failed')
if FAILS:
    print('FAILURES:')
    for f in FAILS:
        print('  - ' + f)
    sys.exit(1)
print('ALL CHECKS PASSED')

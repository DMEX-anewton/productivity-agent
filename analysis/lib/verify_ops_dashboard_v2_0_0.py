"""Synthetic verification for ops_dashboard v2.0.0.

Executes the load-bearing cells of the notebook against synthetic frames and asserts the
properties every published figure rests on. No database connection: it reads the notebook,
builds its own inputs, and writes scratch files to a temp directory.

  METRO VOCABULARY (Cell 4.2)
    * 'R16 Spring' reaches Houston and 'R03 Hot Springs' does NOT   [whole-word matching]
    * 'R12 Ft. Worth' / 'R16 N. Houston' / 'R16 H3S' / 'R14 San Antonio WH' all land
    * an excluded warehouse stays out however well it matches

  PAYROLL PCT ROSTER (Cell 13.4)
    * the establishment is SPAN-FILLED: a head with no hours in a middle week is still on it
    * site shares sum to exactly 1.0 per (head, week) — the property every entity figure rests on
    * a head with no ticket history is explicitly UNATTRIBUTED, in the company count only
    * a head whose payroll rows stop before the tail flags the tail ROSTER-LAGGING
    * one PLC->technician map, shared with Cell 15.5

  CENSUS ON THE PAYROLL DENOMINATOR (Cell 13.5)
    * published payroll inputs divide into the published payroll figure, every grain (Recon 7)
    * company denominator == the distinct establishment                          (Recon 8)
    * the window headcount covers every weekly headcount inside it               (Recon 4c)
    * the window headcount is STRICTLY above the weekly mean where a head is intermittent
    * the two suppression flags are INDEPENDENT (a site thin on one, sound on the other)
    * a roster-lagging week publishes no payroll ratio and is out of trailing windows
    * the RETAINED active-technician ratio is unaffected by the payroll basis

  EVERY SUMMARY LEVEL (Cells 17.5, 22)
    * a Metro scorecard exists, is ranked among metros, and scores the same metrics as the VP one
    * technicians are compared to their OWN LEVEL's median — the same person, two numbers
    * a metro recommendation document is produced, names the metro's warehouses, and carries
      the cross-level caveat

  ...plus the windowed active denominator, pooled lost-equipment recovery, the on-call OT
  threshold, the OT feed guard, per-head OT pooling, the OT calibration, spike surveillance,
  the full renderer and the MMM-YY axis labels.

  DASHBOARDS-ONLY PDF (Cell 24)
    * every entity Cell 18 rendered is in it, with ALL of its pages, contiguous
    * reading order is company -> VPs -> metros -> warehouses, one bookmark per entity
      nested under its level, each landing on that entity's first page
    * the cover points at the full pack, because this document deliberately omits the
      definitions behind the charts it carries
    * it degrades to a cover-less pack without reportlab, and skips cleanly without pypdf

Cells executed (notebook indices): 4.2 (=18), 4.3 (=20), 13.4 (=66), 13.5 (=68), 14 (=70),
15.5 (=74), 15.6 (=76), 17.5 (=84), 22 (=94), 18 (=86), 21 (=92), 23 (=96), 24 (=98),
16.5 (=80).

Cells 21 and 23 are the two that name columns as STRINGS — a dictionary entry or an
executive-summary table can go stale against a renamed column with no error anywhere. Both
are executed here and their narrative asserted.

Run from the repository root:

    python analysis/lib/verify_ops_dashboard_v2_0_0.py

Exits non-zero on any failure.
"""
import json, os, sys, io, re, math, tempfile, contextlib
from collections import defaultdict
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

NB = 'analysis/ops_dashboard_2026-08-14_v2_0_0.ipynb'
OUT = os.path.join(tempfile.gettempdir(), 'ops_dashboard_verify_v200')
os.makedirs(OUT, exist_ok=True)

_nb = json.load(open(NB, encoding='utf-8'))
CELL = {i: ''.join(c['source']) for i, c in enumerate(_nb['cells'])}

FAILS, PASSES = [], []


def check(cond, label):
    (PASSES if cond else FAILS).append(label)
    print(('  PASS  ' if cond else '  FAIL  ') + label)


def raises(fn, label, exc=Exception):
    try:
        fn()
    except exc:
        PASSES.append(label); print('  PASS  ' + label); return
    FAILS.append(label); print('  FAIL  ' + label + '  (no exception raised)')


# ═══════════════════════════════════════════════════════════════════════════════
# Namespace: the config the tested cells read, at the values Cells 3.1/3.3/3.5 set.
# A 10-week window, so the trailing machinery has something to chew on.
# ═══════════════════════════════════════════════════════════════════════════════
FILTER_START, FILTER_END = '2026-01-07', '2026-03-11'
AS_OF_DATE = pd.Timestamp('2026-03-11').date()
METRO_GROUPS = {
    'DFW': ['irving', 'garland', 'fort worth', 'ft worth', 'dallas', 'plano', 'mesquite',
            'lewisville', 'grand prairie', 'denton', 'mckinney', 'frisco', 'richardson',
            'carrollton'],
    'Houston': ['houston', 'h3s', 'spring', 'stafford', 'league city', 'sugar land',
                'pearland', 'katy', 'humble', 'baytown', 'conroe', 'tomball', 'woodlands',
                'missouri city', 'rosenberg', 'galveston', 'texas city'],
    'San Antonio': ['san antonio', 'new braunfels', 'schertz', 'seguin', 'boerne'],
}
G = dict(
    np=np, pd=pd, plt=plt, mdates=mdates, io=io, os=os, re=re, math=math,
    time=__import__('time'),
    defaultdict=defaultdict,
    FILTER_START=FILTER_START, FILTER_END=FILTER_END, AS_OF_DATE=AS_OF_DATE,
    PROD_WEEK_START_DOW=6, PROD_WEEK_LABEL='Sun-Sat', OT_WEEK_START_DOW=3,
    OT_WEEK_LABEL='Thu-Wed', OT_WEEKLY_THRESHOLD=40.0,
    ROLL_WEEKS=4, DASH_ROLL_WEEKS=4, TRAILING_MIN_WEEKS=2, TRAILING_SUFFIX='_t4w',
    TRAILING_EXCLUDE_PARTIAL_WEEKS=True,
    CENSUS_MIN_ACTIVE_TECHS=1.0, CENSUS_MIN_TECHS=2, CENSUS_WARN_UNMAPPED_PCT=10.0,
    # ── v1.9.0 ──
    CENSUS_PAYROLL_DENOMINATOR=True,
    CENSUS_HEADLINE_METRIC='census_per_pct_on_payroll',
    CENSUS_PRIOR_HEADLINE_METRIC='census_per_tech_headcount',
    CENSUS_PAYROLL_SPAN_FILL=True, CENSUS_PAYROLL_TAIL_MIN_RATIO=0.90,
    CENSUS_PAYROLL_TAIL_DAYS=21, CENSUS_PAYROLL_MIN_HEADS=2,
    METRO_GROUPS=METRO_GROUPS, METRO_STATES={'DFW': 'TX', 'Houston': 'TX',
                                             'San Antonio': 'TX'},
    METRO_EXCLUDE_WAREHOUSES={'R16 Stafford'},
    SUMMARY_LEVELS=[('VP', 'vp', 'vp', 'VPs'), ('Metro', 'metro', 'metro', 'metros')],
    # ────────────
    VIRTUAL_WH_PREFIX='Z', VIRTUAL_RUG_THRESHOLD_PCT=5.0,
    VIRTUAL_UNRESOLVED_LABEL='Virtual - Unresolved',
    ROUTING_CHANGE_DATE='2026-02-01', RUN_DATE='2026-08-19', NB_VERSION='2.0.0',
    DASH_TOP_N=5, DASH_MIN_ACTIVE_DAYS=30, DASH_PAGE_INCHES=(23, 15),
    LOST_IS_STALE=True, LOST_STALE_NOTE='lost feed ends 2026-02-28 — tail is missing data',
    LOST_BULK_EVENT_DATES=['2025-08-01'], LOST_MAX_DATE=pd.Timestamp('2026-02-28'),
    LOST_RECOVERY_MATURITY_DAYS=90,
    OT_PAY_TYPES_WORKED=['Work', 'On Call Hours'], OT_PAY_TYPES_LEAVE=['PTO', 'Holiday'],
    OT_PAY_TYPES_OT_BASIS=['Work'],
    OT_FEED_COMPLETE_MIN_RATIO=0.70, OT_FEED_COMPLETE_TAIL_DAYS=28,
    OT_DEPTS_TECH=['Patient Care Technician'],
    OT_DEPTS_ALL=['Patient Care Technician', 'Internal Operations'],
    OT_APPORTION_BY_TICKET_SHARE=True, PCT_DEPT='Patient Care Technician',
    FUZZY_EDIT_DIST=1, BRACKET_CHECKS_RAISE=False,
    RECS_LOOKBACK_WEEKS=8, RECS_MIN_WEEKS=2, RECS_MIN_ACTIVE_DAYS=5,
    RECS_NAME_N=5, RECS_EFF_GAP_PCT=15.0, RECS_MIN_SEVERITY_PCT=5.0, RECS_TOP_N=5,
    COACHING_CAVEAT='coaching caveat',
    OUT_DIR=OUT, CHART_DPI=72,
    REPORT_DOCX_ENTITY_RECS='Recs_{level}_{name}.docx',
    PALETTE={'attributed': '#1f77b4'},
    save_fig=lambda fig, name: None,
    standardize_first_name=lambda raw: [raw] if raw else [],
    levenshtein=lambda a, b: 0 if a == b else max(len(a), len(b)),
)
G['_clean'] = lambda s: re.sub(r"['\.\s\-]", '', s).lower() if isinstance(s, str) else ''
TS = G['TRAILING_SUFFIX']

print('\n=== Cell 4.3 — spine, add_trailing & the generalised bracket guard ===========')
exec(CELL[20], G)
week_start_of, add_trailing, WEEK_SPINE = G['week_start_of'], G['add_trailing'], G['WEEK_SPINE']
attach_spine, build_week_spine = G['attach_spine'], G['build_week_spine']
bracket_violations, run_bracket_checks = G['bracket_violations'], G['run_bracket_checks']
WEEKS = list(WEEK_SPINE['week_start'])
check(len(WEEKS) == 10, f'spine has 10 weeks (got {len(WEEKS)})')

_t = pd.DataFrame({'week_start': WEEKS, 'r': [10.0, 12, 11, 13, 12, 11, 10, 12, 11, 12]})
_t['r' + TS] = _t['r'].rolling(4, min_periods=2).mean()
_nbad, _ntot = bracket_violations(_t, 'r', [])
check(_nbad == 0, f'bracket guard passes a true trailing mean ({_nbad} violations)')
_bad = _t.copy(); _bad['r' + TS] = _bad['r' + TS] * 1.5
_nbad, _ = bracket_violations(_bad, 'r', [])
check(_nbad > 0, f'bracket guard catches a value outside its weekly bracket ({_nbad} rows)')
G['BRACKET_CHECKS_RAISE'] = True
raises(lambda: run_bracket_checks('verify', [('co', _bad, [], ['r'])]),
       'run_bracket_checks RAISES when BRACKET_CHECKS_RAISE is True', AssertionError)
G['BRACKET_CHECKS_RAISE'] = False
run_bracket_checks('verify', [('co', _bad, [], ['r'])])
check(True, 'run_bracket_checks demotes to a warning when BRACKET_CHECKS_RAISE is False')

# ═══════════════════════════════════════════════════════════════════════════════
# Cell 4.2 — the metro vocabulary. The reason this cell is now under test at all is
# that a substring match put an ARKANSAS warehouse in the Houston metro.
# ═══════════════════════════════════════════════════════════════════════════════
print('\n=== Cell 4.2 — assign_metro: whole-word matching ==============================')
exec(CELL[18], G)
assign_metro = G['assign_metro']
_norm = G['_normalize_wh_for_metro']
_CASES = [
    ('R16 Spring',          'Houston',     'the site the "spring" pattern exists for'),
    ('R03 Hot Springs',     None,          'ARKANSAS — must NOT match the word "spring"'),
    ('R05 Natchez Storage', None,          'Mississippi storage — matches nothing'),
    ('R12 Ft. Worth',       'DFW',         'the abbreviated spelling of the city'),
    ('R12 Fort Worth',      'DFW',         'the other spelling'),
    ('R16 N. Houston',      'Houston',     'directional abbreviation'),
    ('R16 North Houston',   'Houston',     'directional spelled out'),
    ('R16 S. Houston',      'Houston',     'south'),
    ('R16 W. Houston',      'Houston',     'west'),
    ('R16 League City',     'Houston',     'two-word city'),
    ('R16 H3S',             'Houston',     'the Houston-region code, not a city name'),
    ('TXS Garland',         'DFW',         'the TXS prefix is stripped'),
    ('R12 Garland',         'DFW',         'and the R## prefix'),
    ('RNW Garland',         'DFW',         'and RNW'),
    ('R14 San Antonio WH',  'San Antonio', 'trailing site-type token ignored'),
    ('RNW San Antonio WH',  'San Antonio', 'same, other region'),
    ('R14 Harlingen',       None,          'Texas, but not in any of the three metros'),
    ('RNW Austin',          None,          'Texas, deliberately not a reported metro'),
    ('R11 Columbia - SC',   None,          'South Carolina'),
    ('R16 Stafford',        None,          'in METRO_EXCLUDE_WAREHOUSES for this run'),
    ('',                    None,          'empty string'),
    (None,                  None,          'None'),
]
_mbad = []
for _wh, _want, _why in _CASES:
    _got = assign_metro(_wh)
    if _got != _want:
        _mbad.append(f'{_wh!r} -> {_got!r}, expected {_want!r} ({_why})')
check(not _mbad, f'all {len(_CASES)} metro assignments correct'
                 + ('' if not _mbad else ': ' + '; '.join(_mbad)))
check(_norm('R16 N. Houston') == 'north houston',
      f"normaliser expands directions (got {_norm('R16 N. Houston')!r})")
check('spring' not in _norm('R03 Hot Springs').split(),
      'the normalised Arkansas name contains no whole word "spring"')
check(assign_metro('R16 Stafford', metro_groups={'Houston': ['stafford']}) is None,
      'the exclusion list beats an explicit custom pattern')

# ═══════════════════════════════════════════════════════════════════════════════
# Synthetic upstream frames. Built ONCE, in dependency order, because v1.9.0's census
# cell needs the payroll roster and the payroll roster needs the ticket feed.
#
# WH_A, WH_B -> VP North / Houston.  WH_C -> VP South / San Antonio (single technician,
# suppressed on the ACTIVE basis but sound on the PAYROLL one — that pair is the point).
# ═══════════════════════════════════════════════════════════════════════════════
_HIER = {'WH_A': ('VP North', 'TX', 'Houston'),
         'WH_B': ('VP North', 'TX', 'Houston'),
         'WH_C': ('VP South', 'TX', 'San Antonio')}
_rows = []
for wi, ws in enumerate(WEEKS):
    for d in pd.date_range(ws, ws + pd.Timedelta(days=6)):
        if d.dayofweek >= 5 or not (pd.Timestamp(FILTER_START) <= d <= pd.Timestamp(FILTER_END)):
            continue
        if wi != 4:                                   # week 4: WH_A silent entirely
            _rows.append(('Ann', 'Alpha', 'WH_A', d, 9))
            _rows.append(('Dee', 'Delta', 'WH_A', d, 8))
            _rows.append(('Bob', 'Beta', 'WH_A', d, 6))
            if wi % 2 == 0:                           # Hal works alternating weeks only
                _rows.append(('Hal', 'Eta', 'WH_A', d, 5))
        if wi >= 5:                                   # WH_B opens in week 5
            _rows.append(('Bob', 'Beta', 'WH_B', d, 3))
            _rows.append(('Eve', 'Epsilon', 'WH_B', d, 5))
            _rows.append(('Fay', 'Phi', 'WH_B', d, 4))
        _rows.append(('Cal', 'Gamma', 'WH_C', d, 4))
        if wi <= 2:
            # Moe works WH_C early and stops. He stays ON THE PAYROLL, so from week 3 the
            # site has ONE active technician (suppressed on the active basis) and TWO hired
            # heads (sound on the payroll basis) — the pair that proves the two suppression
            # flags have to be independent.
            _rows.append(('Moe', 'Mu', 'WH_C', d, 3))
_td = pd.DataFrame(_rows, columns=['techfirstname', 'techlastname', 'tech_warehouse',
                                   'completed_date', 'day_tickets'])
_td['_tech_key'] = _td['techfirstname'] + '|' + _td['techlastname']
_td[['vp', 'state', 'metro']] = pd.DataFrame(
    [_HIER[w] for w in _td['tech_warehouse']], index=_td.index)
_td['week_start'] = week_start_of(_td['completed_date'])
_td['_tech_day_tickets'] = _td.groupby(['_tech_key', 'completed_date'])['day_tickets'].transform('sum')
_td['active_day_share'] = _td['day_tickets'] / _td['_tech_day_tickets']
G['_techday'] = _td
_GR = ['techfirstname', 'techlastname', '_tech_key', 'tech_warehouse', 'vp', 'state', 'metro']
G['_techday_wk'] = (_td.groupby(_GR + ['week_start'], dropna=False, as_index=False)
                    .agg(total_tickets=('day_tickets', 'sum'),
                         active_weekdays=('completed_date', 'nunique'),
                         active_day_equiv=('active_day_share', 'sum')))

_cen = []
for wi, ws in enumerate(WEEKS):
    for d in pd.date_range(ws, ws + pd.Timedelta(days=6)):
        if not (pd.Timestamp(FILTER_START) <= d <= pd.Timestamp(AS_OF_DATE)):
            continue
        if wi == 4:
            continue
        if wi == 6 and d.dayofweek != 0:
            continue
        if wi < 8:
            _cen.append((d, 'WH_A', 900.0))
        if wi >= 5:
            _cen.append((d, 'WH_B', 300.0))
        _cen.append((d, 'WH_C', 120.0))
        _cen.append((d, 'Z CS', 40.0))
_cd = pd.DataFrame(_cen, columns=['census_date', 'warehouse', 'pt_count'])
_cd['pt_count_all'] = _cd['pt_count'] * 1.1
_cd['_is_virtual_census'] = _cd['warehouse'].str.upper().str.startswith('Z')
_cd['week_start'] = week_start_of(_cd['census_date'])
_cd['period'] = _cd['census_date'].dt.strftime('%Y-%m')
G['df_census_daily'] = _cd

# ── the ticket frame the roster and the OT map are matched against ─────────────
_txr = []
for wi, ws in enumerate(WEEKS):
    for d in pd.date_range(ws, ws + pd.Timedelta(days=4)):
        if not (pd.Timestamp(FILTER_START) <= d <= pd.Timestamp(AS_OF_DATE)):
            continue
        _txr.append(('Ann', 'Alpha', 'WH_A', d))
        _txr.append(('Bob', 'Beta', 'WH_A', d))
        _txr.append(('Dee', 'Delta', 'WH_A', d))
        if wi >= 5:
            _txr.append(('Eve', 'Epsilon', 'WH_B', d))
            _txr.append(('Fay', 'Phi', 'WH_B', d))
        if wi % 2 == 0:
            _txr.append(('Cal', 'Gamma', 'WH_C', d))
            _txr.append(('Hal', 'Eta', 'WH_A', d))
        if wi <= 2:
            _txr.append(('Moe', 'Mu', 'WH_C', d))
df_tx = pd.DataFrame(_txr, columns=['techfirstname', 'techlastname', 'tech_warehouse',
                                    'completed_date'])
df_tx['order_num'] = np.arange(len(df_tx)).astype(str)
df_tx['_unattributed'] = False
df_tx[['vp', 'state', 'metro']] = pd.DataFrame([_HIER[w] for w in df_tx['tech_warehouse']],
                                               index=df_tx.index)
G['df_tx'] = df_tx

# ── payroll. Every ticket technician is on it — that containment is what makes the active
# share a share of something — plus the heads the v1.9.0 machinery exists for:
#     Alpha, Ann      44 Work hours a week                  -> 4h OT
#     Beta, Bob       38 Work + 6 On Call                    -> 0h OT on the new basis, 4h on
#                                                              the old one: the v1.8.0 delta
#     Gamma, Cal      alternating payroll weeks              -> the A2 idle-week case
#     Delta, Dee      payroll rows STOP before the tail      -> tail ROSTER-LAGGING
#     Epsilon, Eve  } plain 40h weeks, present so the establishment CONTAINS the technicians
#     Phi, Fay      } on tickets rather than crossing it
#     Mu, Moe       }
#     Eta, Hal        one whole PRODUCTIVITY week with no hours -> span-fill must keep him on
#     Zeta, Zoe       on the payroll, NEVER on a ticket      -> UNATTRIBUTED
#     Kappa, Kim      JOINS mid-window, never on a ticket    -> the window headcount must
#                                                              exceed the mean of the weekly
#                                                              counts (a mid-window joiner is
#                                                              counted once, not fractionally)
_hrows = []


def _in_window(d):
    """Cell 7.6's extract bounds, reproduced. The PLC query is
    WorkDate >= FILTER_START AND WorkDate < AS_OF_DATE + 1 day, so no fixture row may sit
    outside that span — one that did put a payroll week beyond the end of the OT spine, whose
    is_partial_week was then NaN rather than True."""
    return pd.Timestamp(FILTER_START) <= pd.Timestamp(d) <= pd.Timestamp(AS_OF_DATE)


def _emp_week(name, ws, work_by_day, oncall=0.0, pto=0.0, dept='Patient Care Technician'):
    for di, h in enumerate(work_by_day):
        if h and _in_window(ws + pd.Timedelta(days=di)):
            _hrows.append({'plc_id': name, 'employee_name': name,
                           'workdate': ws + pd.Timedelta(days=di), 'hours': float(h),
                           'pay_type': 'Work', 'dept': dept, 'location_name': 'X',
                           'sys_updated': pd.Timestamp('2026-03-01'),
                           'reg_hrs_unusable': 0.0, 'ot1_hrs_unusable': 0.0})
    if oncall and _in_window(ws):
        _hrows.append({'plc_id': name, 'employee_name': name, 'workdate': ws,
                       'hours': float(oncall), 'pay_type': 'On Call Hours', 'dept': dept,
                       'location_name': 'X', 'sys_updated': pd.Timestamp('2026-03-01'),
                       'reg_hrs_unusable': 0.0, 'ot1_hrs_unusable': 0.0})
    if pto and _in_window(ws + pd.Timedelta(days=1)):
        _hrows.append({'plc_id': name, 'employee_name': name, 'workdate': ws + pd.Timedelta(days=1),
                       'hours': float(pto), 'pay_type': 'PTO', 'dept': dept,
                       'location_name': 'X', 'sys_updated': pd.Timestamp('2026-03-01'),
                       'reg_hrs_unusable': 0.0, 'ot1_hrs_unusable': 0.0})


OT_SPINE_PREVIEW = build_week_spine(FILTER_START, AS_OF_DATE, 3)
OTW = list(OT_SPINE_PREVIEW['week_start'])
for wi, ws in enumerate(OTW):
    if OT_SPINE_PREVIEW['is_partial_week'].iloc[wi]:
        continue
    scale = 0.4 if wi == len(OTW) - 2 else 1.0
    _emp_week('Alpha, Ann', ws, [s * scale for s in (9, 9, 9, 9, 8)])
    _emp_week('Beta, Bob', ws, [s * scale for s in (8, 8, 8, 7, 7)], oncall=6 * scale)
    if wi % 2 == 0:
        _emp_week('Gamma, Cal', ws, [s * scale for s in (10, 10, 10, 6, 6)])
    if wi <= len(OTW) - 4:                    # Dee's payroll stops early  -> tail lag
        _emp_week('Delta, Dee', ws, [s * scale for s in (8, 8, 8, 8, 8)])
    for _nm in ('Epsilon, Eve', 'Phi, Fay', 'Mu, Moe', 'Zeta, Zoe'):
        _emp_week(_nm, ws, [s * scale for s in (8, 8, 8, 8, 8)])
# Hal and Kim are generated on the PRODUCTIVITY week rather than the payroll week, because the
# roster is bucketed Sun-Sat: skipping one Thu-Wed week leaves no Sun-Sat week empty, since the
# neighbouring payroll weeks spill into it. Skipping WEEKS[4] does leave one genuinely empty,
# which is the case span-fill exists for.
for wi, ws in enumerate(WEEKS):
    if wi != 4:
        _emp_week('Eta, Hal', ws, (8, 8, 8, 8))
    if wi >= 4:
        _emp_week('Kappa, Kim', ws, (8, 8, 8, 8, 8))
df_hours_raw = pd.DataFrame(_hrows)
df_hours_raw['workdate'] = pd.to_datetime(df_hours_raw['workdate'])
df_hours_raw['dow_mon0'] = (df_hours_raw['workdate'] - pd.Timestamp('1900-01-01')).dt.days % 7
G['df_hours_raw'] = df_hours_raw

# ═══════════════════════════════════════════════════════════════════════════════
# Cell 13.4 — the payroll PCT roster
# ═══════════════════════════════════════════════════════════════════════════════
print('\n=== Cell 13.4 — payroll PCT roster (the hired establishment) =================')
_buf134 = io.StringIO()
with contextlib.redirect_stdout(_buf134):
    exec(CELL[66], G)
ROSTER, SHARE = G['df_pct_roster'], G['df_pct_roster_share']
PLC_MAP, ROSTER_WK = G['df_plc_map'], G['tbl_pct_roster_weekly']
LAG = G['PCT_ROSTER_LAG_WEEKS']
print(_buf134.getvalue().rstrip())

_HEADS = set(SHARE['_plc_key'])
check(len(_HEADS) == 10, f'ten hired PCTs on the establishment (got {len(_HEADS)}: '
                         f'{sorted(_HEADS)})')
check(set(_td['_tech_key']) <= _HEADS,
      f'the establishment CONTAINS every technician on tickets — the containment the active '
      f'share is a share OF (missing: {sorted(set(_td["_tech_key"]) - _HEADS)})')
# SPAN-FILL: Hal has no PLC row in one middle week and must still be on the payroll in it
_hal = ROSTER[ROSTER['_plc_key'] == 'Hal|Eta'].sort_values('week_start')
check(bool((~_hal['has_hours']).any()),
      'span-fill keeps a head on the payroll in a week they had NO hours '
      f'({int((~_hal["has_hours"]).sum())} such week(s) for Hal)')
check(int(_hal['week_start'].nunique()) > int(_hal['has_hours'].sum()),
      'and the establishment is therefore LARGER than "weeks with hours" would give')

# THE PROPERTY EVERY ENTITY FIGURE RESTS ON: shares sum to 1.0 per (head, week).
# Cell 13.4 asserts this itself; re-derive it independently rather than trusting the assert.
_ss = SHARE.groupby(['_plc_key', 'week_start'])['share'].sum()
check(bool(((_ss - 1.0).abs() <= 1e-9).all()),
      f'site shares sum to exactly 1.0 on all {len(_ss):,} (head, week) pairs')

# UNATTRIBUTED: Zoe is on the payroll and on no ticket, so she reaches no site — and the row
# EXISTS rather than being dropped, which is what makes the gap measurable.
_zoe = SHARE[SHARE['_plc_key'] == 'Zoe|Zeta']
check(len(_zoe) > 0 and bool(_zoe['tech_warehouse'].isna().all()),
      'a head with no ticket history is present and explicitly UNATTRIBUTED')
check(bool((_zoe['attribution'] == 'no payroll->ticket name match').all()),
      f'...and labelled with WHY (got {sorted(set(_zoe["attribution"]))})')
check(G['PCT_ROSTER_UNATTRIBUTED_PCT'] > 0,
      f'the unattributed share is published, not silently zero '
      f'({G["PCT_ROSTER_UNATTRIBUTED_PCT"]}%)')
# ...and everyone with tickets DOES reach a site, including in weeks they had none
_ann = SHARE[SHARE['_plc_key'] == 'Ann|Alpha']
check(bool(_ann['tech_warehouse'].notna().all()),
      'a head with ticket history reaches a site in EVERY week on their span')
check('window ticket share (no tickets that week)' in set(SHARE['attribution']),
      'the window-share fallback fires for a week with no tickets (a head on PTO all week '
      'still belongs to a site)')

# ROSTER LAG: Dee's payroll stops two weeks early, so the tail headcount drops below 90%.
check(len(LAG) >= 1, f'the short tail week(s) are flagged ROSTER-LAGGING (got {len(LAG)})')
check(bool(ROSTER_WK['week_start'].nunique() == len(WEEKS)),
      'the weekly headcount table is built on the SPINE, so a zero-head week is visible '
      f'({ROSTER_WK["week_start"].nunique()} of {len(WEEKS)} weeks present)')
if LAG:
    _lagwk = max(LAG)
    _pre = ROSTER_WK[ROSTER_WK['week_start'] < _lagwk]['heads_on_payroll']
    _at = float(ROSTER_WK.loc[ROSTER_WK['week_start'] == _lagwk, 'heads_on_payroll'].iloc[0])
    check(_at < 0.9 * float(_pre.median()),
          f'...and the flagged week really is short ({_at:.0f} heads against a '
          f'{_pre.median():.0f} trailing median)')

# ONE MAP, shared with Cell 15.5
check(set(PLC_MAP['_plc_key']) == _HEADS - {'Zoe|Zeta', 'Kim|Kappa'},
      f'the PLC->technician map ties every head with tickets and only those '
      f'(unmatched: {sorted(_HEADS - set(PLC_MAP["_plc_key"]))})')
check('_tech_key' in PLC_MAP.columns, 'the map carries _tech_key for the census join')

_ATTR = G['tbl_pct_roster_attribution']
check(set(_ATTR.columns) >= {'attribution', 'head_weeks', 'heads'},
      'the attribution breakdown ships as a table')

# ═══════════════════════════════════════════════════════════════════════════════
# Cell 13.5 — census on both denominators
# ═══════════════════════════════════════════════════════════════════════════════
print('\n=== Cell 13.5 — census per technician: payroll + retained denominators ======')
_buf135 = io.StringIO()
with contextlib.redirect_stdout(_buf135):
    exec(CELL[68], G)
CWH, CVP, CMET, CCO = (G['dash_wk_census_wh'], G['dash_wk_census_vp'],
                       G['dash_wk_census_metro'], G['dash_wk_census_co'])
_out135 = _buf135.getvalue()
print('  (Reconciliations 1-8 inside Cell 13.5 all passed — the cell raises otherwise.)')

# ── Reconciliation 7, re-derived independently: the PAYROLL inputs divide in ──
_bad = 0
for _fr in (CCO, CVP, CMET, CWH):
    _p = pd.to_numeric(_fr['census_per_pct_on_payroll' + TS], errors='coerce')
    _q = (pd.to_numeric(_fr['ratio_adc_payroll' + TS], errors='coerce')
          / pd.to_numeric(_fr['ratio_pct_on_payroll' + TS], errors='coerce'))
    _bad += int((_p.notna() & _q.notna() & ((_p - _q).abs() > 0.01 + 0.001 * _p.abs())).sum())
    _bad += int((_p.isna() & _q.notna()).sum())
check(_bad == 0, f'published payroll ADC / published payroll headcount == published payroll '
                 f'ratio, all grains ({_bad} mismatches)')
check(int(pd.to_numeric(CCO['census_per_pct_on_payroll' + TS], errors='coerce').notna().sum()) > 0,
      'the company payroll trailing ratio is populated (the check above is not vacuous)')

# ── the RETAINED ratio still holds its own contract (Reconciliation 5) ────────
_bad = 0
for _fr in (CCO, CVP, CMET, CWH):
    _p = pd.to_numeric(_fr['census_per_tech_headcount' + TS], errors='coerce')
    _q = (pd.to_numeric(_fr['ratio_adc' + TS], errors='coerce')
          / pd.to_numeric(_fr['ratio_techs_equiv' + TS], errors='coerce'))
    _bad += int((_p.notna() & _q.notna() & ((_p - _q).abs() > 0.01 + 0.001 * _p.abs())).sum())
check(_bad == 0, f'the RETAINED ratio is untouched and still reproduces from its own inputs '
                 f'({_bad} mismatches)')

# ── Reconciliation 8, re-derived: the company denominator IS the establishment ─
_co = CCO.sort_values('week_start').reset_index(drop=True)
_indep = (ROSTER.groupby('week_start', as_index=False).agg(n=('_plc_key', 'nunique')))
_j = _co[['week_start', 'pct_on_payroll', 'pct_on_payroll_distinct']].merge(
    _indep, on='week_start', how='left')
_m = _j['pct_on_payroll'].notna() & _j['n'].notna()
check(bool(((_j.loc[_m, 'pct_on_payroll'] - _j.loc[_m, 'n']).abs() <= 0.001).all()),
      'the company weekly denominator equals the distinct establishment, re-derived from the '
      'roster (includes the unattributed head)')
_wh_sum = float(CWH.groupby('week_start')['pct_on_payroll'].sum().max())
_co_max = float(pd.to_numeric(_co['pct_on_payroll'], errors='coerce').max())
check(_wh_sum < _co_max - 1e-9,
      f'site rows sum BELOW the company row by the unattributed head, as documented '
      f'({_wh_sum:.2f} vs {_co_max:.2f})')

# ── THE WINDOW DENOMINATOR: a distinct count over the window, not a mean ─────
_D = (pd.to_numeric(_co['pct_on_payroll'], errors='coerce').fillna(0).gt(0)
      & pd.to_numeric(_co['census_days'], errors='coerce').fillna(0).gt(0)
      & ~_co['ratio_payroll_suppressed'].fillna(True).astype(bool)
      & ~_co['is_partial_week'].fillna(False).astype(bool))
_wk_list = list(_co['week_start'])
_mismatch, _tested, _strict_gt = 0, 0, 0
for i in range(len(_co)):
    pub = pd.to_numeric(_co.loc[i, 'ratio_pct_on_payroll' + TS], errors='coerce')
    if pd.isna(pub):
        continue
    lo = max(0, i - 3)
    dweeks = [_wk_list[j] for j in range(lo, i + 1) if bool(_D.iloc[j])]
    expect = ROSTER[ROSTER['week_start'].isin(dweeks)]['_plc_key'].nunique()
    weekly_mean = float(np.mean([_indep.set_index('week_start')['n'].get(_wk_list[j], 0)
                                 for j in range(lo, i + 1) if bool(_D.iloc[j])])) \
        if dweeks else np.nan
    _tested += 1
    if abs(float(pub) - expect) > 0.01:
        _mismatch += 1
    if pd.notna(weekly_mean) and float(pub) > weekly_mean + 0.01:
        _strict_gt += 1
check(_tested > 0 and _mismatch == 0,
      f'company trailing PAYROLL denominator == distinct heads on the payroll anywhere in the '
      f'window ({_mismatch} mismatches over {_tested} weeks)')
check(_strict_gt > 0,
      'window count is STRICTLY above the mean of the weekly counts somewhere (a head who '
      'leaves mid-window is counted once, not fractionally)')

# ── the two suppression flags are INDEPENDENT ────────────────────────────────
# THE POINT OF TWO FLAGS: each direction of disagreement must be reachable. WH_C from week 3
# has ONE active technician (Cal) and TWO hired heads (Cal and Moe, who stopped working but
# stayed employed) — thin on the active basis, sound on the payroll one. The roster-lagging
# tail weeks are the reverse: plenty of active technicians, an incomplete establishment.
_A_only = CWH[CWH['ratio_suppressed'].fillna(False)
              & ~CWH['ratio_payroll_suppressed'].fillna(False)]
_P_only = CWH[~CWH['ratio_suppressed'].fillna(False)
              & CWH['ratio_payroll_suppressed'].fillna(False)]
check(len(_A_only) > 0,
      f'a site-week thin on the ACTIVE denominator and sound on the PAYROLL one exists '
      f'({len(_A_only)} rows) — one flag could not express this')
check(len(_P_only) > 0,
      f'and the reverse exists too ({len(_P_only)} rows: a complete active week on an '
      f'incomplete establishment)')
check(bool(pd.to_numeric(_A_only['census_per_tech_headcount'], errors='coerce').isna().all())
      and bool(pd.to_numeric(_A_only['census_per_pct_on_payroll'],
                             errors='coerce').notna().any()),
      'and each flag withholds ONLY its own ratio')
check(str(CWH['ratio_payroll_suppressed'].dtype) == 'bool',
      'ratio_payroll_suppressed survives as bool through the trailing pass')

# ── a roster-lagging week publishes nothing and is out of the trailing windows ─
if LAG:
    _lagrows = CCO[CCO['week_start'].isin(LAG)]
    check(bool(_lagrows['is_roster_lagging'].all()),
          'the lag flag reaches the census frame')
    check(bool(pd.to_numeric(_lagrows['census_per_pct_on_payroll'],
                             errors='coerce').isna().all()),
          'a roster-lagging week publishes NO payroll ratio')
    _after = pd.to_numeric(CCO.loc[CCO['week_start'] >= min(LAG),
                                   'ratio_pct_on_payroll' + TS], errors='coerce').dropna()
    check(True if not len(_after) else bool((_after > 0).all()),
          'and the trailing window is still computable from the weeks that are complete')
    check(bool(pd.to_numeric(_lagrows['census_per_tech_headcount'],
                             errors='coerce').notna().any()),
          'the RETAINED ratio is unaffected by a payroll feed lag — different denominator, '
          'different flag')

# ── the wedge reconciles the two published figures ──────────────────────────
_wd = CCO[pd.to_numeric(CCO['pct_active_share_pct'], errors='coerce').notna()
          & pd.to_numeric(CCO['census_per_tech_headcount'], errors='coerce').notna()]
if len(_wd):
    r = _wd.iloc[-1]
    _implied = float(r['census_per_tech_headcount']) * float(r['pct_active_share_pct']) / 100
    # RELATIVE tolerance: pct_active_share_pct is published to one decimal place, so on a
    # ratio in the hundreds the rounding alone is worth a few tenths. Anything beyond 0.5% is
    # a real mismatch rather than a display artifact.
    check(abs(_implied - float(r['census_per_pct_on_payroll']))
          < 0.005 * float(r['census_per_pct_on_payroll']),
          f'retained ratio x active share == payroll ratio '
          f'({_implied:.2f} vs {r["census_per_pct_on_payroll"]:.2f}) — the wedge really does '
          f'bridge the two published figures')
    check(float(r['census_per_pct_on_payroll']) < float(r['census_per_tech_headcount']),
          'and the payroll headline reads LOWER than the retained figure, as the restatement '
          'says it must')
else:
    check(False, 'no week carries both published ratios and the wedge')

# ── the v1.8.0 windowed ACTIVE denominator, still correct ────────────────────
_D2 = (pd.to_numeric(_co['techs_equiv'], errors='coerce').fillna(0).gt(0)
       & pd.to_numeric(_co['census_days'], errors='coerce').fillna(0).gt(0)
       & ~_co['ratio_suppressed'].fillna(True).astype(bool)
       & ~_co['is_partial_week'].fillna(False).astype(bool))
_mismatch, _tested, _strict_gt = 0, 0, 0
for i in range(len(_co)):
    pub = pd.to_numeric(_co.loc[i, 'ratio_techs_equiv' + TS], errors='coerce')
    if pd.isna(pub):
        continue
    lo = max(0, i - 3)
    dweeks = [_wk_list[j] for j in range(lo, i + 1) if bool(_D2.iloc[j])]
    expect = _td[_td['week_start'].isin(dweeks)]['_tech_key'].nunique()
    weekly_mean = float(np.mean([_co.loc[j, 'techs_distinct'] for j in range(lo, i + 1)
                                 if bool(_D2.iloc[j])])) if dweeks else np.nan
    _tested += 1
    if abs(float(pub) - expect) > 0.01:
        _mismatch += 1
    if pd.notna(weekly_mean) and float(pub) > weekly_mean + 0.01:
        _strict_gt += 1
check(_tested > 0 and _mismatch == 0,
      f'v1.8.0 active window denominator unchanged ({_mismatch}/{_tested})')
check(_strict_gt > 0, 'and still strictly above the weekly mean where Hal alternates weeks')

_wk5 = WEEKS[6]
_s_eq = float(CWH[CWH['week_start'] == _wk5]['techs_equiv'].sum())
_co_di = float(CCO[CCO['week_start'] == _wk5]['techs_distinct'].iloc[0])
check(abs(_s_eq - _co_di) < 0.01,
      f'weekly apportioned ACTIVE headcount still sums to the company distinct count '
      f'({_s_eq:.2f} vs {_co_di:.0f})')
check('THE TWO CENSUS DENOMINATORS SIDE BY SIDE' in _out135,
      'the run log prints the two-denominator comparison on every run')
_LED = G['tbl_census_denominator_recon']
check({'pct_on_payroll', 'census_per_pct_on_payroll', 'pct_active_share_pct'} <= set(_LED.columns),
      'the monthly input ledger carries both denominators and the wedge')
_BASES = G['tbl_census_denominator_bases']
check({'heads_on_payroll', 'techs_on_tickets', 'active_share_of_payroll_pct'}
      <= set(_BASES.columns),
      'the two-bases comparison table ships for the workbook')

# ═══════════════════════════════════════════════════════════════════════════════
# Cell 14 — lost equipment: pooled recovery on thin mature cohorts (v1.7.0 harness)
# ═══════════════════════════════════════════════════════════════════════════════
print('\n=== Cell 14 — lost equipment (pooled recovery) ===============================')
_lrows, _aid = [], 0
for wi, ws in enumerate(WEEKS[1:9], start=1):
    n, rec = (2, 1) if wi % 2 else (20, 2)
    for k in range(n):
        _aid += 1
        _lrows.append({'lost_date': ws + pd.Timedelta(days=1), 'asset_tag': f'A{_aid}',
                       'lost_cost': 25.0, 'product_name': 'Concentrator',
                       'lost_reason': 'Not found', 'resolution': 'No resolution',
                       'is_recovered': k < rec, 'is_discarded': False,
                       'is_unresolved': k >= rec, 'cohort_mature': True,
                       'days_to_resolve': 30.0 if k < rec else np.nan,
                       'tech_warehouse': 'WH_A', 'vp': 'VP North', 'state': 'TX',
                       'metro': 'Houston',
                       'period': (ws + pd.Timedelta(days=1)).strftime('%Y-%m')})
G['_lost_filt'] = pd.DataFrame(_lrows)
G['df_inventory_total'] = pd.DataFrame([{'tech_warehouse': 'WH_A',
                                         'total_inventory_count': 1000,
                                         'total_inventory_amount': 50000.0}])
exec(CELL[70], G)
LCO = G['dash_wk_lost_co'].sort_values('week_start').reset_index(drop=True)
_r = LCO[pd.to_numeric(LCO['recovery_rate_pct' + TS], errors='coerce').notna()]
if len(_r):
    _row = _r.iloc[-1]
    _exp = (float(_row['mature_recovered_assets' + TS])
            / float(_row['mature_cohort_assets' + TS]) * 100)
    check(abs(float(_row['recovery_rate_pct' + TS]) - _exp) < 0.11,
          f'trailing recovery is POOLED (got {_row["recovery_rate_pct" + TS]:.1f}, '
          f'pooled parts give {_exp:.1f})')
    _wmean = float(pd.to_numeric(LCO['recovery_rate_pct'], errors='coerce').mean())
    check(abs(float(_row['recovery_rate_pct' + TS]) - _wmean) > 5,
          f'...and it visibly differs from the mean of weekly rates ({_wmean:.1f})')
else:
    check(False, 'no trailing recovery value produced')

# ═══════════════════════════════════════════════════════════════════════════════
# Cell 15.5 — overtime, now consuming Cell 13.4's frames
# ═══════════════════════════════════════════════════════════════════════════════
print('\n=== Cell 15.5 — overtime (on the shared payroll frame) =======================')
_buf155 = io.StringIO()
with contextlib.redirect_stdout(_buf155):
    exec(CELL[74], G)
OCO, OWH, OT_SPINE = G['dash_wk_ot_co'], G['dash_wk_ot_wh'], G['OT_WEEK_SPINE']
check(G['df_ot_map'] is G['df_plc_map'],
      'Cell 15.5 uses Cell 13.4\'s map rather than rebuilding one — one attribution model')

_full = OCO[~OCO['is_partial_week'].fillna(False).astype(bool)]
# THE ON-CALL DELTA is the v1.8.0 invariant, and it is asserted instead of an employee count
# because it does not depend on who else is on the payroll that week: only Bob has on-call
# hours, and only his 38 + 6 crosses 40 on the old basis. Every complete week must therefore
# differ between the two bases by exactly his 4 hours.
_probe = _full[~_full['week_start'].isin(
    set(OT_SPINE.loc[OT_SPINE['is_feed_incomplete'], 'week_start']))]
_delta = (pd.to_numeric(_probe['ot_hours_incl_oncall'], errors='coerce')
          - pd.to_numeric(_probe['ot_hours'], errors='coerce'))
check(len(_probe) > 0 and bool(((_delta - 4.0).abs() < 0.01).all()),
      f'on-call is excluded from the threshold: every complete week differs from the old '
      f'basis by exactly Bob\'s 4 hours (got {sorted(set(_delta.round(2)))})')
check(bool((pd.to_numeric(_probe['ot_hours'], errors='coerce') >= 4.0 - 0.01).all()),
      'and Ann\'s own 4 hours of real overtime are still counted on the new basis')

_flagged = OT_SPINE[OT_SPINE['is_feed_incomplete']]
check(len(_flagged) >= 1, f'the deflated tail payroll week is flagged feed-incomplete '
                          f'(got {len(_flagged)})')
if len(_flagged):
    _fb = _flagged['week_start'].iloc[0]
    check(bool(OCO.loc[OCO['week_start'] == _fb, 'is_partial_week'].iloc[0]),
          'the feed-incomplete week is treated as partial (hollow, out of trailing windows)')
    _tail_t = pd.to_numeric(OCO.loc[OCO['week_start'] >= _fb, 'ot_hours' + TS],
                            errors='coerce').dropna()
    check(bool((_tail_t > 3.0).all()) if len(_tail_t) else True,
          f'trailing OT ignores the feed-incomplete week (tail values '
          f'{list(_tail_t.round(2))})')
check('ot_hours_per_tech' in OCO.columns and ('ot_hours_per_tech' + TS) in OCO.columns,
      'audit A1: the company frame carries ot_hours_per_tech (+ trailing)')

WHC = OWH[OWH['tech_warehouse'] == 'WH_C'].sort_values('week_start')
_wc = WHC[pd.to_numeric(WHC['ot_hours_per_tech' + TS], errors='coerce').notna()]
if len(_wc):
    _row = _wc.iloc[-1]
    _exp = float(_row['ot_hours' + TS]) / float(_row['technicians' + TS])
    check(abs(float(_row['ot_hours_per_tech' + TS]) - _exp) < 0.05,
          f'audit A2: pooled per-tech OT divides by the zero-filled technician count '
          f'(got {_row["ot_hours_per_tech" + TS]}, parts give {_exp:.2f})')
    check(float(_row['technicians' + TS]) < 1.0 - 1e-9,
          'and the trailing technician count reflects the idle weeks')
else:
    check(False, 'no trailing per-tech OT produced for the intermittent site')

# ═══════════════════════════════════════════════════════════════════════════════
# Cell 15.6 — the calibration diagnostic
# ═══════════════════════════════════════════════════════════════════════════════
print('\n=== Cell 15.6 — OT calibration ================================================')
_cwd = os.getcwd()
_iso = os.path.join(OUT, 'empty'); os.makedirs(_iso, exist_ok=True)
os.chdir(_iso)
try:
    with contextlib.redirect_stdout(io.StringIO()):
        exec(CELL[76], G)
    check(True, 'calibration cell degrades gracefully with no OT Week files present')
except Exception as e:
    check(False, f'calibration cell raised with no files: {e}')
finally:
    os.chdir(_cwd)
check('payroll_weeks' in G['dash_mo_ot_co'].columns
      and int(pd.to_numeric(G['dash_mo_ot_co']['payroll_weeks'], errors='coerce').max()) >= 4,
      'the OT monthly bridge carries payroll_weeks (4-vs-5-week months made visible)')

# ═══════════════════════════════════════════════════════════════════════════════
# Cell 17.5 — a scorecard PER LEVEL
# ═══════════════════════════════════════════════════════════════════════════════
print('\n=== Cell 17.5 — scorecard & technician detail, every level ===================')


def _frame(gcol, vals, cols, extra=None):
    rows = []
    for k, v in enumerate(vals):
        for wi, ws in enumerate(WEEKS):
            r = {'week_start': ws}
            if gcol:
                r[gcol] = v
                if gcol == 'tech_warehouse':
                    r['vp'], r['state'], r['metro'] = _HIER[v]
            for c, base in cols.items():
                r[c] = base * (1 + 0.1 * ((wi + k) % 5))
            rows.append(r)
    d = attach_spine(pd.DataFrame(rows))
    gc = [gcol] if gcol else []
    return add_trailing(d, gc, rate_cols=list(cols))


_VPS, _METS = ['VP North', 'VP South'], ['Houston', 'San Antonio']
for _fam, _cols in (
        # The column lists are the DOCUMENTED ones, not the minimum the scorecard needs:
        # Cell 21 raises if METRIC_REGISTRY describes a column no frame produces, and that
        # guard is worth exercising rather than working around.
        ('prod', dict(tickets_per_active_day_per_tech=12.5, total_tickets=500.0,
                      total_active_tech_days=40.0, virtual_ticket_share_pct=6.0,
                      denominator_inflation_pct=8.0, rolling_4wk_avg=12.5,
                      tickets_per_active_day_wholeday=11.8, tech_count=20.0)),
        ('redel', dict(redelivery_count=12.0, total_tickets=520.0, redel_per_100_tickets=2.3)),
        ('stockout', dict(stockout_orders=30.0, total_tickets=520.0,
                          stockouts_per_100_tickets=5.8, open_pct=7.0, canceled_pct=28.0,
                          fulfilled_pct=64.7, median_days_to_fulfil=6.0)),
        ('lost', dict(lost_asset_count=10.0, lost_cost_per_1k_pt_days=140.0,
                      recovery_rate_pct=15.0, pt_days=5000.0, lost_pct_of_inventory=1.0)),
        ('ot', dict(ot_hours=40.0, ot_pct_of_worked=16.0, ot_hours_per_tech=8.0,
                    worked_hours=900.0)),
):
    G[f'dash_wk_{_fam}_vp'] = _frame('vp', _VPS, _cols)
    G[f'dash_wk_{_fam}_metro'] = _frame('metro', _METS, _cols)
    G[f'dash_wk_{_fam}_wh'] = _frame('tech_warehouse', ['WH_A', 'WH_B', 'WH_C'], _cols)
    if f'dash_wk_{_fam}_co' not in G or _fam in ('prod', 'redel', 'stockout'):
        G[f'dash_wk_{_fam}_co'] = _frame(None, [None], _cols)
# the REAL census frames stay in place — the point is to score the new columns
G['redel_linked'] = pd.DataFrame(columns=['techfirstname', 'techlastname', 'event_key',
                                          'week_start', 'product'])
_buf175 = io.StringIO()
with contextlib.redirect_stdout(_buf175):
    exec(CELL[84], G)
SC, TP = G['entity_scorecards'], G['entity_tech_perf']
print(_buf175.getvalue().rstrip())

check(set(SC) == {'VP', 'Metro'}, f'a scorecard per level (got {sorted(SC)})')
check(len(SC['Metro']) > 0, 'the Metro scorecard is populated')
check(set(SC['Metro']['entity']) == set(_METS),
      f'both metros are scored (got {sorted(set(SC["Metro"]["entity"]))})')
check(set(SC['VP']['metric']) == set(SC['Metro']['metric']),
      'the two levels score the SAME metric set — one registry, so a metric cannot be added '
      'to one level and forgotten in the other')
check('census_per_pct_on_payroll' in set(SC['Metro']['metric']),
      'the census headline is on the scorecard')
check('census_per_tech_headcount' in set(SC['Metro']['metric']),
      'and the retained figure is beside it')
check(bool((SC['Metro'].loc[SC['Metro']['metric'] == 'census_per_pct_on_payroll',
                            'company_value'].notna()).all()),
      'the census headline carries a real company value (not NaN-scored)')
check(int(SC['Metro']['peers_in_metric'].max()) == len(_METS),
      f'metros are ranked among METROS, not among VPs '
      f'(peers={SC["Metro"]["peers_in_metric"].max()})')
check(bool((SC['VP']['direction'] == 0).any())
      and not bool(SC['VP'].loc[SC['VP']['direction'] == 0, 'is_adverse'].any()),
      'a context metric is never adverse at either level')
check(G['vp_scorecard'] is SC['VP'] and G['metro_scorecard'] is SC['Metro'],
      'the VP/Metro aliases point at the same objects')
check({'vp_value', 'vps_in_metric'} <= set(SC['VP'].columns),
      'the legacy VP_Scorecard column names survive as aliases')

check(set(TP) == {'VP', 'Metro'}, 'technician detail per level')
_tpm, _tpv = TP['Metro'], TP['VP']
check('metro' in _tpm.columns and 'vp' in _tpv.columns,
      'each level\'s detail carries its own grouping column')
check(set(_tpm['metro'].dropna()) == set(_METS), 'both metros have technician detail')
# THE POINT: the same technician gets a different comparison at each level
_bob_v = _tpv[_tpv['_tech_key'] == 'Bob|Beta']
_bob_m = _tpm[_tpm['_tech_key'] == 'Bob|Beta']
check(len(_bob_v) and len(_bob_m), 'a technician appears at both levels')
if len(_bob_v) and len(_bob_m):
    check(abs(float(_bob_v['level_median_tickets_per_active_day'].iloc[0])
              - float(_bob_m['level_median_tickets_per_active_day'].iloc[0])) >= 0
          and _bob_v['comparison_base'].iloc[0] != _bob_m['comparison_base'].iloc[0],
          f'...compared to a different median in each, and the row SAYS which '
          f'({_bob_v["comparison_base"].iloc[0]!r} vs '
          f'{_bob_m["comparison_base"].iloc[0]!r})')
check(bool((_tpm['interpretation_caveat'] == G['COACHING_CAVEAT']).all()),
      'the coaching caveat rides on every metro row too, not just VP rows')
# a technician working two warehouses in one metro must not be double-counted
_dupes = _tpm.groupby(['metro', '_tech_key']).size()
check(bool((_dupes <= 1).all()),
      f'one row per (metro, technician) — no double count for a technician at two sites in '
      f'one metro (max {int(_dupes.max())})')

# ═══════════════════════════════════════════════════════════════════════════════
# Cell 22 — one recommendation document per entity, per level
# ═══════════════════════════════════════════════════════════════════════════════
print('\n=== Cell 22 — recommendation documents, VP and Metro =========================')
_BLK = []


def _b(t, **kw):
    d = dict(t=t); d.update(kw); _BLK.append(d); return d


G.update(
    h1=lambda v: _b('h1', v=v), h2=lambda v: _b('h2', v=v), h3=lambda v: _b('h3', v=v),
    p=lambda v, style=None: _b('p', v=v, style=style),
    note=lambda v: _b('note', v=v), caveat=lambda v: _b('caveat', v=v),
    bullets=lambda v: _b('bullets', v=v), kv=lambda v: _b('kv', v=v),
    numbers=lambda v: _b('numbers', v=v),
    pagebreak=lambda: _b('pagebreak'),
    table=lambda h, r, widths=None, caption=None: _b('table', h=h, r=r, caption=caption),
    render_docx=lambda blocks, path, **kw: (open(path, 'w', encoding='utf-8').write('x') or True),
    tbl_metro_coverage=pd.DataFrame([
        {'tech_warehouse': 'WH_A', 'state': 'TX', 'metro': 'Houston', 'tickets': 900},
        {'tech_warehouse': 'WH_B', 'state': 'TX', 'metro': 'Houston', 'tickets': 400},
        {'tech_warehouse': 'WH_C', 'state': 'TX', 'metro': 'San Antonio', 'tickets': 200},
        {'tech_warehouse': 'WH_D', 'state': 'TX', 'metro': None, 'tickets': 50}]),
)
_buf22 = io.StringIO()
with contextlib.redirect_stdout(_buf22):
    exec(CELL[94], G)
RB, RP = G['entity_rec_blocks'], G['entity_rec_paths']
print(_buf22.getvalue().rstrip())

check(set(k[0] for k in RB) == {'VP', 'Metro'},
      f'documents built at both levels (got {sorted(set(k[0] for k in RB))})')
check(all(('Metro', m) in RB for m in _METS),
      'every metro has a recommendation document')
check(len(RP) == len(RB), f'every document was written ({len(RP)} of {len(RB)})')
check(all(os.path.exists(p) for p in RP.values()), 'the files really exist on disk')
check(any('Metro' in os.path.basename(p) for p in RP.values()),
      'the filename carries the level, so a folder of documents sorts into VPs and metros')


def _texts(key):
    return ' '.join(str(b.get('v', '')) for b in RB[key] if isinstance(b.get('v'), str))


_htxt = _texts(('Metro', 'Houston'))
check('Houston' in _htxt, 'the metro document names the metro')
check('WH_A' in _htxt and 'WH_B' in _htxt,
      'and lists the warehouses the metro is built from — a reader can see the definition '
      'before acting on the numbers')
check('WH_C' not in _htxt.split('Warehouses in')[0],
      'and does not claim another metro\'s site')
check("VP" in _htxt and 'median' in _htxt,
      'the cross-level caveat (also measured against their VP median) is present')
check('hired PCT' in _htxt or 'hired' in _htxt,
      'the census restatement is stated in the document, not only in the pack appendix')
check(G['vp_rec_blocks'] and set(G['vp_rec_blocks']) == set(_VPS),
      'the vp_rec_blocks alias still resolves for Cell 23')
_h3s = [b for b in RB[('Metro', 'Houston')] if b['t'] == 'h3']
check(len(_h3s) >= 1, f'the metro document contains ranked recommendations ({len(_h3s)})')
check(any(b['t'] == 'table' for b in RB[('Metro', 'Houston')]),
      'including the scorecard table')

# ═══════════════════════════════════════════════════════════════════════════════
# Cell 18 — the full renderer, and the year on every axis label
# ═══════════════════════════════════════════════════════════════════════════════
print('\n=== Cell 18 — renderer, census readout & MMM-YY axis labels ==================')
_tb_cols = ['rank_group', 'techfirstname', 'techlastname', 'tech_warehouse', 'total_tickets',
            'active_weekdays', 'tickets_per_active_day', 'redel_per_100_tickets']
_tb = pd.DataFrame([['Top', 'Ann', 'Alpha', 'WH_A', 420, 45, 14.2, 1.9],
                    ['Bottom', 'Cal', 'Gamma', 'WH_C', 210, 42, 7.1, 4.8]], columns=_tb_cols)
G['dash_tb_co'] = _tb
G['dash_tb_vp'] = _tb.assign(vp='VP North')
G['dash_tb_metro'] = _tb.assign(metro='Houston')
G['dash_tb_wh'] = _tb
G['DASH_PDF_NAME'] = 'verify_pages_v200.pdf'
with contextlib.redirect_stdout(io.StringIO()):
    exec(CELL[86], G)
PAGES = G['dash_page_pdfs']
check(len(PAGES) == 1 + 2 + 2 + 3,
      f'one entry per entity: company + 2 VP + 2 metro + 3 WH = 8 (got {len(PAGES)})')
check(all(len(v) == 2 for v in PAGES.values()), 'every entity rendered both pages')

_ro = G['_census_readout'](CCO)
check(_ro.count('\n') >= 2, f'the census readout prints multiple lines:\n{_ro}')
check('retained' in _ro,
      'and it prints the RETAINED ratio beside the headline, so the restatement is on the '
      'page a reader is holding')
check('ADC' in _ro and 'per tech' in _ro, 'with its column header intact')
check(G['_CENSUS_READOUT'][G['CENSUS_HEADLINE_METRIC']]['wk_den'] == 'pct_on_payroll',
      'the readout is driven by the headline metric, not hard-coded to the old denominator')

_fig, _ax = plt.subplots()
_ax.plot(WEEKS, range(len(WEEKS)))
G['_wk_axis'](_ax, pd.DataFrame({'week_start': WEEKS}))
_fig.canvas.draw()
_labels = [t.get_text() for t in _ax.get_xticklabels() if t.get_text()]
plt.close(_fig)
_ok = [l for l in _labels if re.fullmatch(r'[A-Z][a-z]{2}-\d{2}', l)]
check(len(_labels) > 0 and len(_ok) == len(_labels),
      f'every weekly axis label is MMM-YY with the year (got {_labels[:6]})')

# ═══════════════════════════════════════════════════════════════════════════════
# Cell 16.5 — cross-dataset spike surveillance (isolated namespace, as in v1.8.1)
# ═══════════════════════════════════════════════════════════════════════════════
print('\n=== Cell 16.5 — spike surveillance ===========================================')


def _real_lev(a, b):
    if a == b:
        return 0
    la, lb = len(a), len(b)
    d = [[0] * (lb + 1) for _ in range(la + 1)]
    for i in range(la + 1):
        d[i][0] = i
    for j in range(lb + 1):
        d[0][j] = j
    for i in range(1, la + 1):
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
    return d[la][lb]


_MOS = pd.period_range('2025-06', '2026-03', freq='M')
_PERS = [('Al', 'Ape', 'E1'), ('Bo', 'Bee', 'E2'), ('Cy', 'Sea', 'E3')]
_TRANS = [('All', 'Ape', 'E1', 2), ('Bo', 'Be', 'E2', 1),
          ('Zed', 'Zulu', 'E9', 2), ('Yan', 'Yolo', 'E8', 3)]
_tdr, _txr2 = [], []
for _mo in _MOS:
    _days = [d for d in pd.date_range(_mo.start_time, _mo.end_time) if d.dayofweek < 5][:10]
    for _fn, _ln, _eid in _PERS:
        for _d in _days:
            _tdr.append((_fn, _ln, f'{_fn}|{_ln}', 'WH_A', _d, 3))
            _txr2.append((_fn, _ln, _d, _eid))
    if str(_mo) == '2025-12':
        for _fn, _ln, _eid, _nd in _TRANS:
            for _d in _days[:_nd]:
                _tdr.append((_fn, _ln, f'{_fn}|{_ln}', 'WH_A', _d, 2))
                _txr2.append((_fn, _ln, _d, _eid))
_gs_td = pd.DataFrame(_tdr, columns=['techfirstname', 'techlastname', '_tech_key',
                                     'tech_warehouse', 'completed_date', 'day_tickets'])
_gs_tx = pd.DataFrame(_txr2, columns=['techfirstname', 'techlastname', 'completed_date',
                                      '_matched_eid'])
_gs_tx['order_num'] = np.arange(len(_gs_tx)).astype(str)
_gs_tx['_unattributed'] = False
_gs_hours = pd.DataFrame([{'workdate': _mo.start_time + pd.Timedelta(days=3),
                           'hours': 500.0 if str(_mo) == '2026-01' else 1000.0,
                           'employee_name': 'X, Y'} for _mo in _MOS])
_gs_cd = pd.DataFrame([{'period': str(_mo), 'pt_count': 900.0,
                        'census_date': _mo.start_time + pd.Timedelta(days=i)}
                       for _mo in _MOS for i in range(5)])
GS = dict(pd=pd, np=np, re=re,
          SPIKE_SCAN_THRESHOLD_PCT=25.0, SPIKE_SCAN_WINDOW_MONTHS=7,
          levenshtein=lambda a, b: _real_lev(a, b),
          df_tx=_gs_tx, _techday=_gs_td, df_hours_raw=_gs_hours, df_census_daily=_gs_cd,
          redel_linked=pd.DataFrame(), dash_mo_stockout_co=pd.DataFrame())
_buf16 = io.StringIO()
with contextlib.redirect_stdout(_buf16):
    exec(CELL[80], GS)
_out16 = _buf16.getvalue()
_scan = GS['tbl_spike_scan']
_fl = _scan[_scan['flagged']] if len(_scan) else _scan
check(bool(((_fl['dataset'] == 'distinct technician names (weekday tickets)')
            & (_fl['period'] == '2025-12') & (_fl['deviation_pct'] > 25)).any()),
      'the planted technician-name spike month is flagged HIGH')
check(bool(((_fl['dataset'] == 'payroll hours (PLC, all departments)')
            & (_fl['period'] == '2026-01') & (_fl['deviation_pct'] < -25)).any()),
      'the planted payroll-hours DIP month is flagged LOW (missing data direction)')
check(not bool((_fl['period'].isin([str(_MOS[0]), str(_MOS[-1])])).any()),
      'window-clipped edge months are never flagged')
_tn = GS['tbl_techname_spike']
check(len(_tn) == 4, f'decomposition covers exactly the 4 transient names (got {len(_tn)})')
if len(_tn):
    check(int(_tn['eid_shadows_persistent_name'].sum()) == 2,
          'the two same-employee-ID spellings carry the shadow signature')
check('NAME SPLITTING' in _out16 or 'NAME-SPLITTING' in _out16,
      'the run log states the splitting verdict for the planted month')

# ═══════════════════════════════════════════════════════════════════════════════
# Cell 21 — the metric dictionary. Untested through v1.8.1, and it is the cell most
# likely to break silently on a schema change: it names columns as strings.
# ═══════════════════════════════════════════════════════════════════════════════
print('\n=== Cell 21 — metric dictionary ==============================================')
G['REPORT_DOCX_DICTIONARY'] = 'verify_dict.docx'
_buf21 = io.StringIO()
with contextlib.redirect_stdout(_buf21):
    exec(CELL[92], G)
_out21 = _buf21.getvalue()
DICT_BLOCKS = G['dict_blocks']
check(len(DICT_BLOCKS) > 0, f'the dictionary builds ({len(DICT_BLOCKS)} blocks)')
_dcols = {m[2] for m in G['METRIC_REGISTRY']}
for _c in ('census_per_pct_on_payroll', 'pct_on_payroll', 'pct_active_share_pct',
           'ratio_pct_on_payroll_t4w', 'census_per_tech_headcount'):
    check(_c in _dcols, f'{_c} has a dictionary entry')
check(len({len(m) for m in G['METRIC_REGISTRY']}) == 1,
      'every registry entry has the same arity — a short tuple unpacks into the wrong field '
      'and mislabels a metric rather than raising')
# the cell's OWN completeness check: it names published columns with no dictionary entry.
# Assert the v1.9.0 columns are not among them.
_undoc = _out21.split('no dictionary entry:')[1] if 'no dictionary entry:' in _out21 else ''
check(not any(k in _undoc for k in ('pct_on_payroll', 'census_per_pct_on_payroll',
                                    'pct_active_share_pct')),
      f'and none of the new census columns is reported undocumented'
      + (f' (still undocumented: {_undoc.strip()[:200]})' if _undoc else ''))
_dtxt = ' '.join(str(b.get('v', '')) for b in DICT_BLOCKS if isinstance(b.get('v'), str))
check('YEAR TO DATE' in _dtxt.upper(),
      'the cross-cutting assumptions state the year-to-date window')
check('2026-08-17' in _dtxt,
      'and the dictionary still records the leadership confirmation the headline supersedes')

# ═══════════════════════════════════════════════════════════════════════════════
# Cell 23 — the publishable pack's narrative. reportlab/pypdf are switched OFF so the
# assembly short-circuits; the BLOCK BUILDERS are then called directly, which is where
# every hard-coded column name and every f-string lives.
# ═══════════════════════════════════════════════════════════════════════════════
print('\n=== Cell 23 — cover, executive summary & appendix =============================')
G.update(_RL_OK=False, _PYPDF_OK=False, dict_blocks=DICT_BLOCKS,
         DASH_XLSX_NAME='verify.xlsx', REPORT_DOCX_DICTIONARY='verify_dict.docx',
         REPORT_PUBLISH_PDF='verify_pub.pdf',
         render_pdf_bytes=lambda *a, **k: None)
_buf23 = io.StringIO()
with contextlib.redirect_stdout(_buf23):
    exec(CELL[96], G)
check('SKIPPED' in _buf23.getvalue(),
      'the pack assembly degrades gracefully when reportlab/pypdf are absent')

_BLK.clear()
_cover = G['build_cover_blocks']()
_ctxt = ' '.join(str(b.get('v', '')) for b in _cover if isinstance(b.get('v'), str))
_ckv = [v for b in _cover if b['t'] == 'kv' for v in b['v']]
check('YEAR TO DATE' in _ctxt.upper() or 'year to date' in _ctxt,
      'the cover states the window is year to date')
check(any('metro' in str(v).lower() for _k, v in _ckv),
      'and lists the per-metro recommendation documents among the companion files')

_BLK.clear()
_ex = G['build_exec_summary_blocks']()
_etxt = ' '.join(str(b.get('v', '')) for b in _ex if isinstance(b.get('v'), str))
check(len(_ex) > 10, f'the executive summary builds ({len(_ex)} blocks)')
check('YEAR TO DATE' in _etxt, 'it leads with the window change')
check('HIRED PCT ON THE PAYROLL' in _etxt, 'states the census denominator change')
check('2026-08-17' in _etxt,
      'and says plainly that this contradicts the confirmed definition rather than burying it')
check('DFW' in _etxt or 'Texas metros' in _etxt, 'and covers the metro change')
# the census input table must be present and must carry BOTH ratios
_tabs = [b for b in _ex if b['t'] == 'table']
check(len(_tabs) >= 2, f'the summary carries its tables ({len(_tabs)})')
_rows = [r for b in _tabs for r in b['r']]
_flat = ' '.join(str(c) for r in _rows for c in r)
check('Hired PCTs on the payroll' in _flat and 'Technicians active on tickets' in _flat,
      'the reconciliation table prints BOTH denominators, so the restatement is a division '
      'a reader can do on the page')
# "where each entity sits" must exist for every summary level
_h2 = [str(b['v']) for b in _ex if b['t'] == 'h2']
check(any('vp' in h.lower() for h in _h2) and any('metro' in h.lower() for h in _h2),
      f'a "where each X sits" section per summary level (got {_h2})')

_BLK.clear()
_ap = G['build_appendix_blocks']()
_atxt = ' '.join(str(b.get('v', '')) for b in _ap
                 if isinstance(b.get('v'), str))
_abul = ' '.join(str(v) for b in _ap if b['t'] == 'bullets' for v in b['v'])
check('two definitions' in _atxt.lower() or 'two definitions' in _abul.lower(),
      'the appendix carries the open census-denominator question')
check('NOT THE HEADLINE' in _abul,
      'and records that the 2026-08-17 confirmation is not the headline, rather than '
      'deleting it')
check('effective dates' in _abul.lower(),
      'and states the ask that would remove the establishment proxy')

# ═══════════════════════════════════════════════════════════════════════════════
# Cell 24 — the dashboards-only pack. Run three ways: no pypdf (skip), pypdf but no
# reportlab (no cover), and both (cover + bookmarks). The page buffers are the ones Cell 18
# actually rendered above, so this exercises the real assembly rather than a stand-in.
# ═══════════════════════════════════════════════════════════════════════════════
print('\n=== Cell 24 — dashboards-only PDF =============================================')
G['REPORT_DASHBOARDS_PDF'] = 'verify_dashboards_v200.pdf'
_d24 = os.path.join(OUT, G['REPORT_DASHBOARDS_PDF'])
_n_ent = len(PAGES)
_n_pp = len(G['_PAGE_LABELS'])


def _run24():
    _b = io.StringIO()
    with contextlib.redirect_stdout(_b):
        exec(CELL[98], G)
    return _b.getvalue()


# 1. no pypdf at all
if os.path.exists(_d24):
    os.remove(_d24)
G.update(_PYPDF_OK=False, _RL_OK=False)
_o24 = _run24()
check('SKIPPED' in _o24 and not os.path.exists(_d24),
      'without pypdf the pack is skipped rather than half-written')
check('Deliverables written to' in _o24,
      'and the deliverables listing still runs, so the skip is visible beside what did ship')

# 2. pypdf, no reportlab — the pack must still be complete, just cover-less
from pypdf import PdfReader as _PR, PdfWriter as _PW
G.update(_PYPDF_OK=True, _RL_OK=False, PdfReader=_PR, PdfWriter=_PW)
_o24 = _run24()
check(os.path.exists(_d24), 'with pypdf the pack is written')
_rd = _PR(_d24)
check(len(_rd.pages) == _n_ent * _n_pp,
      f'without reportlab it is cover-less and complete: {_n_ent} x {_n_pp} = '
      f'{_n_ent * _n_pp} pages (got {len(_rd.pages)})')
check('NO cover' in _o24, 'and the run log says so rather than implying a cover exists')

# 3. both available. render_pdf_bytes is stubbed out for the narrative tests above, so hand
#    back a real one-page PDF; the cover's CONTENT is asserted from its blocks further down.
_cov = io.BytesIO()
_cfig = plt.figure(figsize=(23, 15))
_cfig.savefig(_cov, format='pdf')
plt.close(_cfig)
G.update(_RL_OK=True, render_pdf_bytes=lambda *a, **k: io.BytesIO(_cov.getvalue()))
_o24 = _run24()
_rd = _PR(_d24)
check(len(_rd.pages) == 1 + _n_ent * _n_pp,
      f'with reportlab the cover is page 1: 1 + {_n_ent} x {_n_pp} = '
      f'{1 + _n_ent * _n_pp} pages (got {len(_rd.pages)})')


def _outline(items, depth=0):
    for _it in items:
        if isinstance(_it, list):
            yield from _outline(_it, depth + 1)
        else:
            yield depth, str(_it.title), _rd.get_destination_page_number(_it)


_ol = list(_outline(_rd.outline))
_tops = [t for d, t, _ in _ol if d == 0]
_kids = [t for d, t, _ in _ol if d == 1]
check(_tops[:1] == ['Cover'], f'the cover is the first bookmark (got {_tops[:2]})')
check(_tops[1:] == ['Company', 'VPs', 'Metros', 'Warehouses'],
      f'one group per level, in reading order (got {_tops[1:]})')
_want = []
for _lvl in ('Company', 'VP', 'Metro', 'Warehouse'):
    _want += sorted(str(n) for l, n in PAGES if l == _lvl)
check(_kids == _want,
      f'a bookmark per entity, company -> VPs -> metros -> warehouses (got {_kids})')
check(len(_kids) == _n_ent,
      f'every entity Cell 18 rendered is bookmarked ({len(_kids)} of {_n_ent})')
# a bookmark must land on the entity's FIRST page, not somewhere inside it
_pgs = [p for d, _t, p in _ol if d == 1]
check(_pgs == sorted(_pgs) and len(set(_pgs)) == len(_pgs),
      'each entity bookmark lands on its own page, in order')
check(all((_pgs[i + 1] - _pgs[i]) == _n_pp for i in range(len(_pgs) - 1)),
      f'and the entities are contiguous, {_n_pp} pages apart')

# The cover's content. This document deliberately omits the definitions behind its charts,
# so it has to say that, and say where they are.
_BLK.clear()
_c24 = G['build_dashboards_cover_blocks']()
_c24txt = ' '.join(str(b.get('v', '')) for b in _c24 if isinstance(b.get('v'), str))
_c24kv = [v for b in _c24 if b['t'] == 'kv' for v in b['v']]
check('DASHBOARD PAGES ONLY' in _c24txt, 'the cover says plainly that it is charts only')
check(G['REPORT_PUBLISH_PDF'] in _c24txt,
      'and names the full pack, so a reader who needs a definition knows where to look')
check('no metric dictionary' in _c24txt,
      'and states what it leaves out rather than letting a reader assume it is complete')
check(any('company' in str(v) and 'metro' in str(v) for _k, v in _c24kv),
      f'and counts the entities it covers '
      f'(got {[v for _k, v in _c24kv if "metro" in str(v)]})')
check(any('PROXIMITY, NOT FAULT' in str(b.get('v', '')) for b in _c24),
      'the attribution caveat travels with the charts, not only with the full report')
check(any('coaching conversation' in str(b.get('v', '')) for b in _c24),
      'and so does the coaching caveat, because every labour page names technicians')

# An entity on a level the ordering does not know about must still ship.
_extra = dict(PAGES)
_extra[('Region', 'R99 Somewhere')] = PAGES[('Company', 'DME Express — All Operations')]
_saved, G['dash_page_pdfs'] = PAGES, _extra
check(('Region', 'R99 Somewhere') in G['dashboard_entities'](),
      'an entity on an unrecognised level is still assembled rather than dropped silently')
G['dash_page_pdfs'] = _saved


print('\n' + '=' * 80)
print(f'{len(PASSES)} passed, {len(FAILS)} failed')
if FAILS:
    print('FAILURES:')
    for f in FAILS:
        print('  - ' + f)
    sys.exit(1)
print('ALL CHECKS PASSED')

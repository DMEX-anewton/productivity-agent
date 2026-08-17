"""Synthetic verification for ops_dashboard v1.7.0.

No database is reachable from here, so the changed cells are executed against synthetic
feeds shaped to carry every case the last three releases were broken by:

  * an entity that OPENS LATE                     (pre-span weeks must not zero-fill)
  * a week with TICKETS BUT NO CENSUS             (stale census feed at the tail)
  * a week with NEITHER tickets nor census        (the v1.6.1 bool-promotion crash)
  * UNEVEN CENSUS COVERAGE inside one window      (the v1.6.2 mixed-weights defect)
  * a SUPPRESSED week under the thin-denominator floor
  * technicians working TWO SITES                 (techs_equiv < techs_distinct)
  * PARTIAL weeks at both window edges

Cells executed: 4.3 (spine + add_trailing), 13.5 (census), 18 (both dashboard pages).

Run from the repository root:

    python analysis/lib/verify_ops_dashboard_v1_7_0.py

Exits non-zero on any failure. Needs no database connection, reads only the notebook, and
writes its rendered pages to a temp directory.
"""
import json, os, sys, io, re, math, tempfile
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

NB = 'analysis/ops_dashboard_2026-08-14_v1_7_0.ipynb'
OUT = os.path.join(tempfile.gettempdir(), 'ops_dashboard_verify')
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
# Namespace: the config the tested cells read, at the values Cell 3.1/3.5 set.
# ═══════════════════════════════════════════════════════════════════════════════
FILTER_START, FILTER_END, AS_OF_DATE = '2026-01-07', '2026-03-11', '2026-03-11'
G = dict(
    np=np, pd=pd, plt=plt, mdates=mdates, io=io, os=os, re=re, math=math,
    FILTER_START=FILTER_START, FILTER_END=FILTER_END, AS_OF_DATE=AS_OF_DATE,
    PROD_WEEK_START_DOW=6, PROD_WEEK_LABEL='Sun-Sat', OT_WEEK_START_DOW=3,
    OT_WEEK_LABEL='Thu-Wed', OT_WEEKLY_THRESHOLD=40.0,
    ROLL_WEEKS=4, DASH_ROLL_WEEKS=4, TRAILING_MIN_WEEKS=2, TRAILING_SUFFIX='_t4w',
    TRAILING_EXCLUDE_PARTIAL_WEEKS=True,
    CENSUS_MIN_ACTIVE_TECHS=1.0, CENSUS_MIN_TECHS=2, CENSUS_WARN_UNMAPPED_PCT=10.0,
    CENSUS_HEADLINE_METRIC='census_per_tech_headcount',
    VIRTUAL_WH_PREFIX='Z', VIRTUAL_RUG_THRESHOLD_PCT=5.0,
    ROUTING_CHANGE_DATE='2026-02-01', RUN_DATE='2026-08-17',
    DASH_TOP_N=5, DASH_MIN_ACTIVE_DAYS=30, DASH_PAGE_INCHES=(23, 15),
    LOST_IS_STALE=True, LOST_STALE_NOTE='lost feed ends 2026-02-28 — tail is missing data',
    LOST_BULK_EVENT_DATES=['2025-08-01'],
    OUT_DIR=OUT, DASH_PDF_NAME='verify_pages.pdf',
    PALETTE={'attributed': '#1f77b4'},
    save_fig=lambda fig, name: fig.savefig(os.path.join(OUT, f'{name}.png'), dpi=60),
)
TS = G['TRAILING_SUFFIX']

print('\n=== Cell 4.3 — spine & add_trailing =========================================')
exec(CELL[20], G)
week_start_of, add_trailing, WEEK_SPINE = G['week_start_of'], G['add_trailing'], G['WEEK_SPINE']
attach_spine = G['attach_spine']
WEEKS = list(WEEK_SPINE['week_start'])
check(len(WEEKS) == 10, f'spine has 10 weeks (got {len(WEEKS)})')
check(int(WEEK_SPINE['is_partial_week'].sum()) == 2,
      f'both window edges flagged partial (got {int(WEEK_SPINE["is_partial_week"].sum())})')

# ── sum_cols, the new primitive ───────────────────────────────────────────────
# One entity, present every week, indicator 1 on alternating weeks. The trailing sum over
# a 4-week window of [1,0,1,0,...] is 2 once the window is full; the mean is 0.5. Partial
# weeks are excluded from both, so the first and last windows are short.
_t = pd.DataFrame({'week_start': WEEKS,
                   'flag': [1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0]})
_r = add_trailing(_t, [], sum_cols=['flag'])
_full = _r.merge(WEEK_SPINE[['week_start', 'is_partial_week']], on='week_start')
_mid = _full[~_full['is_partial_week']].iloc[3:]      # windows entirely inside the window
check(bool((_mid['flag' + TS] == 2.0).all()),
      f'sum_cols: trailing sum of alternating 1/0 is 2.0 (got {list(_mid["flag" + TS])})')
_r2 = add_trailing(_t, [], rate_cols=['flag'])
check(abs(float(_r2[~_r2['week_start'].isin(
    WEEK_SPINE[WEEK_SPINE['is_partial_week']]['week_start'])]['flag' + TS].iloc[-1]) - 0.5) < 1e-9,
      'rate_cols on the same series still gives the MEAN (0.5), so sum_cols is additive')
raises(lambda: add_trailing(_t, [], count_cols=['flag'], sum_cols=['flag']),
       'sum_cols: a column asked for both a sum and a mean raises rather than colliding',
       ValueError)
# A pre-span week must not contribute a zero to a sum, exactly as for a mean.
_late = pd.DataFrame({'week_start': WEEKS[5:], 'flag': [1.0] * 5})
_rl = add_trailing(_late, [], sum_cols=['flag'])
check(bool(pd.to_numeric(_rl['flag' + TS], errors='coerce').max() <= 4.0),
      'sum_cols: an entity that opens late never sums more than the weeks it existed')
# The dtype-preservation contract still holds with a sum column present.
_tb = _t.assign(flagbool=True)
check(str(add_trailing(_tb, [], sum_cols=['flag'])['flagbool'].dtype) == 'bool',
      'sum_cols: add_trailing still alters no caller dtype (the v1.6.1 contract)')

# ═══════════════════════════════════════════════════════════════════════════════
# Synthetic upstream frames for Cell 13.5
# ═══════════════════════════════════════════════════════════════════════════════
# WH_A  two technicians, one of whom also works WH_B  -> techs_equiv < techs_distinct
# WH_B  opens in week 5                               -> pre-span weeks must stay missing
# WH_C  ONE technician                                -> under the suppression floor
# Census: WH_A observed 7 days most weeks but only 1 day in week 6 (uneven coverage, the
# v1.6.2 case); WH_A has NO census in the last two weeks (stale feed); WH_A has neither
# tickets nor census in week 4 (the v1.6.1 crash case).
_HIER = {'WH_A': ('VP North', 'TX', 'Houston'),
         'WH_B': ('VP North', 'TX', 'Houston'),
         'WH_C': ('VP South', 'LA', 'Other')}
_rows = []
for wi, ws in enumerate(WEEKS):
    for d in pd.date_range(ws, ws + pd.Timedelta(days=6)):
        if d.dayofweek >= 5 or not (pd.Timestamp(FILTER_START) <= d <= pd.Timestamp(AS_OF_DATE)):
            continue
        if wi != 4:                                   # week 4: WH_A silent entirely
            _rows.append(('Ann', 'Alpha', 'WH_A', d, 9))
            _rows.append(('Dee', 'Delta', 'WH_A', d, 8))
            _rows.append(('Bob', 'Beta', 'WH_A', d, 6))
        if wi >= 5:                                   # WH_B opens in week 5
            _rows.append(('Bob', 'Beta', 'WH_B', d, 3))   # Bob splits across two sites
            _rows.append(('Eve', 'Epsilon', 'WH_B', d, 5))
            _rows.append(('Fay', 'Phi', 'WH_B', d, 4))
        _rows.append(('Cal', 'Gamma', 'WH_C', d, 4))  # single-technician site: the floor
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
            continue                                  # WH_A: no census either (crash case)
        if wi == 6 and d.dayofweek != 0:
            continue                                  # WH_A: 1 of 7 days observed
        if wi < 8:
            _cen.append((d, 'WH_A', 900.0))           # stale after week 7
        if wi >= 5:
            _cen.append((d, 'WH_B', 300.0))
        _cen.append((d, 'WH_C', 120.0))
        _cen.append((d, 'Z CS', 40.0))                # virtual: company total only
_cd = pd.DataFrame(_cen, columns=['census_date', 'warehouse', 'pt_count'])
_cd['pt_count_all'] = _cd['pt_count'] * 1.1
_cd['_is_virtual_census'] = _cd['warehouse'].str.upper().str.startswith('Z')
_cd['week_start'] = week_start_of(_cd['census_date'])
_cd['period'] = _cd['census_date'].dt.strftime('%Y-%m')
G['df_census_daily'] = _cd

print('\n=== Cell 13.5 — census per technician =======================================')
exec(CELL[66], G)
CWH, CVP, CMET, CCO = (G['dash_wk_census_wh'], G['dash_wk_census_vp'],
                       G['dash_wk_census_metro'], G['dash_wk_census_co'])

check('census_per_active_tech_weekday' not in CWH.columns,
      'the v1.4.0 basis is absent from the weekly census frame')
check('restatement_vs_v140_pct' not in CWH.columns,
      'restatement_vs_v140_pct is absent from the weekly census frame')
check('census_per_active_tech_weekday' not in G['dash_mo_census_co'].columns,
      'the v1.4.0 basis is absent from the monthly bridge too')
check(all(c in CWH.columns for c in ('adc', 'avg_active_techs')),
      'both inputs of the retired ratio are still published (adc, avg_active_techs)')
check(all(c in CWH.columns for c in
          ('ratio_adc' + TS, 'ratio_techs_equiv' + TS, 'ratio_weeks_observed' + TS)),
      'the three published trailing inputs exist at warehouse grain')

# The point of the whole exercise: the printed inputs must divide into the printed figure.
# Cell 13.5's own Reconciliation 5 raised if not, so reaching here already proves it — but
# re-derive it independently rather than trusting the cell to test itself.
_bad = 0
for _fr in (CCO, CVP, CMET, CWH):
    _p = pd.to_numeric(_fr['census_per_tech_headcount' + TS], errors='coerce')
    _q = (pd.to_numeric(_fr['ratio_adc' + TS], errors='coerce')
          / pd.to_numeric(_fr['ratio_techs_equiv' + TS], errors='coerce'))
    _bad += int((_p.notna() & _q.notna() & ((_p - _q).abs() > 0.01 + 0.001 * _p.abs())).sum())
    _bad += int((_p.isna() & _q.notna()).sum())
check(_bad == 0, f'published ADC / published technicians == published ratio, all grains '
                 f'({_bad} mismatches)')
check(int(pd.to_numeric(CCO['census_per_tech_headcount' + TS], errors='coerce').notna().sum()) > 0,
      'the company trailing ratio is actually populated (the check above is not vacuous)')

# ratio_weeks_observed must be a real count of the pooled weeks, and STRICTLY tighter than
# t4w_weeks_observed somewhere — that difference is the whole reason the column exists.
_a = CWH[CWH['tech_warehouse'] == 'WH_A']
_rw = pd.to_numeric(_a['ratio_weeks_observed' + TS], errors='coerce')
_tw = pd.to_numeric(_a['t4w_weeks_observed'], errors='coerce')
check(bool((_rw.dropna() <= 4).all()) and bool((_rw.dropna() >= 0).all()),
      'ratio_weeks_observed_t4w stays within [0, ROLL_WEEKS]')
check(bool(((_rw < _tw) & _rw.notna()).any()),
      'ratio_weeks_observed_t4w is strictly below t4w_weeks_observed where census lagged '
      '(the claim v1.6.2 made but could not support)')

# Suppression: WH_C has one technician, so every week is under CENSUS_MIN_TECHS=2.
_c = CWH[CWH['tech_warehouse'] == 'WH_C']
check(bool(_c['ratio_suppressed'].all()),
      'the single-technician site is suppressed on every week')
check(bool(pd.to_numeric(_c['census_per_tech_headcount' + TS], errors='coerce').isna().all()),
      'a suppressed site publishes no trailing ratio')
check(bool(pd.to_numeric(_c['ratio_adc' + TS], errors='coerce').isna().all()),
      'a suppressed site publishes no trailing INPUTS either — no orphan numbers on a page')

# Apportionment: Bob splits WH_A/WH_B, so the apportioned headcount must sum to the company
# distinct count while the raw distinct count over-counts him.
_wk5 = WEEKS[6]
_s_eq = float(CWH[CWH['week_start'] == _wk5]['techs_equiv'].sum())
_s_di = float(CWH[CWH['week_start'] == _wk5]['techs_distinct'].sum())
_co_di = float(CCO[CCO['week_start'] == _wk5]['techs_distinct'].iloc[0])
check(abs(_s_eq - _co_di) < 0.01,
      f'apportioned headcount sums to the company distinct count ({_s_eq:.2f} vs {_co_di:.0f})')
check(_s_di > _co_di,
      f'the raw distinct count over-counts the cross-site technician ({_s_di:.0f} > {_co_di:.0f})')

# The v1.6.1 crash case and the bracket invariant both had to survive this data.
check(str(CWH['ratio_suppressed'].dtype) == 'bool',
      'ratio_suppressed survives as bool through the trailing pass (the v1.6.1 crash)')
print('  (Reconciliations 1-5 inside Cell 13.5 all passed — the cell raises otherwise.)')

# ═══════════════════════════════════════════════════════════════════════════════
# Synthetic dash frames for the other five families, then Cell 18.
# ═══════════════════════════════════════════════════════════════════════════════
_ENTS = [('tech_warehouse', ['WH_A', 'WH_B', 'WH_C']), ('vp', ['VP North', 'VP South']),
         ('metro', ['Houston', 'Other']), (None, [None])]


def _frame(gcol, vals, cols):
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
    return add_trailing(d, gc, count_cols=list(cols), rate_cols=list(cols))


_PROD = dict(total_tickets=500.0, total_active_tech_days=40.0,
             tickets_per_active_day_per_tech=12.5, virtual_ticket_share_pct=6.0,
             denominator_inflation_pct=8.0, rolling_4wk_avg=12.5)
_OT = dict(ot_hours=90.0, worked_hours=1600.0, ot_pct_of_worked=5.6, technicians=8.0)
_LOST = dict(lost_asset_count=6.0, lost_asset_cost=900.0, pt_days=6300.0,
             lost_cost_per_1k_pt_days=142.0)
_RED = dict(redelivery_count=12.0, total_tickets=520.0, redel_per_100_tickets=2.3)
_SO = dict(stockout_orders=30.0, total_tickets=520.0, stockouts_per_100_tickets=5.8)
for _fam, _cols in (('prod', _PROD), ('ot', _OT), ('lost', _LOST), ('redel', _RED),
                    ('stockout', _SO)):
    for _gc, _vals in _ENTS:
        _nm = {'tech_warehouse': 'wh', 'vp': 'vp', 'metro': 'metro', None: 'co'}[_gc]
        G[f'dash_wk_{_fam}_{_nm}'] = _frame(_gc, _vals, _cols)

_tb_cols = ['rank_group', 'techfirstname', 'techlastname', 'tech_warehouse', 'total_tickets',
            'active_weekdays', 'tickets_per_active_day', 'redel_per_100_tickets']
_tb = pd.DataFrame([['Top', 'Ann', 'Alpha', 'WH_A', 420, 45, 14.2, 1.9],
                    ['Top', 'Bob', 'Beta', 'WH_A', 380, 44, 12.8, 2.4],
                    ['Bottom', 'Cal', 'Gamma', 'WH_C', 210, 42, 7.1, 4.8]], columns=_tb_cols)
G['dash_tb_co'] = _tb
G['dash_tb_vp'] = _tb.assign(vp='VP North')
G['dash_tb_metro'] = _tb.assign(metro='Houston')
G['dash_tb_wh'] = _tb

print('\n=== Cell 18 — two dashboard pages per entity ================================')
exec(CELL[80], G)
PAGES = G['dash_page_pdfs']
check(len(PAGES) == 1 + 2 + 2 + 3,
      f'one entry per entity: company + 2 VP + 2 metro + 3 WH = 8 (got {len(PAGES)})')
check(all(len(v) == 2 for v in PAGES.values()),
      f'every entity produced exactly 2 pages '
      f'(counts: {sorted(set(len(v) for v in PAGES.values()))})')
check(all(isinstance(b, io.BytesIO) and b.getbuffer().nbytes > 0
          for v in PAGES.values() for b in v),
      'every captured page is a non-empty PDF buffer')

from pypdf import PdfReader, PdfWriter
_pdf = PdfReader(os.path.join(OUT, G['DASH_PDF_NAME']))
check(len(_pdf.pages) == 16, f'combined PDF has 8 entities x 2 pages = 16 (got '
                             f'{len(_pdf.pages)})')
_txt = (_pdf.pages[0].extract_text() or '') + (_pdf.pages[1].extract_text() or '')
for _need, _lbl in (
        ('Page 1 of 2', 'page 1 is labelled "Page 1 of 2"'),
        ('Page 2 of 2', 'page 2 is labelled "Page 2 of 2"'),
        ('Labour & Productivity', 'page 1 names the labour family'),
        ('Equipment, Redeliveries', 'page 2 names the equipment family'),
        ('Attendance Rate', 'the attendance rate has its own panel on page 1'),
        ('ADC', 'the census input readout reaches the page'),
        ('per tech', 'the readout labels its quotient column'),
        ('trailing 4wk', 'the readout gives the trailing window its own row'),
        ('raw distinct techs', 'the readout also shows the raw distinct body count')):
    check(_need in _txt, _lbl)
check('v1.4.0 basis' not in _txt and 'on the road' not in _txt,
      'no page mentions the retired v1.4.0 basis')

# The panel inventory: 6 axes per page, and page 1's table cell is one of them.
_p1 = _pdf.pages[0].extract_text() or ''
for _need in ('Technician Productivity', 'Census per Technician', 'Overtime Hours',
              'Top 5 / Bottom 5', 'Weekday Attendance Rate', 'Overtime as % of worked'):
    check(_need in _p1, f'page 1 carries panel: {_need}')
_p2 = _pdf.pages[1].extract_text() or ''
# NB: an em dash extracts from the PDF as whitespace, so key on the words around it.
for _need in ('Lost Equipment', 'events, by originating week', 'orders, by creation week',
              'Lost equipment $ per 1,000', 'Redeliveries per 100', 'Stock outs per 100'):
    check(_need in _p2, f'page 2 carries panel: {_need}')

# The Cell 18 page-count assertion must actually fire if a page goes missing.
_saved = dict(PAGES)
PAGES[('VP', 'VP North')] = PAGES[('VP', 'VP North')][:1]
_short = {k: len(v) for k, v in PAGES.items() if len(v) != 2}
check(len(_short) == 1, 'the short-page condition Cell 18 asserts on is detectable')
PAGES.update(_saved)

# ── Cell 23's assembly walks the list, so an entity contributes both pages ────
print('\n=== Cell 23 — consolidated assembly over list-valued pages ==================')
_w = PdfWriter()
_secs = []


def _add_pdf(buf, label=None):
    if buf is None:
        return 0
    st = len(_w.pages)
    for pg in PdfReader(buf).pages:
        _w.add_page(pg)
    if label:
        _secs.append((label, st))
    return len(PdfReader(buf).pages)


def _add_entity(key, label=None):
    bufs = PAGES.get(key) or []
    return sum(_add_pdf(b, label if i == 0 else None) for i, b in enumerate(bufs))


_n = _add_entity(('Company', 'DME Express — All Operations'), 'Company dashboard')
for _v in ['VP North', 'VP South']:
    _n += _add_entity(('VP', _v), f'VP: {_v}')
check(_n == 6, f'company + 2 VPs contribute 2 pages each = 6 (got {_n})')
check(len(_secs) == 3 and [s[1] for s in _secs] == [0, 2, 4],
      f'one bookmark per entity, on its FIRST page (got {[s[1] for s in _secs]})')

print('\n' + '=' * 78)
print(f'{len(PASSES)} passed, {len(FAILS)} failed')
if FAILS:
    for f in FAILS:
        print('  FAILED: ' + f)
    sys.exit(1)
print('All synthetic checks passed.')

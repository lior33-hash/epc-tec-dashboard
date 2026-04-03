#!/usr/bin/env python3
"""
Inject SMS data into enriched facilities and build the final HTML dashboard.
"""
import json, re
from datetime import date

# ─── SMS data from today (2026-03-31) — עדכון אוטומטי ────────────────────────
DAILY_CHECK = {
    'ד"א גן יבנה':            '06:17',
    'מט"ש צפע':               '07:20',
    'אשלג סדום 2':            '07:57',
    'אבנת':                   '08:00',
    'רותם תעשיות':            '08:00',
    'נטועה':                  '08:00',
    'אפרסמור':                '08:00',
    'קיבוץ בית הערבה':       '08:00',
    'בית אריזה ערבה':        '08:00',
    'צומת הלידו':             '08:00',
    'אשלים B':                '08:00',
    'סונול שדה עמודים':      '08:00',
    'חאן שער הגיא':          '08:00',
    'אלמוג 2':                '08:00',
    'פז סילבר':               '08:00',
    'שתיל נטו':               '08:00',
    'אורים':                  '08:00',
    'אלמוג 1':                '08:00',
    'חוף קליה':               '08:00',
    'גיתה':                   '08:00',
    'עבדת':                   '08:00',
    'ממשית':                  '08:00',
    'חניון בארות':            '08:01',
    'פז השקמה':               '08:01',
    'אקוסול':                 '08:01',
}

OPEN_ALERTS = {
    'מט"ש צפע': [
        {'content': 'תקלה במשאבת קולחים', 'time': '07:21'},
        {'content': 'מפלס גובה יתר במיכל איגום קולחים עילי', 'time': '07:22'},
    ],
    'אלמוג 2': [
        {'content': 'תקלה במערבל 2', 'time': '08:01'},
    ],
    'ניר יצחק': [
        {'content': 'התראת מתח רשת', 'time': '11:59'},
    ],
}

# רשימת התראות פתוחות מפורטת (לטאב הריכוז)
OPEN_ALERTS_SUMMARY = [
    {'facility': 'ניר יצחק',   'content': 'התראת מתח רשת',                                       'firstDate': '29.03.2026', 'lastTime': '11:59', 'daysOpen': 2},
    {'facility': 'מט"ש צפע',  'content': 'מפלס גובה יתר פסק במיכל איגום קולחים עילי',           'firstDate': '30.03.2026', 'lastTime': '18:02', 'daysOpen': 1},
    {'facility': 'מט"ש צפע',  'content': 'תקלה במשאבת קולחים',                                   'firstDate': '30.03.2026', 'lastTime': '07:21', 'daysOpen': 1},
    {'facility': 'אלמוג 2',    'content': 'תקלה במערבל 2',                                        'firstDate': '31.03.2026', 'lastTime': '08:01', 'daysOpen': 0},
]

ALL_MONITORED = {
    'שתיל נטו','מעלה עמוס - מתקן זמני','ממשית','גיתה','בית אריזה ערבה',
    'צומת הלידו','קיבוץ בית הערבה','פז השקמה','אשלג סדום 2','חוף קליה',
    'ד"א גן יבנה','חאן שער הגיא','עבדת','ניר יצחק','אשלג סדום 1','נטועה',
    'אורים','פז סילבר','סונול בית השקמה','חניון בארות','מט"ש צפע','אקוסול',
    'אשלים B','סונול שדה עמודים','עופרים','רותם תעשיות','אפרסמור','הר עמשא',
    'אבנת','אלמוג 2','אלמוג 1',
}
NO_CHECK = ALL_MONITORED - set(DAILY_CHECK.keys())

def match_sms(sms_name, dash_name):
    rules = {
        'שתיל נטו':          lambda n: 'שתיל' in n,
        'ד"א גן יבנה':       lambda n: 'גן יבנה' in n,
        'מט"ש צפע':          lambda n: 'צפע' in n,
        'אשלג סדום 2':       lambda n: 'סדום' in n,
        'צומת הלידו':        lambda n: 'הלידו' in n,
        'אורים':             lambda n: 'אורים' in n,
        'קיבוץ בית הערבה':  lambda n: 'הערבה' in n and 'אריזה' not in n,
        'סונול שדה עמודים': lambda n: 'עמודים' in n,
        'חאן שער הגיא':     lambda n: 'שער הגיא' in n or 'חאן' in n,
        'אפרסמור':           lambda n: 'אפרסמור' in n,
        'נטועה':             lambda n: 'נטועה' in n,
        'אשלים B':           lambda n: 'אשלים' in n,
        'רותם תעשיות':       lambda n: 'רותם' in n,
        'אבנת':              lambda n: 'אבנת' in n,
        'בית אריזה ערבה':   lambda n: 'אריזה' in n,
        'אקוסול':            lambda n: 'אקוסול' in n,
        'פז סילבר':          lambda n: 'סילבר' in n,
        'עבדת':              lambda n: 'עבדת' in n,
        'אלמוג 2':           lambda n: 'אלמוג' in n,
        'גיתה':              lambda n: 'גיתה' in n,
        'אלמוג 1':           lambda n: 'אלמוג' in n,
        'ממשית':             lambda n: 'ממשית' in n,
        'פז השקמה':          lambda n: 'השקמה' in n and 'פז' in n,
        'ניר יצחק':          lambda n: 'ניר יצחק' in n,
        'חניון בארות':       lambda n: 'בארות' in n or 'חניון' in n,
        'חוף קליה':          lambda n: 'קליה' in n,
        'מעלה עמוס - מתקן זמני': lambda n: 'מעלה עמוס' in n,
        'אשלג סדום 1':       lambda n: 'סדום' in n and '1' in n,
        'עופרים':            lambda n: 'עופרים' in n,
        'סונול בית השקמה':   lambda n: 'השקמה' in n and 'סונול' in n,
        'הר עמשא':           lambda n: 'עמשא' in n,
    }
    fn = rules.get(sms_name)
    return fn(dash_name) if fn else False

# ─── Load facilities ──────────────────────────────────────────────────────────
import os as _os
TMP = '/tmp/epc_work'
_DASH_DIR = _os.path.dirname(_os.path.abspath(__file__))
fac = json.load(open(f'{TMP}/all_facilities_enriched.json'))

# Inject SMS data
for facility in fac:
    name = facility['n']
    # Daily check
    for sms_name, time in DAILY_CHECK.items():
        if match_sms(sms_name, name):
            facility['dly'] = {'ok': True, 'time': time}
            break
    else:
        for sms_name in NO_CHECK:
            if match_sms(sms_name, name):
                facility['dly'] = {'ok': False, 'time': None}
                break

    # Open alerts
    for sms_name, alerts in OPEN_ALERTS.items():
        if match_sms(sms_name, name):
            facility['sms'] = alerts
            break

# Stats
dly_ok  = sum(1 for f in fac if f.get('dly', {}).get('ok') == True)
dly_no  = sum(1 for f in fac if f.get('dly', {}).get('ok') == False)
sms_fac = sum(1 for f in fac if 'sms' in f)
print(f"Daily ✓: {dly_ok} | Daily ✗: {dly_no} | SMS alerts: {sms_fac}")

# ─── Build HTML ───────────────────────────────────────────────────────────────
today = date.today().strftime('%d/%m/%Y')
fac_json = json.dumps(fac, ensure_ascii=False, separators=(',', ':'))

# Separate Bio-Disk and Bio-Robi for tabs
bd_fac = [f for f in fac if f['t'] == 'ביו-דיסק']
br_fac = [f for f in fac if f['t'] == 'ביו-רובי']

# Load gears/blades for extra tabs
gears_raw  = json.load(open(f'{TMP}/gears.json'))
blades_raw = json.load(open(f'{TMP}/blades.json'))
viols_raw  = json.load(open(f'{TMP}/violations.json'))

# ─── ז'אן קלוד בורדים נפרדים: להבים + ביוביות ───────────────────────────
import os as _osb
_dash_dir = _osb.path.dirname(_osb.path.abspath(__file__))
_blades_path = _osb.path.join(_dash_dir, 'blades_new.json')
_biobiot_path = _osb.path.join(_dash_dir, 'biobiot.json')
blades_new  = json.load(open(_blades_path))  if _osb.path.exists(_blades_path)  else []
biobiot_data = json.load(open(_biobiot_path)) if _osb.path.exists(_biobiot_path) else []
biobiot_with_data = [b for b in biobiot_data if b.get('last_d')]
print(f"להבים: {len(blades_new)} | ביוביות: {len(biobiot_data)} ({len(biobiot_with_data)} עם נתונים)")

# ─── ז'אן קלוד: Cross-board data ────────────────────────────────────────────
_OPEN_EXCL = {'טופל','לא נדרש','בוצע',''}

# 1. Open Monday issues (aggregated from all facilities)
jc_issues = []
for _f in fac:
    for _iss in _f.get('all_issues', []):
        if _iss.get('text') and _iss.get('status','') not in _OPEN_EXCL:
            jc_issues.append({'f':_f['n'],'t':_f['t'],'d':_iss.get('d',''),
                               'text':_iss.get('text','')[:115],'s':_iss.get('status',''),'tech':_iss.get('tech','')})
jc_issues.sort(key=lambda x: x['d'], reverse=True)
print(f"ז'אן קלוד issues: {len(jc_issues)}")

# 2. Meter readings — extract latest reading per facility from enriched JSON (fh = flow history)
jc_meters = []
for _f in fac:
    _fh = _f.get('fh', [])
    if _fh:
        _latest = max(_fh, key=lambda x: x.get('d', ''))
        _mv = _latest.get('v', 0)
        if _mv and float(_mv) > 0:
            jc_meters.append({'f': _f['n'], 't': _f['t'], 'd': _latest.get('d',''), 'm': str(_mv), 'mv': float(_mv), 'w': ''})
jc_meters.sort(key=lambda x: x['f'])
print(f"ז'אן קלוד meters: {len(jc_meters)}")

HTML = f'''<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EPC-TEC Dashboard — {today}</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#1e2f42;color:#d0e4f5;font-family:'Segoe UI',Arial,sans-serif;min-height:100vh;direction:rtl}}
/* ── Header ── */
.header{{background:linear-gradient(135deg,#1a3550 0%,#204878 100%);border-bottom:1px solid #2a5070;padding:14px 20px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:50;box-shadow:0 2px 10px rgba(0,0,0,.3)}}
.logo{{font-size:1.1rem;font-weight:700;color:#7dd4ff;letter-spacing:.5px}}
.header-date{{font-size:0.75rem;color:#7aacce}}
/* ── Tabs ── */
.tabs{{display:flex;gap:4px;padding:12px 16px 0;background:#1a2a3c;border-bottom:1px solid #2a4060;overflow-x:auto}}
.tab{{padding:8px 16px;border-radius:8px 8px 0 0;cursor:pointer;font-size:0.82rem;color:#6a9abb;border:1px solid transparent;border-bottom:none;white-space:nowrap;transition:.2s;background:#1e3350}}
.tab.active{{background:#253d58;color:#7dd4ff;border-color:#2a4f72;border-bottom-color:#253d58;font-weight:700;box-shadow:0 -2px 6px rgba(0,0,0,.2)}}
.tab:hover:not(.active){{color:#9ac8e8;background:#223048}}
/* ── Toolbar ── */
.toolbar{{padding:10px 16px;display:flex;align-items:center;gap:10px;flex-wrap:wrap;background:#1c2d40;border-bottom:1px solid #263d56}}
#search{{background:#253d58;border:1px solid #2e5070;color:#d0e4f5;padding:6px 12px;border-radius:8px;font-size:0.82rem;width:200px;direction:rtl}}
#search:focus{{outline:none;border-color:#4a9fd4;box-shadow:0 0 0 2px rgba(74,159,212,.2)}}
.stat-badge{{padding:3px 10px;border-radius:12px;font-size:0.75rem;font-weight:600;margin-right:4px}}
.sb-crit{{background:#4a1515;color:#ff8a80;border:1px solid #7a2020}}.sb-warn{{background:#3d2800;color:#ffc84a;border:1px solid #6a4800}}.sb-ok{{background:#0f3520;color:#66e09a;border:1px solid #1a6035}}
/* ── Grid ── */
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:12px;padding:14px 16px}}
/* ── Card ── */
.card{{background:#253d58;border:1px solid #2e5070;border-radius:12px;padding:12px;cursor:pointer;transition:.2s;position:relative;box-shadow:0 2px 6px rgba(0,0,0,.2)}}
.card:hover{{border-color:#4a9fd4;transform:translateY(-2px);box-shadow:0 6px 18px rgba(0,0,0,.3)}}
.card.critical{{border-right:4px solid #ff5252}}.card.warn{{border-right:4px solid #ffb74d}}.card.ok{{border-right:4px solid #4cde8a}}
.card-header{{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px}}
.card-name{{font-weight:700;font-size:0.9rem;color:#e8f4ff;flex:1}}
.type-badge{{font-size:0.62rem;background:#1e3350;color:#6aacce;padding:2px 6px;border-radius:8px;white-space:nowrap;margin-right:6px;border:1px solid #2e5070}}
.card-metrics{{display:flex;gap:8px;margin-bottom:8px}}
.metric{{flex:1;text-align:center;background:#1c3050;border-radius:8px;padding:6px 4px;border:1px solid #2a4565}}
.metric-label{{font-size:0.62rem;color:#5a8aaa;margin-bottom:3px}}
.metric-value{{font-size:0.92rem;font-weight:600;color:#c8e0f5}}
.do-ok{{color:#4cde8a}}.do-low{{color:#ffb74d}}.do-zero{{color:#ff5252}}
.card-tags{{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:8px}}
.tag{{font-size:0.68rem;padding:2px 7px;border-radius:10px;border:1px solid #2e5070}}
.tag-gear-ok{{background:#0f3020;color:#4cde8a;border-color:#1a5530}}
.tag-gear-bad{{background:#3a1010;color:#ff8a80;border-color:#6a2020}}
.tag-blade-ok{{background:#1a1a3a;color:#9090ff;border-color:#2e2e60}}
.tag-blade-bad{{background:#3a1c00;color:#ffaa55;border-color:#6a3a00}}
.tag-viol{{background:#2e2000;color:#ffd060;border-color:#5a4000}}
.tag-sms{{background:#3a0f0f;color:#ff8a80;border-color:#6a2020}}
.issues-preview{{font-size:0.72rem;color:#6a9abb;background:#1c3050;border-radius:6px;padding:5px 8px;margin-bottom:8px;border:1px solid #2a4565}}
.issues-preview div{{border-bottom:1px solid #253d58;padding:2px 0}}.issues-preview div:last-child{{border:none}}
.card-footer{{display:flex;justify-content:space-between;align-items:center;font-size:0.68rem;color:#4a7a9b;border-top:1px solid #1e3350;padding-top:6px;margin-top:4px}}
/* ── Daily status badges ── */
.dly-ok{{display:inline-flex;align-items:center;gap:4px;font-size:0.68rem;color:#4cde8a;background:#0f3020;border:1px solid #1a5530;border-radius:10px;padding:1px 7px}}
.dly-no{{display:inline-flex;align-items:center;gap:4px;font-size:0.68rem;color:#ffb74d;background:#3d2800;border:1px solid #6a4800;border-radius:10px;padding:1px 7px}}
/* ── Modal ── */
.overlay{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:100;align-items:center;justify-content:center;padding:16px}}
.overlay.open{{display:flex}}
.modal{{background:#1e3248;border:1px solid #2e5070;border-radius:16px;width:100%;max-width:1040px;max-height:94vh;overflow-y:auto;box-shadow:0 20px 50px rgba(0,0,0,.5)}}
.modal-header{{padding:16px 22px 11px;border-bottom:1px solid #2a4565;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;background:#1e3248;z-index:10;border-radius:16px 16px 0 0}}
.modal-title{{font-size:1.25rem;font-weight:700;color:#e8f4ff}}
.modal-close{{background:none;border:none;color:#5a8aaa;font-size:1.5rem;cursor:pointer;padding:4px 10px;border-radius:6px}}
.modal-close:hover{{color:#ff5252;background:#3a1010}}
.modal-body{{padding:16px 22px}}
/* modal sections */
.modal-section{{margin-bottom:16px}}
.section-title{{font-size:0.87rem;color:#7dd4ff;margin-bottom:8px;padding-bottom:5px;border-bottom:1px solid #2a4565;display:flex;align-items:center;gap:6px;font-weight:600}}
.metrics-row{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:14px}}
.metric-big{{background:#162840;border-radius:10px;padding:10px 14px;min-width:110px;text-align:center;border:1px solid #2a4565}}
.metric-big .label{{font-size:0.7rem;color:#5a8aaa;margin-bottom:4px}}
.metric-big .value{{font-size:1.05rem;font-weight:600;color:#d0e4f5}}
.charts-row{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px}}
.chart-box{{background:#162840;border-radius:10px;padding:10px;height:180px;border:1px solid #2a4565}}
.chart-title{{font-size:0.75rem;color:#5a8aaa;margin-bottom:6px;text-align:center}}
.badge{{padding:2px 8px;border-radius:10px;font-size:0.72rem;font-weight:600}}
.badge-green{{background:#0f3020;color:#4cde8a}}.badge-red{{background:#3a1010;color:#ff8a80}}
.badge-orange{{background:#3d2800;color:#ffb74d}}.badge-blue{{background:#0f2040;color:#7dd4ff}}
.badge-grey{{background:#1e3248;color:#6a9abb}}
.mini-table{{width:100%;border-collapse:collapse;font-size:0.78rem}}
.mini-table th{{background:#162840;color:#5a8aaa;padding:6px 8px;text-align:right;font-weight:600;border-bottom:2px solid #2a4565}}
.mini-table td{{padding:5px 8px;border-bottom:1px solid #1e3248;color:#aacce0}}
.mini-table tr:hover td{{background:#1c3050}}
.tag-routine{{color:#4cde8a}}.tag-urgent{{color:#ff8a80}}.tag-other{{color:#aacce0}}
.gear-row{{background:#162840;border-radius:8px;padding:8px 10px;margin-bottom:6px;display:flex;align-items:center;justify-content:space-between;font-size:0.8rem;border:1px solid #2a4565}}
.blade-row{{background:#162840;border-radius:8px;padding:8px 10px;margin-bottom:6px;font-size:0.8rem;border:1px solid #2a4565}}
.open-issue{{background:#162840;border-right:3px solid #4a9fd4;border-radius:6px;padding:8px 10px;margin-bottom:6px;font-size:0.8rem}}
.sms-alert{{background:#2a1010;border-right:3px solid #ff5252;border-radius:6px;padding:8px 10px;margin-bottom:6px;font-size:0.8rem;border:1px solid #5a1515}}
.sms-alert-content{{color:#ffaaaa;font-weight:500}}
.sms-alert-time{{font-size:0.68rem;color:#8a4040;margin-top:2px}}
.no-data{{color:#4a7a9b;text-align:center;padding:24px;font-size:0.85rem}}
.modal-source{{font-size:0.68rem;color:#3a6080;text-align:center;padding:6px;border-top:1px solid #2a4565;margin-top:4px}}
/* ── Alerts tab ── */
.alert-tab-badge{{display:inline-block;background:#8a1a1a;color:#ffaaaa;font-size:0.65rem;font-weight:700;border-radius:9px;padding:0px 6px;margin-right:4px;vertical-align:middle}}
.alerts-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px;padding:16px}}
.alert-card{{background:#253d58;border:1px solid #2e5070;border-radius:12px;padding:14px;border-right:4px solid #ff5252;transition:.2s;box-shadow:0 2px 6px rgba(0,0,0,.2)}}
.alert-card:hover{{border-color:#4a9fd4;transform:translateY(-2px);box-shadow:0 6px 18px rgba(0,0,0,.3)}}
.alert-card.days-2plus{{border-right-color:#ff5252}}
.alert-card.days-1{{border-right-color:#ffb74d}}
.alert-card.days-0{{border-right-color:#4cde8a}}
.alert-facility{{font-size:1rem;font-weight:700;color:#e8f4ff;margin-bottom:6px}}
.alert-content{{font-size:0.85rem;color:#ffaaaa;margin-bottom:10px;line-height:1.5}}
.alert-meta{{display:flex;justify-content:space-between;align-items:center;font-size:0.72rem;color:#5a8aaa;border-top:1px solid #2a4565;padding-top:8px;margin-top:4px}}
.alert-days-badge{{padding:3px 10px;border-radius:10px;font-size:0.72rem;font-weight:700}}
.badge-days-crit{{background:#3a1010;color:#ff8a80;border:1px solid #6a2020}}
.badge-days-warn{{background:#3d2800;color:#ffc84a;border:1px solid #6a4800}}
.badge-days-today{{background:#0f3020;color:#66e09a;border:1px solid #1a5530}}
.alerts-summary{{padding:10px 16px;font-size:0.82rem;color:#6a9abb;display:flex;gap:16px;align-items:center;background:#1c2d40;border-bottom:1px solid #263d56}}
.no-alerts{{text-align:center;padding:48px 24px;color:#4a7a9b;font-size:1rem}}
/* ── Table view (gears/blades tabs) ── */
#table-wrap{{padding:14px 16px;overflow-x:auto}}
#data-table{{width:100%;border-collapse:collapse;font-size:0.8rem}}
#data-table th{{background:#1e3248;color:#5a8aaa;padding:8px 10px;text-align:right;font-weight:600;position:sticky;top:0;border-bottom:2px solid #2a4565}}
#data-table td{{padding:7px 10px;border-bottom:1px solid #1e3248;color:#aacce0}}
#data-table tr:hover td{{background:#1c3050}}
/* ── ז'אן קלוד tabs ── */
.jc-view{{padding:14px 16px}}
.jc-header{{display:flex;gap:16px;align-items:center;padding:10px 16px;background:#1c2d40;border-bottom:1px solid #263d56;font-size:0.82rem;color:#6a9abb;flex-wrap:wrap}}
.jc-table{{width:100%;border-collapse:collapse;font-size:0.8rem}}
.jc-table th{{background:#1e3248;color:#5a8aaa;padding:8px 10px;text-align:right;font-weight:600;position:sticky;top:0;border-bottom:2px solid #2a4565}}
.jc-table td{{padding:7px 10px;border-bottom:1px solid #1e3248;color:#aacce0;vertical-align:top}}
.jc-table tr:hover td{{background:#1c3050}}
.status-pill{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:0.7rem;font-weight:600;white-space:nowrap}}
.sp-urgent{{background:#2e0808;color:#ff8a80;border:1px solid #5a1515}}
.sp-refer{{background:#2e1a00;color:#ffaa44;border:1px solid #5a3500}}
.sp-price{{background:#0a1e38;color:#5bc4ff;border:1px solid #1a3d6a}}
.sp-other{{background:#1e2f42;color:#7a9abb;border:1px solid #2a4565}}
.meter-ok{{color:#4cde8a;font-weight:600}}
.meter-bar{{display:inline-block;height:8px;background:linear-gradient(90deg,#2a6090,#4acde8);border-radius:4px;vertical-align:middle;margin-right:6px}}
</style>
</head>
<body>
<div class="header">
  <div class="logo">⚡ EPC-TEC Dashboard</div>
  <div class="header-date">עודכן: {today} | מאנדיי + SMS Live</div>
</div>
<div class="tabs">
  <div class="tab active" onclick="switchTab('facilities')">🏭 מתקנים</div>
  <div class="tab" onclick="switchTab('alerts')">🚨 התראות פתוחות{' <span class="alert-tab-badge">'+str(len(OPEN_ALERTS_SUMMARY))+'</span>' if OPEN_ALERTS_SUMMARY else ''}</div>
  <div class="tab" onclick="switchTab('monissues')">📋 נושאים לטיפול{' <span class="alert-tab-badge">'+str(len(jc_issues))+'</span>' if jc_issues else ''}</div>
  <div class="tab" onclick="switchTab('meters')">💧 מדי ספיקה{' <span class="alert-tab-badge">'+str(len(jc_meters))+'</span>' if jc_meters else ''}</div>
  <div class="tab" onclick="switchTab('gears')">⚙️ מגרזות/משמנות</div>
  <div class="tab" onclick="switchTab('blades')">🔧 להבי מדחס{' <span class="alert-tab-badge">'+str(sum(1 for b in blades_new if b.get("status") in ("צריך לבדוק","נבדק")))+'</span>' if blades_new else ''}</div>
  <div class="tab" onclick="switchTab('biobiot')">🚽 ביוביות{' <span class="alert-tab-badge">'+str(len(biobiot_with_data))+'</span>' if biobiot_with_data else ''}</div>
  <div class="tab" onclick="switchTab('viols')">🔬 חריגות דיגומים</div>
</div>
<div class="toolbar">
  <input id="search" type="text" placeholder="חיפוש מתקן..." oninput="renderTab()">
  <span id="stats"></span>
</div>

<!-- Facilities grid -->
<div id="fac-view">
  <div class="grid" id="grid"></div>
</div>

<!-- Alerts view -->
<div id="alerts-view" style="display:none">
  <div class="alerts-summary" id="alerts-summary"></div>
  <div class="alerts-grid" id="alerts-grid"></div>
</div>

<!-- ז'אן קלוד: Monday Issues view -->
<div id="monissues-view" style="display:none">
  <div class="jc-header" id="jc-issues-header"></div>
  <div class="jc-view"><table class="jc-table"><thead id="jc-issues-head"></thead><tbody id="jc-issues-body"></tbody></table></div>
</div>

<!-- ז'אן קלוד: Meters view -->
<div id="meters-view" style="display:none">
  <div class="jc-header" id="jc-meters-header"></div>
  <div class="jc-view"><table class="jc-table"><thead id="jc-meters-head"></thead><tbody id="jc-meters-body"></tbody></table></div>
</div>

<!-- ביוביות view -->
<div id="biobiot-view" style="display:none">
  <div style="padding:8px 12px;color:#aac8e0;font-size:0.82rem" id="biobiot-stats"></div>
  <div style="overflow-x:auto"><table class="jc-table"><thead id="biobiot-head"></thead><tbody id="biobiot-body"></tbody></table></div>
</div>

<!-- Table view for other tabs -->
<div id="table-wrap" style="display:none">
  <table id="data-table"><thead id="table-head"></thead><tbody id="table-body"></tbody></table>
</div>

<!-- Modal -->
<div class="overlay" id="overlay" onclick="e=>{{if(e.target===this)closeModal()}}">
  <div class="modal" onclick="event.stopPropagation()">
    <div class="modal-header">
      <div>
        <div class="modal-title" id="modal-title"></div>
        <div style="font-size:0.73rem;color:#4a7a9b;margin-top:2px" id="modal-subtitle"></div>
      </div>
      <button class="modal-close" onclick="closeModal()">✕</button>
    </div>
    <div class="modal-body">
      <div style="margin-bottom:8px;min-height:20px" id="modal-daily"></div>
      <div class="metrics-row" id="modal-metrics"></div>
      <div class="charts-row">
        <div class="chart-box"><div class="chart-title">DO — חמצן מומס (PPM)</div><canvas id="doChart"></canvas></div>
        <div class="chart-box"><div class="chart-title">ספיקה ממוצעת (מ"ק/יום)</div><canvas id="flChart"></canvas></div>
      </div>
      <!-- Tracking sections -->
      <div class="modal-section" id="gears-section" style="display:none">
        <div class="section-title">⚙️ מגרזות/משמנות</div>
        <div id="modal-gears"></div>
      </div>
      <div class="modal-section" id="blades-section" style="display:none">
        <div class="section-title">🔧 להבי מדחס</div>
        <div id="modal-blades"></div>
      </div>
      <!-- Violations -->
      <div class="modal-section" id="violations-section" style="display:none">
        <div class="section-title">🔬 חריגות דיגומים</div>
        <div id="modal-violations"></div>
      </div>
      <!-- Open issues -->
      <div class="modal-section" id="issues-section" style="display:none">
        <div class="section-title">🔧 נושאים לטיפול פתוחים <span id="issues-count" style="font-size:0.75rem;color:#4a7a9b;margin-right:6px"></span></div>
        <div id="modal-issues"></div>
      </div>
      <!-- SMS Alerts -->
      <div class="modal-section" id="sms-section" style="display:none">
        <div class="section-title">🚨 התראות SMS פתוחות <span id="sms-count" style="font-size:0.75rem;color:#4a7a9b;margin-right:6px"></span></div>
        <div id="modal-sms"></div>
      </div>
      <!-- Visit history -->
      <div class="modal-section">
        <div class="section-title">📅 היסטוריית ביקורים</div>
        <table class="mini-table"><thead><tr><th>תאריך</th><th>טכנאי</th><th>סוג</th></tr></thead><tbody id="modal-visits"></tbody></table>
      </div>
      <div class="modal-source">מקור: Monday.com + SMS4Free · {today}</div>
    </div>
  </div>
</div>

<script>
const FAC = {fac_json};
const OPEN_ALERTS = {json.dumps(OPEN_ALERTS_SUMMARY, ensure_ascii=False)};
const JC_ISSUES = {json.dumps(jc_issues, ensure_ascii=False)};
const JC_METERS = {json.dumps(jc_meters, ensure_ascii=False)};
const BLADES_DATA = {json.dumps(blades_new, ensure_ascii=False)};
const BIOBIOT_DATA = {json.dumps(biobiot_data, ensure_ascii=False)};

let doCI=null,flCI=null,curTab='facilities';

function doColor(v){{const n=parseFloat(v);if(!v||isNaN(n))return '';if(n===0)return 'do-zero';if(n<2)return 'do-low';return 'do-ok';}}
function isOverdue(d){{if(!d)return false;return new Date(d)<new Date();}}
function dateCls(d){{if(!d)return '';const diff=(new Date(d)-new Date())/864e5;if(diff<0)return 'style="color:#ff6b6b;font-weight:600"';if(diff<30)return 'style="color:#ffaa33"';return '';}}
function statusBadge(s){{const m={{'צריך להחליף':'badge-red','צריך לבדוק':'badge-orange','הוחלף':'badge-green','נבדק':'badge-blue','לא נדרש':'badge-grey','לא פעיל':'badge-grey','לא בשירות':'badge-grey'}};return`<span class="badge ${{m[s]||'badge-grey'}}">${{s||'—'}}</span>`;}}

function switchTab(tab){{
  curTab=tab;
  const ALL_TABS=['facilities','alerts','monissues','meters','gears','blades','biobiot','viols'];
  document.querySelectorAll('.tab').forEach((t,i)=>{{t.classList.toggle('active',ALL_TABS[i]===tab);}});
  document.getElementById('fac-view').style.display=tab==='facilities'?'':'none';
  document.getElementById('alerts-view').style.display=tab==='alerts'?'':'none';
  document.getElementById('monissues-view').style.display=tab==='monissues'?'':'none';
  document.getElementById('meters-view').style.display=tab==='meters'?'':'none';
  document.getElementById('biobiot-view').style.display=tab==='biobiot'?'':'none';
  document.getElementById('table-wrap').style.display=(tab!=='facilities'&&tab!=='alerts'&&tab!=='monissues'&&tab!=='meters'&&tab!=='biobiot')?'':'none';
  renderTab();
}}

function renderTab(){{
  const q=(document.getElementById('search').value||'').trim();
  if(curTab==='facilities') renderFacilities(q);
  else if(curTab==='alerts') renderAlerts(q);
  else if(curTab==='monissues') renderMonIssues(q);
  else if(curTab==='meters') renderMeters(q);
  else if(curTab==='gears') renderGears(q);
  else if(curTab==='blades') renderBlades(q);
  else if(curTab==='biobiot') renderBiobiot(q);
  else if(curTab==='viols') renderViols(q);
}}

function renderAlerts(q){{
  const filtered=OPEN_ALERTS.filter(a=>!q||a.facility.includes(q)||a.content.includes(q));
  const crit=filtered.filter(a=>a.daysOpen>=2).length;
  const warn=filtered.filter(a=>a.daysOpen===1).length;
  const today=filtered.filter(a=>a.daysOpen===0).length;
  document.getElementById('alerts-summary').innerHTML=
    `<span style="color:#aac8e0;font-weight:600">${{filtered.length}} התראות פתוחות</span>
     <span class="stat-badge sb-crit">🔴 ממושכות: ${{crit}}</span>
     <span class="stat-badge sb-warn">🟡 אתמול: ${{warn}}</span>
     <span class="stat-badge sb-ok">🟢 היום: ${{today}}</span>`;
  if(!filtered.length){{
    document.getElementById('alerts-grid').innerHTML='<div class="no-alerts" style="grid-column:1/-1">✅ אין התראות פתוחות כרגע</div>';
    return;
  }}
  document.getElementById('alerts-grid').innerHTML=filtered.map(a=>{{
    let cls,badge,label;
    if(a.daysOpen>=2){{cls='days-2plus';badge='badge-days-crit';label=`🔴 ${{a.daysOpen}} ימים`;}}
    else if(a.daysOpen===1){{cls='days-1';badge='badge-days-warn';label='🟡 אתמול';}}
    else{{cls='days-0';badge='badge-days-today';label='🟢 היום';}}
    return`<div class="alert-card ${{cls}}">
      <div class="alert-facility">📍 ${{a.facility}}</div>
      <div class="alert-content">⚠ ${{a.content}}</div>
      <div class="alert-meta">
        <span>פתוח מ: ${{a.firstDate}}</span>
        <span class="alert-days-badge ${{badge}}">${{label}}</span>
      </div>
    </div>`;
  }}).join('');
}}

function renderFacilities(q){{
  const filtered=FAC.filter(f=>!q||f.n.includes(q));
  const crit=filtered.filter(f=>f.st==='critical').length;
  const warn=filtered.filter(f=>f.st==='warn').length;
  const ok=filtered.filter(f=>f.st==='ok').length;
  document.getElementById('stats').innerHTML=`${{filtered.length}} מתקנים &nbsp;|&nbsp;<span class="stat-badge sb-crit">⚠️ ${{crit}}</span><span class="stat-badge sb-warn">⚡ ${{warn}}</span><span class="stat-badge sb-ok">✅ ${{ok}}</span>`;
  document.getElementById('grid').innerHTML=filtered.map(f=>{{
    const idx=FAC.indexOf(f);
    const doHtml=f.do?`<span class="${{doColor(f.do)}}">${{f.do}} PPM</span>`:'<span style="color:#3a6080">—</span>';
    const flowAvg=f.fh&&f.fh.length?(Math.round(f.fh.reduce((s,x)=>s+x.v,0)/f.fh.length*10)/10):null;
    const issHtml=f.oi&&f.oi.length?`<div class="issues-preview">${{f.oi.slice(0,2).map(x=>`<div>${{x.substring(0,52)}}</div>`).join('')}}</div>`:'';
    const tags=[];
    if(f.gears&&f.gears.length){{const g=f.gears[0];const bad=g.status==='צריך להחליף'||(g.next&&isOverdue(g.next));tags.push(`<span class="tag ${{bad?'tag-gear-bad':'tag-gear-ok'}}">⚙️ ${{bad?'מגרזות – החלפה':'מגרזות ✓'}}</span>`);}}
    if(f.blades&&f.blades.length){{const b=f.blades[0];const bad=b.status==='צריך לבדוק'||(b.next&&isOverdue(b.next));tags.push(`<span class="tag ${{bad?'tag-blade-bad':'tag-blade-ok'}}">🔧 ${{bad?'להבים – בדיקה':'להבים ✓'}}</span>`);}}
    if(f.violations&&f.violations.length)tags.push(`<span class="tag tag-viol">🔬 חריגת דיגום</span>`);
    if(f.sms&&f.sms.length)tags.push(`<span class="tag tag-sms">🚨 ${{f.sms.length}} התראות</span>`);
    const tagsHtml=tags.length?`<div class="card-tags">${{tags.join('')}}</div>`:'';
    const dlyHtml=f.dly?`<span class="${{f.dly.ok?'dly-ok':'dly-no'}}">${{f.dly.ok?'✓ תקינות '+f.dly.time:'⚠ ללא תקינות'}}</span>`:'';
    return `<div class="card ${{f.st}}" onclick="openModal(${{idx}})">
      <div class="card-header"><div class="card-name">${{f.n}}</div><span class="type-badge">${{f.t}}</span></div>
      <div class="card-metrics">
        <div class="metric"><div class="metric-label">DO</div><div class="metric-value">${{doHtml}}</div></div>
        <div class="metric"><div class="metric-label">ספיקה ממוצעת</div><div class="metric-value" style="color:#44bbee">${{flowAvg!==null?flowAvg+' מ"ק/י':'<span style="color:#3a6080">—</span>'}}</div></div>
      </div>${{issHtml}}${{tagsHtml}}
      <div class="card-footer"><span>ביקור: ${{f.lv||'—'}}</span>${{dlyHtml}}</div>
    </div>`;
  }}).join('');
}}

function renderGears(q){{
  const rows=FAC.filter(f=>f.gears&&f.gears.length).flatMap(f=>f.gears.map(g=>Object.assign({{fac:f.n}},g))).filter(r=>!q||r.fac.includes(q)||r.n.includes(q));
  document.getElementById('stats').innerHTML=`${{rows.length}} רשומות | מגרזות/משמנות`;
  document.getElementById('table-head').innerHTML=`<tr><th>מתקן</th><th>פריט</th><th>סטטוס</th><th>החלפה אחרונה</th><th>החלפה הבאה</th><th>כמות</th><th>חשבון</th></tr>`;
  document.getElementById('table-body').innerHTML=rows.map(r=>`<tr style="${{isOverdue(r.next)&&r.status!=='הוחלף'?'background:#1a0808':''}}">
    <td style="font-weight:600;color:#e8f4ff">${{r.fac}}</td><td style="color:#aac8e0">${{r.n}}</td>
    <td>${{statusBadge(r.status)}}</td><td style="font-size:0.8rem">${{r.last||'—'}}</td>
    <td ${{dateCls(r.next)}} style="font-size:0.8rem">${{r.next||'—'}}</td>
    <td style="font-size:0.8rem;color:#aac8e0">${{r.qty||'—'}}</td>
    <td><span class="badge ${{r.account==='ט.ל.'?'badge-blue':'badge-grey'}}">${{r.account||''}}</span></td>
  </tr>`).join('');
}}

function renderBlades(q){{
  const rows=BLADES_DATA.filter(r=>!q||r.n.includes(q)||r.g.includes(q));
  const needsCheck=rows.filter(r=>r.status==='צריך לבדוק'||r.status==='נבדק').length;
  document.getElementById('stats').innerHTML=`${{rows.length}} מדחסים | ${{needsCheck}} לבדיקה`;
  document.getElementById('table-head').innerHTML=`<tr><th>מתקן/מדחס</th><th>אזור</th><th>סטטוס</th><th>החלפה אחרונה</th><th>בדיקה הבאה</th><th>גובה להב</th><th>סוג</th></tr>`;
  document.getElementById('table-body').innerHTML=rows.map(r=>`<tr style="${{r.overdue&&r.status==='צריך לבדוק'?'background:#1a0808':''}}">
    <td style="font-weight:600;color:#e8f4ff">${{r.n}}</td>
    <td style="color:#8ab0d0;font-size:0.8rem">${{r.g}}</td>
    <td>${{statusBadge(r.status)}}</td>
    <td style="font-size:0.8rem">${{r.last_d||'—'}}</td>
    <td ${{dateCls(r.next_check)}} style="font-size:0.8rem">${{r.next_check||'—'}}</td>
    <td style="font-size:0.8rem;color:#aac8e0">${{r.height||'—'}} mm</td>
    <td style="font-size:0.8rem;color:#aac8e0">${{r.type||'—'}}</td>
  </tr>`).join('');
}}

function renderBiobiot(q){{
  const rows=BIOBIOT_DATA.filter(r=>!q||r.n.includes(q)||r.g.includes(q));
  const withData=rows.filter(r=>r.last_d).length;
  document.getElementById('biobiot-stats').innerHTML=`${{rows.length}} מתקנים | ${{withData}} עם נתוני שאיבה`;
  document.getElementById('biobiot-head').innerHTML=`<tr><th>מתקן</th><th>אזור</th><th>שאיבה אחרונה</th><th>סטטוס</th><th>ימים מאז</th><th>מס' שאיבות</th></tr>`;
  document.getElementById('biobiot-body').innerHTML=rows.map(r=>{{
    const daysAgo=r.days_ago;
    const daysStyle=daysAgo===null?'color:#555':daysAgo>365?'color:#ff6b6b;font-weight:600':daysAgo>180?'color:#ffa066':'color:#7ec8a0';
    const daysText=daysAgo===null?'—':`${{daysAgo}} ימים`;
    return `<tr>
      <td style="font-weight:600;color:#e8f4ff">${{r.n}}</td>
      <td style="color:#8ab0d0;font-size:0.8rem">${{r.g}}</td>
      <td style="font-size:0.8rem">${{r.last_d||'—'}}</td>
      <td>${{r.last_s?`<span class="status-pill" style="background:#2a5a2a;color:#7ec8a0;padding:2px 8px;border-radius:10px;font-size:0.75rem">${{r.last_s}}</span>`:'<span style="color:#444">—</span>'}}</td>
      <td style="font-size:0.9rem;${{daysStyle}}">${{daysText}}</td>
      <td style="text-align:center;color:#aac8e0">${{r.count||0}}</td>
    </tr>`;
  }}).join('');
}}

function renderViols(q){{
  const rows=FAC.filter(f=>f.violations&&f.violations.length).flatMap(f=>f.violations.map(v=>Object.assign({{fac:f.n}},v))).filter(r=>!q||r.fac.includes(q)||r.n.includes(q));
  document.getElementById('stats').innerHTML=`${{rows.length}} חריגות | דיגומים`;
  document.getElementById('table-head').innerHTML=`<tr><th>מתקן</th><th>פרמטרים</th><th>סטטוס</th></tr>`;
  document.getElementById('table-body').innerHTML=rows.map(r=>`<tr>
    <td style="font-weight:600;color:#e8f4ff">${{r.fac}}</td>
    <td style="color:#ff99cc;font-size:0.82rem">${{r.params||'—'}}</td>
    <td><span class="badge ${{r.status==='לא נשלח'?'badge-red':'badge-orange'}}">${{r.status||'—'}}</span></td>
  </tr>`).join('');
}}

function renderMonIssues(q){{
  const filtered=JC_ISSUES.filter(i=>!q||i.f.includes(q)||i.text.includes(q));
  const urgent=filtered.filter(i=>i.s==='דרוש טיפול').length;
  const referred=filtered.filter(i=>i.s==='הועבר לגורם מטפל').length;
  const price=filtered.filter(i=>i.s==='נשלחה הצעת מחיר').length;
  document.getElementById('stats').innerHTML=`${{filtered.length}} נושאים פתוחים &nbsp;|&nbsp;<span class="stat-badge sb-crit">🔴 דרוש טיפול: ${{urgent}}</span><span class="stat-badge sb-warn">🟡 הועבר: ${{referred}}</span><span class="stat-badge sb-ok">💰 הצעת מחיר: ${{price}}</span>`;
  document.getElementById('jc-issues-header').innerHTML=
    `<span style="color:#aac8e0;font-weight:600">📋 נושאים לטיפול — מאנדיי (ז'אן קלוד)</span>
     <span class="stat-badge sb-crit">🔴 ${{urgent}} דרוש טיפול</span>
     <span class="stat-badge sb-warn">🟡 ${{referred}} הועבר</span>
     <span class="stat-badge sb-ok">💰 ${{price}} הצעות מחיר</span>`;
  document.getElementById('jc-issues-head').innerHTML=`<tr><th>מתקן</th><th>סוג</th><th>נושא לטיפול</th><th>סטטוס</th><th>טכנאי</th><th>תאריך</th></tr>`;
  const statusCls={{'דרוש טיפול':'sp-urgent','הועבר לגורם מטפל':'sp-refer','נשלחה הצעת מחיר':'sp-price','אושר ע"י גורם מטפל':'sp-other'}};
  document.getElementById('jc-issues-body').innerHTML=filtered.length
    ? filtered.map(i=>`<tr>
        <td style="font-weight:600;color:#e8f4ff;white-space:nowrap">${{i.f}}</td>
        <td><span style="font-size:0.7rem;color:${{i.t==='ביו-דיסק'?'#7dd4ff':'#66e09a'}}">${{i.t}}</span></td>
        <td style="max-width:420px;line-height:1.45;color:#d0e4f5">${{i.text}}</td>
        <td><span class="status-pill ${{statusCls[i.s]||'sp-other'}}">${{i.s}}</span></td>
        <td style="color:#7a9abb;font-size:0.78rem">${{i.tech||'—'}}</td>
        <td style="color:#5a8aaa;font-size:0.78rem;white-space:nowrap">${{i.d||'—'}}</td>
      </tr>`).join('')
    : '<tr><td colspan="6" class="no-data">אין נושאים פתוחים</td></tr>';
}}

function renderMeters(q){{
  const filtered=JC_METERS.filter(m=>!q||m.f.includes(q));
  const maxMv=Math.max(...filtered.map(m=>m.mv),1);
  document.getElementById('stats').innerHTML=`${{filtered.length}} מתקנים | מדי ספיקה קולחים`;
  document.getElementById('jc-meters-header').innerHTML=
    `<span style="color:#aac8e0;font-weight:600">💧 מדי ספיקה קולחים (מ"ק מצטבר) — ז'אן קלוד</span>
     <span style="color:#5a8aaa">${{filtered.length}} מתקנים עם קריאות</span>`;
  document.getElementById('jc-meters-head').innerHTML=`<tr><th>מתקן</th><th>סוג</th><th>קריאה מצטברת (מ"ק)</th><th>גרף יחסי</th><th>טכנאי</th><th>תאריך קריאה</th></tr>`;
  const sorted=[...filtered].sort((a,b)=>b.mv-a.mv);
  document.getElementById('jc-meters-body').innerHTML=sorted.length
    ? sorted.map(m=>{{
        const pct=Math.round((m.mv/maxMv)*180);
        const mv=parseFloat(m.m.replace(',','')).toLocaleString('he-IL');
        return`<tr>
          <td style="font-weight:600;color:#e8f4ff;white-space:nowrap">${{m.f}}</td>
          <td><span style="font-size:0.7rem;color:${{m.t==='ביו-דיסק'?'#7dd4ff':'#66e09a'}}">${{m.t}}</span></td>
          <td class="meter-ok">${{mv}}</td>
          <td><span class="meter-bar" style="width:${{pct}}px"></span></td>
          <td style="color:#7a9abb;font-size:0.78rem">${{m.w||'—'}}</td>
          <td style="color:#5a8aaa;font-size:0.78rem;white-space:nowrap">${{m.d||'—'}}</td>
        </tr>`;
      }}).join('')
    : '<tr><td colspan="6" class="no-data">אין נתוני מד ספיקה</td></tr>';
}}

function openModal(idx){{
  const f=FAC[idx];
  document.getElementById('modal-title').textContent=f.n;
  document.getElementById('modal-subtitle').textContent=f.t+' | ביקור אחרון: '+(f.lv||'—')+' ('+(f.lt||'—')+')';

  // Daily status
  const dlyEl=document.getElementById('modal-daily');
  if(dlyEl){{
    if(f.dly){{
      dlyEl.innerHTML=f.dly.ok
        ?`<span class="dly-ok" style="font-size:0.8rem;padding:3px 10px">✓ תקינות יומית נשלחה ${{f.dly.time}}</span>`
        :`<span class="dly-no" style="font-size:0.8rem;padding:3px 10px">⚠ לא התקבלה תקינות יומית</span>`;
    }} else dlyEl.innerHTML='';
  }}

  // Metrics
  const flowAvg=f.fh&&f.fh.length?(Math.round(f.fh.reduce((s,x)=>s+x.v,0)/f.fh.length*10)/10):null;
  document.getElementById('modal-metrics').innerHTML=`
    <div class="metric-big"><div class="label">DO (PPM)</div><div class="value ${{doColor(f.do)}}">${{f.do||'—'}}</div></div>
    <div class="metric-big"><div class="label">ספיקה ממוצעת</div><div class="value" style="color:#44bbee">${{flowAvg!==null?flowAvg+' מ"ק/י':'—'}}</div></div>
    <div class="metric-big"><div class="label">נושאים לטיפול</div><div class="value" style="font-size:0.88rem;color:${{f.oi&&f.oi.length?'#ffaa33':'#44cc88'}}">${{f.is||'לא נדרש'}}</div></div>
    <div class="metric-big"><div class="label">שאיבה</div><div class="value" style="font-size:0.82rem;color:#aac8e0">${{f.ps||'—'}}</div></div>`;

  // DO chart
  if(doCI){{doCI.destroy();doCI=null;}}
  if(f.dh&&f.dh.length){{
    doCI=new Chart(document.getElementById('doChart'),{{type:'line',data:{{labels:f.dh.map(d=>d.d),datasets:[{{data:f.dh.map(d=>d.v),borderColor:'#4cde8a',backgroundColor:'rgba(76,222,138,.12)',tension:.3,pointRadius:3,fill:true}}]}},options:{{plugins:{{legend:{{display:false}}}},scales:{{x:{{ticks:{{color:'#5a8aaa',font:{{size:9}}}},grid:{{color:'#1e3248'}}}},y:{{ticks:{{color:'#5a8aaa'}},grid:{{color:'#2a4565'}}}}}},animation:{{duration:400}}}}}});
  }} else document.getElementById('doChart').getContext('2d').clearRect(0,0,999,999);

  // Flow chart
  if(flCI){{flCI.destroy();flCI=null;}}
  if(f.fh&&f.fh.length){{
    flCI=new Chart(document.getElementById('flChart'),{{type:'bar',data:{{labels:f.fh.map(d=>d.d),datasets:[{{data:f.fh.map(d=>d.v),backgroundColor:'rgba(125,212,255,.25)',borderColor:'#7dd4ff',borderWidth:1}}]}},options:{{plugins:{{legend:{{display:false}}}},scales:{{x:{{ticks:{{color:'#5a8aaa',font:{{size:9}}}},grid:{{color:'#1e3248'}}}},y:{{ticks:{{color:'#5a8aaa'}},grid:{{color:'#2a4565'}}}}}},animation:{{duration:400}}}}}});
  }}

  // Gears
  const gearsSec=document.getElementById('gears-section');
  if(f.gears&&f.gears.length){{
    gearsSec.style.display='block';
    document.getElementById('modal-gears').innerHTML=f.gears.map(g=>`
      <div class="gear-row">
        <span style="color:#aac8e0">${{g.n}}</span>
        <div style="display:flex;align-items:center;gap:8px">
          ${{statusBadge(g.status)}}
          <span style="font-size:0.72rem;color:#4a7a9b">החלפה הבאה: ${{g.next||'—'}}</span>
          <span style="font-size:0.72rem;color:#3a6080">${{g.qty||''}}</span>
        </div>
      </div>`).join('');
  }} else gearsSec.style.display='none';

  // Blades
  const bladesSec=document.getElementById('blades-section');
  if(f.blades&&f.blades.length){{
    bladesSec.style.display='block';
    document.getElementById('modal-blades').innerHTML=f.blades.map(b=>`
      <div class="blade-row" style="display:flex;align-items:center;justify-content:space-between">
        <span style="color:#aac8e0;font-size:0.78rem">${{b.n}}</span>
        <div style="display:flex;gap:8px;align-items:center">
          ${{statusBadge(b.status)}}
          <span style="font-size:0.72rem;color:#4a7a9b">בדיקה הבאה: ${{b.next||'—'}}</span>
          <span style="font-size:0.72rem;color:#3a6080">גובה: ${{b.height||'—'}}</span>
        </div>
      </div>`).join('');
  }} else bladesSec.style.display='none';

  // Violations
  const violSec=document.getElementById('violations-section');
  if(f.violations&&f.violations.length){{
    violSec.style.display='block';
    document.getElementById('modal-violations').innerHTML=f.violations.map(v=>`
      <div style="background:#081420;border-radius:8px;padding:8px 10px;margin-bottom:6px;font-size:0.82rem">
        <span style="font-size:0.85rem;color:#ff99cc;font-weight:600">${{v.params}}</span>
        <span style="float:left"><span class="badge ${{v.status==='לא נשלח'?'badge-red':'badge-orange'}}">${{v.status}}</span></span>
      </div>`).join('');
  }} else violSec.style.display='none';

  // Open issues
  const issSec=document.getElementById('issues-section');
  const issData=(f.all_issues&&f.all_issues.length)?f.all_issues:(f.oi&&f.oi.length?f.oi.map(i=>{{return{{text:i,d:'',status:'',tech:''}}}}):[]);
  if(issData.length){{
    issSec.style.display='block';
    document.getElementById('issues-count').textContent='('+issData.length+')';
    const statusColors={{'דרוש טיפול':'#ff6b6b','הועבר לגורם מטפל':'#ffaa33','נשלחה הצעת מחיר':'#5bc4ff','אושר ע"י גורם מטפל':'#44cc88','':'#aac8e0'}};
    document.getElementById('modal-issues').innerHTML=issData.map(i=>{{
      const sc=statusColors[i.status]||'#aac8e0';
      return `<div class="open-issue" style="border-right-color:${{sc}}">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px">
          <span>🔧 ${{i.text||i}}</span>
          ${{i.status?`<span style="font-size:0.72rem;color:${{sc}};white-space:nowrap;padding-top:1px">${{i.status}}</span>`:''}}
        </div>
        ${{i.d?`<div style="font-size:0.7rem;color:#4a7a9b;margin-top:2px">${{i.d}} · ${{i.tech||''}}</div>`:''}}
      </div>`;
    }}).join('');
  }} else issSec.style.display='none';

  // SMS alerts
  const smsSec=document.getElementById('sms-section');
  if(f.sms&&f.sms.length){{
    smsSec.style.display='block';
    document.getElementById('sms-count').textContent='('+f.sms.length+')';
    document.getElementById('modal-sms').innerHTML=f.sms.map(a=>`
      <div class="sms-alert">
        <div class="sms-alert-content">⚠ ${{a.content}}</div>
        <div class="sms-alert-time">🕐 ${{a.time}}</div>
      </div>`).join('');
  }} else smsSec.style.display='none';

  // Visits
  const tbody=document.getElementById('modal-visits');
  if(f.vh&&f.vh.length){{
    tbody.innerHTML=f.vh.map(v=>{{const cls=v.type==='שיגרתי'?'tag-routine':v.type==='חירום'?'tag-urgent':'tag-other';return`<tr><td>${{v.d}}</td><td>${{v.tech}}</td><td class="${{cls}}">${{v.type||'—'}}</td></tr>`;}}).join('');
  }} else tbody.innerHTML='<tr><td colspan="3" style="color:#3a6080;text-align:center">אין היסטוריה</td></tr>';

  document.getElementById('overlay').classList.add('open');
}}

function closeModal(){{
  document.getElementById('overlay').classList.remove('open');
  if(doCI){{doCI.destroy();doCI=null;}} if(flCI){{flCI.destroy();flCI=null;}}
}}
document.getElementById('overlay').addEventListener('click',function(e){{if(e.target===this)closeModal();}});
document.addEventListener('keydown',e=>{{if(e.key==='Escape')closeModal();}});
renderTab();
</script>
</body>
</html>'''

# Write
out = _os.path.join(_DASH_DIR, 'epc-tec-live.html')
with open(out, 'w', encoding='utf-8') as f:
    f.write(HTML)

size = len(HTML)
print(f"✅ Dashboard written: {size:,} bytes ({size//1024}KB)")
print(f"   {len(fac)} facilities | {today}")

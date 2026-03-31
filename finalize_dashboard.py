#!/usr/bin/env python3
"""
Inject SMS data into enriched facilities and build the final HTML dashboard.
"""
import json, re
from datetime import date

# ─── SMS data from today (2026-03-29) — סשן sms4free פג, נתוני SMS לא זמינים ────
DAILY_CHECK = {}

OPEN_ALERTS = {}

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
TMP = '/tmp'
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

HTML = f'''<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EPC-TEC Dashboard — {today}</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#07111c;color:#c8dff0;font-family:'Segoe UI',Arial,sans-serif;min-height:100vh;direction:rtl}}
/* ── Header ── */
.header{{background:linear-gradient(135deg,#0d1c2a 0%,#112233 100%);border-bottom:1px solid #1a3347;padding:14px 20px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:50}}
.logo{{font-size:1.1rem;font-weight:700;color:#5bc4ff;letter-spacing:.5px}}
.header-date{{font-size:0.75rem;color:#4a7a9b}}
/* ── Tabs ── */
.tabs{{display:flex;gap:4px;padding:12px 16px 0;background:#07111c;border-bottom:1px solid #1a3347;overflow-x:auto}}
.tab{{padding:8px 16px;border-radius:8px 8px 0 0;cursor:pointer;font-size:0.82rem;color:#4a7a9b;border:1px solid transparent;border-bottom:none;white-space:nowrap;transition:.2s}}
.tab.active{{background:#0d1c2a;color:#5bc4ff;border-color:#1a3347;font-weight:600}}
.tab:hover:not(.active){{color:#7ab8d8;background:#0a1820}}
/* ── Toolbar ── */
.toolbar{{padding:10px 16px;display:flex;align-items:center;gap:10px;flex-wrap:wrap;background:#07111c}}
#search{{background:#0d1c2a;border:1px solid #1a3347;color:#c8dff0;padding:6px 12px;border-radius:8px;font-size:0.82rem;width:200px;direction:rtl}}
.stat-badge{{padding:3px 10px;border-radius:12px;font-size:0.75rem;font-weight:600;margin-right:4px}}
.sb-crit{{background:#3d1010;color:#ff6b6b}}.sb-warn{{background:#2a1800;color:#ffaa33}}.sb-ok{{background:#0a2a1a;color:#44cc88}}
/* ── Grid ── */
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:12px;padding:14px 16px}}
/* ── Card ── */
.card{{background:#0d1c2a;border:1px solid #1a3347;border-radius:12px;padding:12px;cursor:pointer;transition:.2s;position:relative}}
.card:hover{{border-color:#2a5a7a;transform:translateY(-1px);box-shadow:0 4px 12px rgba(0,0,0,.4)}}
.card.critical{{border-right:3px solid #ff4444}}.card.warn{{border-right:3px solid #ffaa33}}.card.ok{{border-right:3px solid #44cc88}}
.card-header{{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px}}
.card-name{{font-weight:700;font-size:0.9rem;color:#e8f4ff;flex:1}}
.type-badge{{font-size:0.62rem;background:#1a3347;color:#4a8aaa;padding:2px 6px;border-radius:8px;white-space:nowrap;margin-right:6px}}
.card-metrics{{display:flex;gap:8px;margin-bottom:8px}}
.metric{{flex:1;text-align:center;background:#0a1820;border-radius:8px;padding:6px 4px}}
.metric-label{{font-size:0.62rem;color:#3a6080;margin-bottom:3px}}
.metric-value{{font-size:0.92rem;font-weight:600;color:#c8dff0}}
.do-ok{{color:#44cc88}}.do-low{{color:#ffaa33}}.do-zero{{color:#ff6b6b}}
.card-tags{{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:8px}}
.tag{{font-size:0.68rem;padding:2px 7px;border-radius:10px;border:1px solid #1a3347}}
.tag-gear-ok{{background:#1a2a1a;color:#44cc88;border-color:#1a4a2a}}
.tag-gear-bad{{background:#2a1010;color:#ff8888;border-color:#4a1a1a}}
.tag-blade-ok{{background:#1a1a2a;color:#8888ff;border-color:#2a2a4a}}
.tag-blade-bad{{background:#2a1510;color:#ff9944;border-color:#4a2a1a}}
.tag-viol{{background:#2a1a0a;color:#ffcc44;border-color:#4a3a1a}}
.tag-sms{{background:#3a0a0a;color:#ff7070;border-color:#7a2020}}
.issues-preview{{font-size:0.72rem;color:#4a7a9b;background:#081420;border-radius:6px;padding:5px 8px;margin-bottom:8px}}
.issues-preview div{{border-bottom:1px solid #0d1c2a;padding:2px 0}}.issues-preview div:last-child{{border:none}}
.card-footer{{display:flex;justify-content:space-between;align-items:center;font-size:0.68rem;color:#2a5a7a;border-top:1px solid #0a1820;padding-top:6px;margin-top:4px}}
/* ── Daily status badges ── */
.dly-ok{{display:inline-flex;align-items:center;gap:4px;font-size:0.68rem;color:#44cc88;background:#0a2a1a;border:1px solid #1a5a35;border-radius:10px;padding:1px 7px}}
.dly-no{{display:inline-flex;align-items:center;gap:4px;font-size:0.68rem;color:#ff9944;background:#2a1500;border:1px solid #7a3a00;border-radius:10px;padding:1px 7px}}
/* ── Modal ── */
.overlay{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:100;align-items:center;justify-content:center;padding:16px}}
.overlay.open{{display:flex}}
.modal{{background:#0d1c2a;border:1px solid #2a4a62;border-radius:16px;width:100%;max-width:1040px;max-height:94vh;overflow-y:auto}}
.modal-header{{padding:16px 22px 11px;border-bottom:1px solid #1a3347;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;background:#0d1c2a;z-index:10;border-radius:16px 16px 0 0}}
.modal-title{{font-size:1.25rem;font-weight:700;color:#e8f4ff}}
.modal-close{{background:none;border:none;color:#4a7a9b;font-size:1.5rem;cursor:pointer;padding:4px 10px;border-radius:6px}}
.modal-close:hover{{color:#ff6b6b}}
.modal-body{{padding:16px 22px}}
/* modal sections */
.modal-section{{margin-bottom:16px}}
.section-title{{font-size:0.87rem;color:#5bc4ff;margin-bottom:8px;padding-bottom:5px;border-bottom:1px solid #1a3347;display:flex;align-items:center;gap:6px}}
.metrics-row{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:14px}}
.metric-big{{background:#081420;border-radius:10px;padding:10px 14px;min-width:110px;text-align:center}}
.metric-big .label{{font-size:0.7rem;color:#3a6080;margin-bottom:4px}}
.metric-big .value{{font-size:1.05rem;font-weight:600;color:#c8dff0}}
.charts-row{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px}}
.chart-box{{background:#081420;border-radius:10px;padding:10px;height:180px}}
.chart-title{{font-size:0.75rem;color:#4a7a9b;margin-bottom:6px;text-align:center}}
.badge{{padding:2px 8px;border-radius:10px;font-size:0.72rem;font-weight:600}}
.badge-green{{background:#0a2a1a;color:#44cc88}}.badge-red{{background:#3d1010;color:#ff6b6b}}
.badge-orange{{background:#3d2a00;color:#ffaa33}}.badge-blue{{background:#0a1a3d;color:#5bc4ff}}
.badge-grey{{background:#1a2a3a;color:#6a9ab0}}
.mini-table{{width:100%;border-collapse:collapse;font-size:0.78rem}}
.mini-table th{{background:#081420;color:#4a7a9b;padding:5px 8px;text-align:right;font-weight:600}}
.mini-table td{{padding:5px 8px;border-bottom:1px solid #0d1c2a;color:#aac8e0}}
.mini-table tr:hover td{{background:#0a1820}}
.tag-routine{{color:#44cc88}}.tag-urgent{{color:#ff6b6b}}.tag-other{{color:#aac8e0}}
.gear-row{{background:#081420;border-radius:8px;padding:8px 10px;margin-bottom:6px;display:flex;align-items:center;justify-content:space-between;font-size:0.8rem}}
.blade-row{{background:#081420;border-radius:8px;padding:8px 10px;margin-bottom:6px;font-size:0.8rem}}
.open-issue{{background:#081420;border-right:3px solid #3a6080;border-radius:6px;padding:8px 10px;margin-bottom:6px;font-size:0.8rem}}
.sms-alert{{background:#1a0a0a;border-right:3px solid #ff4444;border-radius:6px;padding:8px 10px;margin-bottom:6px;font-size:0.8rem}}
.sms-alert-content{{color:#ffcccc;font-weight:500}}
.sms-alert-time{{font-size:0.68rem;color:#7a3030;margin-top:2px}}
.no-data{{color:#2a5a7a;text-align:center;padding:24px;font-size:0.85rem}}
.modal-source{{font-size:0.68rem;color:#2a5a7a;text-align:center;padding:6px;border-top:1px solid #1a3347;margin-top:4px}}
/* ── Table view (gears/blades tabs) ── */
#table-wrap{{padding:14px 16px;overflow-x:auto}}
#data-table{{width:100%;border-collapse:collapse;font-size:0.8rem}}
#data-table th{{background:#0d1c2a;color:#4a7a9b;padding:8px 10px;text-align:right;font-weight:600;position:sticky;top:0}}
#data-table td{{padding:7px 10px;border-bottom:1px solid #0d1c2a;color:#aac8e0}}
#data-table tr:hover td{{background:#0a1820}}
</style>
</head>
<body>
<div class="header">
  <div class="logo">⚡ EPC-TEC Dashboard</div>
  <div class="header-date">עודכן: {today} | מאנדיי + SMS Live</div>
</div>
<div class="tabs">
  <div class="tab active" onclick="switchTab('facilities')">🏭 מתקנים</div>
  <div class="tab" onclick="switchTab('gears')">⚙️ מגרזות/משמנות</div>
  <div class="tab" onclick="switchTab('blades')">🔧 להבי מדחס</div>
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

let doCI=null,flCI=null,curTab='facilities';

function doColor(v){{const n=parseFloat(v);if(!v||isNaN(n))return '';if(n===0)return 'do-zero';if(n<2)return 'do-low';return 'do-ok';}}
function isOverdue(d){{if(!d)return false;return new Date(d)<new Date();}}
function dateCls(d){{if(!d)return '';const diff=(new Date(d)-new Date())/864e5;if(diff<0)return 'style="color:#ff6b6b;font-weight:600"';if(diff<30)return 'style="color:#ffaa33"';return '';}}
function statusBadge(s){{const m={{'צריך להחליף':'badge-red','צריך לבדוק':'badge-orange','הוחלף':'badge-green','נבדק':'badge-blue','לא נדרש':'badge-grey','לא פעיל':'badge-grey','לא בשירות':'badge-grey'}};return`<span class="badge ${{m[s]||'badge-grey'}}">${{s||'—'}}</span>`;}}

function switchTab(tab){{
  curTab=tab;
  document.querySelectorAll('.tab').forEach((t,i)=>{{t.classList.toggle('active',['facilities','gears','blades','viols'][i]===tab);}});
  document.getElementById('fac-view').style.display=tab==='facilities'?'':'none';
  document.getElementById('table-wrap').style.display=tab!=='facilities'?'':'none';
  renderTab();
}}

function renderTab(){{
  const q=(document.getElementById('search').value||'').trim();
  if(curTab==='facilities') renderFacilities(q);
  else if(curTab==='gears') renderGears(q);
  else if(curTab==='blades') renderBlades(q);
  else if(curTab==='viols') renderViols(q);
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
  const rows=FAC.filter(f=>f.blades&&f.blades.length).flatMap(f=>f.blades.map(b=>Object.assign({{fac:f.n}},b))).filter(r=>!q||r.fac.includes(q)||r.n.includes(q));
  document.getElementById('stats').innerHTML=`${{rows.length}} מדחסים | להבים`;
  document.getElementById('table-head').innerHTML=`<tr><th>מתקן</th><th>מדחס</th><th>סטטוס</th><th>בדיקה אחרונה</th><th>בדיקה הבאה</th><th>גובה</th><th>חשבון</th></tr>`;
  document.getElementById('table-body').innerHTML=rows.map(r=>`<tr style="${{isOverdue(r.next)&&r.status==='צריך לבדוק'?'background:#1a0808':''}}">
    <td style="font-weight:600;color:#e8f4ff">${{r.fac}}</td><td style="color:#aac8e0;font-size:0.8rem">${{r.n}}</td>
    <td>${{statusBadge(r.status)}}</td><td style="font-size:0.8rem">${{r.last||'—'}}</td>
    <td ${{dateCls(r.next)}} style="font-size:0.8rem">${{r.next||'—'}}</td>
    <td style="font-size:0.8rem;color:#aac8e0">${{r.height||'—'}}</td>
    <td><span class="badge badge-blue">${{r.account||'ט.ל.'}}</span></td>
  </tr>`).join('');
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
    doCI=new Chart(document.getElementById('doChart'),{{type:'line',data:{{labels:f.dh.map(d=>d.d),datasets:[{{data:f.dh.map(d=>d.v),borderColor:'#44cc88',backgroundColor:'rgba(68,204,136,.1)',tension:.3,pointRadius:3,fill:true}}]}},options:{{plugins:{{legend:{{display:false}}}},scales:{{x:{{ticks:{{color:'#4a7a9b',font:{{size:9}}}},grid:{{color:'#0d1c2a'}}}},y:{{ticks:{{color:'#4a7a9b'}},grid:{{color:'#1a3347'}}}}}},animation:{{duration:400}}}}}});
  }} else document.getElementById('doChart').getContext('2d').clearRect(0,0,999,999);

  // Flow chart
  if(flCI){{flCI.destroy();flCI=null;}}
  if(f.fh&&f.fh.length){{
    flCI=new Chart(document.getElementById('flChart'),{{type:'bar',data:{{labels:f.fh.map(d=>d.d),datasets:[{{data:f.fh.map(d=>d.v),backgroundColor:'rgba(91,196,255,.5)',borderColor:'#5bc4ff',borderWidth:1}}]}},options:{{plugins:{{legend:{{display:false}}}},scales:{{x:{{ticks:{{color:'#4a7a9b',font:{{size:9}}}},grid:{{color:'#0d1c2a'}}}},y:{{ticks:{{color:'#4a7a9b'}},grid:{{color:'#1a3347'}}}}}},animation:{{duration:400}}}}}});
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

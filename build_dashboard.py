#!/usr/bin/env python3
"""
Build the full EPC-TEC dashboard from Monday.com + SMS data.
"""
import json, re, os
from datetime import datetime, date, timedelta
from collections import defaultdict

# ─── Load existing JSON to preserve hand-curated fields ─────────────────────
# service_round, visit_freq, sample_freq, sh are NOT from Monday — preserve them
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_EXISTING_JSON = os.path.join(_THIS_DIR, 'all_facilities_enriched.json')
_existing_by_name = {}
try:
    _existing_data = json.load(open(_EXISTING_JSON, encoding='utf-8'))
    _existing_by_name = {f['n']: f for f in _existing_data}
    print(f"Loaded existing JSON: {len(_existing_by_name)} facilities (for field preservation)")
except Exception as _e:
    print(f"No existing JSON to load ({_e}) — starting fresh")

# ─── Load raw data ─────────────────────────────────────────────────────────
TMP = '/tmp/epc_work'
def _load(path):
    try:
        data = json.load(open(path))
        return data.get('items', []) if isinstance(data, dict) else data
    except FileNotFoundError: return []

bd_items = _load(f'{TMP}/bio_disk_p1.json') + _load(f'{TMP}/bd2.json')
br_items = _load(f'{TMP}/bio_robi_p1.json') + _load(f'{TMP}/br2.json') + _load(f'{TMP}/br3.json')
gears_raw   = json.load(open(f'{TMP}/gears.json'))
blades_raw  = json.load(open(f'{TMP}/blades.json'))
viols_raw   = json.load(open(f'{TMP}/violations.json'))

# ─── בורדים נפרדים: מגן / אלמוג / מצדה ──────────────────────────────────────
masada_items = _load(f'{TMP}/masada.json')
magen_items  = _load(f'{TMP}/magen.json')
almog_items  = _load(f'{TMP}/almog.json')

print(f"Items: BD={len(bd_items)}, BR={len(br_items)}, Gears={len(gears_raw)}, Blades={len(blades_raw)}, Violations={len(viols_raw)}")
print(f"Extra boards: Masada={len(masada_items)}, Magen={len(magen_items)}, Almog={len(almog_items)}")

# ─── Column IDs ─────────────────────────────────────────────────────────────
BD = dict(facility='single_selectei4jhgr', date='datenrgl3w0y', tech='peopleue9lxpjf',
          type='single_select6k4h3fx', do='numberoqjholqn', meter='numbersz9nyntq',
          ntu='numbersfu2jhpu', sample='single_select2rv1o1c',
          pump='color_mkxevc82', issues_status='color_mkxjntm0', issues_text='long_text8aquc6k6')
BR = dict(facility='single_selectnllyw4n', date='datenrgl3w0y', tech='peopleue9lxpjf',
          type='single_select6k4h3fx', do='numberys7n99to', meter='numbersz9nyntq',
          ntu='number3xw9zzg4', sample='single_select2rv1o1c',
          pump='color_mkxemfqp', issues_status='color_mkxj90x1', issues_text='long_textjc1jbepu')

OPEN_EXCLUDE = {'טופל', 'לא נדרש', 'בוצע', ''}

# ─── Facility name aliases: Monday name → canonical name ─────────────────────
FACILITY_ALIASES = {
    'דרום הר חברון- מעלה חבר': 'דרום הר חברון- פני חבר',
}

# ─── Known bad meter values to exclude (data-entry errors in Monday) ─────────
BAD_METER_VALUES = {
    'כיכר סדום': {47985581},
}

# ─── Column IDs — בורדים נפרדים (שם המתקן = item name) ───────────────────────
MASADA = dict(date='date4', tech='person', type='single_select6944s3e',
              sample='single_select0zd6rlw', do='number1aa5afwy', ntu='numberabemmvtc',
              sample2='single_selectromu99g', pump='color_mm1ymsgp', meter='')
MAGEN  = dict(date='datentbcu9sw', tech='peoplesixgueus', type='single_selectxpajk3i',
              sample='single_select1vxbiim', do='number5e8rkn4j', ntu='numberzpet4au1',
              sample2='single_selectweub9oc', pump='color_mm1ysykj', meter='')
ALMOG  = dict(date='date0391xg6z', tech='peopleied9laft', type='single_selectvtk3cv4',
              sample='single_select8ve42ov', do='number7tpfmcch', ntu='number3n2palc8',
              sample2='single_selectbyc0drf', pump='color_mm1yw5w0', meter='numberk08zvzdc')

# ─── Parse date string ───────────────────────────────────────────────────────
def parse_date(s):
    if not s: return None
    for fmt in ('%Y-%m-%d %H:%M', '%Y-%m-%d'):
        try: return datetime.strptime(s[:16], fmt)
        except: pass
    return None

def fmt_date(dt):
    if not dt: return ''
    return dt.strftime('%d/%m')

def fmt_date_full(dt):
    if not dt: return ''
    return dt.strftime('%Y-%m-%d')

# ─── Parse all visits ────────────────────────────────────────────────────────
visits = []  # list of dicts

for item, col in [(i, BD) for i in bd_items] + [(i, BR) for i in br_items]:
    c = item.get('column_values', {})
    fac_raw = c.get(col['facility'])
    if isinstance(fac_raw, dict): fac_raw = None
    fac_name = (fac_raw or item.get('name') or '').strip()
    if not fac_name or fac_name in ('ביו דיסק', 'ביו רובי'): continue

    dt = parse_date(c.get(col['date'], '') or '')
    tech_raw = c.get(col['tech'], '') or ''
    if isinstance(tech_raw, dict): tech_raw = ''
    # tech: extract first name if multiple
    tech = tech_raw.split(',')[0].strip().split(' ')[0] if tech_raw else ''
    visit_type = c.get(col['type'], '') or ''
    if isinstance(visit_type, dict): visit_type = ''
    do_val = c.get(col['do'], '')
    meter_val = c.get(col['meter'], '')
    ntu_val = c.get(col['ntu'], '')
    pump_st = c.get(col['pump'], '') or ''
    iss_st = c.get(col['issues_status'], '') or ''
    iss_text = c.get(col['issues_text'], '') or ''
    sample_st = c.get(col.get('sample',''), '') or ''
    if isinstance(sample_st, dict): sample_st = ''
    board_type = 'ביו-דיסק' if col == BD else 'ביו-רובי'

    try: do_num = float(str(do_val).replace(',','')) if do_val else None
    except: do_num = None
    try: meter_num = float(str(meter_val).replace(',','')) if meter_val else None
    except: meter_num = None
    try: ntu_num = float(str(ntu_val).replace(',','')) if ntu_val else None
    except: ntu_num = None

    # Apply facility alias (merge duplicate Monday entries)
    fac_name = FACILITY_ALIASES.get(fac_name, fac_name)

    # Nullify known bad meter readings
    if meter_num is not None and meter_num in BAD_METER_VALUES.get(fac_name, set()):
        meter_num = None

    visits.append({
        'fac': fac_name, 'dt': dt, 'tech': tech, 'type': visit_type,
        'do': do_num, 'meter': meter_num, 'ntu': ntu_num, 'pump': pump_st,
        'iss_st': iss_st, 'iss_text': iss_text.strip(), 'board': board_type,
        'sample': sample_st
    })

# ─── Parse extra boards: מגן / אלמוג / מצדה ──────────────────────────────────
# מצדה ומגן: בורדים של מתקן יחיד — כל פריט = ביקור. שם המתקן קבוע.
# אלמוג: כל פריט כולל שם מתקן בשדה name.
FIXED_NAME = {id(i): 'מצדה' for i in masada_items}
FIXED_NAME.update({id(i): 'קיבוץ מגן' for i in magen_items})

for item, col, btype in (
    [(i, MASADA, 'ביו-דיסק') for i in masada_items] +
    [(i, MAGEN,  'ביו-דיסק') for i in magen_items]  +
    [(i, ALMOG,  'ביו-דיסק') for i in almog_items]
):
    c = item.get('column_values', {})
    fac_name = FIXED_NAME.get(id(item)) or item.get('name', '').strip()
    if not fac_name: continue

    dt = parse_date(c.get(col['date'], '') or '')
    tech_raw = c.get(col['tech'], '') or ''
    if isinstance(tech_raw, dict): tech_raw = ''
    tech = tech_raw.split(',')[0].strip() if tech_raw else ''
    visit_type = c.get(col.get('type', ''), '') or ''
    if isinstance(visit_type, dict): visit_type = ''
    do_val    = c.get(col.get('do', ''), '')
    meter_val = c.get(col['meter'], '') if col.get('meter') else None
    ntu_val   = c.get(col.get('ntu', ''), '')
    pump_st   = c.get(col.get('pump', ''), '') or ''
    sample_st = c.get(col.get('sample', ''), '') or ''
    if isinstance(sample_st, dict): sample_st = ''

    try: do_num    = float(str(do_val).replace(',', '')) if do_val else None
    except: do_num = None
    try: meter_num = float(str(meter_val).replace(',', '')) if meter_val else None
    except: meter_num = None
    try: ntu_num   = float(str(ntu_val).replace(',', '')) if ntu_val else None
    except: ntu_num = None

    visits.append({
        'fac': fac_name, 'dt': dt, 'tech': tech, 'type': visit_type,
        'do': do_num, 'meter': meter_num, 'ntu': ntu_num, 'pump': pump_st,
        'iss_st': '', 'iss_text': '', 'board': btype, 'sample': sample_st,
    })

# ─── Group by facility ───────────────────────────────────────────────────────
by_fac = defaultdict(list)
for v in visits:
    if v['fac']:
        by_fac[v['fac']].append(v)

# Sort each facility's visits by date descending
for fac in by_fac:
    by_fac[fac].sort(key=lambda x: x['dt'] or datetime.min, reverse=True)

print(f"Unique facilities: {len(by_fac)}")

# ─── Cross-board matching helpers ────────────────────────────────────────────
GEARS_MAP = {
    'דור אלון- גן יבנה': ['ד"א גן יבנה'],
    'הר עמשא': ['הר עמשא'],
    'אבנת': ['אבנת'],
    'בית הערבה': ['בית הערבה'],
    'בית אריה': ['בית אריה - מגרזות', 'בית אריה - משמנות'],
    'גיתה': ['גיתה'],
    'גני רמת הנדיב': ['רמת הנדיב'],
    'חאן שער הגיא': ['חאן שער הגיא'],
    'מעלה עמוס': ['מעלה עמוס'],
    'משואה': ['משואה'],
    'נטועה': ['נטועה'],
    'ניר יצחק': ['ניר יצחק'],
    'עופרים': ['עופרים'],
    'ערוגות בושם': ['ערוגות הבושם'],
    'פז- השקמה': ['פז השקמה'],
    'רותם תעשיות': ['רותם תעשיות'],
    'סונול- בית שקמה': ['סונול בית השקמה'],
    'דרום הר חברון- סוסיה': ['סוסיה'],
    'דרום הר חברון- מעלה חבר': ['פני חבר'],
    'בית חגי': ['בית חגי'],
    'חניון הגבס': ['חניון הגבס'],
    'דור אלון- צובה': ['צובה'],
    'כיכר סדום': ['כיכר סדום'],
}

BLADES_MAP = {
    'בית אריזה- בית הערבה': ['בית אריזה - בית הערבה - שמאל', 'בית אריזה - בית הערבה - ימין'],
    'בית אריזה בית - שדות נגב': ['בית אריזה - נגב'],
    'צומת הלידו': ['צומת הלידו - 1 - ימין', 'צומת הלידו - 2 - שמאל'],
    'דור אלון- מורן': ['ד"א מורן'],
    'דור אלון- גני חוגה': ['ד"א גני חוגה'],
    'סונול- עמודים': ['סונול עמודים'],
    'דור אלון- זכרון יעקוב': ['ד"א זכרון'],
    'דור אלון- שמרון': ['ד"א שימרון'],
    'דור אלון- יובלים': ['ד"א יובלים'],
    'דור אלון- אורים': ['ד"א אורים'],
    'פז- השקמה': ['פז השקמה'],
    'סונול- בית שקמה': ['סונול בית השקמה'],
    'פז- סילבר': ['פז סילבר'],
    'דור אלון- נגבה': ['ד"א נגבה'],
    'שתיל נטו': ['שתיל נטו'],
    'דור אלון- בני ציון': ['ד"א בני ציון'],
    'אפרסמור': ['אפרסמור'],
    'אקוסול': ['אקוסול'],
    'אשלים B': ['אשלים B'],
    'עבדת': ['עבדת', 'עבדת 2'],
    'אשלג סדום 1': ['אשלג סדום שמאל', 'אשלג סדום ימין'],
    'אשלג סדום 2': ['אשלג סדום שמאל', 'אשלג סדום ימין'],
}

VIOLS_MAP = {
    'דור אלון- גן יבנה': ['גן יבנה'],
    'חכ"ד': ['חכ"ד'],
    'סונול- עמודים': ['סונול עמודים'],
    'אפרסמור': ['אפרסמור'],
    'דור אלון- אורים': ['דור אלון אורים'],
    'פז- השקמה': ['פז השקמה'],
    'חאן שער הגיא': ['חאן שער הגיא'],
    'אשלים B': ['אשלים B', 'אשלים B - ביולוגי 1'],
    'נטועה': ['נטועה'],
    'אבנת': ['אבנת'],
    'מצדה': ['מצדה'],
    'דור אלון- אורים': ['אורים'],
}

# Build lookup dicts
gears_by_name = {g['n']: g for g in gears_raw}
blades_by_name = {b['n']: b for b in blades_raw}
viols_by_name  = {v['n']: v for v in viols_raw}

def get_gears(fac_name):
    keys = GEARS_MAP.get(fac_name, [])
    result = []
    for k in keys:
        if k in gears_by_name:
            result.append(gears_by_name[k])
    # Fuzzy fallback
    if not result:
        for n, g in gears_by_name.items():
            # Normalize both
            fn = fac_name.replace('דור אלון- ', '').replace('דור אלון- ', '').replace('-','').replace(' ','')
            gn = n.replace('ד"א ','').replace('"','').replace('-','').replace(' ','')
            if len(fn) > 3 and fn[:4] in gn:
                result.append(g)
                break
    return result

def get_blades(fac_name):
    keys = BLADES_MAP.get(fac_name, [])
    result = []
    for k in keys:
        if k in blades_by_name:
            result.append(blades_by_name[k])
    return result

def get_viols(fac_name):
    keys = VIOLS_MAP.get(fac_name, [])
    result = []
    for k in keys:
        if k in viols_by_name:
            result.append(viols_by_name[k])
    # Fuzzy: match by short name contained in viol name
    if not result:
        short = fac_name.replace('דור אלון- ','').replace('סונול- ','').replace('פז- ','').strip()
        for n, v in viols_by_name.items():
            if short in n or n in short:
                result.append(v)
                break
    return result

def get_status(fac_visits, gears, blades, viols):
    """Compute card status: critical / warn / ok"""
    if not fac_visits: return 'ok'
    latest = fac_visits[0]
    # Check last visit recency
    if latest['dt']:
        days_ago = (datetime.now() - latest['dt']).days
        if days_ago > 45: return 'critical'
    # Check DO
    if latest['do'] is not None and latest['do'] == 0: return 'critical'
    # Check pump
    if latest['pump'] in ('נדרשת שאיבה',): return 'warn'
    # Check overdue gears
    today = date.today().isoformat()
    for g in gears:
        if g.get('status') == 'צריך להחליף' and g.get('next') and g['next'] < today:
            return 'warn'
    # Check violations
    if viols: return 'warn'
    return 'ok'

def compute_flow_history(fac_visits):
    """Compute flow rate history from meter readings, with outlier filtering."""
    # Collect readings: skip zero values and missing dates
    readings = [(v['dt'], v['meter']) for v in fac_visits
                if v['dt'] and v['meter'] is not None and v['meter'] > 0]
    readings.sort(key=lambda x: x[0])
    if len(readings) < 2: return []

    # Compute raw flows (only where meter increases)
    raw = []
    for i in range(1, len(readings)):
        dt1, m1 = readings[i-1]
        dt2, m2 = readings[i]
        days = (dt2 - dt1).days
        if days > 0 and m2 > m1:
            raw.append({'d': fmt_date_full(dt2), 'v': round((m2 - m1) / days, 1)})

    if not raw: return []

    # Outlier filter: exclude intervals >10x or <0.1x the median
    # (detects decimal-point errors while preserving genuine variation)
    vals = sorted(f['v'] for f in raw)
    median = vals[len(vals) // 2]
    if median > 0:
        fh = [f for f in raw if 0.1 * median <= f['v'] <= 10 * median]
        if not fh:  # fallback: no filtering if everything is filtered
            fh = raw
    else:
        fh = raw

    return fh[-12:]  # last 12 valid readings

def build_open_issues(fac_visits):
    """Collect all open issues across visits, dedup by text."""
    seen = {}
    for v in fac_visits:
        if not v['iss_text'] or v['iss_st'] in OPEN_EXCLUDE:
            continue
        lines = [l.strip() for l in v['iss_text'].split('\n') if l.strip()]
        for line in lines:
            if line not in seen:
                seen[line] = {
                    'd': fmt_date_full(v['dt']) if v['dt'] else '',
                    'text': line,
                    'status': v['iss_st'],
                    'tech': v['tech']
                }
    return list(seen.values())

# ─── מכפילי מד מיוחדים (כאשר השעון בנוי ביחידות שונות) ──────────────────────
METER_MULTIPLIER = {
    'בית אריה': 10,  # השעון מדד ביחידות של 0.1 מ"ק — יש להכפיל ×10
}

# ─── Build enriched facilities list ─────────────────────────────────────────
facilities = []

for fac_name, fac_visits in sorted(by_fac.items()):
    latest = fac_visits[0]
    board_type = latest['board']

    # Visit history (last 8)
    vh = []
    for v in fac_visits[:8]:
        vh.append({'d': fmt_date_full(v['dt']), 'tech': v['tech'], 'type': v['type']})

    # DO history (last 12 with value)
    dh = []
    do_all_vals = []
    for v in fac_visits:
        if v['do'] is not None and v['do'] > 0 and v['dt']:
            dh.append({'d': fmt_date_full(v['dt']), 'v': v['do']})
            do_all_vals.append(v['do'])
    dh = dh[:12]
    # ממוצע רק לפי ביקורים עם ערך ממשי של חמצן מומס (>0)
    do_avg = round(sum(do_all_vals) / len(do_all_vals), 1) if do_all_vals else None

    # NTU history (last 8 with value) + average (same logic as DO — exclude zeros)
    nth = []
    ntu_all_vals = []
    for v in fac_visits:
        if v['ntu'] is not None and v['ntu'] > 0 and v['dt']:
            nth.append({'d': fmt_date_full(v['dt']), 'v': v['ntu']})
            ntu_all_vals.append(v['ntu'])
    nth = nth[:8]
    ntu_latest = nth[0]['v'] if nth else None
    ntu_avg = round(sum(ntu_all_vals) / len(ntu_all_vals), 1) if ntu_all_vals else None

    # Flow history (with optional meter multiplier)
    fh = compute_flow_history(fac_visits)
    mult = METER_MULTIPLIER.get(fac_name, 1)
    if mult != 1:
        fh = [{'d': e['d'], 'v': round(e['v'] * mult, 1)} for e in fh]

    # Open issues
    all_issues = build_open_issues(fac_visits)
    oi_texts = list({i['text'] for i in all_issues})

    # Sample history: visits where sample status == "בוצע"
    # If column is available in raw data, build fresh; otherwise preserve from existing JSON
    sh_fresh = []
    for v in fac_visits:
        if v.get('sample') == 'בוצע' and v['dt']:
            sh_fresh.append({'d': fmt_date_full(v['dt'])})
    sh_fresh.sort(key=lambda x: x['d'], reverse=True)

    _ex = _existing_by_name.get(fac_name, {})
    if sh_fresh:
        # Fresh data available — use it (sample column was fetched)
        sh = sh_fresh
    else:
        # Sample column not in raw data — preserve existing to avoid data loss
        sh = _ex.get('sh', [])

    # Preserve hand-curated fields (not from Monday.com)
    service_round = _ex.get('service_round', '')
    visit_freq    = _ex.get('visit_freq', '2 בחודש')
    sample_freq   = _ex.get('sample_freq', '1 בחודש')

    # Cross-board data
    gears   = get_gears(fac_name)
    blades  = get_blades(fac_name)
    viols   = get_viols(fac_name)

    status = get_status(fac_visits, gears, blades, viols)

    facilities.append({
        'n':  fac_name,
        't':  board_type,
        'lv': fmt_date(latest['dt']),
        'lt': latest['tech'],
        'do': str(do_avg) if do_avg is not None else '',
        'ntu': ntu_latest,
        'ntu_avg': ntu_avg,
        'nth': nth,
        'ps': latest['pump'],
        'is': latest['iss_st'],
        'oi': oi_texts,
        'dh': dh,
        'fh': fh,
        'vh': vh,
        'sh': sh,
        'st': status,
        'service_round': service_round,
        'visit_freq':    visit_freq,
        'sample_freq':   sample_freq,
        'gears':      [{'n': g['n'], 'status': g['status'], 'last': g.get('last',''), 'next': g.get('next',''), 'qty': g.get('qty',''), 'account': g.get('account','')} for g in gears],
        'blades':     [{'n': b['n'], 'status': b['status'], 'last': b.get('last',''), 'next': b.get('next',''), 'height': b.get('height',''), 'account': b.get('account','')} for b in blades],
        'violations': [{'n': v['n'], 'params': v['params'], 'status': v['status']} for v in viols],
        'all_issues': all_issues,
    })

# Sort: critical first, then warn, then ok; alphabetical within
order = {'critical': 0, 'warn': 1, 'ok': 2}
facilities.sort(key=lambda f: (order.get(f['st'], 2), f['n']))

print(f"Built {len(facilities)} facilities")
crit = sum(1 for f in facilities if f['st']=='critical')
warn = sum(1 for f in facilities if f['st']=='warn')
ok   = sum(1 for f in facilities if f['st']=='ok')
print(f"Status: critical={crit}, warn={warn}, ok={ok}")
print("Sample:", facilities[0]['n'], '|', facilities[0]['st'], '|', facilities[0]['lv'])

# Save — write to both /tmp AND the DASHBOARD folder so finalize_dashboard.py
# always picks up freshly-built data (including the DO>0 exclusion fix)
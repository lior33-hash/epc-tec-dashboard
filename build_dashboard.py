#!/usr/bin/env python3
"""
Build the full EPC-TEC dashboard from Monday.com + SMS data.
"""
import json, re
from datetime import datetime, date, timedelta
from collections import defaultdict

# ─── Load raw data ─────────────────────────────────────────────────────────
TMP = '/tmp'
def _load(path):
    try: return json.load(open(path))
    except FileNotFoundError: return []

bd_items = _load(f'{TMP}/bio_disk_p1.json') + _load(f'{TMP}/bd2.json')
br_items = _load(f'{TMP}/bio_robi_p1.json') + _load(f'{TMP}/br2.json') + _load(f'{TMP}/br3.json')
gears_raw   = json.load(open(f'{TMP}/gears.json'))
blades_raw  = json.load(open(f'{TMP}/blades.json'))
viols_raw   = json.load(open(f'{TMP}/violations.json'))

print(f"Items: BD={len(bd_items)}, BR={len(br_items)}, Gears={len(gears_raw)}, Blades={len(blades_raw)}, Violations={len(viols_raw)}")

# ─── Column IDs ─────────────────────────────────────────────────────────────
BD = dict(facility='single_selectei4jhgr', date='datenrgl3w0y', tech='peopleue9lxpjf',
          type='single_select6k4h3fx', do='numberxwi07t9y', meter='numbersz9nyntq',
          pump='color_mkxevc82', issues_status='color_mkxjntm0', issues_text='long_text8aquc6k6')
BR = dict(facility='single_selectnllyw4n', date='datenrgl3w0y', tech='peopleue9lxpjf',
          type='single_select6k4h3fx', do='numberxwi07t9y', meter='numbersz9nyntq',
          pump='color_mkxemfqp', issues_status='color_mkxj90x1', issues_text='long_textjc1jbepu')

OPEN_EXCLUDE = {'טופל', 'לא נדרש', 'בוצע', ''}

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
    fac_name = (c.get(col['facility']) or item.get('name') or '').strip()
    if not fac_name: continue

    dt = parse_date(c.get(col['date'], ''))
    tech_raw = c.get(col['tech'], '') or ''
    # tech: extract first name if multiple
    tech = tech_raw.split(',')[0].strip().split(' ')[0] if tech_raw else ''
    visit_type = c.get(col['type'], '') or ''
    do_val = c.get(col['do'], '')
    meter_val = c.get(col['meter'], '')
    pump_st = c.get(col['pump'], '') or ''
    iss_st = c.get(col['issues_status'], '') or ''
    iss_text = c.get(col['issues_text'], '') or ''
    board_type = 'ביו-דיסק' if col == BD else 'ביו-רובי'

    try: do_num = float(str(do_val).replace(',','')) if do_val else None
    except: do_num = None
    try: meter_num = float(str(meter_val).replace(',','')) if meter_val else None
    except: meter_num = None

    visits.append({
        'fac': fac_name, 'dt': dt, 'tech': tech, 'type': visit_type,
        'do': do_num, 'meter': meter_num, 'pump': pump_st,
        'iss_st': iss_st, 'iss_text': iss_text.strip(), 'board': board_type
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
    """Compute flow rate history from meter readings."""
    # Collect readings with valid dates and meters, sorted ascending
    readings = [(v['dt'], v['meter']) for v in fac_visits if v['dt'] and v['meter'] is not None]
    readings.sort(key=lambda x: x[0])
    if len(readings) < 2: return []

    fh = []
    for i in range(1, len(readings)):
        dt1, m1 = readings[i-1]
        dt2, m2 = readings[i]
        days = (dt2 - dt1).days
        if days > 0 and m2 > m1:
            flow = round((m2 - m1) / days, 1)
            fh.append({'d': fmt_date_full(dt2), 'v': flow})
    return fh[-12:]  # last 12 readings

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
    for v in fac_visits:
        if v['do'] is not None and v['dt']:
            dh.append({'d': fmt_date_full(v['dt']), 'v': v['do']})
    dh = dh[:12]

    # Flow history
    fh = compute_flow_history(fac_visits)

    # Open issues
    all_issues = build_open_issues(fac_visits)
    oi_texts = list({i['text'] for i in all_issues})

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
        'do': str(int(latest['do'])) if latest['do'] is not None else '',
        'ps': latest['pump'],
        'is': latest['iss_st'],
        'oi': oi_texts,
        'dh': dh,
        'fh': fh,
        'vh': vh,
        'st': status,
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

# Save
with open(f'{TMP}/all_facilities_enriched.json', 'w', encoding='utf-8') as f:
    json.dump(facilities, f, ensure_ascii=False, separators=(',',':'))

print(f"Saved to {TMP}/all_facilities_enriched.json ({len(facilities)} facilities)")

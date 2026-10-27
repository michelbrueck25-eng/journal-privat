#!/usr/bin/env python3
"""Orderblock-Prüfung für die KI-Empfehlungen und die offenen/Limit-Positionen.

Liest: journal-export.json (Trades, Chart-Daten), marktdaten/<PAAR>_<D|W>.json (von der App),
       ../journal-daten/cot.csv, wirtschaft.csv, ausblick.json
Schreibt: ../journal-daten/ausblick.json  (Felder `pruefung` und `empfehlungen[i].ob`)

Definition Orderblock (kalibriert an deinen gezeichneten Zonen: Zone = Hoch bis Tief EINER Kerze):
  Long-OB  = fallende (oder Doji-)Kerze, nach der innerhalb von 3 Kerzen das Hoch mindestens 1,0 ATR(14) über ihr Hoch steigt
             und ein Schluss über das höchste Hoch der letzten 8 Kerzen und über ihr Hoch erfolgt.
  Short-OB = Spiegelbild.
  Qualität A: Bewegung >= 2,0 ATR und noch nie berührt; B: >= 1,2 ATR und höchstens 1 Berührung; sonst C.
  Mitigiert (ungültig): spätere Kerze schließt jenseits der Zone.
Diese Schwellen sind meine Annahme (nur 7 Chart-Trades zum Kalibrieren), nicht deine bestätigte Regel.
"""
import csv, datetime as dt, glob, json, os, re, sys

HOME = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HOME, '..', 'journal-daten')
NOW = dt.datetime.now(dt.timezone.utc)
CUR_COUNTRY = {'USD': 'USA', 'EUR': 'Eurozone', 'GBP': 'Großbritannien', 'JPY': 'Japan', 'CHF': 'Schweiz',
               'AUD': 'Australien', 'CAD': 'Kanada', 'NZD': 'Neuseeland'}


def day(ms): return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).strftime('%Y-%m-%d')
def dmy(iso): return '.'.join(reversed(iso.split('-')[:3]))
def fmt(v, sym): return f'{v:.3f}' if sym.endswith('JPY') else f'{v:.5f}'.rstrip('0').rstrip('.') if False else (f'{v:.3f}' if sym.endswith('JPY') else f'{v:.5f}')


def dec_chart(c):
    out = []; pt = pc = 0; cs = c['cs']; fx = c['fx']
    for i in range(0, len(cs) - 4, 5):
        tm = pt + cs[i]; o = pc + cs[i + 1]; cl = o + cs[i + 2]; h = max(o, cl) + cs[i + 3]; l = min(o, cl) - cs[i + 4]
        out.append([tm * 60000, o / fx, h / fx, l / fx, cl / fx]); pt = tm; pc = cl
    return out


def to_weekly(rows):
    wk = {}
    for t, o, h, l, c in rows:
        d = dt.datetime.fromtimestamp(t / 1000, dt.timezone.utc); mon = (d - dt.timedelta(days=d.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        k = int(mon.timestamp() * 1000)
        if k not in wk: wk[k] = [k, o, h, l, c]
        else: w = wk[k]; w[2] = max(w[2], h); w[3] = min(w[3], l); w[4] = c
    return [wk[k] for k in sorted(wk)]


def load_candles(sym, tf, trades):
    p = os.path.join(HOME, 'marktdaten', f'{sym}_{tf}.json')
    if os.path.exists(p):
        j = json.load(open(p)); return j['rows'], 'Marktdaten ' + dmy(j['stand'][:10])
    best = None
    for t in trades:
        ch = t.get('chart')
        if ch and ch.get('sym') == sym:
            r = dec_chart(ch)
            if ch['tf'] == tf: best = (r, 'Chart-Snapshot ' + dmy(day(r[-1][0])))
            elif ch['tf'] == 'D' and tf == 'W' and not best: best = (to_weekly(r), 'Chart-Snapshot ' + dmy(day(r[-1][0])))
    return best if best else (None, None)


def atr(rows, i, n=14):
    s = 0; k = 0
    for j in range(max(1, i - n + 1), i + 1):
        pc = rows[j - 1][4]; s += max(rows[j][2] - rows[j][3], abs(rows[j][2] - pc), abs(rows[j][3] - pc)); k += 1
    return s / k if k else None


def find_obs(rows, direction):
    """Alle Orderblöcke in Richtung direction ('long'|'short') mit Zustand."""
    obs = []; n = len(rows)
    for i in range(9, n - 3):
        t, o, h, l, c = rows[i]
        doji = abs(c - o) <= 0.3 * (h - l)
        a = atr(rows, i)
        if not a: continue
        nxt = rows[i + 1:i + 4]
        if direction == 'long':
            if not (c < o or doji): continue
            ref = max(r[2] for r in rows[i - 8:i])
            disp = max(r[2] for r in nxt) - h
            bos = any(r[4] > ref for r in nxt) and any(r[4] > h for r in nxt)
        else:
            if not (c > o or doji): continue
            ref = min(r[3] for r in rows[i - 8:i])
            disp = l - min(r[3] for r in nxt)
            bos = any(r[4] < ref for r in nxt) and any(r[4] < l for r in nxt)
        if disp < 1.0 * a or not bos: continue
        touches = 0; inside = False; mitig = False
        for r in rows[i + 4:]:
            if direction == 'long':
                inz = r[3] <= h and r[2] >= l
                if r[4] < l: mitig = True; break
            else:
                inz = r[2] >= l and r[3] <= h
                if r[4] > h: mitig = True; break
            if inz and not inside: touches += 1
            inside = inz
        q = 'A' if disp >= 2.0 * a and touches == 0 else 'B' if disp >= 1.2 * a and touches <= 1 else 'C'
        obs.append({'i': i, 't': t, 'lo': l, 'hi': h, 'disp_atr': round(disp / a, 2), 'touches': touches, 'mitigated': mitig, 'q': q, 'age': n - 1 - i})
    return obs


def cot_idx():
    rows = {}
    p = os.path.join(DATA, 'cot.csv')
    for r in csv.DictReader(open(p, encoding='utf-8')):
        try: rows.setdefault(r['waehrung'], []).append((r['datum'], int(r['comm_long']) - int(r['comm_short'])))
        except Exception: pass
    out = {}
    for cur, v in rows.items():
        v.sort(); net = [x[1] for x in v][-26:]
        if len(net) < 26 or max(net) == min(net): continue
        out[cur] = (round(100 * (net[-1] - min(net)) / (max(net) - min(net))), v[-1][0])
    return out


def events(cur_pair, days=5):
    out = []; today = NOW.astimezone().date()
    try:
        for r in csv.DictReader(open(os.path.join(DATA, 'wirtschaft.csv'), encoding='utf-8', newline='')):
            if r['impact'] != 'high': continue
            d = dt.date.fromisoformat(r['date'])
            if today <= d <= today + dt.timedelta(days=days) and any(CUR_COUNTRY[c] == r['country'] for c in cur_pair):
                out.append(f"{dmy(r['date'])[:6]} {r['time']} {r['title']}")
    except Exception: pass
    return out


def main():
    exp = json.load(open(os.path.join(HOME, 'journal-export.json')))
    trades = exp['trades']
    A = json.load(open(os.path.join(DATA, 'ausblick.json')))
    cot = cot_idx()
    live = [t for t in trades if t.get('source') == 'live' and t.get('status') in ('offen', 'limit')]
    aud = sum(1 for t in live if 'AUD' in str(t['instrument']))

    def cot_check(sym, direction):
        b, q = sym[:3], sym[3:]
        cb, cq = cot.get(b), cot.get(q); out = []
        if not cb: return [('warn', f'COT für {b} fehlt.')]
        ok = cb[0] >= 75 if direction == 'long' else cb[0] <= 25
        conf = cq and (cq[0] <= 25 if direction == 'long' else cq[0] >= 75)
        out.append(('ok' if ok else 'bad', f'COT {b} 6M-Index {cb[0]} (Stand {dmy(cb[1])}): {"im passenden Extrembereich" if ok else "nicht mehr im Extrembereich für " + ("Long" if direction == "long" else "Short")}' + (f', {q} {cq[0]} bestätigt gegenläufig.' if ok and conf else (f', {q} {cq[0]}.' if cq else '.'))))
        return out

    fb = {f['k']: f for f in exp.get('obFeedback', [])}
    A['lernen'] = {'n': len(fb), 'gut': sum(1 for f in fb.values() if f['urteil'] == 'gut'), 'schwach': sum(1 for f in fb.values() if f['urteil'] == 'schwach'), 'falsch': sum(1 for f in fb.values() if f['urteil'] == 'falsch'), 'eigene_zonen': [{'paar': f['paar'], 'meine': f['zone'], 'deine': f['eigene']} for f in fb.values() if f.get('eigene')]}

    # ---------- Empfehlungen ----------
    # Auch die übrigen Paare der Liste "Alle Paare" prüfen (Richtung bei Abwarten aus dem COT-Extrem der Basiswährung)
    emp = {e['paar'] for e in A.get('empfehlungen', [])}
    extras = []
    for p in A.get('paare', []):
        if p['paar'] in emp: continue
        d0 = str(p.get('richtung', '')).lower(); b = p['paar'].replace('/', '')[:3]
        if d0 not in ('long', 'short'):
            cb = cot.get(b)
            d0 = 'long' if cb and cb[0] >= 75 else 'short' if cb and cb[0] <= 25 else ''
        if d0: extras.append({'paar': p['paar'], 'richtung': d0, '_p': p})
    for e in A.get('empfehlungen', []) + extras:
        sym = e['paar'].replace('/', ''); d = e['richtung'].lower()
        wk, src = load_candles(sym, 'W', trades); dl, srcd = load_candles(sym, 'D', trades)
        chk = [(k, t) for k, t in cot_check(sym, d)]
        ev = events((sym[:3], sym[3:]))
        if ev: chk.append(('warn', 'Termine in den nächsten 5 Tagen: ' + '; '.join(ev[:4]).replace(';', ',') + '.'))
        ob = {'stand': NOW.astimezone().strftime('%Y-%m-%dT%H:%M'), 'checks': [], 'quelle': src or 'keine Kerzen'}
        if not wk:
            chk.append(('warn', 'Keine Kerzendaten für dieses Paar: Marktdaten in der App senden (Einstellungen, Marktdaten senden), dann prüfe ich Orderblöcke.'))
        else:
            price = wk[-1][4] if not dl else dl[-1][4]; last = wk[-1]; a = atr(wk, len(wk) - 1)
            obs = [o for o in find_obs(wk, d) if not o['mitigated']]
            # nächster Block auf der richtigen Seite des Kurses
            obs = [o for o in obs if (o['hi'] <= price if d == 'long' else o['lo'] >= price)]
            if not obs:
                chk.append(('bad', 'Weekly: kein unmitigierter Orderblock auf der richtigen Seite des Kurses, ein Limit-Einstieg ist so nicht begründbar.'))
            else:
                o = min(obs, key=lambda x: abs((price - x['hi']) if d == 'long' else (x['lo'] - price)))
                dist = ((price - o['hi']) if d == 'long' else (o['lo'] - price)) / a
                rng = o['hi'] - o['lo']
                entry = o['hi'] if d == 'long' else o['lo']; sl = (o['lo'] - 0.1 * rng) if d == 'long' else (o['hi'] + 0.1 * rng)
                R = abs(entry - sl); tp1 = entry + R if d == 'long' else entry - R; tp2 = entry + 2 * R if d == 'long' else entry - 2 * R
                ob.update({'ebene': 'weekly', 'zone': [round(o['lo'], 5), round(o['hi'], 5)], 'qualitaet': o['q'], 'alter_wochen': o['age'], 'beruehrungen': o['touches'], 'bewegung_atr': o['disp_atr'], 'kurs': round(price, 5), 'kursstand': day(wk[-1][0]), 'abstand_atr': round(dist, 1), 'zone_t': o['t'], 'einstieg': round(entry, 5), 'stopp': round(sl, 5), 'ziel1': round(tp1, 5), 'ziel2': round(tp2, 5)})
                chk.append(('ok' if o['q'] in 'AB' else 'warn', f"Weekly-Orderblock {fmt(o['lo'], sym)} bis {fmt(o['hi'], sym)}, Qualität {o['q']} (Bewegung {o['disp_atr']} ATR, {o['touches']} Berührungen, {o['age']} Wochen alt)."))
                chk.append(('ok' if dist <= 4 else 'warn', f'Kurs {fmt(price, sym)} ist {dist:.1f} Wochen-ATR von der Zone entfernt' + ('.' if dist <= 4 else ', der Limit wird lange nicht erreicht.')))
                if dl:
                    d_obs = [x for x in find_obs(dl, d) if not x['mitigated'] and x['lo'] >= o['lo'] - 1e-9 and x['hi'] <= o['hi'] + 1e-9]
                    if d_obs:
                        x = max(d_obs, key=lambda z: z['t'])
                        ob['daily_ob'] = [round(x['lo'], 5), round(x['hi'], 5)]; ob['daily_q'] = x['q']
                        chk.append(('ok', f"Daily-Orderblock in der Weekly-Zone: {fmt(x['lo'], sym)} bis {fmt(x['hi'], sym)}, Qualität {x['q']}. Kombi-Einstieg (30 % Weekly, 70 % Daily) möglich."))
                    else:
                        chk.append(('warn', 'Kein unmitigierter Daily-Orderblock innerhalb der Weekly-Zone: nach deiner Auswertung nicht einsteigen, bis einer entsteht (Daily-Bestätigung).'))
        if ob.get('zone'):
            f = fb.get(e['paar'] + '|' + e['richtung'] + '|' + '-'.join(str(x) for x in ob['zone']))
            if f: chk.append(('ok' if f['urteil'] == 'gut' else 'warn', 'Dein Urteil zu dieser Zone: ' + ('eigene Zone ' + str(f['eigene']) if f['urteil'] == 'eigen' else f['urteil']) + '.'))
        if ob.get('einstieg') is not None:
            f = lambda v: fmt(v, sym)
            e['einstieg'] = (f"Weekly-Teil: Limit am Zonenrand {f(ob['einstieg'])} (Zone {f(ob['zone'][0])} bis {f(ob['zone'][1])}, Qualität {ob['qualitaet']})." +
                             (f" Daily-Teil: Limit im Daily-Orderblock {f(ob['daily_ob'][0])} bis {f(ob['daily_ob'][1])} (Qualität {ob['daily_q']})." if ob.get('daily_ob') else ' Daily-Teil erst, wenn ein Daily-Orderblock in der Zone entsteht.'))
            e['stopp'] = f"{f(ob['stopp'])}, 10 % der Zonenhöhe jenseits des Zonenrands. Nicht nachziehen."
            e['ziel'] = f"Ziel 1: {f(ob['ziel1'])} (1 R), Ziel 2: {f(ob['ziel2'])} (2 R). Weekly-Teil zusätzlich laut Reiter KI Trades."
        ob['checks'] = [{'t': k, 'text': t} for k, t in chk]
        ob['status'] = 'ungültig' if any(k == 'bad' for k, _ in chk) else 'prüfen' if any(k == 'warn' for k, _ in chk) else 'valide'
        e['ob'] = ob
        if '_p' in e: ob['richtung'] = e['richtung']; e['_p']['ob'] = ob

    # ---------- Positionen ----------
    pr = []
    for t in live:
        sym = t['instrument']; d = t['dir']; ch = t.get('chart'); chk = []; z = {}
        chk += cot_check(sym, d)
        ev = events((sym[:3], sym[3:]))
        if ev: chk.append(('warn', 'Termine in den nächsten 5 Tagen: ' + ', '.join(ev[:4]) + '.'))
        fav = [p for p in A.get('paare', []) if p['paar'].replace('/', '') == sym]
        if fav:
            f = fav[0]; same = str(f['richtung']).lower() == d
            chk.append(('ok' if same else 'warn', f"Meine Einschätzung: {f['richtung']} mit Überzeugung {f['staerke']} von 10" + ('.' if same else ', also nicht in deiner Richtung.')))
        else:
            chk.append(('warn', 'Das Paar steht nicht auf meiner Favoritenliste, die Position hängt allein an deiner Zone.'))
        if 'AUD' in sym and aud > 2: chk.append(('warn', f'{aud} AUD-Positionen gleichzeitig, nach deiner Analyse sind mehr als 2 zu viel.'))
        if ch and ch.get('drs'):
            pos = [x for x in ch['drs'] if x['type'] == 'pos']; pos = pos[0] if pos else None
            rects = [x for x in ch['drs'] if x['type'] == 'rect']
            wk, src = load_candles(sym, 'W', trades); dl, srcd = load_candles(sym, 'D', trades)
            base = dl or wk
            if pos and rects:
                entry, sl = pos['entry'], pos['sl']; rect = min(rects, key=lambda r: abs(r['p0'] - entry)) if d == 'long' else min(rects, key=lambda r: abs(r['p1'] - entry))
                top, bot = max(rect['p0'], rect['p1']), min(rect['p0'], rect['p1'])
                z = {'zt': rect['t0'], 'zone': [bot, top], 'entry': round(entry, 5), 'sl': round(sl, 5), 'tp': round(pos['tp'], 5), 'ebene': pos.get('tf') or t.get('zone')}
                if base:
                    last = base[-1]; price = last[4]; kd = day(last[0])
                    chk.append(('ok', f'Kursstand {fmt(price, sym)} vom {dmy(kd)} (Quelle: {src or srcd}).'))
                    t0 = pos['t0']; after = [r for r in base if r[0] >= t0]
                    through = [r for r in after if (r[4] < sl if d == 'long' else r[4] > sl)]
                    touched = [r for r in after[1:] if (r[3] <= entry if d == 'long' else r[2] >= entry)]
                    if through: chk.append(('bad', f'Schlusskurs bereits jenseits des Stopps ({dmy(day(through[0][0]))}): Setup ist ungültig.'))
                    elif touched and t['status'] == 'limit': chk.append(('warn', f'Kurs hat den Limit-Preis seit {dmy(day(touched[0][0]))} erreicht, das Limit müsste ausgelöst sein. Status in der App prüfen.'))
                    else:
                        a = atr(base, len(base) - 1) * (1 if base is dl else 1); dist = abs(price - entry) / a
                        chk.append(('ok' if dist < 10 else 'warn', f'Kurs ist {dist:.1f} {"Tages" if base is dl else "Wochen"}-ATR vom Limit entfernt' + ('.' if dist < 10 else ', das Limit ist weit weg.')))
                    # Zone gegen Orderblock-Definition prüfen (Weekly)
                    zrows = wk or []
                    cand = [r for r in zrows if abs(r[2] - top) / max(top, 1e-9) < 0.0015 and abs(r[3] - bot) / max(bot, 1e-9) < 0.0015]
                    if zrows and cand:
                        i = zrows.index(cand[0]); o = [x for x in find_obs(zrows, d) if x['i'] == i]
                        if o: chk.append(('ok' if o[0]['q'] in 'AB' else 'warn', f"Zone entspricht einem Weekly-Orderblock der Qualität {o[0]['q']} (Bewegung {o[0]['disp_atr']} ATR, seither {o[0]['touches']} Berührungen)" + (', aber mitigiert.' if o[0]['mitigated'] else '.')))
                        else: chk.append(('warn', 'Die Zone ist eine einzelne Weekly-Kerze, erfüllt aber meine Orderblock-Definition nicht (keine Bewegung über 1 ATR mit Strukturbruch).'))
                    wks = (NOW.timestamp() * 1000 - t0) / 6.048e8
                    if wks > 8: chk.append(('warn', f'Das Setup ist {wks:.0f} Wochen alt, prüfe ob die Zone noch gilt.'))
            else:
                chk.append(('warn', 'Im Chart fehlt Position oder Zone, keine Zonenprüfung möglich.'))
        else:
            chk.append(('warn', 'Kein Chart-Tool-Eintrag mit Zone: Zonenprüfung und Kurslage nicht möglich. Zeichne Zone und Position im Chart-Tool, dann prüfe ich sie.'))
        st = 'ungültig' if any(k == 'bad' for k, _ in chk) else 'prüfen' if any(k == 'warn' for k, _ in chk) else 'valide'
        pr.append({'id': t['id'], 'paar': sym[:3] + '/' + sym[3:], 'richtung': d, 'status': st, 'art': 'Limit' if t['status'] == 'limit' else 'Läuft', 'zone': z, 'checks': [{'t': k, 'text': x} for k, x in chk]})
    # Persönliches (deine Positionen, Konflikte) nur ins private Repo, nie in die öffentliche ausblick.json
    stand = NOW.astimezone().strftime('%Y-%m-%dT%H:%M')
    PV = os.path.join(HOME, 'privat.json')
    try: pv = json.load(open(PV, encoding='utf-8'))
    except Exception: pv = {}
    kf = pv.get('konflikte', {})
    for e in A.get('empfehlungen', []):
        if e.get('konflikt'): kf[str(e.get('paar')) + '|' + str(e.get('richtung'))] = e['konflikt']
        e.pop('konflikt', None)
    A.pop('pruefung', None); A.pop('pruefung_stand', None)
    pv.update({'typ': 'privat', 'pruefung': pr, 'pruefung_stand': stand, 'konflikte': kf})
    json.dump(pv, open(PV, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(A, open(os.path.join(DATA, 'ausblick.json'), 'w'), ensure_ascii=False, indent=1)
    for p in pr: print(p['paar'], p['richtung'], p['art'], p['status'])
    for e in A.get('empfehlungen', []): print(e['paar'], e['ob']['status'], e['ob'].get('zone'), e['ob'].get('qualitaet'))


if __name__ == '__main__':
    main()

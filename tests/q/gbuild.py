import sys
src=open('/tmp/w/q/build.py').read()
head,loop=src.split("TESTS=[];SUMM=[]")
loop="TESTS=[];SUMM=[]"+loop
exec(head)
NEW=['donch','rsi2','rsi14','bb','inside','engulf','macd','pin','wkbreak','squeeze','cot']
NAMES.update(donch='Donchian-Ausbruch',rsi2='RSI(2)-Extrem',rsi14='RSI(14)-Umkehr',bb='Bollinger-Rückkehr',inside='Innenstab-Ausbruch',engulf='Engulfing am Trend-EMA',macd='MACD-Kreuzung gegen den Trend',pin='Pinbar nach Rücksetzer',wkbreak='Wochen-Ausbruch',squeeze='Squeeze-Ausbruch',cot='COT-Extrem mit Tages-Auslöser')
th=lambda P:'Wochentrend muss passen' if P.get('htf') else 'Wochentrend nicht gefiltert'
RULES.update(
donch=lambda P:[f"Signal: Tagesschluss über dem {P['n']}-Tage-Hoch (Long) bzw. unter dem Tief (Short), {th(P)}",f"Einstieg Eröffnung Folgetag, Stopp {P['k']} ATR, Ziel {P['tgt']} R, Ausstieg nach {P['maxd']} Tagen"],
rsi2=lambda P:[f"Signal: RSI(2) unter {P['th']} (Long) bzw. über {100-P['th']} (Short), {th(P)}",f"Einstieg Eröffnung Folgetag, Stopp {P['k']} ATR, Ziel {P['tgt']} R, Ausstieg nach {P['maxd']} Tagen"],
rsi14=lambda P:[f"Signal: RSI(14) steigt über {P['th']} zurück (Long) bzw. fällt unter {100-P['th']} (Short), {th(P)}",f"Einstieg Eröffnung Folgetag, Stopp {P['k']} ATR, Ziel {P['tgt']} R, Ausstieg nach {P['maxd']} Tagen"],
bb=lambda P:["Signal: Schluss kehrt in das Bollinger-Band (20, 2) zurück, nachdem der Vortag außerhalb schloss, "+th(P),f"Einstieg Eröffnung Folgetag, Stopp {P['k']} ATR, Ziel {P['tgt']} R, Ausstieg nach {P['maxd']} Tagen"],
inside=lambda P:["Signal: Innenstab (Hoch und Tief innerhalb der Vortageskerze), Richtung = Trend (EMA20 gegen EMA50), "+th(P),f"Einstieg Eröffnung Folgetag, Stopp {P['k']} ATR, Ziel {P['tgt']} R, Ausstieg nach {P['maxd']} Tagen"],
engulf=lambda P:[f"Signal: Engulfing-Kerze in Trendrichtung (EMA20 gegen EMA50), Tief/Hoch höchstens {P['near']} ATR von der EMA{P['ema']}, {th(P)}",f"Einstieg Eröffnung Folgetag, Stopp {P['k']} ATR, Ziel {P['tgt']} R, Ausstieg nach {P['maxd']} Tagen"],
macd=lambda P:["Signal: MACD kreuzt seine Signallinie nach oben unter Null (Long) bzw. nach unten über Null (Short), "+th(P),f"Einstieg Eröffnung Folgetag, Stopp {P['k']} ATR, Ziel {P['tgt']} R, Ausstieg nach {P['maxd']} Tagen"],
pin=lambda P:["Signal: Pinbar (Docht mindestens 60 % der Spanne) nach drei Kerzen gegen die Richtung, "+th(P),f"Einstieg Eröffnung Folgetag, Stopp {P['k']} ATR, Ziel {P['tgt']} R, Ausstieg nach {P['maxd']} Tagen"],
wkbreak=lambda P:["Signal: Tagesschluss über dem 5-Tage-Hoch (Long) bzw. unter dem 5-Tage-Tief (Short), "+th(P),f"Einstieg Eröffnung Folgetag, Stopp {P['k']} ATR, Ziel {P['tgt']} R, Ausstieg nach {P['maxd']} Tagen"],
squeeze=lambda P:["Signal: Bollinger-Band lag zuvor innerhalb des Keltner-Kanals, Schluss bricht das Band aus, "+th(P),f"Einstieg Eröffnung Folgetag, Stopp {P['k']} ATR, Ziel {P['tgt']} R, Ausstieg nach {P['maxd']} Tagen"],
cot=lambda P:[f"Signal: COT-Index (26 Wochen) der Basiswährung mindestens {P['th']} und der Quote höchstens {100-P['th']} (Long, gespiegelt für Short), Tagesschluss über dem Vortageshoch bzw. unter dem Vortagestief, "+th(P),f"Einstieg Eröffnung Folgetag, Stopp {P['k']} ATR, Ziel {P['tgt']} R, Ausstieg nach {P['maxd']} Tagen"])
loop=loop.replace("for fam in ('mr','trend','fib','sweep'):","for fam in NEW:")
exec(loop)
j=json.load(open('/home/claude/journal-privat/strategietests.json'))
ids={t['id'] for t in TESTS}
j['tests']=[t for t in j['tests'] if t['id'] not in ids]+TESTS
j['stand']=datetime.datetime.now().strftime('%Y-%m-%dT%H:%M')
json.dump(j,open('/home/claude/journal-privat/strategietests.json','w'),ensure_ascii=False,indent=1)
print(len(j['tests']))
for fam,P,s,rb,p,passed,npar in SUMM: print(fam,passed,f"n{s['n']} wr{s['wr']:.1f} avg{s['avg']:.3f} p{p:.3f}")

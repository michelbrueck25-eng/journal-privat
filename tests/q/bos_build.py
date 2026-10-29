import sys,pickle,json,datetime,collections
src=open('/tmp/w/q/build.py').read().split("TESTS=[];SUMM=[]")[0]
exec(src)
NAMES['bos']='Doppelter Bruch mit Retest'
RULES['bos']=lambda P:[f"Struktur: Fraktal-Swings mit {P['n']} Kerzen links und rechts, ein Swing gilt erst nach {P['n']} Kerzen als bekannt",f"Erster Bruch: Tagesschluss über dem letzten bestätigten Swing-Hoch (Long) bzw. unter dem Swing-Tief (Short), zweiter Bruch in derselben Richtung innerhalb von {P['gap']} Tagen an einem höheren (tieferen) Swing, Wochentrend {'muss passen' if P['htf'] else 'nicht gefiltert'}",f"Einstieg: Limit am Niveau des zweiten Bruchs (Retest), Auftrag gilt {P['wait']} Tage, wird verworfen, wenn der Schluss den Stopp erreicht",f"Stopp hinter dem Pullback-Extrem zwischen den Brüchen plus 0,1 ATR (max. {P['cap']} ATR), Ziel {P['tgt']} R, Ausstieg nach {P['maxd']} Tagen"]
res=pickle.load(open('res_bos.pkl','rb'))
big=[r for r in res if r[1]['n']>=300]
(P,s,trs)=max(big,key=lambda r:r[1]['avg'])
rb=randbase('bos',dict(P,k=1.5),min(s['n'],1000)); p=float((rb>=s['avg']).mean())
tid='lab-bos'; dd=[dict(sym=x[0],date=x[1],r=x[3],days=x[4]) for x in sorted(trs,key=lambda x:x[1])]
def grp(keyf):
    g=collections.defaultdict(list)
    for x in dd: g[keyf(x)].append(x['r'])
    rows=[]
    for k,v in sorted(g.items()):
        v=np.array(v); w=(v>0).sum(); l=v[v<=0]; pf=v[v>0].sum()/abs(l.sum()) if len(l) and l.sum()!=0 else 0
        rows.append([k,len(v),fmt(v.mean()),f"{round(100*w/len(v))} %",fmt(pf)])
    return rows
cols=['Gruppe','Trades','Ø R','Trefferquote','Profitfaktor']
meta=render('bos',trs,P,tid)
eq=list(np.round(np.cumsum([x['r'] for x in dd]),2)); eq=eq[::max(1,len(eq)//300)]
best_any=max(res,key=lambda r:r[1]['avg'])
now=datetime.datetime.now().strftime('%Y-%m-%dT%H:%M')
T=dict(id='smvtd2t9z',name='Überprüfe, dass ein Bruch im daily und dann noch einer (doppelter Strukturbruch mit Retest)',status='fertig',geprueft=now,
 zeitraum=f"{ds(U['EURUSD'],0)} bis {ds(U['EURUSD'],len(U['EURUSD']['c'])-1)}",daten="11 Paare, je 3000 Tageskerzen (rund 11 Jahre), Wochenkerzen für den Trend",
 zusammenfassung=(f"Doppelter Daily-Strukturbruch mit Retest-Einstieg: Kein Vorteil nachweisbar. Von 144 getesteten Varianten erfüllt keine 50+ % Trefferquote bei mindestens 300 Trades. Beste Variante mit mindestens 300 Trades: {s['n']} Trades, Trefferquote {fmt(s['wr'],1)} %, Ø {fmt(s['avg'],3)} R nach Spread, 95-%-Intervall {fmt(s['lo'],3)} bis {fmt(s['hi'],3)}, nur {s['ypos']} von {s['ylen']} Jahren positiv. Das ist statistisch von null nicht zu unterscheiden. "
  f"Die Varianten mit leicht positivem Ø R (bis +{fmt(best_any[1]['avg'],3)} R) haben nur {best_any[1]['n']} Trades und ein Intervall von {fmt(best_any[1]['lo'],2)} bis {fmt(best_any[1]['hi'],2)}, also nicht belastbar. Ziel 1 bis 2 R bei 50+ % ist damit nicht erreicht."),
 urteil=(f"{len(res)} Konfigurationen (Fraktal 2, 3 oder 5, Wochentrend, Abstand der Brüche, Wartezeit, Ziel 1,0 bis 2,0 R, Haltedauer 10 oder 20 Tage). Mit mindestens 300 Trades liegt die beste bei Ø {fmt(s['avg'],3)} R und {fmt(s['wr'],1)} % Trefferquote, die Zufallsbasis bei Ø {fmt(rb.mean(),3)} R. Das Muster tritt selten auf (zwischen 81 und 590 Trades in 11 Jahren auf 11 Paaren). Im Vergleich dazu hatte Mean Reversion Ø +0,10 R bei 55,6 %."),
 kennzahlen=[{"label":"Trades (beste mit 300+)","wert":str(s['n'])},{"label":"Trefferquote","wert":fmt(s['wr'],1)+' %'},{"label":"Ø R nach Spread","wert":fmt(s['avg'],3)},{"label":"95-%-Intervall Ø R","wert":f"{fmt(s['lo'],3)} bis {fmt(s['hi'],3)}"},{"label":"Profitfaktor","wert":fmt(s['pf'])},{"label":"Max-Drawdown","wert":fmt(s['dd'],0)+' R'},{"label":"Jahre mit Gewinn","wert":f"{s['ypos']} von {s['ylen']}"},{"label":"Zufallsbasis Ø R","wert":fmt(rb.mean(),3)},{"label":"Getestete Varianten","wert":str(len(res))}],
 equity=[float(x) for x in eq],equityHinweis=f"Kumulierte R, {s['n']} Trades nach Datum.",
 tabellen=[{"titel":"Je Jahr","spalten":cols,"zeilen":grp(lambda x:x['date'][:4])},{"titel":"Je Paar","spalten":cols,"zeilen":grp(lambda x:x['sym'])}],
 regeln=RULES['bos'](P),
 annahmen=["Deine Beschreibung ist knapp, ich habe sie so gelesen: erster Strukturbruch, zweiter Bruch in dieselbe Richtung, Einstieg am Retest des letzten Bruchs, Stopp hinter dem Pullback-Extrem, Ziel 1 bis 2 R","Strukturbruch als Tagesschluss über dem letzten bestätigten Fraktal-Hoch bzw. unter dem -Tief","Spread 1 Pip, Stopp zuerst bei gleicher Kerze, Stopp auch in der Einstiegskerze geprüft"],
 schwaechen=["Die Regel-Deutung ist meine Annahme: bitte sag mir, wenn du den Bruch anders definierst (z. B. Hoch-Tief-Folge statt Fraktal, 4H statt Daily)","Nur 11 Paare, Tageskerzen","Bei den Konfigurationen mit 300+ Trades sind die Ergebnisse knapp unter null, die kleinen Stichproben knapp darüber"],
 naechste="Wenn du mir sagst, wie du den Bruch genau erkennst (Kerzenschluss oder Docht, welcher Swing), teste ich die exakte Definition. Danach auf allen 34 Instrumenten und mit 4H-Retest wiederholen.",bilder=meta,params=P)
j=json.load(open('/home/claude/journal-privat/strategietests.json'))
j['tests']=[t for t in j['tests'] if t['id']!='smvtd2t9z']+[T]; j['stand']=now
json.dump(j,open('/home/claude/journal-privat/strategietests.json','w'),ensure_ascii=False,indent=1)
print(P,s['n'],round(s['avg'],3),len(meta))

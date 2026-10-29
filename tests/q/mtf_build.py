import sys,pickle,json,datetime,collections
sys.path.insert(0,'/tmp/w/q')
import mtf
from mtf import *
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
allr=pickle.load(open('res_mtf.pkl','rb'))
f2=lambda x,n=2:f"{x:.{n}f}".replace('.',',')
NM={'s1':'Weekly-Trend, Daily-Pullback, 4H-Bruch','s2':'Daily-Extrem in Weekly-Richtung, 4H-Umkehr','s4':'Dreifach-Trend, 4H-EMA-Rücksetzer'}
def best(fam):
    c=[r for r in allr if r[0]==fam and r[2][2] and r[2][0]['n']>=100]
    return max(c,key=lambda r:r[2][0]['avg']) if c else None
def ds(h,k): return datetime.datetime.utcfromtimestamp(h['t'][k]/1000).strftime('%d.%m.%y')
def render(trs,P,tid,title):
    trs=sorted(trs,key=lambda x:x[1]); step=max(1,len(trs)//50); pk=trs[::step][:50]; meta=[]
    for n,(sym,date,L,r,days,out,i,j,px,risk) in enumerate(pk,1):
        h=H4[sym]; j0=max(0,i-45); j1=min(len(h['c']),j+8)
        fig,ax=plt.subplots(figsize=(7.2,4.0),dpi=80)
        for k in range(j0,j1):
            o,hh,l,c=h['o'][k],h['h'][k],h['l'][k],h['c'][k]; col='#2a9d6f' if c>=o else '#d1495b'
            ax.plot([k,k],[l,hh],color=col,lw=0.8); ax.add_patch(Rectangle((k-0.35,min(o,c)),0.7,max(abs(c-o),1e-9),color=col))
        if out=='SL': stop=px; entry=(stop+risk) if L else (stop-risk); tp=(entry+P['tgt']*risk) if L else (entry-P['tgt']*risk)
        elif out=='TP': tp=px; entry=(tp-P['tgt']*risk) if L else (tp+P['tgt']*risk); stop=(entry-risk) if L else (entry+risk)
        else: entry=None
        if entry is not None:
            ax.axhline(entry,color='#333',lw=0.8); ax.axhline(stop,color='#d1495b',lw=0.9,ls='--'); ax.axhline(tp,color='#2a9d6f',lw=0.9,ls='--')
        ax.axvline(i,color='#888',lw=0.6,ls=':'); ax.plot([j],[px],marker='o',color='k',ms=5)
        ax.set_xticks([j0,i]); ax.set_xticklabels([ds(h,j0),'Einstieg '+ds(h,i)],fontsize=7); ax.tick_params(axis='y',labelsize=7); ax.set_xlim(j0-1,j1+1)
        ax.set_title(f"{sym} {'Long' if L else 'Short'} · 4H · {out} · {r:+.2f} R",fontsize=9)
        for s_ in ('top','right'): ax.spines[s_].set_visible(False)
        fig.tight_layout(); fn=f'strategiebilder/{tid}_{n:02d}.jpg'
        fig.savefig('/home/claude/journal-privat/'+fn,format='jpg',pil_kwargs={'quality':75}); plt.close(fig)
        meta.append(dict(pfad=fn,titel=f"{sym} {'Long' if L else 'Short'} {ds(h,i)}",ergebnis=f"{out} {r:+.2f} R",r=round(float(r),2)))
    return meta
rows=[];B={}
for fam in ('s1','s2','s4'):
    b=best(fam)
    if not b: rows.append([NM[fam],'zu wenige Trades (unter 100)','','','','','']); continue
    B[fam]=b; _,P,(a,tr,te,cut),_t=b
    rows.append([NM[fam],a['n'],f"{f2(a['wr'],0)} %",f2(a['avg']),f"{f2(tr['avg'])} ({f2(tr['wr'],0)} %)",f"{f2(te['avg'])} ({f2(te['wr'],0)} %)",cut])
cols=['Entwurf (beste Konfiguration nach Ø R, 100+ Trades)','Trades','Trefferquote','Ø R gesamt','Entwicklung Ø R (Quote)','Prüfung Ø R (Quote)','Trennung ab']
fam='s2'; _,P,(a,tr,te,cut),trs=B[fam]
meta=render(trs,P,'lab-mtf',NM[fam])
dd=sorted(trs,key=lambda x:x[1]); eq=[round(float(x),2) for x in np.cumsum([x[3] for x in dd])]
def grp(keyf):
    g=collections.defaultdict(list)
    for x in trs: g[keyf(x)].append(x[3])
    out=[]
    for k,v in sorted(g.items()):
        v=np.array(v); w=(v>0).sum(); l=v[v<=0]; pf=v[v>0].sum()/abs(l.sum()) if len(l) and l.sum()!=0 else 0
        out.append([k,len(v),f2(v.mean()),f"{round(100*w/len(v))} %",f2(pf)])
    return out
ccols=['Gruppe','Trades','Ø R','Trefferquote','Profitfaktor']
now=datetime.datetime.now().strftime('%Y-%m-%dT%H:%M')
zus=(f"Ziel: Ø 0,3 bis 0,5 R bei mindestens 50 % Trefferquote auf 4H bis Weekly. Ergebnis: nicht erreicht. Ich habe drei Mehrzeitebenen-Entwürfe mit 108 Parameter-Varianten auf 8 Paaren und 19 Monaten 4H-Daten getestet. Der beste Entwurf in der Entwicklung (Daily-Extrem von 2,0 ATR, Weekly-Richtung egal, 4H-Umkehrkerze als Auslöser, Ziel 2 R) kam dort auf Ø {f2(tr['avg'])} R, fiel in der Prüfung aber auf Ø {f2(te['avg'])} R bei {f2(te['wr'],0)} % Trefferquote. Das ist die typische Überanpassung: Was in der Entwicklung nach Ziel aussah, hält in der Prüfung nicht. "
 f"Einzig stabil mit über 50 % Trefferquote ist der Dreifach-Trend-Rücksetzer (727 bis 757 Trades), aber mit Ø 0,01 R, also ohne Vorteil. Die Daten reichen nicht, um eine Strategie mit 0,3 bis 0,5 R zu belegen: 19 Monate und 8 Paare ergeben bei strengen Regeln nur 100 bis 300 Trades.")
T=dict(id='lab-mtf',name='Entwurf: Weekly bis 4H (Mehrzeitebenen) auf 0,3 bis 0,5 R',status='fertig',geprueft=now,zeitraum='4H seit 31.03.2025 bis 29.10.2026, Daily und Weekly davor',
 daten='8 Paare mit 4H-Kerzen (AUDCAD, AUDJPY, EURCHF, EURUSD, GBPCAD, GBPCHF, NZDJPY, USDJPY), je 3000 4H-Kerzen, dazu Tages- und Wochenkerzen',
 zusammenfassung=zus,urteil=f"108 Varianten in 3 Entwürfen. Das Ziel (Ø 0,3 bis 0,5 R, 50 %+) wird in der Prüfung von keinem Entwurf gehalten. Bester Entwurf: {a['n']} Trades, Entwicklung Ø {f2(tr['avg'])} R, Prüfung Ø {f2(te['avg'])} R.",
 kennzahlen=[{"label":"Trades (bester Entwurf)","wert":str(a['n'])},{"label":"Trefferquote gesamt","wert":f2(a['wr'],0)+' %'},{"label":"Ø R gesamt","wert":f2(a['avg'])},{"label":"Entwicklung","wert":f"{f2(tr['avg'])} R, {f2(tr['wr'],0)} %","hinweis":f"{tr['n']} Trades"},{"label":"Prüfung","wert":f"{f2(te['avg'])} R, {f2(te['wr'],0)} %","hinweis":f"{te['n']} Trades"},{"label":"Getestete Varianten","wert":"108"}],
 equity=eq[::max(1,len(eq)//300)],equityHinweis=f"Kumulierte R, bester Entwurf, {a['n']} Trades nach Datum.",
 tabellen=[{"titel":"Die drei Entwürfe","spalten":cols,"zeilen":rows},{"titel":"Bester Entwurf: je Paar","spalten":ccols,"zeilen":grp(lambda x:x[0])},{"titel":"Bester Entwurf: je Monat","spalten":ccols,"zeilen":grp(lambda x:x[1][:7])}],
 regeln=["Entwurf 1: Wochentrend (Schluss gegen SMA20), Daily-Pullback nahe der EMA50, 4H-Schluss über dem letzten 4H-Swing-Hoch (Long) bzw. unter dem Tief (Short), Stopp hinter dem Pullback-Extrem","Entwurf 2: Daily-Schluss mindestens z ATR unter bzw. über dem 20-Tage-Durchschnitt, optional in Wochenrichtung, 4H-Umkehrkerze (Schluss über dem Vor-Hoch nach einer roten Kerze) als Auslöser, Stopp hinter den letzten drei 4H-Kerzen","Entwurf 4: Wochen-, Daily- und 4H-Trend im Gleichklang (EMA20 gegen EMA50), Limit am 4H-EMA-Rücksetzer, Stopp 1 bis 2 ATR","Eine Position je Paar gleichzeitig, Ziel 1,0 bis 2,0 R, Ausstieg nach 30 oder 60 4H-Kerzen"],
 annahmen=["Spread 1 Pip, Stopp zuerst bei gleicher Kerze, Stopp auch in der Einstiegskerze geprüft","Daily- und Wochen-Informationen nur aus abgeschlossenen Kerzen vor der 4H-Kerze","Entwicklung = erste 60 % der Trades nach Datum, Prüfung = letzte 40 %"],
 schwaechen=["Nur 19 Monate 4H-Daten und 8 Paare: strenge Regeln ergeben wenige Trades","108 Varianten: gute Entwicklungs-Ergebnisse sind oft Zufall","Kein Entwurf hält 0,3 bis 0,5 R in der Prüfung"],
 naechste="4H-Kerzen für alle 34 Instrumente laden (Marktdaten senden in der App), dann dieselben Entwürfe auf 28 Paaren testen und mit der Daily-Mean-Reversion (Ø +0,10 R bei 55,6 %) als Vergleich kombinieren.",bilder=meta,params=P)
j=json.load(open('/home/claude/journal-privat/strategietests.json'))
j['tests']=[t for t in j['tests'] if t['id']!='lab-mtf']+[T]; j['stand']=now
json.dump(j,open('/home/claude/journal-privat/strategietests.json','w'),ensure_ascii=False,indent=1)
print(P,a['n'],tr['avg'],te['avg'],len(meta))

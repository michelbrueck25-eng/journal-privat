import sys,pickle,json,random,datetime
sys.path.insert(0,'/tmp/w/q')
from fam import *
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
NAMES={'trend':'Trend-Rücksetzer an der EMA','fib':'Fibonacci-Rücksetzer','sweep':'Vortag-Sweep','mr':'Mean Reversion (Abstand zum Durchschnitt)'}
RULES={
'trend':lambda P:[f"Trend: EMA20 über EMA50 (Long) bzw. darunter (Short), Wochentrend {'muss passen (Schluss gegen SMA20)' if P['htf'] else 'wird nicht gefiltert'}",f"Einstieg: Limit an der EMA{P['ema']} vom Vortag, Berührung am Signaltag",f"Stopp {P['k']} ATR vom Einstieg, Ziel {P['tgt']} R, Ausstieg nach {P['maxd']} Tagen"],
'fib':lambda P:[f"Swing per Fraktal (5 Kerzen links und rechts), Bein mindestens {P['leg']} ATR, Swing erst 5 Kerzen später bekannt",f"Einstieg: Limit bei {P['fib']*100:.1f} % Rücksetzer, bis 10 Kerzen warten, Wochentrend {'muss passen' if P['htf'] else 'nicht gefiltert'}",f"Stopp 0,2 ATR hinter dem Swing-Ursprung, Ziel {P['tgt']} R, Ausstieg nach {P['maxd']} Tagen"],
'sweep':lambda P:[f"Signal: Tageskerze durchbricht das {P['look']}-Tage-Tief (Long) bzw. -Hoch (Short) und schließt wieder in der Spanne",f"Einstieg zur Eröffnung der Folgekerze, Stopp hinter dem Kerzenextrem plus 0,1 ATR (max. {P['cap']} ATR), Wochentrend {'muss passen' if P['htf'] else 'nicht gefiltert'}",f"Ziel {P['tgt']} R, Ausstieg nach {P['maxd']} Tagen"],
'mr':lambda P:[f"Signal: Schlusskurs mindestens {P['z']} ATR unter (Long) bzw. über (Short) dem 20-Tage-Durchschnitt, Wochentrend {'muss passen' if P['htf'] else 'nicht gefiltert'}",f"Einstieg zur Eröffnung der Folgekerze, Stopp {P['k']} ATR, Ziel {P['tgt']} R, Ausstieg nach {P['maxd']} Tagen"]}
def pick(fam,res):
    ok=[r for r in res if r[1]['wr']>=50 and r[1]['n']>=300 and r[1]['lo']>0]
    pool=ok or [r for r in res if r[1]['n']>=100]
    return (max(pool,key=lambda r:r[1]['avg']), bool(ok))
def randbase(fam,P,n,runs=200):
    fn=None; rng=np.random.default_rng(5); syms=list(U); out=[]
    for _ in range(runs):
        rs=[]
        for _k in range(n):
            sym=syms[rng.integers(len(syms))]; d=U[sym]; i=int(rng.integers(60,len(d['c'])-12)); L=bool(rng.integers(2)); a=d['atr'][i]
            if np.isnan(a): continue
            entry=d['o'][i+1]; k=P.get('k',1.5)
            stop=entry-k*a if L else entry+k*a
            r=simulate(d,i+1,L,entry,stop,P['tgt'],P['maxd'],sym)
            if r: rs.append(r[0])
        out.append(float(np.mean(rs)))
    return np.array(out)
def ds(d,k): return datetime.datetime.utcfromtimestamp(d['t'][k]/1000).strftime('%d.%m.%y')
def render(fam,trs,P,tid):
    random.seed(3); trs=sorted(trs,key=lambda x:x[1]); step=max(1,len(trs)//50); pick_=trs[::step][:50]; meta=[]
    for n,(sym,date,L,r,days,out,i,j,px,risk) in enumerate(pick_,1):
        d=U[sym]; j0=max(0,i-40); j1=min(len(d['c']),j+6)
        fig,ax=plt.subplots(figsize=(7.2,4.0),dpi=80)
        for k in range(j0,j1):
            o,h,l,c=d['o'][k],d['h'][k],d['l'][k],d['c'][k]; col='#2a9d6f' if c>=o else '#d1495b'
            ax.plot([k,k],[l,h],color=col,lw=0.9); ax.add_patch(Rectangle((k-0.32,min(o,c)),0.64,max(abs(c-o),1e-9),color=col))
        ent=px if False else None
        # Einstieg und Stopp/Ziel rekonstruieren
        if out=='SL': stop=px; entry=(stop+risk) if L else (stop-risk); tp=(entry+P['tgt']*risk) if L else (entry-P['tgt']*risk)
        elif out=='TP': tp=px; entry=(tp-P['tgt']*risk) if L else (tp+P['tgt']*risk); stop=(entry-risk) if L else (entry+risk)
        else:
            entry=None
        if entry is not None:
            ax.axhline(entry,color='#333',lw=0.8); ax.axhline(stop,color='#d1495b',lw=0.9,ls='--'); ax.axhline(tp,color='#2a9d6f',lw=0.9,ls='--')
        if fam in('trend',):
            key=d['e20'] if P['ema']==20 else d['e50']; ax.plot(range(j0,j1),key[j0:j1],color='#4c78a8',lw=1)
        ax.axvline(i,color='#888',lw=0.6,ls=':'); ax.plot([j],[px],marker='o',color='k',ms=5)
        ax.set_xticks([j0,i]); ax.set_xticklabels([ds(d,j0),'Einstiegskerze '+ds(d,i)],fontsize=7); ax.tick_params(axis='y',labelsize=7); ax.set_xlim(j0-1,j1+1)
        ax.set_title(f"{sym} {'Long' if L else 'Short'} · {NAMES[fam].split(' (')[0]} · {out} · {r:+.2f} R",fontsize=9)
        for s_ in ('top','right'): ax.spines[s_].set_visible(False)
        fig.tight_layout(); fn=f'strategiebilder/{tid}_{n:02d}.jpg'
        fig.savefig('/home/claude/journal-privat/'+fn,format='jpg',pil_kwargs={'quality':75}); plt.close(fig)
        meta.append(dict(pfad=fn,titel=f"{sym} {'Long' if L else 'Short'} {ds(d,i)}",ergebnis=f"{out} {r:+.2f} R",r=round(float(r),2)))
    return meta
def fmt(x,n=2): return f"{x:.{n}f}".replace('.',',')
TESTS=[];SUMM=[]
for fam in ('mr','trend','fib','sweep'):
    res=pickle.load(open(f'res_{fam}.pkl','rb')); (P,s,trs),passed=pick(fam,res)
    rb=randbase(fam,P,min(s['n'],1500)); p=float((rb>=s['avg']).mean())
    tid='lab-'+fam; dd=[dict(sym=x[0],date=x[1],r=x[3],days=x[4]) for x in sorted(trs,key=lambda x:x[1])]
    import collections
    def grp(keyf):
        g=collections.defaultdict(list)
        for x in dd: g[keyf(x)].append(x['r'])
        rows=[]
        for k,v in sorted(g.items()):
            v=np.array(v); w=(v>0).sum(); l=v[v<=0]; pf=v[v>0].sum()/abs(l.sum()) if len(l) and l.sum()!=0 else 0
            rows.append([k,len(v),fmt(v.mean()),f"{round(100*w/len(v))} %",fmt(pf)])
        return rows
    cols=['Gruppe','Trades','Ø R','Trefferquote','Profitfaktor']
    meta=render(fam,trs,P,tid)
    eq=list(np.round(np.cumsum([x['r'] for x in dd]),2)); eq=eq[::max(1,len(eq)//300)]
    npar=len(res)
    urteil=(f"Beste Konfiguration von {npar} getesteten: {s['n']} Trades, Trefferquote {fmt(s['wr'],1)} %, Ø {fmt(s['avg'],3)} R nach Spread, Profitfaktor {fmt(s['pf'])}, 95-%-Intervall für Ø R [{fmt(s['lo'],3)}; {fmt(s['hi'],3)}], {s['ypos']} von {s['ylen']} Jahren positiv. "
      f"Zufalls-Einstiege mit gleichem Stopp und Ziel kommen im Schnitt auf Ø {fmt(rb.mean(),3)} R (p = {fmt(p,3)}). "
      +("Bedingung 50+ % und positives Intervall erfüllt, der Vorteil pro Trade ist aber klein." if passed else "Die Bedingung (50+ % Trefferquote, Intervall über null, mindestens 300 Trades) erfüllt keine Konfiguration dieser Familie."))
    T=dict(id=tid,name='Test: '+NAMES[fam],status='fertig',geprueft=datetime.datetime.now().strftime('%Y-%m-%dT%H:%M'),
      zeitraum=f"{ds(U['EURUSD'],0)} bis {ds(U['EURUSD'],len(U['EURUSD']['c'])-1)}",daten="11 Paare (AUDCAD, AUDJPY, AUDNZD, AUDUSD, EURCHF, EURGBP, EURUSD, GBPCAD, GBPCHF, NZDJPY, USDJPY), je 3000 Tageskerzen, Wochenkerzen für den Trend",
      urteil=urteil,kennzahlen=[{"label":"Trades","wert":str(s['n'])},{"label":"Trefferquote","wert":fmt(s['wr'],1)+' %'},{"label":"Ø R nach Spread","wert":fmt(s['avg'],3)},{"label":"95-%-Intervall Ø R","wert":f"{fmt(s['lo'],3)} bis {fmt(s['hi'],3)}"},{"label":"Profitfaktor","wert":fmt(s['pf'])},{"label":"Max-Drawdown","wert":fmt(s['dd'],0)+' R'},{"label":"Längste Verlustserie","wert":str(s['ms'])},{"label":"Ø Haltedauer","wert":fmt(s['tage'],1)+' Tage'},{"label":"Jahre mit Gewinn","wert":f"{s['ypos']} von {s['ylen']}"},{"label":"Zufallsbasis Ø R","wert":fmt(rb.mean(),3),"hinweis":f"p = {fmt(p,3)}"}],
      equity=[float(x) for x in eq],equityHinweis=f"Kumulierte R, {s['n']} Trades nach Datum.",
      tabellen=[{"titel":"Je Jahr","spalten":cols,"zeilen":grp(lambda x:x['date'][:4])},{"titel":"Je Paar","spalten":cols,"zeilen":grp(lambda x:x['sym'])}],
      regeln=RULES[fam](P),annahmen=["Spread 1 Pip je Trade, Stopp zuerst bei gleicher Kerze, Stopp wird auch in der Einstiegskerze geprüft","Signale nur mit Daten bis zur Signalkerze, Einstieg danach","Letzte, noch laufende Tageskerze nicht verwendet",f"{npar} Konfigurationen in dieser Familie getestet, Zufallstreffer möglich"],
      schwaechen=["Nur 11 Paare, die übrigen Instrumente kommen nach der Datenübertragung","Auswahl der besten Konfiguration ist in der Stichprobe optimiert, kein echter Prüfzeitraum","Nur Tageskerzen, keine 4H/1H"],
      naechste="Nach Eingang aller 34 Instrumente wiederholen und eine Out-of-Sample-Periode (letzte 2 Jahre) abtrennen.",bilder=meta,params=P)
    TESTS.append(T); SUMM.append((fam,P,s,rb,p,passed,npar))
pickle.dump((TESTS,SUMM),open('built.pkl','wb'))
for fam,P,s,rb,p,passed,npar in SUMM: print(fam,passed,P,f"n{s['n']} wr{s['wr']:.1f} avg{s['avg']:.3f} CI[{s['lo']:.3f},{s['hi']:.3f}] rand{rb.mean():.3f} p{p:.3f}")

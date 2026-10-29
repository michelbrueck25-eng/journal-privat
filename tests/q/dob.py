"""Daily-Orderblock-Test: Zonen aus Tageskerzen (Regeln wie ob_check.find_obs, ohne Berührungszähler), Varianten A/B/C, alle Instrumente in marktdaten/.
Aufruf: python3 dob.py  -> schreibt Test 'lab-dailyob' in strategietests.json (privat) und die Bilder."""
import sys,json,datetime,collections,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import eng
from eng import *
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
PIPS={'GOLD':0.1,'SILBER':0.01,'PLATIN':1.0,'KUPFER':0.002,'OEL':0.03,'ERDGAS':0.003}
eng.pip=lambda s: PIPS.get(s,0.01 if s.endswith('JPY') else 0.0001)
U=load_all(); A={s:atr(U[s]) for s in U}
def load4(sym):
    f=f'{HOME}/marktdaten/{sym}_4H.json'
    if not os.path.exists(f): return None
    r=np.array(json.load(open(f))['rows'],float)
    return dict(t=r[:,0],o=r[:,1],h=r[:,2],l=r[:,3],c=r[:,4])
U4={s:load4(s) for s in U}
SPLIT=datetime.datetime(2024,10,29).timestamp()*1000
def zones(sym):
    d=U[sym]; n=len(d['c']); out=[]
    for i in range(9,n-3):
        a=A[sym][i]
        if np.isnan(a): continue
        o,h,l,c=d['o'][i],d['h'][i],d['l'][i],d['c'][i]; doji=abs(c-o)<=0.3*(h-l)
        for L in (True,False):
            if L:
                if not (c<o or doji): continue
                ref=d['h'][i-8:i].max(); disp=d['h'][i+1:i+4].max()-h
                bos=(d['c'][i+1:i+4]>ref).any() and (d['c'][i+1:i+4]>h).any()
            else:
                if not (c>o or doji): continue
                ref=d['l'][i-8:i].min(); disp=l-d['l'][i+1:i+4].min()
                bos=(d['c'][i+1:i+4]<ref).any() and (d['c'][i+1:i+4]<l).any()
            if disp<1.0*a or not bos: continue
            q='A' if disp>=2*a else 'B' if disp>=1.2*a else 'C'
            # erster Berührungstag ab i+4, Zone verfaellt bei Schluss jenseits oder nach 60 Kerzen
            t0=None
            for k in range(i+4,min(n,i+64)):
                if (d['c'][k]<l) if L else (d['c'][k]>h): break
                if d['l'][k]<=h and d['h'][k]>=l: t0=k; break
            if t0 is None: continue
            out.append(dict(sym=sym,L=L,lo=l,hi=h,q=q,i=i,t0=t0,a=A[sym][t0-1]))
    return out
Z=[z for s in U for z in zones(s)]
def tr(z,r,i0,j,entry,stop,tg,why,tf='D'):
    return dict(r=r,date=datetime.datetime.utcfromtimestamp((U[z['sym']]['t'][z['t0']])/1000).strftime('%Y-%m-%d'),sym=z['sym'],dir='long' if z['L'] else 'short',days=j-i0,why=why,z=z,i0=i0,j=j,entry=entry,stop=stop,tg=tg,tf=tf,q=z['q'],ts=U[z['sym']]['t'][z['t0']])
def runA(tg,md=10):
    out=[]
    for z in Z:
        d=U[z['sym']]; L=z['L']; k=z['t0']
        if np.isnan(z['a']): continue
        if (d['o'][k]<z['lo']) if L else (d['o'][k]>z['hi']): continue
        entry=z['hi'] if L else z['lo']; stop=z['lo']-0.1*z['a'] if L else z['hi']+0.1*z['a']
        r=simulate(d,k,L,entry,stop,tg,md,z['sym'])
        if r: out.append(tr(z,r[0],k,k+r[1],entry,stop,tg,r[2]))
    return out
def runB(tg,md=10):
    out=[]
    for z in Z:
        d=U[z['sym']]; L=z['L']; k=z['t0']
        if k+1>=len(d['c']) or np.isnan(z['a']): continue
        if not ((d['c'][k]>z['hi']) if L else (d['c'][k]<z['lo'])): continue
        entry=d['o'][k+1]; stop=(min(z['lo'],d['l'][k])-0.1*z['a']) if L else (max(z['hi'],d['h'][k])+0.1*z['a'])
        risk=abs(entry-stop)
        if risk<=0 or risk>3*z['a'] or ((entry<=stop) if L else (entry>=stop)): continue
        r=simulate(d,k+1,L,entry,stop,tg,md,z['sym'])
        if r: out.append(tr(z,r[0],k+1,k+1+r[1],entry,stop,tg,r[2]))
    return out
def runC(tg,md=60):
    out=[]
    for z in Z:
        s=z['sym']; d4=U4.get(s)
        if d4 is None or np.isnan(z['a']): continue
        d=U[s]; L=z['L']; ts=d['t'][z['t0']]; te=ts+3*86400e3
        ix=np.where((d4['t']>=ts)&(d4['t']<te))[0]
        if len(ix)==0: continue
        touched=False; low=1e9; high=-1e9
        for b in ix:
            if d4['l'][b]<=z['hi'] and d4['h'][b]>=z['lo']: touched=True
            if not touched: continue
            low=min(low,d4['l'][b]); high=max(high,d4['h'][b])
            if (d4['c'][b]<z['lo']) if L else (d4['c'][b]>z['hi']): break
            if (d4['c'][b]>z['hi']) if L else (d4['c'][b]<z['lo']):
                entry=d4['c'][b]; stop=(min(z['lo'],low)-0.1*z['a']) if L else (max(z['hi'],high)+0.1*z['a'])
                risk=abs(entry-stop)
                if risk<=0 or risk>3*z['a']: break
                r=simulate(d4,b,L,entry,stop,tg,md,s,check_entry_bar=False)
                if r:
                    t=tr(z,r[0],b,b+r[1],entry,stop,tg,r[2],tf='4H'); t['days']=r[1]/6; out.append(t)
                break
    return out
def f(x,n=2): return f"{x:.{n}f}".replace('.',',')
NAME={'A':'A: Einstieg an der Zonenkante (Limit, erste Berührung)','B':'B: Daily-Bestätigung (Tagesschluss aus der Zone, Einstieg zur Eröffnung)','C':'C: 4H-Bestätigung (4H-Schluss aus der Zone)'}
G={}
for v,fn in (('A',runA),('B',runB),('C',runC)):
    for tg in (1.0,1.5,2.0):
        t=fn(tg)
        for qs in ('alle','AB'):
            tt=[x for x in t if qs=='alle' or x['q'] in 'AB']
            if tt: G[(v,tg,qs)]=tt
rows=[]
def halves(t): return [x for x in t if x['ts']<SPLIT],[x for x in t if x['ts']>=SPLIT]
res={}
for k,t in sorted(G.items()):
    s=stats(t); a,b=halves(t); sa,sb=(stats(a) if len(a)>=10 else None),(stats(b) if len(b)>=10 else None)
    res[k]=(s,sa,sb)
    rows.append([k[0],f"{f(k[1],1)} R",k[2],s['n'],f"{f(s['wr'],1)} %",f(s['avg'],3),f"[{f(s['lo'],2)}; {f(s['hi'],2)}]",(f(sa['avg'],2) if sa else '–'),(f(sb['avg'],2) if sb else '–')])
for k,(s,sa,sb) in sorted(res.items()): print(k,s['n'],round(s['wr'],1),round(s['avg'],3),sa and round(sa['avg'],3),sb and round(sb['avg'],3))
# Hauptvariante: Kandidaten mit n>=150 (C: >=60), Auswahl nach schwaecherer Haelfte
cand=[(min(sa['avg'],sb['avg']),k) for k,(s,sa,sb) in res.items() if sa and sb and s['n']>=(60 if k[0]=='C' else 150)]
best=max(cand)[1] if cand else max(res,key=lambda k:res[k][0]['avg'])
T=G[best]; st,sa,sb=res[best]; print('best',best,len(res))
pickle=__import__('pickle'); pickle.dump(dict(best=best,res={k:(v[0],) for k,v in res.items()}),open('/tmp/dob_res.pkl','wb'))
# Zufall
rng=np.random.default_rng(11); rb=[]
for _ in range(200):
    rs=[]
    for x in T:
        d=U[x['sym']]; i=int(rng.integers(60,len(d['c'])-12)); L=bool(rng.integers(2)); a=A[x['sym']][i-1]
        if np.isnan(a): continue
        rk=abs(x['entry']-x['stop'])/x['z']['a']*a; en=d['o'][i]; stp=en-rk if L else en+rk
        r=simulate(d,i,L,en,stp,best[1],10,x['sym'])
        if r: rs.append(r[0])
    rb.append(np.mean(rs))
rb=np.array(rb); p=float((rb>=st['avg']).mean())
def grp(keyf):
    g=collections.defaultdict(list)
    for x in T: g[keyf(x)].append(x['r'])
    out=[]
    for k,v in sorted(g.items()):
        v=np.array(v); w=(v>0).sum(); l=v[v<=0]; pf=v[v>0].sum()/abs(l.sum()) if len(l) and l.sum()!=0 else 0
        out.append([k,len(v),f(v.mean()),f"{round(100*w/len(v))} %",f(pf)])
    return out
cols=['Gruppe','Trades','Ø R','Trefferquote','Profitfaktor']
tabs=[dict(titel='Alle getesteten Varianten (Einstieg, Ziel, Zonenqualität)',spalten=['Einstieg','Ziel','Qualität','Trades','Trefferquote','Ø R','95-%-Intervall','Ø R bis 10/2024','Ø R ab 10/2024'],zeilen=rows),
 dict(titel='Hauptvariante: je Jahr',spalten=cols,zeilen=grp(lambda x:x['date'][:4])),
 dict(titel='Hauptvariante: je Paar',spalten=cols,zeilen=grp(lambda x:x['sym'])),
 dict(titel='Hauptvariante: Richtung',spalten=cols,zeilen=grp(lambda x:x['dir'])),
 dict(titel='Hauptvariante: Zonenqualität',spalten=cols,zeilen=grp(lambda x:x['q']))]
# Charts
ds=lambda ms: datetime.datetime.utcfromtimestamp(ms/1000).strftime('%d.%m.%y')
Ts=sorted(T,key=lambda x:x['ts']); step=max(1,len(Ts)//54); pk=Ts[::step][:54]; meta=[]
for n,x in enumerate(pk,1):
    z=x['z']; L=z['L']; d=U[z['sym']] if x['tf']=='D' else U4[z['sym']]; i,j=x['i0'],x['j']
    j0=max(0,i-45 if x['tf']=='D' else i-120); j1=min(len(d['c']),j+5)
    fig,ax=plt.subplots(figsize=(7.2,4.0),dpi=80)
    ax.add_patch(Rectangle((j0-1,z['lo']),j1-j0+2,z['hi']-z['lo'],color='#e9a23b',alpha=0.22,lw=0))
    for k in range(j0,j1):
        o,h,l,c=d['o'][k],d['h'][k],d['l'][k],d['c'][k]; col='#2a9d6f' if c>=o else '#d1495b'
        ax.plot([k,k],[l,h],color=col,lw=0.9); ax.add_patch(Rectangle((k-0.32,min(o,c)),0.64,max(abs(c-o),1e-9),color=col))
    risk=abs(x['entry']-x['stop']); tp=x['entry']+x['tg']*risk*(1 if L else -1)
    ax.axhline(x['entry'],color='#333',lw=0.8); ax.axhline(x['stop'],color='#d1495b',lw=0.9,ls='--'); ax.axhline(tp,color='#2a9d6f',lw=0.9,ls='--')
    ax.axvline(i,color='#888',lw=0.6,ls=':'); ax.set_xticks([j0,i]); ax.set_xticklabels([ds(d['t'][j0]),'Einstieg '+ds(d['t'][i])],fontsize=7); ax.tick_params(axis='y',labelsize=7); ax.set_xlim(j0-1,j1+1)
    ax.set_title(f"{z['sym']} {'Long' if L else 'Short'} · Daily-OB {z['q']} · {x['why']} · {x['r']:+.2f} R",fontsize=9)
    for s_ in ('top','right'): ax.spines[s_].set_visible(False)
    fig.tight_layout(); fn=f'strategiebilder/lab-dailyob_{n:02d}.jpg'
    fig.savefig(HOME+'/'+fn,format='jpg',pil_kwargs={'quality':75}); plt.close(fig)
    meta.append(dict(pfad=fn,titel=f"{z['sym']} {'Long' if L else 'Short'} {ds(x['ts'])}",ergebnis=f"{x['why']} {x['r']:+.2f} R",r=round(float(x['r']),2)))
weak=min((sa['avg'],sa['wr']),(sb['avg'],sb['wr']))
eq=list(np.round(np.cumsum([x['r'] for x in Ts]),2)); eq=eq[::max(1,len(eq)//300)]
syms=sorted(U); nsy=len(syms)
T_=dict(id='lab-dailyob',name='Test: Daily-Orderblock (A Zonenkante, B Daily-Bestätigung, C 4H-Bestätigung)',status='fertig',geprueft=datetime.datetime.now().strftime('%Y-%m-%dT%H:%M'),
 zeitraum=f"{ds(U['EURUSD']['t'][0])} bis {ds(U['EURUSD']['t'][-1])}",daten=f"{nsy} Instrumente ({', '.join(syms)}), je 3000 Tageskerzen; 4H nur ca. 1,5 Jahre",
 zusammenfassung=f"Zonen sind Tages-Orderblöcke (Regeln wie im Journal, erst nach der Bestätigung bekannt). Hauptvariante {NAME[best[0]]}, Ziel {f(best[1],1)} R, Zonenqualität {best[2]}: {st['n']} Trades, Trefferquote {f(st['wr'],1)} %, Ø {f(st['avg'],3)} R nach Spread, Profitfaktor {f(st['pf'])}.",
 urteil=f"Hauptvariante gewählt aus {len(res)} getesteten Varianten nach der schwächeren Hälfte (bis 10/2024: {f(sa['avg'],2)} R, ab 10/2024: {f(sb['avg'],2)} R). 95-%-Intervall für Ø R [{f(st['lo'],2)}; {f(st['hi'],2)}], {st['ypos']} von {st['ylen']} Jahren positiv. Zufalls-Einstiege mit gleichem Risiko und Ziel: Ø {f(rb.mean(),3)} R (p = {f(p,3)}). Wegen der Auswahl aus {len(res)} Varianten kann das Ergebnis der Hauptvariante zu gut ausfallen.",
 kennzahlen=[dict(label='Trades',wert=str(st['n'])),dict(label='Trefferquote',wert=f(st['wr'],1)+' %'),dict(label='Ø R',wert=f(st['avg'],3)),dict(label='95-%-Intervall',wert=f"{f(st['lo'],2)} bis {f(st['hi'],2)}"),dict(label='Profitfaktor',wert=f(st['pf'])),dict(label='Max-Drawdown',wert=f(st['dd'],1)+' R'),dict(label='Längste Verlustserie',wert=str(st['ms']))],
 equity=eq,equityHinweis='Kumulierte R der Hauptvariante nach Datum.',tabellen=tabs,
 regeln=['Zone: Tageskerze gegen die Richtung (oder Doji), danach innerhalb von 3 Kerzen mindestens 1,0 ATR Bewegung und Schluss über/unter dem 8-Kerzen-Extrem; Qualität A ab 2,0 ATR, B ab 1,2 ATR, sonst C','Zone gilt ab dem 4. Tag nach der Kerze, bis zu 60 Tage, verfällt bei Tagesschluss jenseits der Zone','Nur die erste Berührung zählt','A: Limit an der Zonenkante; B: Tagesschluss der Berührungskerze aus der Zone heraus, Einstieg zur nächsten Eröffnung; C: 4H-Schluss aus der Zone innerhalb von 3 Tagen nach der Berührung','Stopp 0,1 ATR hinter Zone (B/C: hinter dem Extrem der Berührung, höchstens 3 ATR), Ziel 1,0/1,5/2,0 R, Ausstieg nach 10 Tagen'],
 annahmen=['Stopp zuerst bei beidem in einer Kerze, 1 Pip Spread (Metalle grob geschätzt)','Variante C hat nur etwa 1,5 Jahre 4H-Daten und deshalb wenige Trades','Qualität nur aus der Bewegung, ohne Berührungszähler (der wäre Look-ahead)'],
 schwaechen=['Zonen benachbarter Paare sind korreliert','Auswahl der Hauptvariante aus vielen Varianten','Charts zeigen den Verlauf nach dem Einstieg und sind nur Illustration'],
 naechste='Mit COT-Filter und Wochentrend-Filter kombinieren, wenn die Trefferquote unter 50 % bleibt.',
 bilder=meta,ranking=dict(avg=round(weak[0],3),wr=round(float(weak[1]),1),n=st['n'],basis='schwächere Hälfte (bis 10/2024 gegen ab 10/2024)'))
p_=HOME+'/strategietests.json'; J=json.load(open(p_,encoding='utf-8'))
J['tests']=[t for t in J['tests'] if t['id']!='lab-dailyob']+[T_]; J['stand']=datetime.datetime.now().isoformat(timespec='minutes')
json.dump(J,open(p_,'w',encoding='utf-8'),ensure_ascii=False,indent=1)
print('fertig',nsy,len(Z),'best',best,st['n'],round(st['wr'],1),round(st['avg'],3),'rand',round(rb.mean(),3),p)

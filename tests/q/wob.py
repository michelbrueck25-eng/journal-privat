"""Weekly-Orderblock-Varianten (Zeitebene Weekly-Zone, Einstieg und Verlauf auf Tageskerzen), COT-Modi, Ziele, Haltedauer.
Schreibt backtest + Trade-Verlauf in forwardtest.json (privat). Aufruf: python3 wob.py"""
import sys,json,os,csv,bisect,datetime
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import eng
from eng import *
PIPS={'GOLD':0.1,'SILBER':0.01,'PLATIN':1.0,'KUPFER':0.002,'OEL':0.03,'ERDGAS':0.003}
eng.pip=lambda s: PIPS.get(s,0.01 if s.endswith('JPY') else 0.0001)
U=load_all()
# COT: Netto Commercials je Waehrung, Index ueber 26 Berichte, nutzbar ab Freitag (Dienstag+3 Tage)
cot={}
for r in csv.DictReader(open('/home/claude/journal-daten/cot.csv',encoding='utf-8')):
    try: cot.setdefault(r['waehrung'],[]).append((r['datum'],int(r['comm_long'])-int(r['comm_short'])))
    except Exception: pass
CI={}
for c,v in cot.items():
    v.sort(); ts=[];ix=[]
    for k in range(25,len(v)):
        w=[x[1] for x in v[k-25:k+1]]
        if max(w)==min(w): continue
        d=datetime.datetime.strptime(v[k][0],'%Y-%m-%d')+datetime.timedelta(days=3)
        ts.append(d.timestamp()*1000); ix.append(100*(v[k][1]-min(w))/(max(w)-min(w)))
    CI[c]=(ts,ix)
def cidx(cur,t):
    if cur not in CI: return None
    ts,ix=CI[cur]; k=bisect.bisect_right(ts,t)-1
    return ix[k] if k>=0 else None
def wzones(sym):
    W=U[sym]['W']; d=dict(h=W[:,2],l=W[:,3],c=W[:,4]); a=atr(d); n=len(W); out=[]
    for i in range(9,n-3):
        if np.isnan(a[i]): continue
        o,h,l,c=W[i,1],W[i,2],W[i,3],W[i,4]; doji=abs(c-o)<=0.3*(h-l)
        for L in (True,False):
            if L:
                if not (c<o or doji): continue
                ref=W[i-8:i,2].max(); disp=W[i+1:i+4,2].max()-h; bos=(W[i+1:i+4,4]>ref).any() and (W[i+1:i+4,4]>h).any()
            else:
                if not (c>o or doji): continue
                ref=W[i-8:i,3].min(); disp=l-W[i+1:i+4,3].min(); bos=(W[i+1:i+4,4]<ref).any() and (W[i+1:i+4,4]<l).any()
            if disp<1.0*a[i] or not bos: continue
            q='A' if disp>=2*a[i] else 'B' if disp>=1.2*a[i] else 'C'
            out.append(dict(sym=sym,L=L,lo=l,hi=h,q=q,wa=a[i],tv=W[i+4,0],tmax=W[i+4,0]+40*7*864e5))
    return out
Z=[]
for s in U:
    d=U[s]
    for z in wzones(s):
        k0=int(np.searchsorted(d['t'],z['tv']))
        for k in range(k0,len(d['t'])):
            if d['t'][k]>z['tmax']: break
            if (d['c'][k]<z['lo']) if z['L'] else (d['c'][k]>z['hi']): break
            if d['l'][k]<=z['hi'] and d['h'][k]>=z['lo']: z['k']=k; z['t0']=d['t'][k]; Z.append(z); break
print('Zonen mit Beruehrung',len(Z),flush=True)
def cotmode(z,mode):
    if mode=='ohne': return True
    s=z['sym']; 
    if s[:3] not in CI or s[3:] not in CI: return False
    b=cidx(s[:3],z['t0']); q=cidx(s[3:],z['t0'])
    if b is None or q is None: return False
    diff=(b-q) if z['L'] else (q-b)   # >0: COT in Handelsrichtung
    if mode=='stark': return diff>=30
    if mode=='schwach': return diff<=-30
    if mode=='extrem': return (b>75 and q<25) if z['L'] else (b<25 and q>75)
MODES={'ohne':'ohne COT','stark':'COT relativ stark (Index Basis minus Quote mindestens 30 in Handelsrichtung)','schwach':'COT relativ schwach (Index-Differenz mindestens 30 gegen die Handelsrichtung, Kontrolle)','extrem':'COT im Extrem (Basis über 75 und Quote unter 25 für long, umgekehrt für short)'}
def run(tg,md,mode):
    out=[]
    for z in Z:
        if not cotmode(z,mode): continue
        d=U[z['sym']]; L=z['L']; k=z['k']
        if (d['o'][k]<z['lo']) if L else (d['o'][k]>z['hi']): continue
        a=atr(d)[k-1]
        if not a==a: continue
        entry=z['hi'] if L else z['lo']; stop=z['lo']-0.1*a if L else z['hi']+0.1*a
        r=simulate(d,k,L,entry,stop,tg,md,z['sym'])
        if r: out.append((z['t0'],r[0],z['sym'],'long' if L else 'short',z['q']))
    out.sort(); return out
def kz(t):
    r=np.array([x[1] for x in t]); eq=np.cumsum(r); gl=-r[r<0].sum(); gw=r[r>0].sum()
    return dict(n=len(r),wr=round(float((r>0).mean()*100),1),avg=round(float(r.mean()),3),pf=round(float(gw/gl),2) if gl>0 else None,dd=round(float((np.maximum.accumulate(eq)-eq).max()),1),sum=round(float(r.sum()),1),yrs=round((t[-1][0]-t[0][0])/31557600000,1))
RES={}
for mode in MODES:
    for tg in (1.0,1.5,2.0):
        for md in (7,10):
            t=run(tg,md,mode)
            if len(t)>=10: RES[(mode,tg,md)]=t
json.dump({f'{m}|{tg}|{md}':[[x[0],round(x[1],3),x[2],x[3],x[4]] for x in t] for (m,tg,md),t in RES.items()},open('/tmp/wob_res.json','w'))
for k,t in RES.items(): print(k,kz(t))

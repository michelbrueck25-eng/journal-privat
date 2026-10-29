import sys; sys.path.insert(0,'/tmp/w/q')
from eng import *
U=load_all()
for s,d in U.items():
    d['atr']=atr(d); d['e20']=ema(d['c'],20); d['e50']=ema(d['c'],50); d['wt']=wk_trend(d)
def dstr(d,i): return dt.datetime.utcfromtimestamp(d['t'][i]/1000).strftime('%Y-%m-%d')
def mk(sym,d,i,L,res,fam,extra=None):
    r,days,out,j,px,risk=res
    return dict(sym=sym,i=i,L=L,date=dstr(d,i),r=r,days=days,out=out,j=j,px=px,risk=risk,fam=fam,**(extra or {}))
# ---------- Familie 1: Trend-Ruecksetzer an EMA ----------
def f_trend(P):
    out=[]
    for sym,d in U.items():
        n=len(d['c']); lvl=d['e20'] if P['ema']==20 else d['e50']
        for i in range(60,n-1):
            a=d['atr'][i-1]
            if np.isnan(a): continue
            for L in ((True,False)):
                if P['htf'] and d['wt'][i]!=(1 if L else -1): continue
                if (L and not d['e20'][i-1]>d['e50'][i-1]) or ((not L) and not d['e20'][i-1]<d['e50'][i-1]): continue
                entry=lvl[i-1]
                if L:
                    if d['l'][i]>entry: continue
                    if d['o'][i]<entry: entry=d['o'][i]
                    stop=entry-P['k']*a
                else:
                    if d['h'][i]<entry: continue
                    if d['o'][i]>entry: entry=d['o'][i]
                    stop=entry+P['k']*a
                res=simulate(d,i,L,entry,stop,P['tgt'],P['maxd'],sym)
                if res: out.append(mk(sym,d,i,L,res,'trend'))
    return out
# ---------- Familie 2: Fibonacci ----------
def swings(d,n=5):
    h,l=d['h'],d['l']; sh=[];sl=[]
    for i in range(n,len(h)-n):
        if h[i]==h[i-n:i+n+1].max() and h[i]>h[i-n:i].max(): sh.append(i)
        if l[i]==l[i-n:i+n+1].min() and l[i]<l[i-n:i].min(): sl.append(i)
    return sh,sl
def f_fib(P):
    out=[]
    for sym,d in U.items():
        n=len(d['c']); sh,sl=swings(d); sw=sorted([(i,'H') for i in sh]+[(i,'L') for i in sl]); 
        conf=[(i+5,i,k) for i,k in sw]  # Swing erst 5 Kerzen spaeter bekannt
        for idx in range(1,len(sw)):
            (i2,k2),(i1,k1)=sw[idx],sw[idx-1]
            if k1==k2: continue
            a=d['atr'][i2]
            if np.isnan(a): continue
            hi=d['h'][i2] if k2=='H' else d['h'][i1]; lo=d['l'][i2] if k2=='L' else d['l'][i1]
            if hi-lo<P['leg']*a: continue
            up=(k2=='H')  # Aufwaertsbein -> Long beim Ruecksetzer
            if P['htf']:
                pass
            lvl=hi-P['fib']*(hi-lo) if up else lo+P['fib']*(hi-lo)
            stop=lo-P['sbuf']*a if up else hi+P['sbuf']*a
            start=i2+5+1; end=min(start+P['wait'],n-1)
            for i in range(start,end):
                if up and d['c'][i]<lo or ((not up) and d['c'][i]>hi): break
                if P['htf'] and d['wt'][i]!=(1 if up else -1): continue
                touch=(d['l'][i]<=lvl) if up else (d['h'][i]>=lvl)
                if touch:
                    entry=min(lvl,d['o'][i]) if up else max(lvl,d['o'][i])
                    res=simulate(d,i,up,entry,stop,P['tgt'],P['maxd'],sym)
                    if res: out.append(mk(sym,d,i,up,res,'fib'))
                    break
    return out
# ---------- Familie 3: Vortag-Sweep ----------
def f_sweep(P):
    out=[]
    for sym,d in U.items():
        n=len(d['c'])
        for i in range(60,n-2):
            a=d['atr'][i]
            if np.isnan(a): continue
            for L in (True,False):
                if P['htf'] and d['wt'][i]!=(1 if L else -1): continue
                ref=d['l'][i-P['look']:i].min() if L else d['h'][i-P['look']:i].max()
                if L and not (d['l'][i]<ref and d['c'][i]>ref): continue
                if (not L) and not (d['h'][i]>ref and d['c'][i]<ref): continue
                entry=d['o'][i+1]; stop=(d['l'][i]-0.1*a) if L else (d['h'][i]+0.1*a)
                if abs(entry-stop)>P['cap']*a: continue
                res=simulate(d,i+1,L,entry,stop,P['tgt'],P['maxd'],sym,check_entry_bar=True)
                if res: out.append(mk(sym,d,i+1,L,res,'sweep'))
    return out
# ---------- Familie 4: Mean Reversion (Abstand zum MA in ATR) ----------
def f_mr(P):
    out=[]
    for sym,d in U.items():
        n=len(d['c']); ma=np.array([d['c'][max(0,i-19):i+1].mean() for i in range(n)])
        for i in range(60,n-2):
            a=d['atr'][i]
            if np.isnan(a): continue
            z=(d['c'][i]-ma[i])/a
            for L in (True,False):
                if P['htf'] and d['wt'][i]!=(1 if L else -1): continue
                if (L and z>-P['z']) or ((not L) and z<P['z']): continue
                entry=d['o'][i+1]; stop=entry-P['k']*a if L else entry+P['k']*a
                res=simulate(d,i+1,L,entry,stop,P['tgt'],P['maxd'],sym)
                if res: out.append(mk(sym,d,i+1,L,res,'mr'))
    return out
FAMS={'trend':(f_trend,dict(ema=[20,50],htf=[0,1],k=[1.0,1.5,2.0],tgt=[1.0,1.5,2.0],maxd=[10])),
 'fib':(f_fib,dict(fib=[0.5,0.618],leg=[3,5],sbuf=[0.2],wait=[10],htf=[0,1],tgt=[1.0,1.5,2.0],maxd=[10])),
 'sweep':(f_sweep,dict(look=[1,5],htf=[0,1],cap=[2.0],tgt=[1.0,1.5,2.0],maxd=[5,10])),
 'mr':(f_mr,dict(z=[1.5,2.5],htf=[0,1],k=[1.5,2.5],tgt=[0.75,1.0,1.5],maxd=[5,10]))}
def configs(g):
    import itertools
    ks=list(g); return [dict(zip(ks,v)) for v in itertools.product(*[g[k] for k in ks])]

import sys,pickle,time,random
sys.path.insert(0,'/home/claude/journal-privat/tests/q')
from gen import *
import gen
SYMS=list(U)
CUT='2023-01-01'
for sym,d in U.items():
    c=d['c']; n=len(c)
    d['dtr']=np.where(d['e20']>d['e50'],1,-1)
    a100=sma(d['atr'],100); d['vol']=np.where(d['atr']>np.nan_to_num(a100,nan=1e9),1,-1)
    d['mom']=np.where(d['rsi14']>50,1,-1)
    d['date']=np.array([dstr(d,i) for i in range(n)])
    d['wd']=np.array([__import__('datetime').datetime.utcfromtimestamp(t/1000).weekday() for t in d['t']])
    b,q=sym[:3],sym[3:]; ca=np.zeros(n)
    for i in range(n):
        cb,cq=cot_idx(b,d['date'][i]),cot_idx(q,d['date'][i])
        if cb is not None and cq is not None: ca[i]=1 if cb>cq+20 else (-1 if cq>cb+20 else 0)
    d['cotal']=ca
    d['cl3']=np.array([ (1 if (i>=3 and c[i]<c[i-1]<c[i-2]<c[i-3]) else (-1 if (i>=3 and c[i]>c[i-1]>c[i-2]>c[i-3]) else 0)) for i in range(n)])
    d['cl4']=np.array([ (1 if (i>=4 and c[i]<c[i-1]<c[i-2]<c[i-3]<c[i-4]) else (-1 if (i>=4 and c[i]>c[i-1]>c[i-2]>c[i-3]>c[i-4]) else 0)) for i in range(n)])
    ma=d['ma20']; d['z']=(c-ma)/np.where(d['atr']>0,d['atr'],np.nan)
SIGS={}
def addsig(name,fn):
    tab=[]
    for si,sym in enumerate(SYMS):
        d=U[sym]
        for i in range(60,len(d['c'])-1):
            if np.isnan(d['atr'][i]): continue
            r=fn(d,i)
            if r is None: continue
            tab.append((si,i,r))
    SIGS[name]=tab
for n in (10,20,55): addsig(f'donch{n}',lambda d,i,n=n:(True if d['c'][i]>d['h'][i-n:i].max() else (False if d['c'][i]<d['l'][i-n:i].min() else None)))
for th in (5,10): addsig(f'rsi2_{th}',lambda d,i,th=th:(True if d['rsi2'][i]<th else (False if d['rsi2'][i]>100-th else None)))
for th in (25,30): addsig(f'rsi14x{th}',lambda d,i,th=th:(True if d['rsi14'][i-1]<th<=d['rsi14'][i] else (False if d['rsi14'][i-1]>100-th>=d['rsi14'][i] else None)))
addsig('bbret',lambda d,i:(True if d['c'][i-1]<d['bbl'][i-1] and d['c'][i]>d['bbl'][i] else (False if d['c'][i-1]>d['bbu'][i-1] and d['c'][i]<d['bbu'][i] else None)))
addsig('bbout',lambda d,i:(True if d['c'][i]>d['bbu'][i] else (False if d['c'][i]<d['bbl'][i] else None)))
for z in (1.5,2.0,2.5): addsig(f'zmr{z}',lambda d,i,z=z:(True if d['z'][i]<-z else (False if d['z'][i]>z else None)))
addsig('emax',lambda d,i:(True if d['e20'][i-1]<=d['e50'][i-1] and d['e20'][i]>d['e50'][i] else (False if d['e20'][i-1]>=d['e50'][i-1] and d['e20'][i]<d['e50'][i] else None)))
addsig('macdx',lambda d,i:(True if d['macd'][i-1]<d['macds'][i-1] and d['macd'][i]>=d['macds'][i] else (False if d['macd'][i-1]>d['macds'][i-1] and d['macd'][i]<=d['macds'][i] else None)))
addsig('inside',lambda d,i:((bool(d['dtr'][i]>0)) if d['h'][i]<d['h'][i-1] and d['l'][i]>d['l'][i-1] else None))
addsig('pin',lambda d,i:(True if (min(d['c'][i],d['o'][i])-d['l'][i])>=0.6*(d['h'][i]-d['l'][i]) and d['h'][i]>d['l'][i] else (False if (d['h'][i]-max(d['c'][i],d['o'][i]))>=0.6*(d['h'][i]-d['l'][i]) and d['h'][i]>d['l'][i] else None)))
for lk in (1,5): addsig(f'sweep{lk}',lambda d,i,lk=lk:(True if d['l'][i]<d['l'][i-lk:i].min() and d['c'][i]>d['l'][i-lk:i].min() else (False if d['h'][i]>d['h'][i-lk:i].max() and d['c'][i]<d['h'][i-lk:i].max() else None)))
addsig('cl3',lambda d,i:(True if d['cl3'][i]==1 else (False if d['cl3'][i]==-1 else None)))
addsig('cl4',lambda d,i:(True if d['cl4'][i]==1 else (False if d['cl4'][i]==-1 else None)))
addsig('engulf',lambda d,i:(True if d['c'][i]>d['o'][i-1] and d['o'][i]<=d['c'][i-1] and d['c'][i-1]<d['o'][i-1] and d['c'][i]>d['o'][i] else (False if d['c'][i]<d['o'][i-1] and d['o'][i]>=d['c'][i-1] and d['c'][i-1]>d['o'][i-1] and d['c'][i]<d['o'][i] else None)))
addsig('kcout',lambda d,i:(True if d['c'][i]>d['kcu'][i] else (False if d['c'][i]<d['kcl'][i] else None)))
addsig('gapday',lambda d,i:(True if d['c'][i]>d['h'][i-1] else (False if d['c'][i]<d['l'][i-1] else None)))   # Schluss ueber Vortageshoch
print('Signale',{k:len(v) for k,v in SIGS.items()},flush=True)
# Null-Signale: zufaellige Tage/Richtung gleicher Haeufigkeit
rng=random.Random(11)
for name in ('null1','null2','null3','null4'):
    tab=[]
    for si,sym in enumerate(SYMS):
        d=U[sym]
        for i in range(60,len(d['c'])-1):
            if rng.random()<0.06 and not np.isnan(d['atr'][i]): tab.append((si,i,rng.random()<0.5))
    SIGS[name]=tab
def evaluate(cfg):
    tab=SIGS[cfg['sig']]; inv=cfg['inv']; k=cfg['k']; tgt=cfg['tgt']; maxd=cfg['maxd']
    busy={}; tr=[]
    for si,i,L in tab:
        sym=SYMS[si]; d=U[sym]
        if i<=busy.get(si,-1): continue
        if inv: L=not L
        s=1 if L else -1
        f=cfg['f']
        if f['wt'] and d['wt'][i]!=s*f['wt']: continue
        if f['dtr'] and d['dtr'][i]!=s*f['dtr']: continue
        if f['mom'] and d['mom'][i]!=s*f['mom']: continue
        if f['cot'] and d['cotal'][i]!=s*f['cot']: continue
        if f['vol'] and d['vol'][i]!=f['vol']: continue
        if f['nofri'] and d['wd'][i]==4: continue
        if cfg['dir']=='long' and not L: continue
        if cfg['dir']=='short' and L: continue
        a=d['atr'][i]; entry=d['o'][i+1]; stop=entry-k*a if L else entry+k*a
        res=simulate(d,i+1,L,entry,stop,tgt,maxd,sym)
        if res: tr.append((sym,d['date'][i+1],L,res[0],res[1],res[2],i+1,res[3],res[4],res[5])); busy[si]=i+1+res[1]
    return tr
def sstat(tr):
    if not tr: return None
    r=np.array([x[3] for x in tr]); return dict(n=len(r),avg=float(r.mean()),wr=float(100*(r>0).mean()))
def rand_cfg(rg,null=False):
    sig=rg.choice(['null1','null2','null3','null4'] if null else [s for s in SIGS if not s.startswith('null')])
    f=dict(wt=rg.choice([0,0,1,-1]),dtr=rg.choice([0,0,1,-1]),mom=rg.choice([0,0,1,-1]),cot=rg.choice([0,0,0,1,-1]),vol=rg.choice([0,0,1,-1]),nofri=rg.choice([0,1]))
    return dict(sig=sig,inv=rg.choice([0,1]),f=f,k=rg.choice([1.0,1.5,2.0,3.0]),tgt=rg.choice([0.5,0.75,1.0,1.5,2.0,3.0]),maxd=rg.choice([5,10,20]),dir=rg.choice(['both','both','long','short']))
if __name__=='__main__':
    NREAL=int(sys.argv[1]); NNULL=int(sys.argv[2]); rg=random.Random(2026); out=[]; t0=time.time()
    for nm,N,null in (('real',NREAL,False),('null',NNULL,True)):
        for q in range(N):
            cfg=rand_cfg(rg,null); tr=evaluate(cfg)
            a=sstat([x for x in tr if x[1]<CUT]); b=sstat([x for x in tr if x[1]>=CUT]); c=sstat(tr)
            if a and b and c: out.append((nm,cfg,a,b,c))
            if q%500==0: print(nm,q,round(time.time()-t0),'s',flush=True)
    pickle.dump(out,open('res_free.pkl','wb')); print('fertig',len(out),round(time.time()-t0),'s')

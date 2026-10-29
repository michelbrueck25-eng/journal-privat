import json,random,datetime as dt,numpy as np,pandas as pd,itertools,sys
from seas import P,SYMS,cost_r
FX=[s for s in SYMS if s!='GOLD']
def sim(s,i,L,sa,tg,N):
    d=P[s]['d']; n=len(d['c'])
    if i+1+N>=n or np.isnan(P[s]['a'][i]): return None
    a=P[s]['a'][i]; e=d['o'][i+1]; sd=sa*a; stp=e-sd if L else e+sd; tp=None if not tg else (e+tg*sd if L else e-tg*sd)
    for j in range(i+1,i+1+N):
        if (d['l'][j]<=stp) if L else (d['h'][j]>=stp): r=-1.0; break
        if tp is not None and ((d['h'][j]>=tp) if L else (d['l'][j]<=tp)): r=tg; break
    else:
        j=i+N; r=((d['c'][j]-e) if L else (e-d['c'][j]))/sd
    cal=(P[s]['ts'][j]-P[s]['ts'][i+1]).days
    return r-cost_r(s,sd,a,cal),j,i+1
def runsig(sigs,sa,tg,N):
    out=[];busy={}
    for (s,i,L) in sorted(sigs,key=lambda x:(P[x[0]]['ts'][x[1]],x[0])):
        if i<=busy.get(s,-1): continue
        t=sim(s,i,L,sa,tg,N)
        if not t: continue
        busy[s]=t[1]; out.append(dict(sym=s,date=str(P[s]['ts'][t[2]]),dir='long' if L else 'short',r=float(t[0])))
    return out
def summ(tr,split='2023-01-01'):
    def f(t):
        if len(t)<5: return dict(n=len(t),avg=None)
        r=np.array([x['r'] for x in t]); eq=np.cumsum(r); y=len(set(x['date'][:4] for x in t))
        return dict(n=len(r),wr=round(float((r>0).mean()*100),1),avg=round(float(r.mean()),3),pf=round(float(r[r>0].sum()/max(1e-9,abs(r[r<=0].sum()))),2),dd=round(float((np.maximum.accumulate(eq)-eq).max()),1),jahr=round(float(r.sum()/y),1))
    return f(tr),f([x for x in tr if x['date']<split]),f([x for x in tr if x['date']>=split])
# ---------- Signale
def sig_basket(Lb,k=1,rev=False,hold_wd=4):
    df=pd.DataFrame({s:(lambda x:x[~x.index.duplicated(keep='last')])(pd.Series(P[s]['d']['c'],index=pd.to_datetime(P[s]['ts']))) for s in FX}).sort_index().ffill()
    lr=np.log(df/df.shift(Lb)); C=['AUD','CAD','CHF','EUR','GBP','JPY','NZD','USD']
    S=pd.DataFrame(0.0,index=df.index,columns=C)
    for s in FX:
        S[s[:3]]+=lr[s]/7; S[s[3:]]-=lr[s]/7
    sigs=[]
    for t in df.index:
        if t.weekday()!=hold_wd or np.isnan(S.loc[t]).any(): continue
        row=S.loc[t].sort_values(); 
        for q in range(k):
            top,bot=row.index[-1-q],row.index[q]
            if rev: top,bot=bot,top
            sym=top+bot if top+bot in P else bot+top
            L=(sym[:3]==top)
            i=P[sym]['idx'].get(t.date())
            if i is not None: sigs.append((sym,i,L))
    return sigs
def rsi2(c):
    d=np.diff(c,prepend=c[0]);up=np.where(d>0,d,0);dn=np.where(d<0,-d,0);r=np.full(len(c),np.nan)
    au=ad=None
    for i in range(len(c)):
        if i<2: continue
        if au is None: au=up[1:3].mean();ad=dn[1:3].mean()
        else: au=(au+up[i])/2; ad=(ad+dn[i])/2   # Wilder n=2 : (au*(n-1)+x)/n
        r[i]=100 if ad==0 else 100-100/(1+au/ad)
    return r
def sig_pull(thr,use_trend=True):
    from eng import wk_trend
    out=[]
    for s in FX:
        d=P[s]['d']; r=rsi2(d['c']); tr=wk_trend(d); sma=pd.Series(d['c']).rolling(50).mean().values
        for i in range(60,len(r)-2):
            if r[i]<thr and (tr[i]>0 if use_trend else d['c'][i]>sma[i]): out.append((s,i,True))
            if r[i]>100-thr and (tr[i]<0 if use_trend else d['c'][i]<sma[i]): out.append((s,i,False))
    return out
def sig_don(n,use_trend=True):
    from eng import wk_trend
    out=[]
    for s in FX:
        d=P[s]['d']; tr=wk_trend(d); h=pd.Series(d['h']).rolling(n).max().shift(1).values; l=pd.Series(d['l']).rolling(n).min().shift(1).values
        for i in range(n+1,len(d['c'])-2):
            if d['c'][i]>h[i] and (tr[i]>0 or not use_trend): out.append((s,i,True))
            if d['c'][i]<l[i] and (tr[i]<0 or not use_trend): out.append((s,i,False))
    return out
def sig_nr(n,use_trend=True):
    from eng import wk_trend
    out=[]
    for s in FX:
        d=P[s]['d']; tr=wk_trend(d); rg=d['h']-d['l']
        for i in range(n+1,len(rg)-2):
            if rg[i]==rg[i-n+1:i+1].min():   # engste Spanne der letzten n Tage, Ausbruch am Folgetag nicht moeglich ohne Stop-Order -> Richtung = Trend
                if tr[i]>0: out.append((s,i,True))
                elif tr[i]<0: out.append((s,i,False))
    return out
if __name__=='__main__':
    res=[]
    def add(name,sigs,sa,tg,N):
        tr=runsig(sigs,sa,tg,N); a,b,c=summ(tr); res.append(dict(name=name,sa=sa,tg=tg,N=N,all=a,dev=b,test=c,_tr=tr)); print(name,sa,tg,N,'| alle',a,'| dev',b.get('avg'),'| test',c.get('avg'),c.get('n'),flush=True)
    for Lb in (5,10,20,60):
        for k in (1,2):
            for rev in (False,True):
                sg=sig_basket(Lb,k,rev)
                for (sa,tg,N) in ((2,None,5),(2,None,10),(3,None,20)): add(f'Korb L{Lb} k{k} {"Umkehr" if rev else "Trend"}',sg,sa,tg,N)
    for thr in (5,10):
        for ut in (True,False):
            sg=sig_pull(thr,ut)
            for (sa,tg,N) in ((2.5,None,5),(2.5,1.0,7),(3,1.5,10)): add(f'RSI2 {thr} {"Wochentrend" if ut else "SMA50"}',sg,sa,tg,N)
    for n in (20,55):
        for ut in (True,):
            sg=sig_don(n,ut)
            for (sa,tg,N) in ((2,3,20),(3,None,20),(2,2,10)): add(f'Donchian {n} Wochentrend',sg,sa,tg,N)
    for n in (4,7):
        sg=sig_nr(n)
        for (sa,tg,N) in ((1.5,2,10),(2,3,15)): add(f'NR{n} Trend',sg,sa,tg,N)
    import pickle; pickle.dump(res,open('/tmp/ideen.pkl','wb'))
    print(len(res),'Varianten')

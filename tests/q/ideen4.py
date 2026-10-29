import pickle
src=open('ideen.py').read().split("if __name__=='__main__':")[0]; exec(src)
from eng import wk_trend
res=[]
def add(name,sigs,sa,tg,N):
    tr=runsig(sigs,sa,tg,N); a,b,c=summ(tr); res.append(dict(name=name,sa=sa,tg=tg,N=N,all=a,dev=b,test=c,_tr=tr))
def feats(s):
    d=P[s]['d']; c=pd.Series(d['c']); h=pd.Series(d['h']); l=pd.Series(d['l'])
    return d,c,h,l,wk_trend(d)
def S_bb_rev(k,tr_on):
    out=[]
    for s in FX:
        d,c,h,l,tr=feats(s); m=c.rolling(20).mean(); sd=c.rolling(20).std(); lo=m-k*sd; up=m+k*sd
        for i in range(60,len(c)-2):
            if c[i]<lo[i] and c[i-1]>=lo[i-1] and (not tr_on or tr[i]>0): out.append((s,i,True))
            if c[i]>up[i] and c[i-1]<=up[i-1] and (not tr_on or tr[i]<0): out.append((s,i,False))
    return out
def S_bb_squeeze(q):
    out=[]
    for s in FX:
        d,c,h,l,tr=feats(s); m=c.rolling(20).mean(); sd=c.rolling(20).std(); w=(4*sd/m); thr=w.rolling(120).quantile(q); up=m+2*sd; lo=m-2*sd
        for i in range(140,len(c)-2):
            if w[i-1]<=thr[i-1]:
                if c[i]>up[i]: out.append((s,i,True))
                elif c[i]<lo[i]: out.append((s,i,False))
    return out
def S_ma_x(f,sl,use_w):
    out=[]
    for s in FX:
        d,c,h,l,tr=feats(s); a=c.ewm(span=f,adjust=False).mean(); b=c.ewm(span=sl,adjust=False).mean()
        for i in range(sl+5,len(c)-2):
            if a[i]>b[i] and a[i-1]<=b[i-1] and (not use_w or tr[i]>0): out.append((s,i,True))
            if a[i]<b[i] and a[i-1]>=b[i-1] and (not use_w or tr[i]<0): out.append((s,i,False))
    return out
def S_ma_pull(f,sl):
    out=[]
    for s in FX:
        d,c,h,l,tr=feats(s); a=c.ewm(span=f,adjust=False).mean(); b=c.ewm(span=sl,adjust=False).mean()
        for i in range(sl+5,len(c)-2):
            if a[i]>b[i] and tr[i]>0 and d['l'][i]<=a[i] and c[i]>a[i]: out.append((s,i,True))
            if a[i]<b[i] and tr[i]<0 and d['h'][i]>=a[i] and c[i]<a[i]: out.append((s,i,False))
    return out
def S_keltner(n,k):
    out=[]
    for s in FX:
        d,c,h,l,tr=feats(s); m=c.ewm(span=n,adjust=False).mean(); at=pd.Series(P[s]['a']); up=m+k*at; lo=m-k*at
        for i in range(n+20,len(c)-2):
            if c[i]>up[i] and c[i-1]<=up[i-1] and tr[i]>0: out.append((s,i,True))
            if c[i]<lo[i] and c[i-1]>=lo[i-1] and tr[i]<0: out.append((s,i,False))
    return out
def S_stoch(n,lo_,hi_):
    out=[]
    for s in FX:
        d,c,h,l,tr=feats(s); ll=l.rolling(n).min(); hh=h.rolling(n).max(); k=100*(c-ll)/(hh-ll); dd=k.rolling(3).mean()
        for i in range(n+5,len(c)-2):
            if dd[i-1]<lo_ and dd[i]>=lo_ and tr[i]>0: out.append((s,i,True))
            if dd[i-1]>hi_ and dd[i]<=hi_ and tr[i]<0: out.append((s,i,False))
    return out
def S_macd(use_w):
    out=[]
    for s in FX:
        d,c,h,l,tr=feats(s); m=c.ewm(span=12,adjust=False).mean()-c.ewm(span=26,adjust=False).mean(); sg=m.ewm(span=9,adjust=False).mean()
        for i in range(40,len(c)-2):
            if m[i]>sg[i] and m[i-1]<=sg[i-1] and m[i]<0 and (not use_w or tr[i]>0): out.append((s,i,True))
            if m[i]<sg[i] and m[i-1]>=sg[i-1] and m[i]>0 and (not use_w or tr[i]<0): out.append((s,i,False))
    return out
def S_inside(use_w):
    out=[]
    for s in FX:
        d,c,h,l,tr=feats(s)
        for i in range(10,len(c)-2):
            if h[i]<h[i-1] and l[i]>l[i-1]:   # Innenstab: Richtung = Wochentrend
                if tr[i]>0: out.append((s,i,True))
                elif tr[i]<0: out.append((s,i,False))
    return out
def S_wk_break(n):
    out=[]
    for s in FX:
        d=P[s]['d']; W=d['W']; wt=W[:,0]; wh=pd.Series(W[:,2]); wl=pd.Series(W[:,3]); wc=W[:,4]
        hh=wh.rolling(n).max().shift(1).values; ll=wl.rolling(n).min().shift(1).values
        ts=P[s]['ts']
        for k in range(n+2,len(wc)-1):
            t=dt.datetime.fromtimestamp(wt[k]/1000,dt.timezone.utc).date()+dt.timedelta(days=6)   # Wochenende
            # Signal am letzten Handelstag der Woche k
            i=None
            for back in range(0,4):
                i=P[s]['idx'].get(t-dt.timedelta(days=back))
                if i is not None: break
            if i is None: continue
            if wc[k]>hh[k]: out.append((s,i,True))
            elif wc[k]<ll[k]: out.append((s,i,False))
    return out
for k in (2.0,2.5):
    for tr_on in (True,False):
        sg=S_bb_rev(k,tr_on)
        for (sa,tg,N) in ((2,1.0,8),(2.5,1.5,12),(3,None,10)): add(f'Bollinger-Umkehr {k} {"Wochentrend" if tr_on else "ohne Trend"}',sg,sa,tg,N)
for q in (0.15,0.3):
    sg=S_bb_squeeze(q)
    for (sa,tg,N) in ((2,3,15),(2,2,10),(3,None,20)): add(f'Bollinger-Squeeze {q}',sg,sa,tg,N)
for (f,sl) in ((10,30),(20,50),(50,200)):
    for uw in (True,False):
        sg=S_ma_x(f,sl,uw)
        for (sa,tg,N) in ((3,None,20),(2.5,3,15)): add(f'MA-Kreuzung EMA{f}/{sl} {"Wochentrend" if uw else "ohne"}',sg,sa,tg,N)
for (f,sl) in ((20,50),(10,30)):
    sg=S_ma_pull(f,sl)
    for (sa,tg,N) in ((2,2,10),(2.5,3,15),(3,None,10)): add(f'EMA-Rücksetzer {f}/{sl}',sg,sa,tg,N)
for (n,k) in ((20,1.5),(20,2.0)):
    sg=S_keltner(n,k)
    for (sa,tg,N) in ((2,3,15),(3,None,20)): add(f'Keltner-Ausbruch {n}/{k}',sg,sa,tg,N)
for (n,lo_,hi_) in ((14,20,80),(8,20,80)):
    sg=S_stoch(n,lo_,hi_)
    for (sa,tg,N) in ((2,1.5,8),(2.5,2,12)): add(f'Stochastik {n} {lo_}/{hi_} Wochentrend',sg,sa,tg,N)
for uw in (True,):
    sg=S_macd(uw)
    for (sa,tg,N) in ((2,2,10),(2.5,3,15)): add('MACD-Kreuzung unter Nulllinie',sg,sa,tg,N)
sg=S_inside(True)
for (sa,tg,N) in ((1.5,2,8),(2,3,12)): add('Innenstab Wochentrend',sg,sa,tg,N)
for n in (10,26):
    sg=S_wk_break(n)
    for (sa,tg,N) in ((3,None,15),(3,None,20),(4,None,28)): add(f'Weekly-Ausbruch {n} Wochen',sg,sa,tg,N)
pickle.dump(res,open('/tmp/ideen4.pkl','wb'))
r=[x for x in res if x['all'].get('avg') is not None]; r.sort(key=lambda x:-x['all']['avg'])
for x in r[:12]: print(x['name'],x['sa'],x['tg'],x['N'],x['all']['n'],x['all']['avg'],'dev',x['dev']['avg'],'test',x['test']['avg'],x['test']['n'],'dd',x['all']['dd'],'j',x['all']['jahr'])
print(len(res),'Varianten',sum(1 for x in r if x['all']['avg']>=0.15),'>=0.15, Median',np.median([x['all']['avg'] for x in r]))

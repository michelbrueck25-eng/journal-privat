import json,glob,os,random,math,datetime as dt,bisect
import numpy as np
HOME='/home/claude/journal-privat'
def pip(s): return 0.01 if s.endswith('JPY') else 0.0001
SPREAD_PIPS=1.0
def load_all():
    U={}
    for f in sorted(glob.glob(f'{HOME}/marktdaten/*_D.json')):
        sym=os.path.basename(f).split('_')[0]
        r=json.load(open(f))['rows']
        if dt.datetime.utcfromtimestamp(r[-1][0]/1000).date()>=dt.datetime.utcnow().date(): r=r[:-1]  # unvollstaendige Tageskerze
        a=np.array(r,float)
        W=np.array(json.load(open(f'{HOME}/marktdaten/{sym}_W.json'))['rows'],float)
        U[sym]=dict(t=a[:,0],o=a[:,1],h=a[:,2],l=a[:,3],c=a[:,4],W=W)
    return U
def atr(d,n=14):
    h,l,c=d['h'],d['l'],d['c']; pc=np.r_[c[0],c[:-1]]
    tr=np.maximum(h-l,np.maximum(abs(h-pc),abs(l-pc)))
    out=np.full(len(c),np.nan)
    cs=np.cumsum(tr)
    out[n:]=(cs[n:]-cs[:-n])/n
    return out
def ema(x,n):
    a=2/(n+1); o=np.empty(len(x)); o[0]=x[0]
    for i in range(1,len(x)): o[i]=a*x[i]+(1-a)*o[i-1]
    return o
def wk_trend(d):
    """+1/-1/0 je Tag: letzter abgeschlossener Wochenschluss gegen SMA20 der Wochenschluesse (nur Daten vor dem Tag)"""
    W=d['W']; wt=W[:,0]; wc=W[:,4]; sma=np.full(len(wc),np.nan)
    for i in range(19,len(wc)): sma[i]=wc[i-19:i+1].mean()
    out=np.zeros(len(d['t']))
    for i,t in enumerate(d['t']):
        k=bisect.bisect_right(wt,t-7*86400e3)-1   # Woche muss vor Tag-7d begonnen haben => abgeschlossen
        if k>=19 and not np.isnan(sma[k]): out[i]=1 if wc[k]>sma[k] else -1
    return out
def simulate(d,i0,L,entry,stop,tgt_r,maxd,sym,check_entry_bar=True):
    """Einstieg-Limit in Kerze i0 (gefuellt), Stopp-Check in Einstiegskerze pessimistisch, danach Kerzen i0+1..."""
    risk=abs(entry-stop)
    if risk<=0: return None
    sp=SPREAD_PIPS*pip(sym)
    if check_entry_bar and ((d['l'][i0]<=stop) if L else (d['h'][i0]>=stop)): return (-1-sp/risk,0,'SL',i0,stop,risk)
    tp=entry+tgt_r*risk if L else entry-tgt_r*risk
    end=min(i0+1+maxd,len(d['c']))
    if i0+1>=len(d['c']): return None
    for j in range(i0+1,end):
        hs=(d['l'][j]<=stop) if L else (d['h'][j]>=stop); ht=(d['h'][j]>=tp) if L else (d['l'][j]<=tp)
        if hs: return (-1-sp/risk,j-i0,'SL',j,stop,risk)
        if ht: return (tgt_r-sp/risk,j-i0,'TP',j,tp,risk)
    c=d['c'][end-1]; r=((c-entry) if L else (entry-c))/risk
    return (r-sp/risk,end-1-i0,'Zeit',end-1,c,risk)
def stats(tr):
    if not tr: return None
    r=np.array([x['r'] for x in tr]); w=(r>0).sum(); l=r[r<=0]
    pf=r[r>0].sum()/abs(l.sum()) if len(l) and l.sum()!=0 else float('nan')
    eq=np.cumsum(r); dd=float((np.maximum.accumulate(eq)-eq).max())
    ms=cur=0
    for x in r:
        cur=cur+1 if x<=0 else 0; ms=max(ms,cur)
    yrs={}
    for x in tr: yrs.setdefault(x['date'][:4],[]).append(x['r'])
    ypos=sum(1 for v in yrs.values() if np.mean(v)>0)
    # Bootstrap 95%-KI fuer Ø R
    rng=np.random.default_rng(1); bs=[rng.choice(r,len(r)).mean() for _ in range(400)]
    return dict(n=len(r),avg=float(r.mean()),wr=100*w/len(r),pf=float(pf),dd=dd,ms=ms,tage=float(np.mean([x['days'] for x in tr])),ylen=len(yrs),ypos=ypos,lo=float(np.percentile(bs,2.5)),hi=float(np.percentile(bs,97.5)))

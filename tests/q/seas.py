import sys,json,random,datetime as dt,numpy as np
from eng import load_all,atr,stats
U=load_all()
SYMS=sorted(U)
def cost_r(sym,stopd,a,cal):
    if sym=='GOLD': return (0.05*a+0.012*a*cal)/stopd
    p=0.01 if sym.endswith('JPY') else 0.0001
    return (1.0+0.3*cal)*p/stopd   # 1 Pip Spread + 0.3 Pip Swap je Kalendertag (Annahme)
P={}
for s in SYMS:
    d=U[s]; ts=[dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).date() for t in d['t']]
    P[s]=dict(d=d,ts=ts,a=atr(d),yr=np.array([x.year for x in ts]),idx={x:i for i,x in enumerate(ts)})
def first_on_or_after(s,date):
    ts=P[s]['ts']; lo,hi=0,len(ts)
    while lo<hi:
        m=(lo+hi)//2
        if ts[m]<date: lo=m+1
        else: hi=m
    return lo if lo<len(ts) else None
def trade(s,i,N,L,shift=0):
    """Einstieg Schlusskurs Bar i, Stopp 2 ATR, Zeitausstieg nach N Bars. Rueckgabe r (netto), Bar-Ende"""
    d=P[s]['d']; a=P[s]['a'][i]
    if np.isnan(a) or i+N>=len(d['c']): return None
    e=d['c'][i]; sd=2*a; stp=e-sd if L else e+sd
    for j in range(i+1,i+N+1):
        if (d['l'][j]<=stp) if L else (d['h'][j]>=stp):
            r=-1; break
    else:
        r=((d['c'][i+N]-e) if L else (e-d['c'][i+N]))/sd; j=i+N
    cal=(P[s]['ts'][j]-P[s]['ts'][i]).days
    return r-cost_r(s,sd,a,cal),j
def cells(N,step,fixed=None):
    """Kandidaten (Monat,Tag)"""
    out=[]
    if fixed: return fixed
    for m in range(1,13):
        for dd in range(1,29,step): out.append((m,dd))
    return out
def run(N,step,thr,minyrs,mean_min,mode='fenster',null=0,seed=0):
    rnd=random.Random(seed); trades=[]
    for s in SYMS:
        busy=-1
        # Matrix: je Zelle Jahr -> (idx, r_long) , r_short nicht gleich -r (Stopp) -> beide rechnen
        years=sorted(set(P[s]['yr'])); 
        R={}
        for (m,dd) in cells(N,step):
            for y in years:
                try: date=dt.date(y,m,dd)
                except: continue
                i=first_on_or_after(s,date)
                if i is None or P[s]['ts'][i]>date+dt.timedelta(days=5): continue
                lo=trade(s,i,N,True); sh=trade(s,i,N,False)
                if lo and sh: R[(m,dd,y)]=(i,lo[0],sh[0],lo[1])
        for y in years:
            if y<years[0]+minyrs: continue
            sig=[]
            for (m,dd) in cells(N,step):
                past=[R[(m,dd,yy)] for yy in years if yy<y and (m,dd,yy) in R]
                if len(past)<minyrs: continue
                for L,k in ((True,1),(False,2)):
                    rs=np.array([p[k] for p in past]); wr=(rs>0).mean()
                    if wr>=thr and rs.mean()>=mean_min: sig.append((wr,m,dd,L,rs.mean()))
            sig.sort(reverse=True)
            for wr,m,dd,L,mn in sig:
                if (m,dd,y) not in R: continue
                if null:   # Nullmodell: Einstieg an zufaellig verschobenem Datum, gleiche Richtung
                    off=rnd.randint(40,300); date=dt.date(y,m,dd)+dt.timedelta(days=off)
                    i=first_on_or_after(s,date)
                    if i is None: continue
                    t=trade(s,i,N,L)
                    if not t: continue
                    r,j=t[0],t[1]; i0=i
                else:
                    i0,rl,rs_,j=R[(m,dd,y)]; r=rl if L else rs_
                if i0<=busy: continue
                busy=j; trades.append(dict(sym=s,date=str(P[s]['ts'][i0]),dir='long' if L else 'short',r=float(r),wr=float(wr),win=f'{m:02d}-{dd:02d}',N=N))
    return trades
def summ(tr):
    if not tr: return None
    r=np.array([x['r'] for x in tr]); eq=np.cumsum(r)
    yrs=sorted(set(x['date'][:4] for x in tr)); span=max(1,len(yrs))
    return dict(n=len(r),wr=float((r>0).mean()*100),avg=float(r.mean()),pf=float(r[r>0].sum()/abs(r[r<=0].sum())) if (r<=0).any() else 99,jahr=float(r.sum()/ (len(set(x['date'][:4] for x in tr)) or 1)),dd=float((np.maximum.accumulate(eq)-eq).max()))
if __name__=='__main__':
    CFG={'s1':(10,7,0.75,6,0.05),'s2':(20,7,0.75,6,0.05),'s3':(5,3,0.80,6,0.03),'s4':(10,7,0.80,6,0.10),'s5':(30,14,0.75,6,0.05)}
    out={}
    for k,(N,step,thr,my,mm) in CFG.items():
        tr=run(N,step,thr,my,mm); nl=run(N,step,thr,my,mm,null=1,seed=1)
        te=[x for x in tr if x['date']>='2023-01-01']
        print(k,N,step,thr,'real',summ(tr),'| 2023+',summ(te),'| null',summ(nl),flush=True)
        out[k]=tr
    json.dump(out,open('/tmp/seas.json','w'))

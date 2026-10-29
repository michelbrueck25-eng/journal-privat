import sys,itertools,json,statistics
sys.path.insert(0,'/tmp/w')
from sim import *

def cot_mode(s,mode):
    if mode=='none': return True
    b,q=s['sym'][:3],s['sym'][3:]
    cb,cq=cot_at(b,s['date']),cot_at(q,s['date'])
    if cb is None or cq is None: return False
    if mode=='rel': return (cb>cq) if s['dir']=='long' else (cb<cq)
    if mode=='ext': return (cb>=60 and cq<=40) if s['dir']=='long' else (cb<=40 and cq>=60)
def trade(s,P):
    sym=s['sym'];Dd=D[sym];i=s['i'];dirn=s['dir'];lo,hi=s['lo'],s['hi'];sp=pip(sym)
    a=ob.atr(Dd,i); L=dirn=='long'
    if P['entry']=='edge' or P['entry']=='mid':
        entry=(hi if L else lo) if P['entry']=='edge' else (lo+hi)/2
        # Limit muss in/nach Touch-Kerze erreichbar sein: Touch-Kerze hat Zone beruehrt; fuer mid erst ab naechster Kerze fuellen
        if P['entry']=='mid':
            fill=None
            for j in range(i,min(i+4,len(Dd)-1)):
                if (Dd[j][3]<=entry if L else Dd[j][2]>=entry): fill=j;break
            if fill is None: return None
            i0=fill+1
        else: i0=i+1
        stop=(lo-P['buf']*a) if L else (hi+P['buf']*a)
        if P['entry']=='mid' and abs(entry-stop)<=0: return None
        i_start=i0
    else:
        n=P['n'];ext=Dd[i][3] if L else Dd[i][2];conf=None
        for j in range(i,min(i+1+P['win'],len(Dd)-1)):
            t,o,h,l,c=Dd[j]
            ext=min(ext,l) if L else max(ext,h)
            if L and c<lo: break
            if (not L) and c>hi: break
            if j>i:
                prev=Dd[max(i-n+1,0):j]
                if L and c>max(x[2] for x in prev): conf=j;break
                if (not L) and c<min(x[3] for x in prev): conf=j;break
        if conf is None: return None
        entry=Dd[conf][4]
        stop=(ext-P['buf']*a) if L else (ext+P['buf']*a)
        if abs(entry-stop)>P['cap']*a: return None
        i_start=conf+1
    risk=abs(entry-stop)
    if risk<=0: return None
    if P['entry'] in ('edge','mid'):
        fc=i if P['entry']=='edge' else fill
        if ((Dd[fc][3]<=stop) if L else (Dd[fc][2]>=stop)): return (-1-sp/risk,1,risk/sp)
    # Simulation mit optionalem Break-even
    tp=entry+(P['tgt']*risk if L else -P['tgt']*risk); st=stop; be=False
    end=min(i_start+P['maxd'],len(Dd))
    if i_start>=len(Dd): return None
    for j in range(i_start,end):
        t,o,h,l,c=Dd[j]
        hs=(l<=st) if L else (h>=st); ht=(h>=tp) if L else (l<=tp)
        if hs: r=(-1 if not be else 0)-sp/risk; return (r,j-i_start+1,risk/sp)
        if ht: return (P['tgt']-sp/risk,j-i_start+1,risk/sp)
        if P['be'] and not be:
            trig=entry+(P['be']*risk if L else -P['be']*risk)
            if (h>=trig) if L else (l<=trig): be=True; st=entry
    c=Dd[end-1][4]; r=((c-entry) if L else (entry-c))/risk
    return (r-sp/risk,end-i_start,risk/sp)
def evalP(P,subset):
    out=[]
    for s in subset:
        if P['q']=='AB' and s['q']=='C': continue
        if P['dir']!='both' and s['dir']!=P['dir']: continue
        if not cot_mode(s,P['cot']): continue
        t=trade(s,P)
        if t: out.append((s['date'],)+t)
    return out
def st_(o):
    if not o: return None
    r=[x[1] for x in o]; w=sum(1 for x in r if x>0)
    return dict(n=len(r),avg=round(sum(r)/len(r),3),wr=round(100*w/len(r),1),tage=round(sum(x[2] for x in o)/len(o),1),stop=round(sum(x[3] for x in o)/len(o),1))
dates=sorted(s['date'] for s in S); mid=dates[len(dates)*6//10]
TR=[s for s in S if s['date']<=mid]; TE=[s for s in S if s['date']>mid]

import sim as _sim
SD=json.load(open('/tmp/w/setups_d.json'))
for s in SD: D.setdefault(s['sym'],load(s['sym'],'D'))
WK={}
def htf_ok(s):
    sym=s['sym']
    if sym not in WK: WK[sym]=load(sym,'W')
    W=WK[sym]; import datetime as dt
    cut=dt.datetime.strptime(s['date'],'%Y-%m-%d').replace(tzinfo=dt.timezone.utc).timestamp()*1000-7*86400e3
    cl=[r[4] for r in W if r[0]<=cut]
    if len(cl)<22: return False
    sma=sum(cl[-20:])/20
    return (cl[-1]>sma) if s['dir']=='long' else (cl[-1]<sma)
_old=evalP
def evalP2(P,subset):
    out=[]
    for s in subset:
        if P['q']=='AB' and s['q']=='C': continue
        if P['htf']=='wk' and not htf_ok(s): continue
        if not cot_mode(s,P['cot']): continue
        t=trade(s,P)
        if t: out.append((s['date'],)+t)
    return out
dates=sorted(s['date'] for s in SD); mid=dates[len(dates)*6//10]
TR=[s for s in SD if s['date']<=mid]; TE=[s for s in SD if s['date']>mid]
grid=[]
for entry in ('edge','mid','conf'):
  for tgt in (1.0,1.5,2.0):
    for maxd in (5,7,10):
      for be in (0,1.0):
        for cot in ('none','rel'):
          for htf in ('none','wk'):
            for q in ('all','AB'):
              base=dict(entry=entry,tgt=tgt,maxd=maxd,be=be,cot=cot,htf=htf,q=q,dir='both',n=0,win=0,buf=0.1,cap=9)
              if entry!='conf': grid.append(base)
              else:
                for n in (1,3):
                  for cap in (1.5,3.0): grid.append(dict(base,n=n,win=5,cap=cap))
print(len(grid),flush=True)
res=[]
for P in grid:
    a=st_(evalP2(P,TR)); b=st_(evalP2(P,TE)); c=st_(evalP2(P,SD))
    if a and b and c: res.append((P,a,b,c))
import pickle; pickle.dump(res,open('/tmp/w/gridd2.pkl','wb'))
print('done',len(res),flush=True)

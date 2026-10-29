import json,csv,sys,glob,os,datetime as dt,random,statistics as st
sys.path.insert(0,'/home/claude/journal-privat')
import ob_check as ob
HOME='/home/claude/journal-privat'
def load(sym,tf):
    p=f'{HOME}/marktdaten/{sym}_{tf}.json'
    return json.load(open(p))['rows'] if os.path.exists(p) else None
# COT
cot={}
for r in csv.DictReader(open('/home/claude/journal-daten/cot.csv',encoding='utf-8')):
    try: cot.setdefault(r['waehrung'],[]).append((r['datum'],int(r['comm_long'])-int(r['comm_short'])))
    except: pass
for k in cot: cot[k].sort()
def cot_at(cur,date,n=26):
    v=[x[1] for x in cot.get(cur,[]) if x[0]<=date][-n:]
    if len(v)<n or max(v)==min(v): return None
    return 100*(v[-1]-min(v))/(max(v)-min(v))
def pip(sym): return 0.01 if sym.endswith('JPY') else 0.0001
syms=sorted({os.path.basename(p).split('_')[0] for p in glob.glob(f'{HOME}/marktdaten/*_D.json')})
D0=None
res=[]  # setups
for sym in syms:
    W=load(sym,'W'); D=load(sym,'D')
    base,quote=sym[:3],sym[3:]
    dday=[ob.day(r[0]) for r in D]
    d_start=dday[0]
    for dirn in ('long','short'):
        # point-in-time OBs: evaluate at each weekly bar k (ob known when formed; use rows up to k)
        seen={}
        for k in range(30,len(W)):
            rows=W[:k+1]
            for o in ob.find_obs(rows,dirn):
                if o['mitigated']: continue
                key=o['t']
                if key not in seen: seen[key]=(o,k)
        for key,(o,k) in seen.items():
            valid_from=ob.day(W[k][0])  # known at end of that week
            # zone first touched by daily candle after valid_from+7d, before mitigation
            lo,hi=o['lo'],o['hi']
            start=next((i for i,d in enumerate(dday) if d>valid_from),None)
            if start is None: continue
            for i in range(max(start,10),len(D)-1):
                t,op,h,l,c=D[i]
                if c<lo and dirn=='long' or c>hi and dirn=='short': break  # mitigated
                touch = (l<=hi and h>=lo)
                if touch:
                    res.append(dict(sym=sym,dir=dirn,lo=lo,hi=hi,q=o['q'],i=i,date=dday[i],atrw=None)); break
json.dump(res,open('/tmp/w/setups.json','w'))
print(len(res),'setups')

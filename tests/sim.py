import json,sys,os,random,csv
sys.path.insert(0,'/home/claude/journal-privat')
HOME='/home/claude/journal-privat'
import ob_check as ob
def load(sym,tf): return json.load(open(f'{HOME}/marktdaten/{sym}_{tf}.json'))['rows']
cot={}
for r in csv.DictReader(open('/home/claude/journal-daten/cot.csv',encoding='utf-8')):
    try: cot.setdefault(r['waehrung'],[]).append((r['datum'],int(r['comm_long'])-int(r['comm_short'])))
    except: pass
for k in cot: cot[k].sort()
def cot_at(cur,date,n=26):
    v=[x[1] for x in cot.get(cur,[]) if x[0]<=date][-n:]
    if len(v)<n or max(v)==min(v): return None
    return 100*(v[-1]-min(v))/(max(v)-min(v))
def pip(s): return 0.01 if s.endswith('JPY') else 0.0001
S=json.load(open('/tmp/w/setups.json'))
D={}
def cotok(s):
    b,q=s['sym'][:3],s['sym'][3:]
    cb,cq=cot_at(b,s['date']),cot_at(q,s['date'])
    if cb is None or cq is None: return None
    return (cb>cq) if s['dir']=='long' else (cb<cq)
def sim(entry,stop,dirn,Dd,i0,tgt_r,maxd,spread):
    risk=abs(entry-stop)
    if risk<=0: return None
    tp=entry+(tgt_r*risk if dirn=='long' else -tgt_r*risk)
    end=min(i0+maxd,len(Dd))
    if i0>=len(Dd): return None
    for j in range(i0,end):
        t,o,h,l,c=Dd[j]
        hs=(l<=stop) if dirn=='long' else (h>=stop)
        ht=(h>=tp) if dirn=='long' else (l<=tp)
        if hs: return -1-spread/risk,j-i0+1
        if ht: return tgt_r-spread/risk,j-i0+1
    c=Dd[end-1][4]
    r=((c-entry) if dirn=='long' else (entry-c))/risk
    return r-spread/risk,end-i0
def run(variant,tgt,maxd,cotf,spread_pips=1.0,confirm_days=5,S=S):
    out=[]
    for s in S:
        if cotf and not cotok(s): continue
        sym=s['sym']; Dd=D.setdefault(sym,load(sym,'D')); i=s['i']; dirn=s['dir']
        lo,hi=s['lo'],s['hi']; sp=spread_pips*pip(sym)
        a=ob.atr(Dd,i)
        if variant=='A':
            entry=hi if dirn=='long' else lo
            stop=(lo-0.1*a) if dirn=='long' else (hi+0.1*a)
            r=sim(entry,stop,dirn,Dd,i+1,tgt,maxd,sp)
            if r: out.append((s,r[0],r[1],abs(entry-stop)/pip(sym)))
        else:
            ext=Dd[i][3] if dirn=='long' else Dd[i][2]; conf=None
            for j in range(i,min(i+1+confirm_days,len(Dd)-1)):
                t,o,h,l,c=Dd[j]
                ext=min(ext,l) if dirn=='long' else max(ext,h)
                if dirn=='long' and c<lo: break
                if dirn=='short' and c>hi: break
                if j>i:
                    prev=Dd[max(i-2,0):j]
                    if dirn=='long' and c>max(x[2] for x in prev): conf=j;break
                    if dirn=='short' and c<min(x[3] for x in prev): conf=j;break
            if conf is None: continue
            entry=Dd[conf][4]
            stop=(ext-0.1*a) if dirn=='long' else (ext+0.1*a)
            risk=abs(entry-stop)
            if risk>2.5*a: continue
            r=sim(entry,stop,dirn,Dd,conf+1,tgt,maxd,sp)
            if r: out.append((s,r[0],r[1],risk/pip(sym)))
    return out
def stats(o):
    r=[x[1] for x in o]
    if not r: return None
    w=[x for x in r if x>0]; l=[x for x in r if x<=0]
    pf=round(sum(w)/abs(sum(l)),2) if l and sum(l)!=0 else None
    eq=pk=dd=streak=ms=0
    for x in r:
        eq+=x;pk=max(pk,eq);dd=max(dd,pk-eq)
        if x<=0: streak+=1;ms=max(ms,streak)
        else: streak=0
    return dict(n=len(r),avgR=round(sum(r)/len(r),2),wr=round(100*len(w)/len(r)),pf=pf,dd=round(dd,1),ms=ms,tage=round(sum(x[2] for x in o)/len(o),1),stop_pips=round(sum(x[3] for x in o)/len(o),1))
if __name__=='__main__':
    for v in 'AB':
        for cf in (False,True):
            for tgt in (1.0,1.5,2.0):
                print(v,'cot' if cf else 'ohne',tgt,stats(run(v,tgt,7,cf)))

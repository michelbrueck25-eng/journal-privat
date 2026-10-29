import json,sys,os,glob
sys.path.insert(0,'/home/claude/journal-privat')
import ob_check as ob
HOME='/home/claude/journal-privat'
def load(sym,tf): return json.load(open(f'{HOME}/marktdaten/{sym}_{tf}.json'))['rows']
syms=sorted({os.path.basename(p).split('_')[0] for p in glob.glob(f'{HOME}/marktdaten/*_D.json')})
out=[]
for sym in syms:
    D=load(sym,'D'); dday=[ob.day(r[0]) for r in D]
    for dirn in ('long','short'):
        seen={}
        for k in range(30,len(D)-1):
            for o in ob.find_obs(D[:k+1],dirn):
                if o['mitigated']: continue
                if o['t'] not in seen: seen[o['t']]=(o,k)
        for key,(o,k) in seen.items():
            lo,hi=o['lo'],o['hi']
            for i in range(k+1,len(D)-1):
                t,op,h,l,c=D[i]
                if (c<lo if dirn=='long' else c>hi): break
                if l<=hi and h>=lo:
                    out.append(dict(sym=sym,dir=dirn,lo=lo,hi=hi,q=o['q'],i=i,date=dday[i],zi=o['i'])); break
json.dump(out,open('/tmp/w/setups_d.json','w'))
print(len(out))

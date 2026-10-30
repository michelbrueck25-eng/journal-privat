import json,pickle,random,numpy as np,datetime as dt,sys,os
_t=open('ideen6.py').read(); exec(_t[:_t.index('\nres=[]\ndef add(')])
rnd=random.Random(7); nprng=np.random.default_rng(3)
CFGS={ # id: (name, signalfunc, sa, tg, N, beschreibung-regeln)
 'fw6-d1':('COT-Veränderung 8 Wochen folgen · 40 Tage',lambda:S_cot('comm',156,1,'folgen',50,delta=8),4,None,40),
 'fw6-d2':('COT-Veränderung 8 Wochen folgen · 20 Tage',lambda:S_cot('comm',156,1,'folgen',50,delta=8),3,None,20),
 'fw6-p1':('COT Top gegen Flop · Stopp 3 ATR · 15 Tage (Winrate-Profil 59 %)',lambda:S_cot('comm',156,1,'folgen',70),3,None,15),
 'fw6-p2':('COT Top gegen Flop · Stopp 6 ATR, Ziel 4 R · 40 Tage',lambda:S_cot('comm',156,1,'folgen',70),6,4,40),
 'fw6-g1':('Gold COT Commercials Umkehr · 104 Wochen · 20 Tage',lambda:S_gold(104,'Umkehr',20),3,None,20),
}
LIM=10.;TARGET=5.;CAP=1.5
def plan(r,py,note):
    n=max(5,int(round(py)));d=[]
    for _ in range(2000):
        x=nprng.choice(r,n);eq=np.cumsum(x);d.append(float((np.maximum.accumulate(np.r_[0,eq])[1:]-eq).max()))
    d50,d95=np.percentile(d,[50,95]);risk=min(CAP,TARGET/max(d95,1e-9));risk=round(risk*20)/20 if risk>=0.05 else round(risk,2)
    return dict(empfohlen_pct=float(risk),dd_median_pct=round(float(d50*risk),1),dd95_pct=round(float(d95*risk),1),monat_pct=round(float(np.mean(r)*py*risk/12),2),trades_pro_jahr=n,annahme='Gesamtverlust-Limit 10 %, Ziel-Drawdown (95 %) höchstens 5 %, Deckel 1,5 % je Trade. '+note)
out={};TR={}
for sid,(name,fn,sa,tg,N) in CFGS.items():
    sg=fn(); tr=runsig(sg,sa,tg,N); a,b,c=summ(tr); r=np.array([x['r'] for x in tr]); TR[sid]=tr
    reals=r.mean(); nulls=[]
    for _ in range(150):
        sh=[]
        for (s,i,L) in sg:
            j=i+rnd.randint(30,250)
            if j<len(P[s]['d']['c'])-2: sh.append((s,j,L))
        t=runsig(sh,sa,tg,N)
        if t: nulls.append(np.mean([x['r'] for x in t]))
    nulls=np.array(nulls); bs=np.percentile([np.mean(nprng.choice(r,len(r))) for _ in range(2000)],[5,95])
    out[sid]=dict(a=a,b=b,c=c,nullm=float(nulls.mean()),null95=float(np.percentile(nulls,95)),nullge=float((nulls>=reals).mean()),ci=[float(bs[0]),float(bs[1])],r=r.tolist(),tr=tr)
    print(sid,a,'null',round(nulls.mean(),3),round(np.percentile(nulls,95),3),'ge',(nulls>=reals).mean(),'CI',bs.round(2),flush=True)
# Korrelation und Portfolio (Monatsrenditen in R), inkl. c1,c2 aus ideen2
c1=runsig(sig_cot(156,1,'folgen',70),3,None,20); c2=runsig(sig_cot(156,2,'folgen',70),4,None,40)
TR['fw5-c1']=c1;TR['fw5-c2']=c2
def monthly(tr):
    m={}
    for x in tr: m[x['date'][:7]]=m.get(x['date'][:7],0)+x['r']
    return m
allm=sorted(set(k for t in TR.values() for k in monthly(t)))
M={k:np.array([monthly(t).get(m,0) for m in allm]) for k,t in TR.items()}
ids=list(M);C=np.corrcoef([M[k] for k in ids]);print(ids);print(np.round(C,2))
port=sum(M[k] for k in ids);eq=np.cumsum(port);dd=float((np.maximum.accumulate(eq)-eq).max())
print('Portfolio Summe R/Jahr',port.sum()/ (len(allm)/12),'Max-DD R',dd)
pickle.dump((out,{k:C[i].tolist() for i,k in enumerate(ids)},ids,dict(jahr=float(port.sum()/(len(allm)/12)),dd=dd)),open('/tmp/build6.pkl','wb'))

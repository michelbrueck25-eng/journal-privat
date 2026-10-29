import pickle,numpy as np,pandas as pd,datetime as dt
from ideen import *
cot=pd.read_csv('/home/claude/journal-daten/cot.csv'); C8=['AUD','CAD','CHF','EUR','GBP','JPY','NZD','USD']
cot=cot[cot.waehrung.isin(C8)].copy(); cot['net']=cot.comm_long-cot.comm_short; cot['datum']=pd.to_datetime(cot.datum)
def sig_cot(lb,k,mode,minspread,hold_wd=0):
    piv=cot.pivot_table(index='datum',columns='waehrung',values='net').sort_index()
    idx=(piv-piv.rolling(lb).min())/(piv.rolling(lb).max()-piv.rolling(lb).min())*100
    sigs=[]
    for t,row in idx.dropna().iterrows():
        avail=t+pd.Timedelta(days=6)     # Dienstag-Stand, Freitag veroeffentlicht, Handel ab Montag danach
        sym_day=None
        r=row.sort_values()
        for q in range(k):
            lo,hi=r.index[q],r.index[-1-q]
            if r.iloc[-1-q]-r.iloc[q]<minspread: continue
            top,bot=(hi,lo) if mode=='folgen' else (lo,hi)
            sym=top+bot if top+bot in P else bot+top
            L=(sym[:3]==top)
            # Signalbar: letzter Handelstag vor avail (Freitag/Sonntag-Abgleich) -> Bar am Datum avail-1
            d0=(avail-pd.Timedelta(days=1)).date()
            i=P[sym]['idx'].get(d0)
            if i is None:
                for back in (1,2,3):
                    i=P[sym]['idx'].get(d0-dt.timedelta(days=back))
                    if i is not None: break
            if i is not None: sigs.append((sym,i,L))
    return sigs
res=[]
def add(name,sigs,sa,tg,N):
    tr=runsig(sigs,sa,tg,N); a,b,c=summ(tr); res.append(dict(name=name,sa=sa,tg=tg,N=N,all=a,dev=b,test=c,_tr=tr)); print(name,sa,tg,N,'| alle',a,'| dev',b.get('avg'),b.get('n'),'| test',c.get('avg'),c.get('n'),flush=True)
for lb in (52,156):
  for k in (1,2):
    for mode in ('folgen','Umkehr'):
      for ms in (40,70):
        sg=sig_cot(lb,k,mode,ms)
        for (sa,tg,N) in ((3,None,10),(3,None,20),(4,None,40)): add(f'COT {lb}W k{k} {mode} Abstand{ms}',sg,sa,tg,N)
for Lb in (120,250):
  for k in (1,2):
    for rev in (False,True):
      sg=sig_basket(Lb,k,rev)
      for (sa,tg,N) in ((3,None,20),(4,None,40)): add(f'Korb L{Lb} k{k} {"Umkehr" if rev else "Trend"}',sg,sa,tg,N)
pickle.dump(res,open('/tmp/ideen2.pkl','wb'))
r=[x for x in res if x['all'].get('avg') is not None]; r.sort(key=lambda x:-x['all']['avg'])
print('---TOP');[print(x['name'],x['sa'],x['tg'],x['N'],x['all']['n'],x['all']['avg'],'dev',x['dev']['avg'],'test',x['test']['avg'],x['test']['n'],'dd',x['all']['dd'],'j',x['all']['jahr']) for x in r[:10]]
print(len(res),'Varianten',sum(1 for x in r if x['all']['avg']>=0.15),'>=0.15')

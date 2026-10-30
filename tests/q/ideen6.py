import pickle
src=open('ideen2.py').read().split('res=[]')[0]; exec(src)
from eng import wk_trend
cotall=pd.read_csv('/home/claude/journal-daten/cot.csv'); cotall['datum']=pd.to_datetime(cotall.datum)
def idx_of(measure,lb,syms):
    c=cotall[cotall.waehrung.isin(syms)].copy()
    c['v']={'comm':c.comm_long-c.comm_short,'nc':c.noncomm_long-c.noncomm_short,'nr':c.nonrep_long-c.nonrep_short}[measure]
    piv=c.pivot_table(index='datum',columns='waehrung',values='v').sort_index()
    ind=(piv-piv.rolling(lb).min())/(piv.rolling(lb).max()-piv.rolling(lb).min())*100
    return piv,ind
def pair_sig(row,k,mode,minspread):
    r=row.sort_values(); out=[]
    for q in range(k):
        lo,hi=r.index[q],r.index[-1-q]
        if r.iloc[-1-q]-r.iloc[q]<minspread: continue
        top,bot=(hi,lo) if mode=='folgen' else (lo,hi)
        sym=top+bot if top+bot in P else bot+top
        out.append((sym,sym[:3]==top))
    return out
def sigdate(sym,t):
    d0=(t+pd.Timedelta(days=5)).date()
    for back in range(0,4):
        i=P[sym]['idx'].get(d0-dt.timedelta(days=back))
        if i is not None: return i
def S_cot(measure,lb,k,mode,ms,delta=0,trend=False):
    piv,ind=idx_of(measure,lb,C8)
    if delta: ind=ind-ind.shift(delta)
    out=[]
    for t,row in ind.dropna().iterrows():
        for sym,L in pair_sig(row,k,mode,ms):
            i=sigdate(sym,t)
            if i is None: continue
            if trend:
                tr=wk_trend(P[sym]['d']); 
                if (tr[i]>0)!=L or tr[i]==0: continue
            out.append((sym,i,L))
    return out
def S_gold(lb,mode,thr):
    piv,ind=idx_of('comm',lb,['GOLD']); out=[]
    for t,v in ind['GOLD'].dropna().items():
        i=sigdate('GOLD',t)
        if i is None: continue
        if v>=100-thr: out.append(('GOLD',i,mode=='folgen'))
        elif v<=thr: out.append(('GOLD',i,mode!='folgen'))
    return out
res=[]
def add(name,sigs,sa,tg,N,fam):
    tr=runsig(sigs,sa,tg,N); a,b,c=summ(tr); res.append(dict(name=name,fam=fam,sa=sa,tg=tg,N=N,all=a,dev=b,test=c,_tr=tr)); return a
def log(n,a): print(n,a and (a['n'],a.get('avg'),a.get('wr'),a.get('pf'),a.get('dd')),flush=True)
for meas,nm in (('nc','Non-Commercials'),('nr','Retail')):
    for mode in ('folgen','Umkehr'):
        for lb in (52,156):
            for ms in (60,80):
                sg=S_cot(meas,lb,1,mode,ms)
                for (sa,N) in ((3,20),(4,40)): log(f'{nm} {mode} {lb} {ms} {N}',add(f'COT {nm} {mode} {lb}W Abstand {ms} {N} Tage',sg,sa,None,N,'cot-'+meas))
for lb in (156,):
    for d in (4,8):
        for mode in ('folgen','Umkehr'):
            sg=S_cot('comm',lb,1,mode,50,delta=d)
            for (sa,N) in ((3,20),(4,40)): log(f'Aenderung {d}W {mode} {N}',add(f'COT Commercials Veränderung {d} Wochen {mode} {N} Tage',sg,sa,None,N,'cot-delta'))
for ms in (60,70,80):
    sg=S_cot('comm',156,1,'folgen',ms,trend=True)
    for (sa,N) in ((3,20),(4,40)): log(f'Comm+Wochentrend {ms} {N}',add(f'COT Commercials + Wochentrend Abstand {ms} {N} Tage',sg,sa,None,N,'cot-trend'))
for lb in (104,156,260):
    for thr in (10,20):
        for mode in ('folgen','Umkehr'):
            sg=S_gold(lb,mode,thr)
            for (sa,N) in ((3,20),(4,40)): log(f'Gold {lb} {thr} {mode} {N}',add(f'Gold COT Commercials {mode} {lb}W Schwelle {thr} {N} Tage',sg,sa,None,N,'gold'))
# Profile: Winrate-/Ziel-Variation auf Commercials-Signal
sg=S_cot('comm',156,1,'folgen',70)
for (sa,tg,N) in ((1.5,0.5,20),(2,1,20),(3,1,20),(3,1.5,20),(4,2,30),(5,3,30),(6,4,40),(3,None,10),(3,None,15),(2,None,20)):
    log(f'Profil sa{sa} tg{tg} N{N}',add(f'COT Commercials Top gegen Flop Profil Stopp {sa} ATR Ziel {tg} R {N} Tage',sg,sa,tg,N,'profil'))
pickle.dump(res,open('/tmp/ideen6.pkl','wb'))
r=[x for x in res if x['all'].get('avg') is not None]; r.sort(key=lambda x:-x['all']['avg'])
print('---TOP')
for x in r[:14]: print(x['name'],x['all']['n'],x['all']['avg'],x['all']['wr'],'dev',x['dev']['avg'],x['dev']['n'],'test',x['test']['avg'],x['test']['n'],'dd',x['all']['dd'],'j',x['all']['jahr'])
print(len(res),sum(1 for x in r if x['all']['avg']>=0.15),'>=0.15, Median',np.median([x['all']['avg'] for x in r]))

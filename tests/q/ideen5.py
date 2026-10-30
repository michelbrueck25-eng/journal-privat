import pickle
src=open('ideen2.py').read().split('res=[]')[0]; exec(src)
from eng import wk_trend
res=[]
def add(name,sigs,sa,tg,N,fam):
    tr=runsig(sigs,sa,tg,N); a,b,c=summ(tr); res.append(dict(name=name,fam=fam,sa=sa,tg=tg,N=N,all=a,dev=b,test=c,_tr=tr)); return a
def F(s):
    d=P[s]['d']; return d,pd.Series(d['c']),pd.Series(d['h']),pd.Series(d['l']),wk_trend(d)
# 1 Zeitreihen-Momentum, monatlich
def S_tsmom(L):
    out=[]
    for s in FX:
        d,c,h,l,tr=F(s); r=c/c.shift(L)-1; ts=P[s]['ts']
        for i in range(L+5,len(c)-2):
            if ts[i].month!=ts[i+1].month:   # letzter Handelstag des Monats
                if r[i]>0: out.append((s,i,True))
                elif r[i]<0: out.append((s,i,False))
    return out
# 2 Fair-Value-Gap
def S_fvg(minatr,use_tr):
    out=[]
    for s in FX:
        d,c,h,l,tr=F(s); at=P[s]['a']; hh=h.values; ll=l.values; cc=c.values
        for i in range(30,len(c)-3):
            # bullische Luecke: Tief[i] > Hoch[i-2] (3-Kerzen-Muster Mitte i-1)
            if ll[i]>hh[i-2] and (ll[i]-hh[i-2])>=minatr*at[i] and (not use_tr or tr[i]>0):
                # Rücksetzer in die Luecke innerhalb 8 Tagen: Signal beim ersten Tag, an dem Tief <= Luecken-Mitte und Schluss > Luecken-Unterkante
                mid=(ll[i]+hh[i-2])/2
                for j in range(i+1,min(i+9,len(c)-2)):
                    if ll[j]<=mid and cc[j]>hh[i-2]: out.append((s,j,True)); break
                    if cc[j]<hh[i-2]: break
            if hh[i]<ll[i-2] and (ll[i-2]-hh[i])>=minatr*at[i] and (not use_tr or tr[i]<0):
                mid=(hh[i]+ll[i-2])/2
                for j in range(i+1,min(i+9,len(c)-2)):
                    if hh[j]>=mid and cc[j]<ll[i-2]: out.append((s,j,False)); break
                    if cc[j]>ll[i-2]: break
    return out
# 3 Liquiditaets-Sweep
def S_sweep(n,mode):
    out=[]
    for s in FX:
        d,c,h,l,tr=F(s); hh=h.rolling(n).max().shift(1).values; ll=l.rolling(n).min().shift(1).values
        for i in range(n+2,len(c)-2):
            if d['l'][i]<ll[i] and d['c'][i]>ll[i] and (mode=='fade' or tr[i]>0) and (mode!='trend' or tr[i]>0): out.append((s,i,True))
            if d['h'][i]>hh[i] and d['c'][i]<hh[i] and (mode=='fade' or tr[i]<0) and (mode!='trend' or tr[i]<0): out.append((s,i,False))
    return out
# 4 Dreiecks-Residual (EURGBP gegen EURUSD/GBPUSD usw.)
def S_tri(z_thr,Lb):
    out=[];trip=[('EURGBP','EURUSD','GBPUSD'),('EURJPY','EURUSD','USDJPY'),('GBPJPY','GBPUSD','USDJPY'),('AUDNZD','AUDUSD','NZDUSD'),('EURCHF','EURUSD','USDCHF'),('AUDJPY','AUDUSD','USDJPY'),('NZDJPY','NZDUSD','USDJPY'),('EURAUD','EURUSD','AUDUSD'),('GBPAUD','GBPUSD','AUDUSD')]
    for a,b,c_ in trip:
        # synthetisch: a = b / c_ (fuer USD-Quote/USD-Basis), Vorzeichen je nach Konstellation
        def ser(s): x=pd.Series(P[s]['d']['c'],index=pd.to_datetime(P[s]['ts'])); return x[~x.index.duplicated(keep='last')]
        A,B,C=ser(a),ser(b),ser(c_)
        df=pd.concat([A,B,C],axis=1,keys=['a','b','c']).dropna()
        for synth in (df.b/df.c, df.b*df.c):
            pass
        cands={'div':np.log(df.a)-(np.log(df.b)-np.log(df.c)),'mul':np.log(df.a)-(np.log(df.b)+np.log(df.c))}
        best=min(cands,key=lambda k:cands[k].std()); res_=cands[best]
        z=(res_-res_.rolling(Lb).mean())/res_.rolling(Lb).std()
        for t in z.index[Lb+2:-2]:
            if abs(z[t])>=z_thr:
                i=P[a]['idx'].get(t.date())
                if i is not None: out.append((a,i,bool(z[t]<0)))   # Residual negativ -> a zu billig -> long
    return out
# 5 Entscheidungsbaum, Walk-forward
def S_tree(depth,hor,conf):
    from sklearn.ensemble import GradientBoostingClassifier
    rows=[]
    for s in FX:
        d,c,h,l,tr=F(s); at=pd.Series(P[s]['a'])
        f=pd.DataFrame({'r5':c/c.shift(5)-1,'r20':c/c.shift(20)-1,'r60':c/c.shift(60)-1,'v':at/c,'vr':at/at.shift(20),'pos':(c-l.rolling(60).min())/(h.rolling(60).max()-l.rolling(60).min()),'tr':tr,'mo':[x.month for x in P[s]['ts']]})
        for k in ('r5','r20','r60'): f[k]=f[k]/f['v']
        f['y']=(c.shift(-hor)/c-1)
        f['sym']=s; f['i']=range(len(c)); f['yr']=P[s]['yr']
        rows.append(f)
    D=pd.concat(rows).dropna(); X=['r5','r20','r60','v','vr','pos','tr','mo']
    out=[]
    for y in range(2020,2027):
        trn=D[D.yr<y-0]; te=D[D.yr==y]
        trn=trn[trn.i%3==0]
        if len(te)==0 or len(trn)<2000: continue
        m=GradientBoostingClassifier(n_estimators=80,max_depth=depth,subsample=0.8,random_state=1).fit(trn[X],(trn.y>0).astype(int))
        p=m.predict_proba(te[X])[:,1]
        for (s,i,pp) in zip(te.sym,te.i,p):
            if pp>=0.5+conf: out.append((s,int(i),True))
            elif pp<=0.5-conf: out.append((s,int(i),False))
    return out
def log(n,a): print(n,a and (a['n'],a['avg'],a['wr'],a['pf'],a['dd']),flush=True)
for L in (60,120,250):
    sg=S_tsmom(L)
    for (sa,tg,N) in ((3,None,20),(4,None,40)): log(f'TSMOM {L} {sa} {N}',add(f'Zeitreihen-Momentum {L} Tage',sg,sa,tg,N,'mom'))
for (mn,ut) in ((0.3,True),(0.5,True),(0.3,False)):
    sg=S_fvg(mn,ut)
    for (sa,tg,N) in ((1.5,2,10),(2,3,15),(1.5,1,8)): log(f'FVG {mn} {ut} {sa} {tg} {N}',add(f'Fair-Value-Gap min {mn} ATR {"Wochentrend" if ut else "ohne"}',sg,sa,tg,N,'fvg'))
for n in (20,50):
    for mode in ('fade','trend'):
        sg=S_sweep(n,mode)
        for (sa,tg,N) in ((1.5,2,10),(2,1,8),(2,3,15)): log(f'Sweep {n} {mode} {sa} {tg} {N}',add(f'Liquiditäts-Sweep {n} Tage {mode}',sg,sa,tg,N,'sweep'))
for z in (2.0,2.5):
    for Lb in (60,120):
        sg=S_tri(z,Lb)
        for (sa,tg,N) in ((2,None,10),(3,None,15)): log(f'Tri z{z} L{Lb} {sa} {N}',add(f'Dreiecks-Abweichung z {z} Fenster {Lb}',sg,sa,tg,N,'tri'))
for (dp,hor,cf) in ((2,10,0.06),(3,10,0.08),(2,20,0.08)):
    sg=S_tree(dp,hor,cf)
    for (sa,tg,N) in ((3,None,hor),): log(f'Baum d{dp} h{hor} c{cf}',add(f'Entscheidungsbaum Tiefe {dp} {hor} Tage Schwelle {cf}',sg,sa,tg,N,'tree'))
pickle.dump(res,open('/tmp/ideen5.pkl','wb'))
r=[x for x in res if x['all'].get('avg') is not None]; r.sort(key=lambda x:-x['all']['avg'])
print('---TOP')
for x in r[:12]: print(x['name'],x['sa'],x['tg'],x['N'],x['all']['n'],x['all']['avg'],'dev',x['dev']['avg'],'test',x['test']['avg'],x['test']['n'],'dd',x['all']['dd'],'j',x['all']['jahr'])
print(len(res),'Varianten',sum(1 for x in r if x['all']['avg']>=0.15),'>=0.15, Median',np.median([x['all']['avg'] for x in r]))

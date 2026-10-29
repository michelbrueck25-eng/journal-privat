import sys,pickle,time,itertools
sys.path.insert(0,'/tmp/w/q')
from fam import U,dstr,mk,np,simulate,stats,configs
def conf_swings(d,n):
    h,l=d['h'],d['l']; N=len(h); SH=[];SL=[]
    for i in range(n,N-n):
        if h[i]==h[i-n:i+n+1].max() and h[i]>h[i-n:i].max() : SH.append((i+n,i))
        if l[i]==l[i-n:i+n+1].min() and l[i]<l[i-n:i].min(): SL.append((i+n,i))
    return SH,SL
def f_bos(P):
    out=[]
    for sym,d in U.items():
        N=len(d['c']); n=P['n']; SH,SL=conf_swings(d,n)
        sh_by={c:i for c,i in SH}; sl_by={c:i for c,i in SL}
        hi_list=[];lo_list=[]  # bestaetigte Swings (idx)
        stage={'dir':0,'t1':None,'lvl1':None,'broken':set()}
        pend=None
        for t in range(n*2+5,N-1):
            if t in sh_by: hi_list.append(sh_by[t])
            if t in sl_by: lo_list.append(sl_by[t])
            a=d['atr'][t]
            if np.isnan(a): continue
            # offener Retest-Auftrag?
            if pend:
                L,lvl,stop,t2=pend['L'],pend['lvl'],pend['stop'],pend['t2']
                if t-t2>P['wait']: pend=None
                elif t>t2:
                    if (L and d['c'][t]<stop) or ((not L) and d['c'][t]>stop): pend=None
                    else:
                        touch=(d['l'][t]<=lvl) if L else (d['h'][t]>=lvl)
                        if touch:
                            entry=min(lvl,d['o'][t]) if L else max(lvl,d['o'][t])
                            res=simulate(d,t,L,entry,stop,P['tgt'],P['maxd'],sym)
                            if res: out.append(mk(sym,d,t,L,res,'bos'))
                            pend=None
                            stage={'dir':0,'t1':None,'lvl1':None,'broken':set()}
                    continue
            for L in (True,False):
                if not (hi_list if L else lo_list): continue
                k=hi_list[-1] if L else lo_list[-1]; lvl=d['h'][k] if L else d['l'][k]
                brk=(d['c'][t]>lvl and d['c'][t-1]<=lvl) if L else (d['c'][t]<lvl and d['c'][t-1]>=lvl)
                if not brk or (L,k) in stage['broken']: continue
                stage['broken'].add((L,k))
                if P['htf'] and d['wt'][t]!=(1 if L else -1): stage={'dir':0,'t1':None,'lvl1':None,'broken':stage['broken']}; continue
                if stage['dir']==(1 if L else -1) and stage['t1'] is not None and t-stage['t1']<=P['gap'] and ((L and lvl>stage['lvl1']) or ((not L) and lvl<stage['lvl1'])):
                    # zweiter Bruch: Pullback-Extrem zwischen t1 und t
                    seg=slice(stage['t1'],t+1)
                    pb=d['l'][seg].min() if L else d['h'][seg].max()
                    stop=pb-0.1*a if L else pb+0.1*a
                    if abs(lvl-stop)<=P['cap']*a and abs(lvl-stop)>0 and ((L and stop<lvl) or ((not L) and stop>lvl)):
                        pend=dict(L=L,lvl=lvl,stop=stop,t2=t)
                    stage={'dir':0,'t1':None,'lvl1':None,'broken':stage['broken']}
                else:
                    stage={'dir':1 if L else -1,'t1':t,'lvl1':lvl,'broken':stage['broken']}
                break
    return out
G=dict(n=[3,5],htf=[0,1],gap=[30],wait=[5,10],cap=[3.0],tgt=[1.0,1.5,2.0],maxd=[10,20])
if __name__=='__main__':
    res=[];t0=time.time()
    for P in configs(G):
        tr=f_bos(P); s=stats(tr)
        if s: res.append((P,s,[(x['sym'],x['date'],x['L'],x['r'],x['days'],x['out'],x['i'],x['j'],x['px'],x['risk']) for x in tr]))
    pickle.dump(res,open('res_bos.pkl','wb')); print(len(res),round(time.time()-t0),'s')
    res.sort(key=lambda r:-r[1]['avg'])
    for P,s,_ in res[:8]: print(P,f"n{s['n']} wr{s['wr']:.1f} avg{s['avg']:.3f} pf{s['pf']:.2f} CI[{s['lo']:.3f},{s['hi']:.3f}] y{s['ypos']}/{s['ylen']} t{s['tage']:.1f}")
    ok=[r for r in res if r[1]['wr']>=50 and r[1]['n']>=300]
    print('WR>=50,n>=300:',len(ok),'davon avg>0',sum(1 for r in ok if r[1]['avg']>0))

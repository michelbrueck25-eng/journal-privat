import sys,pickle,time,itertools,bisect
sys.path.insert(0,'/tmp/w/q')
from eng import *
import eng
U=load_all()
H4={}
for sym in U:
    p=f'{HOME}/marktdaten/{sym}_4H.json'
    if os.path.exists(p):
        a=np.array(json.load(open(p))['rows'],float)
        # letzte unvollstaendige Kerze verwerfen
        if a[-1][0]+4*3600e3>dt.datetime.utcnow().timestamp()*1000: a=a[:-1]
        H4[sym]=dict(t=a[:,0],o=a[:,1],h=a[:,2],l=a[:,3],c=a[:,4])
for s,d in U.items():
    d['atr']=atr(d); d['e20']=ema(d['c'],20); d['e50']=ema(d['c'],50); d['wt']=wk_trend(d)
for s,h in H4.items():
    h['atr']=atr(h); h['e20']=ema(h['c'],20); h['e50']=ema(h['c'],50)
    d=U[s]; day0=(h['t']//86400e3)*86400e3
    h['di']=np.searchsorted(d['t'],day0)-1   # letzte abgeschlossene Tageskerze vor dem Tag
def sim4(h,i0,L,entry,stop,tgt,maxb,sym,chk=True):
    d=dict(h); return simulate(d,i0,L,entry,stop,tgt,maxb,sym,check_entry_bar=chk)
def ds4(h,i): return dt.datetime.utcfromtimestamp(h['t'][i]/1000).strftime('%Y-%m-%d')
def mk4(sym,h,i,L,res,fam):
    r,days,out,j,px,risk=res
    return dict(sym=sym,i=i,L=L,date=ds4(h,i),r=r,days=days,out=out,j=j,px=px,risk=risk,fam=fam)
def sw_last(h,i,n,L):
    """letztes bestaetigtes Swing-Hoch (L) / -Tief vor i (Kerze k mit k+n<=i)"""
    arr=h['h'] if L else h['l']
    for k in range(i-n,n,-1):
        seg=arr[k-n:k+n+1]
        if (L and arr[k]==seg.max()) or ((not L) and arr[k]==seg.min()): return k
    return None
# S1: Weekly-Trend + Daily Pullback-Zone (Abstand zur Daily-EMA50 <= z ATR) + 4H-Bruch des letzten Swing
def s1(P):
    out=[]
    for sym,h in H4.items():
        d=U[sym]; N=len(h['c']); busy=-1
        for i in range(60,N-1):
            if i<=busy: continue
            di=h['di'][i]
            if di<60: continue
            a=h['atr'][i]; da=d['atr'][di]
            if np.isnan(a) or np.isnan(da): continue
            for L in (True,False):
                if d['wt'][di]!=(1 if L else -1): continue
                dist=(d['c'][di]-d['e50'][di])/da
                if P['dz']>=0 and not ((-P['dz']<=dist<=0.5) if L else (-0.5<=dist<=P['dz'])): 
                    # Pullback-Zone: Daily-Schluss nahe oder unter EMA50 im Aufwaertstrend (L): dist in [-dz,0.5]
                    continue
                k=sw_last(h,i,2,L)
                if k is None or i-k>P['look']: continue
                lvl=h['h'][k] if L else h['l'][k]
                brk=(h['c'][i]>lvl and h['c'][i-1]<=lvl) if L else (h['c'][i]<lvl and h['c'][i-1]>=lvl)
                if not brk: continue
                seg=slice(k,i+1); ext=h['l'][seg].min() if L else h['h'][seg].max()
                entry=h['c'][i]; stop=ext-0.1*a if L else ext+0.1*a
                if abs(entry-stop)>P['cap']*a or abs(entry-stop)<0.3*a: continue
                res=sim4(h,i+1,L,entry,stop,P['tgt'],P['maxb'],sym,chk=True)
                if res: out.append(mk4(sym,h,i+1,L,res,'s1')); busy=i+res[1]; break
    return out
# S2: Daily-Extrem (z) in Weekly-Richtung + 4H-Umkehrkerze (Schluss ueber Vor-Hoch)
def s2(P):
    out=[]
    for sym,h in H4.items():
        d=U[sym]; N=len(h['c']); busy=-1
        ma=np.array([d['c'][max(0,x-19):x+1].mean() for x in range(len(d['c']))])
        for i in range(60,N-1):
            if i<=busy: continue
            di=h['di'][i]
            if di<60: continue
            a=h['atr'][i]; da=d['atr'][di]
            if np.isnan(a) or np.isnan(da): continue
            z=(d['c'][di]-ma[di])/da
            for L in (True,False):
                if P['htf'] and d['wt'][di]!=(1 if L else -1): continue
                if (L and z>-P['z']) or ((not L) and z<P['z']): continue
                trig=(h['c'][i]>h['h'][i-1] and h['c'][i-1]<h['o'][i-1]) if L else (h['c'][i]<h['l'][i-1] and h['c'][i-1]>h['o'][i-1])
                if not trig: continue
                ext=min(h['l'][i-2:i+1]) if L else max(h['h'][i-2:i+1])
                entry=h['c'][i]; stop=ext-0.1*a if L else ext+0.1*a
                if abs(entry-stop)>P['cap']*a or abs(entry-stop)<0.3*a: continue
                res=sim4(h,i+1,L,entry,stop,P['tgt'],P['maxb'],sym)
                if res: out.append(mk4(sym,h,i+1,L,res,'s2')); busy=i+res[1]; break
    return out
# S4: Alle drei Ebenen im Trend (Weekly, Daily EMA20>EMA50, 4H EMA20>EMA50), Limit am 4H-EMA50-Ruecksetzer
def s4(P):
    out=[]
    for sym,h in H4.items():
        d=U[sym]; N=len(h['c']); busy=-1
        for i in range(60,N-1):
            if i<=busy: continue
            di=h['di'][i]
            if di<60: continue
            a=h['atr'][i-1]
            if np.isnan(a): continue
            for L in (True,False):
                if d['wt'][di]!=(1 if L else -1): continue
                if (L and not d['e20'][di]>d['e50'][di]) or ((not L) and not d['e20'][di]<d['e50'][di]): continue
                if (L and not h['e20'][i-1]>h['e50'][i-1]) or ((not L) and not h['e20'][i-1]<h['e50'][i-1]): continue
                lvl=h['e50'][i-1] if P['ema']==50 else h['e20'][i-1]
                if L:
                    if h['l'][i]>lvl: continue
                    entry=min(lvl,h['o'][i]); stop=entry-P['k']*a
                else:
                    if h['h'][i]<lvl: continue
                    entry=max(lvl,h['o'][i]); stop=entry+P['k']*a
                res=sim4(h,i,L,entry,stop,P['tgt'],P['maxb'],sym,chk=True)
                if res: out.append(mk4(sym,h,i,L,res,'s4')); busy=i+res[1]; break
    return out
FAM={'s1':(s1,dict(dz=[-1,1.0,2.0],look=[12,30],cap=[3.0],tgt=[1.0,1.5,2.0],maxb=[30,60])),
 's2':(s2,dict(z=[1.5,2.0,2.5],htf=[0,1],cap=[3.0],tgt=[1.0,1.5,2.0],maxb=[30,60])),
 's4':(s4,dict(ema=[20,50],k=[1.0,1.5,2.0],tgt=[1.0,1.5,2.0],maxb=[30,60]))}
def split_stats(tr):
    tr=sorted(tr,key=lambda x:x['date']); 
    if len(tr)<10: return None
    cut=tr[int(len(tr)*0.6)]['date']
    return stats(tr),stats([x for x in tr if x['date']<=cut]),stats([x for x in tr if x['date']>cut]),cut
if __name__=='__main__':
    allr=[]
    for fam,(fn,g) in FAM.items():
        t0=time.time()
        for P in [dict(zip(g,v)) for v in itertools.product(*g.values())]:
            tr=fn(P); ss=split_stats(tr)
            if ss: allr.append((fam,P,ss,[(x['sym'],x['date'],x['L'],x['r'],x['days'],x['out'],x['i'],x['j'],x['px'],x['risk']) for x in tr]))
        print(fam,len(allr),round(time.time()-t0),'s',flush=True)
    pickle.dump(allr,open('res_mtf.pkl','wb'))

import sys,pickle,time,itertools,csv
sys.path.insert(0,'/tmp/w/q')
from fam import U,np,simulate,stats,configs,dstr,mk,atr,ema
import bisect
def rsi(c,n):
    d=np.diff(c,prepend=c[0]); up=np.where(d>0,d,0.0); dn=np.where(d<0,-d,0.0)
    ru=np.zeros(len(c)); rd=np.zeros(len(c)); ru[n]=up[1:n+1].mean(); rd[n]=dn[1:n+1].mean()
    for i in range(n+1,len(c)): ru[i]=(ru[i-1]*(n-1)+up[i])/n; rd[i]=(rd[i-1]*(n-1)+dn[i])/n
    out=np.full(len(c),50.0); m=rd>0; out[m]=100-100/(1+ru[m]/rd[m]); out[(rd==0)&(ru>0)]=100
    return out
def sma(x,n):
    out=np.full(len(x),np.nan); cs=np.cumsum(np.r_[0,x]); out[n-1:]=(cs[n:]-cs[:-n])/n; return out
for s,d in U.items():
    c=d['c']; d['rsi2']=rsi(c,2); d['rsi14']=rsi(c,14); d['ma20']=sma(c,20)
    sd=np.array([c[max(0,i-19):i+1].std() for i in range(len(c))]); d['bbu']=d['ma20']+2*sd; d['bbl']=d['ma20']-2*sd
    d['kcu']=d['ma20']+1.5*d['atr']; d['kcl']=d['ma20']-1.5*d['atr']
    m12=ema(c,12); m26=ema(c,26); d['macd']=m12-m26; d['macds']=ema(d['macd'],9)
# COT-Index (26 Wochen) je Waehrung und Datum
cot={}
for r in csv.DictReader(open('/home/claude/journal-daten/cot.csv',encoding='utf-8')):
    try: cot.setdefault(r['waehrung'],[]).append((r['datum'],int(r['comm_long'])-int(r['comm_short'])))
    except: pass
for k in cot: cot[k].sort()
def cot_idx(cur,date):
    v=cot.get(cur,[]); k=bisect.bisect_right([x[0] for x in v],date)-1
    if k<25: return None
    w=[x[1] for x in v[k-25:k+1]]
    return None if max(w)==min(w) else 100*(w[-1]-min(w))/(max(w)-min(w))
def S_donch(d,P,i):
    n=P['n']; 
    if i<n+1: return []
    out=[]
    if d['c'][i]>d['h'][i-n:i].max(): out.append(True)
    if d['c'][i]<d['l'][i-n:i].min(): out.append(False)
    return out
def S_rsi2(d,P,i):
    r=d['rsi2'][i]; return [True] if r<P['th'] else ([False] if r>100-P['th'] else [])
def S_rsi14(d,P,i):
    r=d['rsi14'][i]; rp=d['rsi14'][i-1]
    o=[]
    if rp<P['th'] and r>=P['th']: o.append(True)
    if rp>100-P['th'] and r<=100-P['th']: o.append(False)
    return o
def S_bb(d,P,i):
    o=[]
    if d['c'][i-1]<d['bbl'][i-1] and d['c'][i]>d['bbl'][i]: o.append(True)
    if d['c'][i-1]>d['bbu'][i-1] and d['c'][i]<d['bbu'][i]: o.append(False)
    return o
def S_inside(d,P,i):
    if d['h'][i]<d['h'][i-1] and d['l'][i]>d['l'][i-1]:
        return [None]   # Richtung = Trend (E20>E50)
    return []
def S_engulf(d,P,i):
    o=[]; e=d['e20'] if P['ema']==20 else d['e50']
    bull=d['c'][i]>d['o'][i-1] and d['o'][i]<=d['c'][i-1] and d['c'][i-1]<d['o'][i-1] and d['c'][i]>d['o'][i]
    bear=d['c'][i]<d['o'][i-1] and d['o'][i]>=d['c'][i-1] and d['c'][i-1]>d['o'][i-1] and d['c'][i]<d['o'][i]
    near=abs(d['l'][i]-e[i])<=P['near']*d['atr'][i] if bull else abs(d['h'][i]-e[i])<=P['near']*d['atr'][i]
    if bull and d['l'][i]<=e[i]+P['near']*d['atr'][i] and d['e20'][i]>d['e50'][i]: o.append(True)
    if bear and d['h'][i]>=e[i]-P['near']*d['atr'][i] and d['e20'][i]<d['e50'][i]: o.append(False)
    return o
def S_macd(d,P,i):
    o=[]
    if d['macd'][i-1]<d['macds'][i-1] and d['macd'][i]>=d['macds'][i] and d['macd'][i]<0: o.append(True)
    if d['macd'][i-1]>d['macds'][i-1] and d['macd'][i]<=d['macds'][i] and d['macd'][i]>0: o.append(False)
    return o
def S_pin(d,P,i):
    o=[]; h,l,c,op=d['h'][i],d['l'][i],d['c'][i],d['o'][i]; rng=h-l
    if rng<=0: return o
    if (min(c,op)-l)>=0.6*rng and c>=l+0.6*rng and d['c'][i-3:i].mean()>d['c'][i]: o.append(True)
    if (h-max(c,op))>=0.6*rng and c<=h-0.6*rng and d['c'][i-3:i].mean()<d['c'][i]: o.append(False)
    return o
def S_wkbreak(d,P,i):
    if i<6: return []
    ph=d['h'][i-5:i].max(); pl=d['l'][i-5:i].min(); o=[]
    if d['c'][i]>ph: o.append(True)
    if d['c'][i]<pl: o.append(False)
    return o
def S_squeeze(d,P,i):
    sq=d['bbu'][i-1]<d['kcu'][i-1] and d['bbl'][i-1]>d['kcl'][i-1]
    if not sq: return []
    o=[]
    if d['c'][i]>d['bbu'][i]: o.append(True)
    if d['c'][i]<d['bbl'][i]: o.append(False)
    return o
def S_cot(d,P,i,sym):
    date=dstr(d,i); b,q=sym[:3],sym[3:]
    cb,cq=cot_idx(b,date),cot_idx(q,date)
    if cb is None or cq is None: return []
    o=[]
    if cb>=P['th'] and cq<=100-P['th'] and d['c'][i]>d['h'][i-1]: o.append(True)
    if cb<=100-P['th'] and cq>=P['th'] and d['c'][i]<d['l'][i-1]: o.append(False)
    return o
SIG={'donch':S_donch,'rsi2':S_rsi2,'rsi14':S_rsi14,'bb':S_bb,'inside':S_inside,'engulf':S_engulf,'macd':S_macd,'pin':S_pin,'wkbreak':S_wkbreak,'squeeze':S_squeeze,'cot':S_cot}
def run(fam,P):
    out=[]
    for sym,d in U.items():
        N=len(d['c']); busy=-1
        for i in range(60,N-1):
            if i<=busy: continue
            a=d['atr'][i]
            if np.isnan(a): continue
            sg=SIG[fam](d,P,i,sym) if fam=='cot' else SIG[fam](d,P,i)
            for L in sg:
                if L is None: L=bool(d['e20'][i]>d['e50'][i])
                if P.get('htf') and d['wt'][i]!=(1 if L else -1): continue
                entry=d['o'][i+1]; k=P['k']
                stop=entry-k*a if L else entry+k*a
                res=simulate(d,i+1,L,entry,stop,P['tgt'],P['maxd'],sym)
                if res: out.append(mk(sym,d,i+1,L,res,fam)); busy=i+1+res[1]; break
    return out
GR={'donch':dict(n=[20,55],htf=[0,1],k=[1.5,2.5],tgt=[1.0,2.0],maxd=[10,20]),
 'rsi2':dict(th=[5,10],htf=[0,1],k=[1.5,2.5],tgt=[0.75,1.0,1.5],maxd=[5,10]),
 'rsi14':dict(th=[30,25],htf=[0,1],k=[1.5,2.5],tgt=[1.0,1.5],maxd=[10]),
 'bb':dict(htf=[0,1],k=[1.5,2.5],tgt=[0.75,1.0,1.5],maxd=[5,10]),
 'inside':dict(htf=[0,1],k=[1.5,2.5],tgt=[1.0,1.5,2.0],maxd=[10]),
 'engulf':dict(ema=[20,50],near=[0.5,1.0],htf=[0,1],k=[1.5,2.5],tgt=[1.0,1.5],maxd=[10]),
 'macd':dict(htf=[0,1],k=[1.5,2.5],tgt=[1.0,1.5,2.0],maxd=[10,20]),
 'pin':dict(htf=[0,1],k=[1.5,2.5],tgt=[1.0,1.5],maxd=[10]),
 'wkbreak':dict(htf=[0,1],k=[1.5,2.5],tgt=[1.0,2.0],maxd=[10]),
 'squeeze':dict(htf=[0,1],k=[1.5,2.5],tgt=[1.0,2.0],maxd=[10,20]),
 'cot':dict(th=[70,80],htf=[0,1],k=[1.5,2.5],tgt=[1.0,1.5,2.0],maxd=[10,20])}
if __name__=='__main__':
    fam=sys.argv[1]; res=[]; t0=time.time()
    for P in configs(GR[fam]):
        tr=run(fam,P); s=stats(tr)
        if s: res.append((P,s,[(x['sym'],x['date'],x['L'],x['r'],x['days'],x['out'],x['i'],x['j'],x['px'],x['risk']) for x in tr]))
    pickle.dump(res,open(f'res_{fam}.pkl','wb')); print(fam,len(res),round(time.time()-t0),'s',flush=True)

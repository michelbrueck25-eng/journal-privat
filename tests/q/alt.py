"""Alternativen zur Weekly-OB-Strategie (Forward-Test-Bereich): Backtests mit gleichem Rahmen (Spread 1 Pip, Stopp zuerst, kein Blick in die Zukunft).
Aufruf: python3 alt.py -> /tmp/alt_res.json"""
import sys,os,json,datetime,bisect
sys.path.insert(0,'/home/claude/journal-privat/tests/q'); __file__='/home/claude/journal-privat/tests/q/wob.py'
exec(open('/home/claude/journal-privat/tests/q/wob.py').read().split("RES={}")[0])
def dmy(ms): return datetime.datetime.fromtimestamp(ms/1000,datetime.timezone.utc)
# ---------- Hilfen
def sim_tp(d,i0,L,entry,stop,tp,maxn,sym):
    risk=abs(entry-stop)
    if risk<=0: return None
    sp=SPREAD_PIPS*eng.pip(sym)
    if ((d['l'][i0]<=stop) if L else (d['h'][i0]>=stop)): return (-1-sp/risk,)
    R=abs(tp-entry)/risk
    end=min(i0+1+maxn,len(d['c']))
    if i0+1>=len(d['c']): return None
    for j in range(i0+1,end):
        hs=(d['l'][j]<=stop) if L else (d['h'][j]>=stop); ht=(d['h'][j]>=tp) if L else (d['l'][j]<=tp)
        if hs: return (-1-sp/risk,)
        if ht: return (R-sp/risk,)
    c=d['c'][end-1]; r=((c-entry) if L else (entry-c))/risk
    return (r-sp/risk,)
def wk_active():
    """Weekly-Zonen mit Aktivfenster (ab 4. Wochenkerze, bis Tagesschluss durch die Zone oder 40 Wochen)"""
    out={}
    for s in U:
        d=U[s]; L=[]
        for z in wzones(s):
            k0=int(np.searchsorted(d['t'],z['tv'])); end=z['tmax']
            for k in range(k0,len(d['t'])):
                if d['t'][k]>z['tmax']: break
                if (d['c'][k]<z['lo']) if z['L'] else (d['c'][k]>z['hi']): end=d['t'][k]; break
            z['t_end']=end; L.append(z)
        out[s]=L
    return out
def dzones(sym,tol=None):
    d=U[sym]; a_=atr(d); n=len(d['c']); out=[]
    for i in range(9,n-3):
        a=a_[i]
        if np.isnan(a): continue
        o,h,l,c=d['o'][i],d['h'][i],d['l'][i],d['c'][i]; doji=abs(c-o)<=0.3*(h-l)
        for L in (True,False):
            if L:
                if not (c<o or doji): continue
                ref=d['h'][i-8:i].max(); disp=d['h'][i+1:i+4].max()-h; bos=(d['c'][i+1:i+4]>ref).any() and (d['c'][i+1:i+4]>h).any()
            else:
                if not (c>o or doji): continue
                ref=d['l'][i-8:i].min(); disp=l-d['l'][i+1:i+4].min(); bos=(d['c'][i+1:i+4]<ref).any() and (d['c'][i+1:i+4]<l).any()
            if disp<1.0*a or not bos: continue
            q='A' if disp>=2*a else 'B' if disp>=1.2*a else 'C'
            tv=d['t'][i+4] if i+4<n else None
            if tv is None: continue
            t_end=d['t'][min(n-1,i+64)]; k_touch=None
            for k in range(i+4,min(n,i+64)):
                if (d['c'][k]<l) if L else (d['c'][k]>h): t_end=d['t'][k]; break
                if k_touch is None and d['l'][k]<=h and d['h'][k]>=l: k_touch=k
            out.append(dict(sym=sym,L=L,lo=l,hi=h,q=q,tv=tv,t_end=t_end,k=k_touch,a=a_[k_touch-1] if k_touch else None,t0=d['t'][k_touch] if k_touch else None))
    return out
print('berechne Zonen ...',flush=True)
WA=wk_active(); DZ={s:dzones(s) for s in U}
def d_entry(z,mode='rand',stopf=0.1,tg=1.5,md=10,tpfun=None,stopmode='atr'):
    d=U[z['sym']]; L=z['L']; k=z['k']
    if k is None or z['a'] is None or z['a']!=z['a']: return None
    if (d['o'][k]<z['lo']) if L else (d['o'][k]>z['hi']): return None
    if mode=='rand': entry=z['hi'] if L else z['lo']
    else: entry=(z['hi']+z['lo'])/2
    if (d['l'][k]>entry) if L else (d['h'][k]<entry): return None   # Mittelwert nicht erreicht
    if stopmode=='atr': stop=z['lo']-stopf*z['a'] if L else z['hi']+stopf*z['a']
    elif stopmode=='mitte': stop=(z['hi']+z['lo'])/2 - (0 if True else 0)
    if stopmode=='mitte' and ((stop>=entry) if L else (stop<=entry)): return None
    if tpfun:
        tp=tpfun(d,k,L,entry,stop)
        if tp is None: return None
        r=sim_tp(d,k,L,entry,stop,tp,md,z['sym'])
        return (z['t0'],r[0]) if r else None
    r=simulate(d,k,L,entry,stop,tg,md,z['sym'])
    return (z['t0'],r[0]) if r else None
ALT={}
def collect(key,items):
    t=sorted([x for x in items if x]); 
    if t: ALT[key]=t
wz=lambda: [z for s in U for z in WA[s]]
# weekly touch zones (Z) aus wob.py: enthalten k/t0, aber ohne a: Daily-ATR ergaenzen
for z in Z: z['a']=atr(U[z['sym']])[z['k']-1]
q=lambda zs,qs: [z for z in zs if z['q'] in qs]
cm=lambda zs,mode: [z for z in zs if cotmode(z,mode)]
def cot_wide(z):
    s=z['sym']
    if s[:3] not in CI or s[3:] not in CI: return False
    b=cidx(s[:3],z['t0']); qq=cidx(s[3:],z['t0'])
    if b is None or qq is None: return False
    return (b>65 and qq<35) if z['L'] else (b<35 and qq>65)
# 1 COT breiter
collect('fw-x1',[d_entry(z) for z in Z if cot_wide(z)])
# 2 Qualitaet A+B (ohne COT) 
collect('fw-x2',[d_entry(z) for z in q(Z,'AB')])
# 3 Stopp 0,25 ATR
collect('fw-x3',[d_entry(z,stopf=0.25) for z in Z])
# 4 Einstieg Mitte
collect('fw-x4',[d_entry(z,mode='mitte') for z in Z])
# 5 Weekly-Trend, 6 COT stark + Trend
TR={s:wk_trend(U[s]) for s in U}
def trend_ok(z):
    d=U[z['sym']]; k=z['k']; return TR[z['sym']][k]==(1 if z['L'] else -1)
collect('fw-x5',[d_entry(z) for z in Z if trend_ok(z)])
collect('fw-x6',[d_entry(z) for z in Z if trend_ok(z) and cotmode(z,'stark')])
# 17 Block: Woche mit NFP (erster Freitag des Monats)
def nfp_week(ms):
    dt=dmy(ms); 
    for off in range(-6,7):
        x=dt+datetime.timedelta(days=off)
        if x.weekday()==4 and x.day<=7 and x.isocalendar()[1]==dt.isocalendar()[1]: return True
    return False
collect('fw-x17',[d_entry(z) for z in Z if not nfp_week(z['t0'])])
# 18 Alternative Stopps: Zonenmitte als Stopp
collect('fw-x18',[d_entry(z,stopmode='mitte') for z in Z])
# Daily-Zonen
DALL=[z for s in U for z in DZ[s] if z['k'] is not None]
for z in DALL: pass
collect('fw-x7',[d_entry(z) for z in q(DALL,'AB')])
# 8 Daily-Bestaetigung: erster Tagesschluss aus der Zone heraus nach Beruehrung, Einstieg naechste Eroeffnung, Risiko <= 3 ATR
def d_confirm(z):
    d=U[z['sym']]; L=z['L']; k=z['k']; n=len(d['c'])
    for j in range(k,min(n-2,k+6)):
        if (d['c'][j]>z['hi']) if L else (d['c'][j]<z['lo']):
            e=d['o'][j+1]; stop=z['lo']-0.1*z['a'] if L else z['hi']+0.1*z['a']
            if abs(e-stop)>3*z['a'] or ((e<=stop) if L else (e>=stop)): return None
            r=simulate(d,j+1,L,e,stop,1.5,10,z['sym']); return (d['t'][j+1],r[0]) if r else None
        if (d['c'][j]<z['lo']) if L else (d['c'][j]>z['hi']): return None
    return None
collect('fw-x8',[d_confirm(z) for z in q(DALL,'AB')])
def cot_for(z,mode):
    zz=dict(z); return cotmode(zz,mode)
collect('fw-x9',[d_entry(z) for z in q(DALL,'AB') if cotmode(z,'stark')])
collect('fw-x10',[d_entry(z) for z in q(DALL,'AB') if cotmode(z,'extrem')])
# 14 Daily-OB innerhalb eines Weekly-OB (gleiche Richtung, Zone liegt in der Weekly-Zone, Weekly-Zone aktiv)
def inside(z,w,tol=0.0): return z['L']==w['L'] and z['lo']>=w['lo']-tol and z['hi']<=w['hi']+tol and w['tv']<=z['tv']<=w['t_end']
def has_parent(z,P,sym):
    return any(inside(z,w) for w in P[sym])
collect('fw-x14',[d_entry(z) for z in q(DALL,'AB') if has_parent(z,WA,z['sym'])])
# 15 Daily-OB OHNE Weekly-Zone mit COT-Filter (relativ stark)
collect('fw-x15',[d_entry(z) for z in q(DALL,'AB') if not has_parent(z,WA,z['sym']) and cotmode(z,'stark')])
# 19 Alternative Ziele: naechstes Swing (20-Tage-Hoch/Tief vor dem Einstieg), mind. 1 R
def swing_tp(d,k,L,entry,stop):
    risk=abs(entry-stop)
    tp=d['h'][max(0,k-20):k].max() if L else d['l'][max(0,k-20):k].min()
    if abs(tp-entry)<1.0*risk or ((tp<=entry) if L else (tp>=entry)): return None
    if abs(tp-entry)>5*risk: tp=entry+5*risk if L else entry-5*risk
    return tp
collect('fw-x19',[d_entry(z,tpfun=swing_tp,md=20) for z in q(DALL,'AB')])
# ---------- 4H
def load4h(s):
    f=f'/home/claude/journal-privat/marktdaten/{s}_4H.json'
    if not os.path.exists(f): return None
    r=np.array(json.load(open(f))['rows'],float); return dict(t=r[:,0],o=r[:,1],h=r[:,2],l=r[:,3],c=r[:,4])
H4={s:load4h(s) for s in U}
def hzones(sym):
    d=H4[sym]
    if d is None: return []
    a_=atr(d); n=len(d['c']); out=[]
    for i in range(9,n-3):
        a=a_[i]
        if np.isnan(a): continue
        o,h,l,c=d['o'][i],d['h'][i],d['l'][i],d['c'][i]; doji=abs(c-o)<=0.3*(h-l)
        for L in (True,False):
            if L:
                if not (c<o or doji): continue
                ref=d['h'][i-8:i].max(); disp=d['h'][i+1:i+4].max()-h; bos=(d['c'][i+1:i+4]>ref).any() and (d['c'][i+1:i+4]>h).any()
            else:
                if not (c>o or doji): continue
                ref=d['l'][i-8:i].min(); disp=l-d['l'][i+1:i+4].min(); bos=(d['c'][i+1:i+4]<ref).any() and (d['c'][i+1:i+4]<l).any()
            if disp<1.0*a or not bos: continue
            if i+4>=n: continue
            tv=d['t'][i+4]; kt=None
            for k in range(i+4,min(n,i+64)):
                if (d['c'][k]<l) if L else (d['c'][k]>h): break
                if d['l'][k]<=h and d['h'][k]>=l: kt=k; break
            if kt is None: continue
            out.append(dict(sym=sym,L=L,lo=l,hi=h,tv=tv,k=kt,t0=d['t'][kt],a=a_[kt-1]))
    return out
HZ={s:hzones(s) for s in U}
def h_entry(z,tg=1.5,md=60):
    d=H4[z['sym']]; L=z['L']; k=z['k']
    if z['a']!=z['a']: return None
    if (d['o'][k]<z['lo']) if L else (d['o'][k]>z['hi']): return None
    entry=z['hi'] if L else z['lo']; stop=z['lo']-0.1*z['a'] if L else z['hi']+0.1*z['a']
    r=simulate(d,k,L,entry,stop,tg,md,z['sym']); return (z['t0'],r[0]) if r else None
def wk_parent(z):
    return any(inside(z,w) and w['tv']<=z['t0']<=w['t_end'] for w in WA[z['sym']])
def dy_parent(z):
    return any(inside(z,w) and w['tv']<=z['t0']<=w['t_end'] and w['q'] in 'AB' for w in DZ[z['sym']])
HALL=[z for s in U for z in HZ[s]]
collect('fw-x11',[h_entry(z) for z in HALL if dy_parent(z) and wk_parent(z)])
collect('fw-x12',[h_entry(z) for z in HALL if dy_parent(z)])
collect('fw-x13',[h_entry(z) for z in HALL if wk_parent(z)])
def h_trend(z):
    d=U[z['sym']]; k=int(np.searchsorted(d['t'],z['t0']))-1
    return k>=0 and TR[z['sym']][k]==(1 if z['L'] else -1)
collect('fw-x16',[h_entry(z) for z in HALL if h_trend(z)])
def kz(t):
    r=np.array([x[1] for x in t]); h=len(r)//2; eq=np.cumsum(r); gl=-r[r<0].sum(); gw=r[r>0].sum()
    return dict(n=len(r),wr=round(float((r>0).mean()*100),1),avg=round(float(r.mean()),3),pf=round(float(gw/gl),2) if gl>0 else None,dd=round(float((np.maximum.accumulate(eq)-eq).max()),1),h1=round(float(r[:h].mean()),3),h2=round(float(r[h:].mean()),3),yrs=round((t[-1][0]-t[0][0])/31557600000,2))
json.dump({k:[[x[0],round(x[1],3)] for x in v] for k,v in ALT.items()},open('/tmp/alt_res.json','w'))
for k in sorted(ALT,key=lambda x:int(x[4:])): print(k,kz(ALT[k]))

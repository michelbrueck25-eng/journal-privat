"""Gezielte Parametersuche nach Expectancy 0,3 bis 0,5 R: Weekly- und Daily-Zonen, Entwicklung (erste 60 % der Zeit) gegen Prüfung (letzte 40 %).
Zahl der Varianten wird ausgewiesen. Aufruf: python3 search.py -> /tmp/search_res.json"""
import sys,os,json,datetime,itertools,time
sys.path.insert(0,'/home/claude/journal-privat/tests/q'); __file__='/home/claude/journal-privat/tests/q/wob.py'
src=open('/home/claude/journal-privat/tests/q/alt.py').read()
exec(src.split("ALT={}")[0])
for z in Z: z['a']=atr(U[z['sym']])[z['k']-1]
TR={s:wk_trend(U[s]) for s in U}
def feats(z):
    z['s30']=cotmode(z,'stark'); z['ext']=cotmode(z,'extrem')
    z['wide']=cot_wide(z) if 'cot_wide' in globals() else False
    z['tr']=TR[z['sym']][z['k']]==(1 if z['L'] else -1)
def cot_wide(z):
    s=z['sym']
    if s[:3] not in CI or s[3:] not in CI: return False
    b=cidx(s[:3],z['t0']); qq=cidx(s[3:],z['t0'])
    if b is None or qq is None: return False
    return (b>65 and qq<35) if z['L'] else (b<35 and qq>65)
def s40(z):
    s=z['sym']
    if s[:3] not in CI or s[3:] not in CI: return False
    b=cidx(s[:3],z['t0']); qq=cidx(s[3:],z['t0'])
    if b is None or qq is None: return False
    diff=(b-qq) if z['L'] else (qq-b); return diff>=50
DALL=[z for s in U for z in DZ[s] if z['k'] is not None and z['q'] in 'AB' and z['a']==z['a']]
ZS={'W':[z for z in Z if z['a']==z['a']],'D':DALL}
for k,zs in ZS.items():
    for z in zs: z['tf']=k; feats(z); z['s50']=s40(z)
allt=[z['t0'] for zs in ZS.values() for z in zs]; SPLIT=min(allt)+0.6*(max(allt)-min(allt))
print('Split',datetime.datetime.fromtimestamp(SPLIT/1000,datetime.timezone.utc).date(),flush=True)
ENT=('rand','mitte'); STOP=(0.1,0.25,0.5); TG=(1.0,1.5,2.0,3.0); MD=(7,10,20)
COTF={'ohne':lambda z:True,'stark30':lambda z:z['s30'],'stark50':lambda z:z['s50'],'extrem':lambda z:z['ext'],'breit':lambda z:z['wide']}
QF={'ABC':'ABC','AB':'AB','A':'A'}
RES=[]; nvar=0; t_start=time.time()
for tf,zs in ZS.items():
    t0=np.array([z['t0'] for z in zs]); isdev=t0<SPLIT
    masks={}
    for cn,cf in COTF.items():
        for tn in (False,True):
            for qn,qs in QF.items():
                masks[(cn,tn,qn)]=np.array([cf(z) and (z['tr'] or not tn) and z['q'] in qs for z in zs])
    for ent,sf,tg,md in itertools.product(ENT,STOP,TG,MD):
        r=np.full(len(zs),np.nan)
        for i,z in enumerate(zs):
            x=d_entry(z,mode='rand' if ent=='rand' else 'mitte',stopf=sf,tg=tg,md=md)
            if x: r[i]=x[1]
        for key,m in masks.items():
            mm=m&~np.isnan(r); n=mm.sum(); nvar+=1
            if n<100: continue
            rd=r[mm&isdev]; rt=r[mm&~isdev]
            if len(rd)<50 or len(rt)<30: continue
            RES.append(dict(tf=tf,ent=ent,stop=sf,tg=tg,md=md,cot=key[0],trend=key[1],q=key[2],n=int(n),avg=float(r[mm].mean()),wr=float((r[mm]>0).mean()*100),nd=len(rd),ad=float(rd.mean()),nt=len(rt),at=float(rt.mean()),wt=float((rt>0).mean()*100)))
    print(tf,'fertig',round(time.time()-t_start),'s, Varianten',nvar,flush=True)
json.dump(dict(nvar=nvar,split=SPLIT,res=RES),open('/tmp/search_res.json','w'))
print('Konfigurationen mit n>=100:',len(RES))
for lab,flt in (('n>=300',lambda r:r['n']>=300),('n>=100',lambda r:r['n']>=100)):
    top=sorted([r for r in RES if flt(r)],key=lambda r:-min(r['ad'],r['at']))[:8]
    print(lab)
    for r in top: print({k:(round(v,3) if isinstance(v,float) else v) for k,v in r.items()})

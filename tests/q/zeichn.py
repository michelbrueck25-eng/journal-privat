"""Zeichnungsdaten für Strategien (Forward-Test 'Im Chart zeigen'): Zonen und Beispiel-Trades je Paar (die jüngsten N), neutral, ohne Positionen des Nutzers.
Aufruf: python3 zeichn.py -> strategiezeichnungen/<id>.json"""
import sys,os,json,datetime
sys.path.insert(0,'/home/claude/journal-privat/tests/q'); __file__='/home/claude/journal-privat/tests/q/wob.py'
src=open('/home/claude/journal-privat/tests/q/search.py').read().split("ENT=('rand','mitte')")[0]
exec(src)
# Zonenstartzeit nachtragen: Zone beginnt bei der Zonenkerze i
def zone_time(z):
    d=U[z['sym']]; return int(d['t'][max(0,int(np.searchsorted(d['t'],z['tv']))-4)])
CFG={'fw3-k1':(dict(mode='mitte',stopf=0.25,tg=3.0,md=10),lambda z:z['q']=='A'),'fw3-k2':(dict(mode='mitte',stopf=0.5,tg=3.0,md=7),lambda z:z['q']=='A' and z['tr']),'fw3-k3':(dict(mode='rand',stopf=0.1,tg=3.0,md=10),lambda z:z['q']=='A' and z['s30'])}
N=25
os.makedirs('/home/claude/journal-privat/strategiezeichnungen',exist_ok=True)
for sid,(cfg,flt) in CFG.items():
    per={}
    for z in ZS['D']:
        if not flt(z): continue
        d=U[z['sym']]; L=z['L']; k=z['k']
        if z['a']!=z['a'] or ((d['o'][k]<z['lo']) if L else (d['o'][k]>z['hi'])): continue
        a=z['a']; entry=z['hi'] if (L and cfg['mode']=='rand') else z['lo'] if (not L and cfg['mode']=='rand') else (z['hi']+z['lo'])/2
        if cfg['mode']!='rand' and ((d['l'][k]>entry) if L else (d['h'][k]<entry)): continue
        stop=z['lo']-cfg['stopf']*a if L else z['hi']+cfg['stopf']*a
        r=simulate(d,k,L,entry,stop,cfg['tg'],cfg['md'],z['sym'])
        if not r: continue
        risk=abs(entry-stop); tp=entry+cfg['tg']*risk if L else entry-cfg['tg']*risk
        j=min(len(d['t'])-1,k+max(1,r[1])); tz=zone_time(z)
        per.setdefault(z['sym'],[]).append(dict(z=dict(t0=tz,t1=int(d['t'][j]),p0=float(z['hi']),p1=float(z['lo'])),p=dict(dir='long' if L else 'short',t0=int(d['t'][k]),t1=int(d['t'][j]),entry=float(entry),sl=float(stop),tp=float(tp),rrk=cfg['tg'],r=round(float(r[0]),2))))
    for s in per: per[s]=sorted(per[s],key=lambda x:x['p']['t0'])[-N:]
    json.dump(dict(typ='strategiezeichnungen',id=sid,paare=per),open(f'/home/claude/journal-privat/strategiezeichnungen/{sid}.json','w'),separators=(',',':'))
    print(sid,{s:len(v) for s,v in list(per.items())[:4]},sum(len(v) for v in per.values()))

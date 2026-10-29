import sys,json,datetime,numpy as np,os
sys.path.insert(0,'/tmp')
from PIL import Image
from tfocr import tf_of
D='/home/claude/journal-privat/'
R=json.load(open('/tmp/fin.json'))
J=json.load(open(D+'journal-export.json',encoding='utf-8')); TR={t['id']:t for t in J['trades']}
def body_w(path,c):
    im=np.array(Image.open(path).convert('RGB')).astype(int); y=int((c['ymin']+c['ymax'])/2)
    ws=[]
    for yy in range(y-60,y+60,6):
        row=im[yy,10:1315]; m=((row[:,2]>200)&(row[:,0]<120))|((row[:,0]>170)&(abs(row[:,0]-row[:,1])<6))
        xs=np.where(m)[0]
        if len(xs)==0: continue
        run=1
        for a,b in zip(xs[:-1],xs[1:]):
            if b==a+1: run+=1
            else:
                if run>=2: ws.append(run)
                run=1
    return float(np.median(ws)) if ws else 0
out={}
for o in R:
    t=TR[o['id']]; c=json.load(open(f'/tmp/C3/{o["id"]}.json')); p=D+o['pfad']; rec=dict(sym=o['inst'],dir=o['dir'],pfad=o['pfad'],flags=list(o['flags']))
    if 'a' not in c: out[o['id']]=rec; continue
    txt,tf=tf_of(p,c)
    if tf not in ('W','T','D'):
        tf='W' if body_w(p,c)>=5 else 'D'
    rec['tf']='W' if tf=='W' else 'D'
    tm=o.get('tm')
    if tm:
        s,b=tm['s'],tm['b']; X=lambda x:int((s*x+b)*1000)
        drs=[]; i=0
        rects=sorted(o['rects'],key=lambda r:(r['x0'],r['y0']))
        for r in rects:
            d=dict(type='rect',t0=X(r['x0']),p0=round(r['top'],6),t1=X(r['x1']),p1=round(r['bot'],6))
            if r['col']=='blue': d['line']='#3a88fe'
            if r['x0']<=14: d['abgeschnitten']=True
            drs.append(d)
        if 'pos' in o:
            po=o['pos']; ent,stop=po['entry'],po['stop']; risk=abs(ent-stop)
            d=dict(type='pos',dir=o['dir'],t0=X(po['x0']),t1=X(po['x1']),entry=round(ent,6),sl=round(stop,6),tf=rec['tf'])
            z=po['ziele']
            if z:
                d['tp']=round(z[0],6); d['rrk']=round(abs(z[0]-ent)/risk,2)
                if len(z)>1: d['tp2']=round(z[1],6); d['rrk2']=round(abs(z[1]-ent)/risk,2)
            else: rec['flags'].append('keine Ziele')
            drs.append(d)
        rec['drs']=drs
    else: rec['flags'].append('Zeit')
    out[o['id']]=rec
json.dump(out,open('/tmp/assembled.json','w'),ensure_ascii=False,default=float,indent=0)
import collections
print(len(out),collections.Counter(r.get('tf') for r in out.values()),collections.Counter(f for r in out.values() for f in r['flags']))
print(sum(1 for r in out.values() if any(d['type']=='pos' for d in r.get('drs',[]))),'mit pos')

import sys,json,pickle,os
sys.path.insert(0,'/tmp')
import numpy as np
from PIL import Image
from ax import yaxis
from xax import labels,timemap
import multiprocessing as mp
D='/home/claude/journal-privat/'
J=json.load(open(D+'journal-export.json',encoding='utf-8'))
bt=[t for t in J['trades'] if t['source']=='backtest' and t.get('bilderListe')]
def calib2(pts):
    pts=np.array([(p[0],p[1]) for p in pts]); best=None
    for i in range(len(pts)):
        for j in range(i+1,len(pts)):
            if pts[j,0]==pts[i,0]: continue
            a=(pts[j,1]-pts[i,1])/(pts[j,0]-pts[i,0]); b=pts[i,1]-a*pts[i,0]
            res=abs(pts[:,1]-(a*pts[:,0]+b)); inl=(res<abs(a)*2.5).sum()
            if best is None or inl>best[0]: best=(inl,a,b)
    inl,a,b=best; m=abs(pts[:,1]-(a*pts[:,0]+b))<abs(a)*2.5
    A=np.polyfit(pts[m,0],pts[m,1],1); return float(A[0]),float(A[1]),pts[m,0]
def work(t):
    cf=f'/tmp/C3/{t["id"]}.json'
    if os.path.exists(cf): return json.load(open(cf))
    p=D+t['bilderListe'][0]['pfad']; im=Image.open(p).convert('RGB'); o=dict(id=t['id'])
    try:
        ya=yaxis(im)
        if len(ya)>=4:
            a,b,ys=calib2(ya); o.update(a=a,b=b,ymin=float(ys.min()),ymax=float(ys.max()),n=int(len(set(np.round(ys)))))
        labs=labels(im); import datetime as _d; tm=timemap(labs,_d.date.fromisoformat(t['analysisDate'])); o['tm']=tm; o['labs']=len(labs)
    except Exception as e: o['err']=repr(e)[:80]
    json.dump(o,open(cf,'w')); return o
if __name__=='__main__':
    os.makedirs('/tmp/C3',exist_ok=True)
    with mp.Pool(4) as pool: R=pool.map(work,bt)
    print(len(R),sum(1 for o in R if 'a' in o),sum(1 for o in R if o.get('tm')))

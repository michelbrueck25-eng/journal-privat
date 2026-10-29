import sys,json,os,collections,datetime
sys.path.insert(0,'/tmp')
import numpy as np
from PIL import Image,ImageDraw
from ext import runs,merge
import multiprocessing as mp
D='/home/claude/journal-privat/'
J=json.load(open(D+'journal-export.json',encoding='utf-8'))
bt=[t for t in J['trades'] if t['source']=='backtest' and t.get('bilderListe')]
def lines_for(path,c):
    im=np.array(Image.open(path).convert('RGB')).astype(int); H,W,_=im.shape
    r,g,bl=im[:,:,0],im[:,:,1],im[:,:,2]
    y0=max(30,int(c['ymin']-35)); y1=min(H-60,int(c['ymax']+35))
    plot=np.zeros((H,W),bool); plot[y0:y1,10:W-(112 if H>900 else 85)]=True
    M=dict(white=(r>215)&(g>215)&(bl>215)&(abs(r-g)<10)&(abs(g-bl)<10)&plot,
      blue=(bl>170)&(r<150)&(bl-r>60)&(g<190)&plot,
      green=(g>r+25)&(g>bl+25)&(g>100)&plot,
      red=(r>g+55)&(r>130)&(r>bl+45)&plot)
    L={}
    for k,mn,gp in (('white',14,30),('blue',14,30),('green',12,6),('red',12,6)):
        ls=[l for l in merge(runs(M[k],mn,gp)) if l['n']<=6]
        L[k]=ls
    # Icon-Baender: viele kurze Linien in engem y-Band
    for k in ('red','blue','green'):
        cnt=collections.Counter(int(l['y']//12) for l in L[k])
        L[k]=[l for l in L[k] if cnt[int(l['y']//12)]<5 or (l['x1']-l['x0'])>=90]
    for k in L:
        for l in L[k]: l['p']=c['a']*l['y']+c['b']
    return L,H,W
import cv2
def fill_rects(path,c):
    im=np.array(Image.open(path).convert('RGB')).astype(int); H,W,_=im.shape
    r,g,bl=im[:,:,0],im[:,:,1],im[:,:,2]
    y0=max(30,int(c['ymin']-35)); y1=min(H-60,int(c['ymax']+35))
    plot=np.zeros((H,W),bool); plot[y0:y1,10:W-(112 if H>900 else 85)]=True
    gray=(abs(r-g)<=3)&(abs(g-bl)<=4)&plot
    m_out=(gray&(r>=23)&(r<=32))|(gray&(r>=35)&(r<=45))
    m_in=gray&(r>=35)&(r<=45)
    res=[]
    def comps(mask,tag):
        mm=cv2.morphologyEx(mask.astype(np.uint8)*255,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_RECT,(3,3)))
        mm=cv2.morphologyEx(mm,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(9,9)))
        n,lab,st,_=cv2.connectedComponentsWithStats(mm)
        for i in range(1,n):
            x,y,w,h,a=st[i]
            if w<30 or h<12 or w*h<1500: continue
            fillfrac=mask[y:y+h,x:x+w].mean()
            if fillfrac<0.4: continue
            res.append(dict(tag=tag,x0=int(x)-1,x1=int(x+w)+1,y0=int(y)-1,y1=int(y+h)+1,ff=float(fillfrac)))
    comps(m_out,'out'); comps(m_in,'in')
    for rc in res:
        wid=rc['x1']-rc['x0']; best_w=0; best_b=0
        for yy in (rc['y0'],rc['y1']):
            cw=cb=0
            for dy in (-2,-1,0,1,2):
                row=im[min(max(yy+dy,0),H-1),rc['x0']:rc['x1']]
                cw=max(cw,((row[:,0]>215)&(row[:,1]>215)&(row[:,2]>215)).sum()); cb=max(cb,((row[:,2]>170)&(row[:,0]<150)&(row[:,2]-row[:,0]>60)).sum())
            best_w=max(best_w,cw); best_b=max(best_b,cb)
        if rc['tag']=='in': rc['col']='blue'
        else: rc['col']='white' if best_w>=0.35*wid else 'blue'
        rc['top']=c['a']*rc['y0']+c['b']; rc['bot']=c['a']*rc['y1']+c['b']
    return res
def rects_of(L):
    rects=[]
    for col in ('white','blue'):
        ls=[l for l in L[col] if l['x1']-l['x0']>=40]
        for i,l in enumerate(ls):
            for m in ls[i+1:]:
                if abs(l['x1']-m['x1'])<=20 and abs(l['y']-m['y'])>6:
                    rects.append(dict(col=col,top=max(l['p'],m['p']),bot=min(l['p'],m['p']),x0=min(l['x0'],m['x0']),x1=max(l['x1'],m['x1'])))
    return rects
def work(t):
    c=json.load(open(f'/tmp/C3/{t["id"]}.json')); o=dict(id=t['id'],dir=t['dir'],inst=t['instrument'],pfad=t['bilderListe'][0]['pfad'],flags=[])
    if 'a' not in c or c.get('n',0)<5: o['flags'].append('Achse'); return o
    p=D+o['pfad']; L,H,W=lines_for(p,c); dirn=t['dir']
    tm=c.get('tm'); o['tm']=tm
    if not tm: o['flags'].append('Zeit')
    pairs=[]
    for g in L['green']:
        for r in L['red']:
            if not (abs(r['x1']-g['x1'])<=8 or abs(r['x0']-g['x0'])<=8): continue
            if ((r['p']<g['p']) if dirn=='long' else (r['p']>g['p'])) and abs(r['p']-g['p'])<0.2*g['p'] and abs(r['y']-g['y'])>6: pairs.append((g,r))
    if pairs:
        g,r=max(pairs,key=lambda pr:(max(pr[0]['x1'],pr[1]['x1']),min(pr[0]['x1']-pr[0]['x0'],pr[1]['x1']-pr[1]['x0'])))
        ent,stop=g['p'],r['p']; ex0=min(g['x0'],r['x0']); ex1=max(g['x1'],r['x1']); L_=ent>stop
        zs=[w['p'] for w in L['white'] if abs(w['x1']-ex1)<=14 and w['x0']>=ex0-14 and 12<=w['x1']-w['x0']<=(ex1-ex0)+30 and ((w['p']>ent) if L_ else (w['p']<ent))]
        zs=sorted(zs,key=lambda p_:abs(p_-ent))
        o['pos']=dict(entry=ent,stop=stop,x0=ex0,x1=ex1,ziele=zs)
    o['rects']=fill_rects(p,c)
    o['L']={k:[(round(l['p'],5),l['x0'],l['x1']) for l in v if (k in('green','red') or l['x1']-l['x0']>=40)] for k,v in L.items()}
    if not o['rects'] and 'pos' not in o: o['flags'].append('nichts')
    # Overlay
    img=Image.open(p).convert('RGB'); d=ImageDraw.Draw(img)
    for rc in o['rects']:
        yt=(rc['top']-c['b'])/c['a']; yb=(rc['bot']-c['b'])/c['a']
        d.rectangle([rc['x0'],yt,rc['x1'],yb],outline=(255,0,255) if rc['col']=='white' else (255,140,0),width=2)
        d.text((rc['x0']+4,yt+2),f"{rc['top']:.5g}",fill=(255,0,255)); d.text((rc['x0']+4,yb-12),f"{rc['bot']:.5g}",fill=(255,0,255))
    if 'pos' in o:
        po=o['pos']
        for k,col in (('entry',(0,255,255)),('stop',(255,255,0))):
            y=(po[k]-c['b'])/c['a']; d.line([(po['x0'],y),(po['x1'],y)],fill=col,width=2); d.text((po['x1']+4,y-5),f"{k[0]}:{po[k]:.5g}",fill=col)
        for z in po['ziele']:
            y=(z-c['b'])/c['a']; d.line([(po['x0'],y),(po['x1'],y)],fill=(0,255,0),width=2); d.text((po['x1']+4,y-5),f"z:{z:.5g}",fill=(0,255,0))
    img.save(f"/tmp/ov/{t['id']}.jpg",quality=80)
    return o
if __name__=='__main__':
    with mp.Pool(4) as pool: R=pool.map(work,bt)
    json.dump(R,open('/tmp/fin.json','w'),default=float)
    c=collections.Counter()
    for o in R:
        c[('pos' if 'pos' in o else 'nopos')+('+rect' if o.get('rects') else '')]+=1
    print(c, collections.Counter(f for o in R for f in o['flags']))

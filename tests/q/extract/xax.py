import re,datetime,numpy as np,pytesseract
from PIL import Image,ImageOps
MON=['jan','feb','mrz','apr','mai','jun','jul','aug','sep','okt','nov','dez']
def _tok(crop,scale,psm,thr):
    g=ImageOps.invert(crop.convert('L'))
    if thr: g=g.point(lambda v:0 if v<thr else 255)
    big=g.resize((g.width*scale,g.height*scale),Image.LANCZOS)
    d=pytesseract.image_to_data(big,config=f'--psm {psm} -c tessedit_char_whitelist=0123456789JanFebMrzAprMaiJunulAugSepOktNovDez',output_type=pytesseract.Output.DICT)
    return [(t.strip(),(x+w/2)/scale) for t,x,w in zip(d['text'],d['left'],d['width']) if t.strip()]
def lev(a,b):
    if a==b: return 0
    d=list(range(len(b)+1))
    for i,ca in enumerate(a,1):
        p=d[:]; d[0]=i
        for j,cb in enumerate(b,1): d[j]=min(p[j]+1,d[j-1]+1,p[j-1]+(ca!=cb))
    return d[-1]
def labels(img):
    W,H=img.size; crop=img.crop((0,H-105,W-80,H-45)); toks=[]
    for scale,psm,thr in ((3,11,150),(3,6,0),(4,11,130)): toks+=_tok(crop,scale,psm,thr)
    out=[]
    for t,x in toks:
        if re.fullmatch(r'20\d\d',t): out.append((x,'y',int(t)))
        else:
            tl=t.lower()
            if 3<=len(tl)<=4:
                best=min(range(12),key=lambda i:lev(tl[:3],MON[i]))
                if lev(tl[:3],MON[best])==0: out.append((x,'m',best+1))
    out.sort(); res=[]
    for x,k,v in out:
        if res and abs(res[-1][0]-x)<25 and res[-1][1]==k and res[-1][2]==v: continue
        res.append((x,k,v))
    return res
def timemap(labs,hint=None):
    ys=[l for l in labs if l[1]=='y']
    if not ys:
        if not hint or len(labs)<3: return None
        # kein Jahreslabel: Jahr aus dem Analysedatum, Monate links->rechts
        y=hint.year-(1 if labs[0][2]>hint.month+1 else 0); prev=labs[0][2]; pts=[]
        for x,k,v in labs:
            if v<prev: y+=1
            prev=v; pts.append((x,datetime.datetime(y,v,1,tzinfo=datetime.timezone.utc).timestamp()))
        labs=None; P=np.array(sorted(pts)); best=None
        for i in range(len(P)):
            for j in range(i+1,len(P)):
                if P[j,0]-P[i,0]<60: continue
                s_=(P[j,1]-P[i,1])/(P[j,0]-P[i,0]); b_=P[i,1]-s_*P[i,0]
                res=abs(P[:,1]-(s_*P[:,0]+b_)); n=(res<10*86400).sum()
                if best is None or n>best[0]: best=(n,s_,b_)
        if best is None or best[0]<3: return None
        n,s_,b_=best; m=abs(P[:,1]-(s_*P[:,0]+b_))<10*86400; A=np.polyfit(P[m,0],P[m,1],1); return dict(s=float(A[0]),b=float(A[1]),n=int(m.sum()),hint=True)
    # Jahre als Anker: sequenz links->rechts
    toks=[(x,k,v) for x,k,v in labs]
    i0=next(i for i,t in enumerate(toks) if t[1]=='y'); Y0=toks[i0][2]
    dates={}
    dates[i0]=datetime.date(Y0,1,1)
    y=Y0; prev=1
    for i in range(i0+1,len(toks)):
        x,k,v=toks[i]
        if k=='y': y=v; prev=1; dates[i]=datetime.date(y,1,1); continue
        if v<prev: y+=1
        dates[i]=datetime.date(y,v,1); prev=v
    yy=Y0-1; prev=13
    for i in range(i0-1,-1,-1):
        x,k,v=toks[i]
        if k=='y': yy=v-1; prev=13; dates[i]=datetime.date(v,1,1); continue
        if v>=prev: yy-=1
        dates[i]=datetime.date(yy,v,1); prev=v
    pts=[(toks[i][0],datetime.datetime(d.year,d.month,d.day,tzinfo=datetime.timezone.utc).timestamp()) for i,d in dates.items()]
    if len(pts)<2: return None
    P=np.array(sorted(pts)); best=None
    for i in range(len(P)):
        for j in range(i+1,len(P)):
            if P[j,0]-P[i,0]<60: continue
            s=(P[j,1]-P[i,1])/(P[j,0]-P[i,0]); b=P[i,1]-s*P[i,0]
            res=abs(P[:,1]-(s*P[:,0]+b)); n=(res<10*86400).sum()
            if best is None or n>best[0]: best=(n,s,b)
    if best is None or best[0]<2: return None
    n,s,b=best; m=abs(P[:,1]-(s*P[:,0]+b))<10*86400
    A=np.polyfit(P[m,0],P[m,1],1); return dict(s=float(A[0]),b=float(A[1]),n=int(m.sum()))
if __name__=='__main__':
    import sys
    im=Image.open(sys.argv[1]); l=labels(im); print(l); tm=timemap(l); print(tm)
    if tm:
        for x in (100,700,1300): print(x,datetime.datetime.utcfromtimestamp(tm['s']*x+tm['b']).date())

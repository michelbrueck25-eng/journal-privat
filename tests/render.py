import json,sys,os,random,datetime as dt
sys.path.insert(0,'/home/claude/journal-privat'); sys.path.insert(0,'/tmp/w')
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import ob_check as ob
HOME='/home/claude/journal-privat'
def load(sym): return json.load(open(f'{HOME}/marktdaten/{sym}_D.json'))['rows']
SD=[s for s in json.load(open('/tmp/w/setups_d.json')) if s['q']!='C']
TG,MD,BUF=1.5,7,0.1
def pipv(sym): return 0.01 if sym.endswith('JPY') else 0.0001
items=[]
for s in SD:
    D=load(s['sym']); i=s['i']; L=s['dir']=='long'; a=ob.atr(D,i)
    entry=s['hi'] if L else s['lo']; stop=(s['lo']-BUF*a) if L else (s['hi']+BUF*a); risk=abs(entry-stop)
    tp=entry+TG*risk if L else entry-TG*risk; sp=pipv(s['sym'])
    res=None
    if (D[i][3]<=stop) if L else (D[i][2]>=stop): res=('SL',i,stop)
    else:
        end=min(i+1+MD,len(D))
        for j in range(i+1,end):
            hs=(D[j][3]<=stop) if L else (D[j][2]>=stop); ht=(D[j][2]>=tp) if L else (D[j][3]<=tp)
            if hs: res=('SL',j,stop);break
            if ht: res=('TP',j,tp);break
        if not res: res=('Zeit',end-1,D[end-1][4])
    if i+1>=len(D): continue
    r=((res[2]-entry) if L else (entry-res[2]))/risk-sp/risk
    items.append(dict(s=s,entry=entry,stop=stop,tp=tp,res=res,r=r,a=a,risk=risk))
print(len(items))
random.seed(7)
# gleichmaessig ueber Zeit, mind. 60
items.sort(key=lambda x:x['s']['date'])
step=max(1,len(items)//64); pick=items[::step][:64]
os.makedirs('/home/claude/journal-privat/strategiebilder',exist_ok=True)
meta=[]
for n,it in enumerate(pick,1):
    s=it['s']; D=load(s['sym']); i=s['i']; L=s['dir']=='long'
    j0=max(0,i-35); j1=min(len(D),it['res'][1]+6)
    fig,ax=plt.subplots(figsize=(7.2,4.0),dpi=80)
    for k in range(j0,j1):
        t,o,h,l,c=D[k]; col='#2a9d6f' if c>=o else '#d1495b'
        ax.plot([k,k],[l,h],color=col,lw=0.9); ax.add_patch(Rectangle((k-0.32,min(o,c)),0.64,max(abs(c-o),1e-9),color=col))
    zi=s['zi']
    ax.add_patch(Rectangle((max(zi,j0)-0.5,s['lo']),j1-max(zi,j0)+0.5,s['hi']-s['lo'],color='#4c78a8',alpha=0.22,lw=0))
    ax.axhline(it['entry'],color='#333',lw=0.8,ls='-'); ax.axhline(it['stop'],color='#d1495b',lw=0.9,ls='--'); ax.axhline(it['tp'],color='#2a9d6f',lw=0.9,ls='--')
    ax.axvline(i,color='#888',lw=0.6,ls=':')
    xs=it['res'][1]; ax.plot([xs],[it['res'][2]],marker='o',color='k',ms=5)
    ds=lambda k: dt.datetime.fromtimestamp(D[k][0]/1000,dt.timezone.utc).strftime('%d.%m.%y')
    ax.set_xticks([j0,i]); ax.set_xticklabels([ds(j0),'Zonenberührung '+ds(i)],fontsize=7)
    ax.tick_params(axis='y',labelsize=7); ax.set_xlim(j0-1,j1+1)
    ax.set_title(f"{s['sym']} {'Long' if L else 'Short'} · Daily-Zone ({s['q']}) · {it['res'][0]} · {it['r']:+.2f} R",fontsize=9)
    for sp_ in ('top','right'): ax.spines[sp_].set_visible(False)
    fig.tight_layout(); fn=f'strategiebilder/smvtc0ajx_{n:02d}.jpg'
    fig.savefig('/home/claude/journal-privat/'+fn,format='jpg',pil_kwargs={'quality':78}); plt.close(fig)
    meta.append(dict(pfad=fn,titel=f"{s['sym']} {'Long' if L else 'Short'} {ds(i)}",ergebnis=f"{it['res'][0]} {it['r']:+.2f} R",r=round(it['r'],2)))
json.dump(meta,open('/tmp/w/bilder_meta.json','w'),ensure_ascii=False)
print(len(meta), sum(1 for m in meta if m['r']>0),'Gewinner')
json.dump([dict(sym=i['s']['sym'],dir=i['s']['dir'],date=i['s']['date'],q=i['s']['q'],r=i['r'],days=i['res'][1]-i['s']['i'],res=i['res'][0]) for i in items],open('/tmp/w/items.json','w'))

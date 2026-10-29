# Definitionsbilder: Orderblock-Regeln an echten Beispielen (Weekly und Daily) mit Einstieg, Stopp, Ziel
import json,sys,datetime
sys.path.insert(0,'/home/claude/journal-privat')
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import ob_check as oc
def rows(sym,tf): return json.load(open(f'marktdaten/{sym}_{tf}.json'))['rows']
def draw(sym,tf,direction,fn,title,nb=22,na=14):
    R=rows(sym,tf)[:-1]; obs=[o for o in oc.find_obs(R,direction) if o['q'] in ('A','B') and o['i']>len(R)-(600 if tf=='W' else 900) and o['i']<len(R)-30]
    # Beispiel: Zone, die später wirklich zurückkam
    best=None
    for o in obs:
        i=o['i']; lo,hi=o['lo'],o['hi']
        for j in range(i+4,min(len(R),i+40)):
            r=R[j]
            if (direction=='long' and r[3]<=hi and r[2]>=lo) or (direction=='short' and r[2]>=lo and r[3]<=hi): best=(o,j); break
        if best: break
    o,j=best; i=o['i']; a=oc.atr(R,i)
    a0=max(0,i-nb); a1=min(len(R)-1,j+na); fig,ax=plt.subplots(figsize=(11,6.2),dpi=110); fig.patch.set_facecolor('#1b1b1b'); ax.set_facecolor('#1b1b1b')
    for k in range(a0,a1+1):
        t,op,h,l,c=R[k]; col='#3a88fe' if c>=op else '#bbbbbb'
        ax.plot([k,k],[l,h],color=col,lw=1); ax.add_patch(Rectangle((k-.3,min(op,c)),.6,max(abs(c-op),a*0.01),color=col))
    lo,hi=o['lo'],o['hi']; ax.add_patch(Rectangle((i-.5,lo),a1-i+1,hi-lo,fill=True,color='#e91ee9',alpha=.18)); ax.add_patch(Rectangle((i-.5,lo),a1-i+1,hi-lo,fill=False,ec='#e91ee9',lw=1.4))
    if direction=='long': entry=hi; stop=lo-0.1*a; tp=entry+1.5*(entry-stop)
    else: entry=lo; stop=hi+0.1*a; tp=entry-1.5*(stop-entry)
    for y,cl,tx in ((entry,'#4ec04e','Einstieg: Limit am Zonenrand'),(stop,'#e5484d','Stopp: 0,1 ATR hinter der Zone'),(tp,'#ffffff','Ziel: 1,5 R')):
        ax.hlines(y,j-.5,a1+.5,color=cl,lw=1.6); ax.text(a1+.7,y,tx,color=cl,va='center',fontsize=9)
    ax.annotate('Orderblock: letzte Gegenkerze\nvor der Bewegung',xy=(i,(lo+hi)/2),xytext=(a0+1,(hi+ (max(R[k][2] for k in range(a0,a1+1)))) /2 if direction=='long' else lo),color='#e91ee9',fontsize=10,arrowprops=dict(arrowstyle='->',color='#e91ee9'))
    mv=max(range(i+1,i+4),key=lambda k:R[k][2] if direction=='long' else -R[k][3])
    ax.annotate('Bewegung weg von der Zone\n(mind. 1 ATR) und Strukturbruch',xy=(mv,R[mv][2] if direction=='long' else R[mv][3]),xytext=(mv+1,R[mv][2]+a*1.2 if direction=='long' else R[mv][3]-a*1.2),color='#ddd',fontsize=9,arrowprops=dict(arrowstyle='->',color='#999'))
    ax.annotate('Preis kehrt zurück\n(erste Berührung der Zone)',xy=(j,R[j][3] if direction=='long' else R[j][2]),xytext=(j-4,R[j][3]-a*2.2 if direction=='long' else R[j][2]+a*2.2),color='#ddd',fontsize=9,arrowprops=dict(arrowstyle='->',color='#999'))
    d=lambda ms: datetime.datetime.utcfromtimestamp(ms/1000).strftime('%d.%m.%Y')
    ax.set_title(f'{title} · Beispiel {sym}, Zeitebene {"Weekly" if tf=="W" else "Daily"}, Zone vom {d(R[i][0])}',color='#eee',fontsize=12)
    ax.tick_params(colors='#999'); [s.set_color('#444') for s in ax.spines.values()]; ax.set_xticks([])
    ax.set_xlim(a0-1,a1+14); fig.tight_layout(); fig.savefig(fn,facecolor=fig.get_facecolor()); plt.close(fig)
import os; os.makedirs('strategiebilder',exist_ok=True)
draw('EURUSD','W','long','strategiebilder/def_weekly_ob_long.jpg','Weekly-Orderblock (Nachfrage, long)')
draw('GBPUSD','W','short','strategiebilder/def_weekly_ob_short.jpg','Weekly-Orderblock (Angebot, short)')
draw('EURUSD','D','long','strategiebilder/def_daily_ob_long.jpg','Daily-Orderblock (Nachfrage, long)')
draw('USDJPY','D','short','strategiebilder/def_daily_ob_short.jpg','Daily-Orderblock (Angebot, short)')

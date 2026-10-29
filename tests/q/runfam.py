import sys,pickle,time
sys.path.insert(0,'/tmp/w/q')
from fam import *
fam=sys.argv[1]; fn,g=FAMS[fam]; res=[]
t0=time.time()
cf=configs(g)
# Signale pro (Familie, Basisparameter ohne tgt/maxd) einmal... einfach alles laufen lassen
for P in cf:
    tr=fn(P); s=stats(tr)
    if s: res.append((P,s,[(x['sym'],x['date'],x['L'],x['r'],x['days'],x['out'],x['i'],x['j'],x['px'],x['risk']) for x in tr]))
pickle.dump(res,open(f'/tmp/w/q/res_{fam}.pkl','wb'))
print(fam,len(cf),len(res),round(time.time()-t0),'s')

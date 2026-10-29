import pickle
src=open('ideen2.py').read().split('res=[]')[0]; exec(src)
res=[]
def add(name,sigs,sa,tg,N):
    tr=runsig(sigs,sa,tg,N); a,b,c=summ(tr); res.append(dict(name=name,sa=sa,tg=tg,N=N,all=a,dev=b,test=c,_tr=tr))
for lb in (104,156,208):
  for ms in (60,70,80):
    for k in (1,2,3):
      sg=sig_cot(lb,k,'folgen',ms)
      for (sa,N) in ((3,20),(4,30),(4,40),(5,55)): add(f'COT {lb}W k{k} A{ms}',sg,sa,None,N)
pickle.dump(res,open('/tmp/ideen3.pkl','wb'))
r=[x for x in res if x['all'].get('avg') is not None]; r.sort(key=lambda x:-x['all']['avg'])
for x in r[:14]: print(x['name'],x['sa'],x['N'],x['all']['n'],x['all']['avg'],'dev',x['dev']['avg'],x['dev']['n'],'test',x['test']['avg'],x['test']['n'],'dd',x['all']['dd'],'j',x['all']['jahr'])
print(len(res),sum(1 for x in r if x['all']['avg']>=0.15),'>=0.15; median',np.median([x['all']['avg'] for x in r]))

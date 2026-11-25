import json, numpy as np, sys
sys.argv=['x']
exec(open('/home/claude/mr4/polish/intrude.py').read().split('rep=[]')[0])

from sklearn.cluster import DBSCAN
allp=[]
for f in ['mr4_track','mr4_struct','mr4_signs']:
    h=check(f, f'/home/claude/mr4/out/{f}.glb')
    for mn,b in h.items():
        b=np.vstack(b)
        for p in b: allp.append((f,mn,p))
X=np.array([p for _,_,p in allp])
lab=DBSCAN(eps=4,min_samples=3).fit(X).labels_
out=[]
for L in sorted(set(lab)):
    sel=[i for i in range(len(allp)) if lab[i]==L]
    pts=X[sel]; c=pts.mean(0)
    mats=sorted(set(allp[i][0][4:]+'/'+allp[i][1] for i in sel))
    # depth: how far inside the nearest marble centre
    d,_=tree.query(pts); depth=MR-d.min()
    out.append((len(sel),np.round(c,1).tolist(),round(float(depth),2),mats, np.round(pts.min(0),1).tolist(), np.round(pts.max(0),1).tolist()))
out.sort(key=lambda o:-o[0])
for o in out: print(o)
json.dump(out,open('/home/claude/mr4/polish/clusters.json','w'))

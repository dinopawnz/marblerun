import json, numpy as np, trimesh
from sklearn.cluster import DBSCAN
P=np.array(json.load(open('/home/claude/mr4/polish/paths.json')))
P=P[P[:,3]==0]; P[:,1]-=P[:,4]; P=P[:,:3]
key=np.round(P/1.0).astype(np.int64); _,idx=np.unique(key,axis=0,return_index=True); P=P[idx]
sc=trimesh.load('/home/claude/mr4/out/mr4_track.glb',force='scene')
top=[]
for name,g in sc.geometry.items():
    mn=g.visual.material.name if hasattr(g.visual,'material') else name
    for node in sc.graph.geometry_nodes.get(name,[]):
        T,_=sc.graph.get(node); m=g.copy(); m.apply_transform(T); top.append(m)
M=trimesh.util.concatenate(top)
ray=trimesh.ray.ray_triangle.RayMeshIntersector(M)
orig=P+np.array([0,1.5,0]); dirs=np.tile([0,-1,0],(len(P),1))
loc,ri,_=ray.intersects_location(orig,dirs,multiple_hits=False)
hit=np.full(len(P),np.inf); hit[ri]=orig[ri,1]-loc[:,1]-1.5   # how far below the contact point the first surface is
bad=P[(hit>0.6)]
print("contact points", len(P), "with no track under them (gap > 0.6 m):", len(bad))
if len(bad):
    lab=DBSCAN(eps=3,min_samples=2).fit(bad).labels_
    rows=[]
    for L in set(lab):
        q=bad[lab==L]; rows.append((len(q),np.round(q.mean(0),1).tolist(),np.round(q.min(0),1).tolist(),np.round(q.max(0),1).tolist()))
    for r in sorted(rows,key=lambda r:-r[0])[:40]: print(r)
json.dump(bad.tolist(),open('/home/claude/mr4/polish/gaps.json','w'))

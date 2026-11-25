import json, math, numpy as np, trimesh
from scipy.spatial import cKDTree
MR=4.0
P=np.array(json.load(open('/home/claude/mr4/polish/paths.json')))
# unique marble centres on a 0.5 m grid
C=P[:,:3].copy(); C[:,1]+=MR
key=np.round(C/0.5).astype(np.int64); _,idx=np.unique(key,axis=0,return_index=True); C=C[idx]; AIR=P[idx,3]
tree=cKDTree(C)
w=json.load(open('/home/claude/mr4/out/world4.json'))
def parts(path, xf=None):
    sc=trimesh.load(path, force='scene')
    for name,g in sc.geometry.items():
        for node in sc.graph.geometry_nodes.get(name,[]):
            T,_=sc.graph.get(node)
            m=g.copy(); m.apply_transform(T)
            if xf is not None: m.apply_transform(xf)
            mn=getattr(getattr(m.visual,'material',None),'name',None) or name
            yield mn, m
def check(label, path, xf=None, thr=MR-0.35, report=None):
    hits={}
    for mn,m in parts(path,xf):
        if len(m.faces)==0: continue
        pts,_=trimesh.sample.sample_surface_even(m, max(200,int(m.area/0.15)), radius=None)
        if len(pts)==0: continue
        d,_=tree.query(pts, distance_upper_bound=thr)
        bad=pts[np.isfinite(d)]
        if len(bad): hits[mn]=hits.get(mn,[])+[bad]
    for mn,b in hits.items():
        b=np.vstack(b)
        print(f"{label:22s} {mn:28s} {len(b):6d} pts  e.g. {np.round(b[len(b)//2],1).tolist()}")
        if report is not None: report.append([label,mn,np.round(b[::max(1,len(b)//40)],1).tolist()])
    return hits
rep=[]
for f in ['mr4_track','mr4_struct','mr4_signs','mr4_station','mr4_ground']:
    check(f, f'/home/claude/mr4/out/{f}.glb', report=rep)
for i,(name,x,y,z,ry,s,anim) in enumerate(w['props']):
    a=math.radians(ry)
    T=np.array([[s*math.cos(a),0,s*math.sin(a),x],[0,s,0,y],[-s*math.sin(a),0,s*math.cos(a),z],[0,0,0,1]])
    check(f'prop{i}:{name}', f'/home/claude/mr4/out/{name}.glb', T, report=rep)
json.dump(rep,open('/home/claude/mr4/polish/intrude.json','w'))

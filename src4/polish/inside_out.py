import trimesh, numpy as np, glob, os, sys
files = sys.argv[1:] or sorted(glob.glob('/home/claude/mr4/out/mr4_*.glb'))
for f in files:
    n=os.path.basename(f)[:-4]
    if n.startswith(('mr4_lit_','mr4_trail_')) and not n.endswith('_rose'): continue
    if 'collide' in n: continue
    sc=trimesh.load(f,force='scene')
    for name,g in sc.geometry.items():
        mn=getattr(g.visual,'material',None); mn=mn.name if mn is not None else name
        for node in sc.graph.geometry_nodes.get(name,[]):
            T,_=sc.graph.get(node); m=g.copy(); m.apply_transform(T)
            comps=m.split(only_watertight=False)
            tot=0; inw=0
            for c in comps:
                if len(c.faces)<12: continue
                cen=c.vertices.mean(0)
                d=((c.triangles_center-cen)*c.face_normals).sum(1)
                a=c.area_faces
                tot+=a.sum(); inw+=a[d<0].sum()
            if tot>0 and inw/tot>0.35:
                print(f"{n:22s} {mn:18s} inward {100*inw/tot:5.1f}%  comps {len(comps)}")

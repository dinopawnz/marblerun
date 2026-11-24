"""Finds z-fighting: two surfaces facing the same way, closer than TOL, overlapping by more than AREA."""
import sys, numpy as np, trimesh
from shapely.geometry import Polygon
from collections import defaultdict
TOL, AREA = 0.08, 0.02
tris, src = [], []
for f in sys.argv[1:]:
    sc = trimesh.load(f, force="scene")
    for name, g in sc.geometry.items():
        T = sc.graph.get(name)[0] if name in sc.graph.nodes else np.eye(4)
        for node in sc.graph.nodes_geometry:
            if sc.graph[node][1] == name:
                m = g.copy(); m.apply_transform(sc.graph[node][0])
                mn = getattr(getattr(g.visual, "material", None), "name", "?")
                tris.append(m.triangles); src += [f.split("/")[-1] + ":" + str(mn)] * len(m.triangles)
T = np.concatenate(tris)
n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); area = np.linalg.norm(n, axis=1) / 2
ok = area > 1e-4
_n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); _n /= (np.linalg.norm(_n, axis=1)[:, None] + 1e-12)
ok &= ~((_n[:, 1] < -0.9) & (T[:, :, 1].max(1) < 0.25))     # bottoms resting on the ground: never seen
T, n, area = T[ok], n[ok], area[ok]; src = [s for s, k in zip(src, ok) if k]
n = n / np.linalg.norm(n, axis=1)[:, None]
d = np.einsum("ij,ij->i", n, T[:, 0])
# bucket by rounded normal; within a bucket, by plane offset
key = np.round(n * 50).astype(int)
groups = defaultdict(list)
for i, k in enumerate(map(tuple, key)): groups[k].append(i)
hits = []
for k, idx in groups.items():
    idx = np.array(idx)
    o = np.argsort(d[idx]); idx = idx[o]
    nn = n[idx[0]]
    # 2D frame on the plane
    a = np.cross(nn, [0, 0, 1] if abs(nn[2]) < 0.9 else [1, 0, 0]); a /= np.linalg.norm(a); b = np.cross(nn, a)
    P2 = np.stack([np.einsum("ijk,k->ij", T[idx], a), np.einsum("ijk,k->ij", T[idx], b)], -1)
    lo, hi = P2.min(1), P2.max(1)
    for ii in range(len(idx)):
        jj = ii + 1
        while jj < len(idx) and d[idx[jj]] - d[idx[ii]] < TOL:
            if (lo[ii] < hi[jj]).all() and (lo[jj] < hi[ii]).all():
                ov = Polygon(P2[ii]).intersection(Polygon(P2[jj])).area
                if ov > AREA and not (src[idx[ii]] == src[idx[jj]] and abs(d[idx[jj]] - d[idx[ii]]) < 0.002):
                    c = T[idx[ii]].mean(0)
                    hits.append((ov, src[idx[ii]], src[idx[jj]], abs(d[idx[jj]] - d[idx[ii]]), c))
            jj += 1
hits.sort(key=lambda h: -h[0])
from collections import Counter
cat = Counter((h[1], round(h[4][1]), round(h[3], 2)) for h in hits)
for (f, y, gap), c in cat.most_common(25): print("   %4d x  %s  at height %s  %.2f m apart" % (c, f, y, gap))
print(len(hits), "overlapping pairs")
for h in hits[:15]:
    print("  %.2f m2  %s / %s  %.3f m apart  near (x %.1f, y %.1f, z %.1f) [glTF coords]" % (h[0], h[1], h[2], h[3], *h[4]))
if "-v" in sys.argv[0:0] or True:
    import os
    if os.environ.get("ZV"):
        for h in [h for h in hits if h[3] < 0.005][:40]:
            print("  0gap %.2f m2 %s|%s  (x %.1f, y %.2f, z %.1f)" % (h[0], h[1], h[2], *h[4]))
if os.environ.get("ZP"):
    pc = Counter((min(h[1],h[2]), max(h[1],h[2]), round(h[3],2)) for h in hits)
    for (a,b,g),c in pc.most_common(60): print("  pair %4d  %s | %s  gap %.2f" % (c,a,b,g))
if os.environ.get("ZW"):
    a,b = os.environ["ZW"].split(",")
    for h in hits:
        if {h[1].split(":")[1],h[2].split(":")[1]} == {a,b}: print("  where %.2f m2 gap %.2f (x %.1f, y %.2f, z %.1f)" % (h[0],h[3],*h[4]))

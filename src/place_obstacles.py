"""Writes out/_placed.glb: the moving parts where they rest at the start, for the overlap check."""
import json, math, trimesh, numpy as np
c = json.load(open("course.json"))
H, D = c["heading"], c["dirs"]
sc = trimesh.Scene()
def put(f, at, ry):
    m = trimesh.load(f, force="scene")
    T = trimesh.transformations.translation_matrix(at) @ trimesh.transformations.rotation_matrix(math.radians(ry), [0, 1, 0])
    for node in m.graph.nodes_geometry:
        tf, g = m.graph[node]
        sc.add_geometry(m.geometry[g].copy(), transform=T @ tf, geom_name=g + "_%d" % len(sc.geometry))
for k in range(8):
    for key, run in (("gates", 3), ("last_gates", 11)):
        p = c[key][k]; n = [D[run][1], -D[run][0]]
        put("out/mr_gate.glb", [p[0] - n[0] * 4.3, p[1], p[2] - n[1] * 4.3], H[run])
    t = c["traps"][k]; d5 = D[5]
    put("out/mr_hatch.glb", [t[0] - d5[0] * 4.6, t[1], t[2] - d5[1] * 4.6], H[5])
    put("out/mr_elev.glb", c["elevs"][k], 0)
sc.export("out/_placed.glb")

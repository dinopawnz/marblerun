import trimesh, numpy as np, os
raw = trimesh.load('/home/claude/mr4/out/mr4_collide_raw.glb', force='mesh')
c = raw.triangles_center
keep = ((abs(c[:, 0]) <= 80) & (c[:, 2] >= -30) & (c[:, 2] <= 15))
for bx, bz in ((440, 80), (232, -160)):
    keep |= (np.hypot(c[:, 0] - bx, c[:, 2] - bz) < 6)
st = trimesh.Trimesh(raw.vertices, raw.faces[keep], process=True)
gr = trimesh.load('/home/claude/mr4/out/mr4_ground.glb', force='mesh')
gr = trimesh.Trimesh(gr.vertices, gr.faces, process=True)
m = trimesh.util.concatenate([st, gr]); m.merge_vertices()
m = trimesh.Trimesh(vertices=m.vertices, faces=m.faces, process=True)
m.visual = trimesh.visual.ColorVisuals(m)
m.export('/home/claude/mr4/out/mr4_collide.glb', include_normals=False)
print('collider', len(m.faces), 'tris', os.path.getsize('/home/claude/mr4/out/mr4_collide.glb') // 1024, 'KB', m.bounds.round(1).tolist())

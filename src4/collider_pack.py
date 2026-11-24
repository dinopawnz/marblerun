"""mr_collide_raw.glb -> mr_collide.glb: one welded mesh, positions only (a PLAIN glb: no meshopt, no gzip)."""
import trimesh
m = trimesh.load("/home/claude/mr4/out/mr4_collide_raw.glb", force="mesh")
m.merge_vertices()
m = trimesh.Trimesh(vertices=m.vertices, faces=m.faces, process=True)
m.visual = trimesh.visual.ColorVisuals(m)
m.export("/home/claude/mr4/out/mr4_collide.glb", include_normals=False)
import os; print("collider", len(m.faces), "tris", os.path.getsize("/home/claude/mr4/out/mr4_collide.glb") // 1024, "KB")

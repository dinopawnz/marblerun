import sys, math, json
sys.path.insert(0, "/home/claude/mr")
import bpy
from mathutils import Vector
from blib import reset, B, OUT
import course as C

reset()
sc = bpy.context.scene
def imp(name, loc=(0, 0, 0), yaw=0, rx=0, rz=0):
    bpy.ops.import_scene.gltf(filepath=f"{OUT}/{name}.glb")
    objs = list(bpy.context.selected_objects)
    root = bpy.data.objects.new(name + "_root", None)
    sc.collection.objects.link(root)
    for o in objs:
        if o.parent is None:
            o.parent = root
    root.location = B(loc)
    root.rotation_mode = "XYZ"
    root.rotation_euler = (math.radians(rx), math.radians(-rz), math.radians(yaw))
    return root

imp("mr_ground"); imp("mr_track"); imp("mr_scenery"); imp("mr_bridge")
names = [n.lower() for n in C.NAMES]
SNAP = sys.argv[sys.argv.index("--") + 1] if "--snap" in sys.argv else None
snaps = json.load(open("/home/claude/mr/out/snaps.json"))
which0 = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["all"]
snap = next((w.split("=")[1] for w in which0 if w.startswith("t=")), "64")
for k in range(8):
    p = snaps[snap][k]
    imp("mr_pod_" + names[k], p)
    imp("mr_ball_" + names[k], (p[0], p[1] + C.MR, p[2]))

# sky + sun
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.55, 0.7, 0.95, 1); bg.inputs[1].default_value = 0.9
sun = bpy.data.lights.new("sun", "SUN"); sun.energy = 3.5
so = bpy.data.objects.new("sun", sun); sc.collection.objects.link(so); so.rotation_euler = (math.radians(50), 0, math.radians(35))
cam = bpy.data.cameras.new("cam"); cam.lens = 28; cam.clip_end = 3000
co = bpy.data.objects.new("cam", cam); sc.collection.objects.link(co); sc.camera = co
sc.render.engine = "CYCLES"; sc.cycles.samples = 24; sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 1280, 720
def shot(name, eye, look, lens=28):
    cam.lens = lens
    co.location = B(eye)
    d = Vector(B(look)) - Vector(B(eye))
    co.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = f"/home/claude/mr/preview_{name}.png"
    bpy.ops.render.render(write_still=True)
which = which0
def at_snap(k):
    return snaps[snap][k]
if "all" in which or "over" in which: shot("overview", (-170, 260, -330), (130, 30, 40), 24)
if "all" in which or "station" in which: shot("station", (-30, 14, -55), (0, 4, 10), 26)
if "all" in which or "finish" in which: shot("finish", (22, 9, -30), (-4, 14, -62), 24)
if "corner" in which: shot("corner", (240 + 70, 105, 300 + 60), (225, 60, 300), 26)
if "pinball" in which: shot("pinball", (300, 80, 300), (240, 50, 200), 28)
if "zig" in which: shot("zig", (60, 110, 230), (190, 40, 110), 24)
if "near" in which:
    p = at_snap(int(next((w.split("=")[1] for w in which if w.startswith("k=")), "0")))
    shot("near", (p[0] + 22, p[1] + 14, p[2] + 22), (p[0], p[1] + 3, p[2]), 30)

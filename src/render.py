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
lanes = json.load(open("/home/claude/mr/course.json"))["lanes"]
names = [n.lower() for n in C.NAMES]
# marbles: four parked in the station, others out on the course
spots = {0: 0, 1: 0, 2: 3, 3: 6, 4: 7, 5: 9, 6: 10, 7: 0}
for k in range(8):
    g = lanes[k][spots[k]]
    p = g["a"] if spots[k] == 0 else [(g["a"][i] + g["b"][i]) / 2 for i in range(3)]
    imp("mr_pod_" + names[k], p)
    imp("mr_ball_" + names[k], (p[0], p[1] + C.MR, p[2]))
for k in range(8):
    ga = json.load(open("/home/claude/mr/course.json"))["gates"][k]
    d = C.D[3]; n = C.normal(d)
    imp("mr_gate", (ga[0] - n[0] * 4.3, ga[1], ga[2] - n[1] * 4.3), yaw=C.heading_deg(3), rz=0 if k % 2 else 80)
    tr = json.load(open("/home/claude/mr/course.json"))["traps"][k]
    d5 = C.D[5]
    imp("mr_hatch", (tr[0] - d5[0] * 4.6, tr[1], tr[2] - d5[1] * 4.6), yaw=C.heading_deg(5), rx=0 if k % 3 else -80)
    el = json.load(open("/home/claude/mr/course.json"))["elevs"][k]
    imp("mr_elev", (el[0], el[1] + (k % 3) * 3, el[2]))

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
which = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["all"]
if "all" in which or "over" in which: shot("overview", (-170, 210, -330), (130, 10, 40), 24)
if "all" in which or "station" in which: shot("station", (-30, 14, -55), (0, 4, 10), 26)
if "all" in which or "zig" in which: shot("obstacles", (60, 95, 200), (200, 40, 110), 26)
if "all" in which or "inside" in which:
    g = lanes[2][3]; p = [(g["a"][i] + g["b"][i]) / 2 for i in range(3)]
    d = C.D[g["run"]]
    shot("inside", (p[0] - d[0] * 1.5, p[1] + 2.9, p[2] - d[1] * 1.5), (p[0] + d[0] * 60, p[1] - 4, p[2] + d[1] * 60), 22)
if "all" in which or "finish" in which: shot("finish", (22, 9, -30), (-4, 14, -62), 24)
if "corner" in which: shot("corner", (240 + 60, 75, 300 + 50), (240, 44, 300), 26)

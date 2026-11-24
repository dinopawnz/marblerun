"""Night renders for v4: imports glTF models, dark sky, glow (compositor glare)."""
import bpy, sys, math, json, os
from mathutils import Vector
sys.path.insert(0, "/home/claude/mr4")

OUT = "/home/claude/mr4/out"


def setup(samples=48, res=(1280, 720)):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    try:
        sc.cycles.device = "CPU"
    except Exception:
        pass
    sc.render.resolution_x, sc.render.resolution_y = res
    w = bpy.data.worlds.new("night"); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    sky = w.node_tree.nodes.new("ShaderNodeTexGradient")
    # deep night: a gradient from indigo at the horizon to near-black
    bg.inputs["Color"].default_value = (0.012, 0.01, 0.04, 1)
    bg.inputs["Strength"].default_value = 1.0
    # moon light
    L = bpy.data.lights.new("moon", "SUN"); L.energy = 0.35; L.color = (0.6, 0.7, 1.0)
    lo = bpy.data.objects.new("moon", L); sc.collection.objects.link(lo); lo.rotation_euler = (0.9, 0.2, 0.6)
    # glow: compositor glare (bloom)
    try:
        sc.use_nodes = True
        nt = sc.node_tree
        rl = nt.nodes.get("Render Layers") or nt.nodes.new("CompositorNodeRLayers")
        comp = nt.nodes.get("Composite") or nt.nodes.new("CompositorNodeComposite")
        g = nt.nodes.new("CompositorNodeGlare")
        try:
            g.glare_type = "BLOOM"
        except Exception:
            g.glare_type = "FOG_GLOW"
        for attr, val in (("threshold", 0.6), ("size", 8), ("quality", "HIGH")):
            try:
                setattr(g, attr, val)
            except Exception:
                pass
        nt.links.new(rl.outputs["Image"], g.inputs[0])
        nt.links.new(g.outputs[0], comp.inputs[0])
    except Exception as e:
        print("no compositor glare:", e)
    sc.view_settings.view_transform = "AgX" if "AgX" in [i.identifier for i in sc.view_settings.bl_rna.properties["view_transform"].enum_items] else "Filmic"
    sc.view_settings.look = "None"
    return sc


def imp(name, at=(0, 0, 0), ry=0.0, s=1.0):
    path = os.path.join(OUT, name + ".glb")
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in new if o.parent is None or o.parent not in new]
    for o in roots:
        o.location = Vector((at[0], -at[2], at[1])) + o.location
        o.rotation_euler[2] += math.radians(ry)
        o.scale *= s
    return new


def shot(name, eye, look, lens=28, sc=None):
    sc = sc or bpy.context.scene
    cam = bpy.data.cameras.new(name); cam.lens = lens; cam.clip_end = 5000
    co = bpy.data.objects.new(name, cam); sc.collection.objects.link(co)
    co.location = Vector((eye[0], -eye[2], eye[1]))
    d = Vector((look[0], -look[2], look[1])) - co.location
    co.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    sc.camera = co
    sc.render.filepath = os.path.join("/home/claude/mr4", "preview_" + name + ".png")
    bpy.ops.render.render(write_still=True)
    print("rendered", name)


if __name__ == "__main__" and "--props" in sys.argv:
    sc = setup(40)
    names = ["mr4_mush_m", "mr4_mush_c", "mr4_mush_l", "mr4_bumper_a", "mr4_fern_g", "mr4_fern_v", "mr4_fronds_g", "mr4_crystals_c",
             "mr4_crystals_p", "mr4_crystals_g", "mr4_willow", "mr4_island_a", "mr4_jelly_a", "mr4_jelly_b"]
    pos = {}
    for i, n in enumerate(names):
        x = (i % 7) * 20 - 60; z = (i // 7) * 28
        y = 14 if "island" in n or "jelly" in n else 0
        imp(n, (x, y, z))
    # a ground plane under them
    imp("mr4_groundtest") if os.path.exists(os.path.join(OUT, "mr4_groundtest.glb")) else None
    shot("props", (0, 30, -70), (0, 8, 14), 24)


def world(prop_limit=400):
    for n in ("mr4_track", "mr4_struct", "mr4_signs", "mr4_station", "mr4_ground"):
        imp(n)
    W = json.load(open(os.path.join(OUT, "world4.json")))
    cache = {}
    for name, x, y, z, ry, s, anim in W["props"][:prop_limit]:
        if name not in cache:
            objs = imp(name, (0, -1000, 0))
            cache[name] = [o for o in objs if o.type == "MESH"]
        for o in cache[name]:
            d = o.copy()
            bpy.context.scene.collection.objects.link(d)
            d.parent = None
            d.matrix_world = o.matrix_world.copy()
            d.location = Vector((x, -z, y))
            d.rotation_euler = (math.radians(90), 0, math.radians(ry)) if False else d.rotation_euler
            d.rotation_euler[2] += math.radians(ry)
            d.scale = Vector((s, s, s)) * (o.matrix_world.to_scale().x)
            # (armature-deformed props render in their rest pose)
            for m in list(d.modifiers):
                d.modifiers.remove(m)
    return W


def marbles(snapfile, t):
    S = json.load(open(snapfile))[str(t)]
    names = ["ruby", "cobalt", "jade", "amber", "violet", "frost", "rose", "copper"]
    for k, p in enumerate(S):
        if os.path.exists(os.path.join(OUT, "mr4_pod_" + names[k] + ".glb")):
            imp("mr4_pod_" + names[k], p)
            imp("mr4_ball_" + names[k], (p[0], p[1] + 4, p[2]))


if __name__ == "__main__" and "--world" in sys.argv:
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sc = setup(int(next((a.split("=")[1] for a in args if a.startswith("s=")), "40")))
    world()
    snap = next((a.split("=")[1] for a in args if a.startswith("t=")), None)
    if snap:
        marbles(os.path.join(OUT, "snaps.json"), snap)
    VIEWS = {
        "over": ((-260, 380, -520), (260, 40, -40), 22),
        "start": ((60, 190, 160), (0, 150, 330), 24),
        "bowl": ((70, 175, 380), (10, 140, 420), 22),
        "pinball": ((370, 140, 380), (300, 105, 300), 24),
        "bumpers": ((600, 110, 140), (520, 80, 60), 24),
        "tunnel": ((520, 95, -95), (420, 70, -60), 22),
        "station": ((-40, 16, -70), (0, 8, 0), 26),
        "finish": ((25, 10, -20), (0, 14, -62), 26),
        "forest": ((-200, 40, -330), (-140, 10, -380), 24),
    }
    for v in [a for a in args if a in VIEWS]:
        e, l, lens = VIEWS[v]
        shot("w_" + v, e, l, lens)

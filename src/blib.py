"""Small Blender helpers: build meshes in MML coordinates (x, y-up, z), materials, text textures."""
import bpy, bmesh, math, os
from mathutils import Vector
from PIL import Image, ImageDraw, ImageFont

_mats = {}
OUT = "/home/claude/mr/out"
TEX = "/home/claude/mr/tex"
os.makedirs(OUT, exist_ok=True)
os.makedirs(TEX, exist_ok=True)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _mats.clear()


def hexrgb(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    # sRGB -> linear for Blender colour inputs
    return [((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c]





def mat(name, color="#808080", rough=0.5, metal=0.0, emit=0.0, alpha=1.0, image=None, emit_image=False):
    key = name
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    rgb = hexrgb(color) + [1]
    b.inputs["Base Color"].default_value = rgb
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if image:
        img = bpy.data.images.load(image)
        tn = nt.nodes.new("ShaderNodeTexImage")
        tn.image = img
        nt.links.new(tn.outputs["Color"], b.inputs["Base Color"])
        if emit_image:
            nt.links.new(tn.outputs["Color"], b.inputs["Emission Color"])
            b.inputs["Emission Strength"].default_value = emit or 0.5
    elif emit:
        b.inputs["Emission Color"].default_value = rgb
        b.inputs["Emission Strength"].default_value = emit
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
        try:
            m.surface_render_method = "BLENDED"
        except Exception:
            m.blend_method = "BLEND"
    _mats[key] = m
    return m


def text_png(name, text, w=1024, h=256, bg="#12161f", fg="#ffd23f", border=None, size=None, sub=None):
    path = os.path.join(TEX, name + ".png")
    im = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(im)
    if border:
        d.rectangle([6, 6, w - 7, h - 7], outline=border, width=max(4, h // 32))
    fs = size or int(h * 0.62)
    while True:
        f = ImageFont.truetype(FONT, fs)
        bb = d.textbbox((0, 0), text, font=f)
        if bb[2] - bb[0] <= w * 0.9 or fs < 10:
            break
        fs -= 4
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    yoff = -h * 0.08 if sub else 0
    d.text(((w - tw) / 2 - bb[0], (h - th) / 2 - bb[1] + yoff), text, font=f, fill=fg)
    if sub:
        f2 = ImageFont.truetype(FONT, int(h * 0.16))
        bb2 = d.textbbox((0, 0), sub, font=f2)
        d.text(((w - (bb2[2] - bb2[0])) / 2 - bb2[0], h * 0.78 - bb2[1]), sub, font=f2, fill=fg)
    im.save(path)
    return path


def checker_png(name, n=8, w=512, h=128, a="#111111", b="#f4f4f4"):
    path = os.path.join(TEX, name + ".png")
    im = Image.new("RGB", (w, h), a)
    d = ImageDraw.Draw(im)
    cw, ch = w // n, h // 2
    for r in range(2):
        for c in range(n):
            if (r + c) % 2:
                d.rectangle([c * cw, r * ch, (c + 1) * cw - 1, (r + 1) * ch - 1], fill=b)
    im.save(path)
    return path


def B(p):   # MML (x, y, z) -> Blender (x, -z, y)
    return (p[0], -p[2], p[1])


class Mesh:
    """collects faces in MML coordinates; each face has a material and optional UVs"""

    def __init__(self):
        self.v, self.f, self.m, self.uv = [], [], [], []
        self.mats = []

    def mi(self, material):
        if material not in self.mats:
            self.mats.append(material)
        return self.mats.index(material)

    def face(self, pts, material, uv=None, out=None):
        """pts in MML coords. out: a point the face must face away from (for solids)"""
        if out is not None:
            a, b, c = Vector(pts[0]), Vector(pts[1]), Vector(pts[2])
            n = (b - a).cross(c - a)
            ctr = sum((Vector(p) for p in pts), Vector()) / len(pts)
            if n.dot(ctr - Vector(out)) < 0:
                pts = list(reversed(pts))
                if uv:
                    uv = list(reversed(uv))
        base = len(self.v)
        self.v.extend(pts)
        self.f.append(list(range(base, base + len(pts))))
        self.m.append(self.mi(material))
        self.uv.append(uv or [(0, 0)] * len(pts))

    def solid(self, bottom, top, material, cap_mat=None, uvscale=None):
        """a closed prism from a bottom ring and a top ring of points (same count)"""
        n = len(bottom)
        ctr = tuple(sum(p[i] for p in bottom + top) / (2 * n) for i in range(3))
        self.face(list(top), cap_mat or material, out=ctr)
        self.face(list(bottom), material, out=ctr)
        for i in range(n):
            j = (i + 1) % n
            self.face([bottom[i], bottom[j], top[j], top[i]], material, out=ctr)

    def box(self, c, s, material, yaw=0.0, cap_mat=None):
        """axis box at centre c, size s (w, h, d), turned yaw degrees about y"""
        w, h, d = s[0] / 2, s[1] / 2, s[2] / 2
        cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        ring = []
        for (x, z) in ((-w, -d), (w, -d), (w, d), (-w, d)):
            ring.append((c[0] + x * cy + z * sy, c[2] - x * sy + z * cy))
        bot = [(x, c[1] - h, z) for x, z in ring]
        top = [(x, c[1] + h, z) for x, z in ring]
        self.solid(bot, top, material, cap_mat)

    def prism(self, c, r, h, material, n=8, y0=None, cap_mat=None, r_top=None):
        y0 = c[1] - h / 2 if y0 is None else y0
        rt = r if r_top is None else r_top
        bot = [(c[0] + r * math.cos(2 * math.pi * k / n + math.pi / n), y0, c[2] + r * math.sin(2 * math.pi * k / n + math.pi / n)) for k in range(n)]
        top = [(c[0] + rt * math.cos(2 * math.pi * k / n + math.pi / n), y0 + h, c[2] + rt * math.sin(2 * math.pi * k / n + math.pi / n)) for k in range(n)]
        self.solid(bot, top, material, cap_mat)

    def sign(self, c, w, h, yaw, material, two=True, thick=0.3, frame=None):
        """a text panel facing +z turned by yaw (both sides show the picture, the right way round)"""
        cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        def P(x, y, z):
            return (c[0] + x * cy + z * sy, c[1] + y, c[2] - x * sy + z * cy)
        hw, hh, t = w / 2, h / 2, thick / 2
        if frame:
            self.box((c[0], c[1], c[2]), (w + 0.6, h + 0.6, thick * 0.8), frame, yaw=yaw)
        front = [P(-hw, -hh, t), P(hw, -hh, t), P(hw, hh, t), P(-hw, hh, t)]
        self.face(front, material, uv=[(0, 0), (1, 0), (1, 1), (0, 1)], out=P(0, 0, -5))
        if two:
            back = [P(hw, -hh, -t), P(-hw, -hh, -t), P(-hw, hh, -t), P(hw, hh, -t)]
            self.face(back, material, uv=[(0, 0), (1, 0), (1, 1), (0, 1)], out=P(0, 0, 5))

    def obj(self, name, smooth=False):
        me = bpy.data.meshes.new(name)
        verts = [B(p) for p in self.v]
        me.from_pydata(verts, [], self.f)
        me.update()
        uvl = me.uv_layers.new(name="UVMap")
        k = 0
        for poly, uvs in zip(me.polygons, self.uv):
            for li, u in zip(poly.loop_indices, uvs):
                uvl.data[li].uv = u
            poly.material_index = self.m[k]
            poly.use_smooth = smooth
            k += 1
        for m in self.mats:
            me.materials.append(m)
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        # merge duplicate verts inside each solid would break UV seams; keep as is
        return ob


def bevel(ob, width=0.06, segs=1):
    md = ob.modifiers.new("bevel", "BEVEL")
    md.width = width
    md.segments = segs
    md.limit_method = "ANGLE"
    return ob


def export(name, objs=None):
    bpy.ops.object.select_all(action="DESELECT")
    for o in (objs or bpy.context.scene.objects):
        o.select_set(True)
    path = os.path.join(OUT, name + ".glb")
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True,
                              export_yup=True, export_cameras=False, export_lights=False)
    return path


def tris(objs=None):
    dg = bpy.context.evaluated_depsgraph_get()
    n = 0
    for o in (objs or bpy.context.scene.objects):
        if o.type != "MESH":
            continue
        me = o.evaluated_get(dg).to_mesh()
        me.calc_loop_triangles()
        n += len(me.loop_triangles)
        o.evaluated_get(dg).to_mesh_clear()
    return n

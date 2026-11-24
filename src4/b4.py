"""Blender helpers for v4: meshes with UVs built in MML coordinates (x, y up, z), glowing PBR materials,
lofts / lathes / sweeps, armature animation, glTF export."""
import bpy, bmesh, math, os, random
from mathutils import Vector, Matrix

OUT = "/home/claude/mr4/out"
TEX = "/home/claude/mr4/tex"
os.makedirs(OUT, exist_ok=True)
_mats = {}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _mats.clear()


def lin(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c]


def B(p):
    """MML (x, y-up, z) -> Blender (x, -z, y); the glTF exporter (y-up) turns it back"""
    return Vector((p[0], -p[2], p[1]))


def mat(name, tex=None, color="#ffffff", emit=0.0, emit_color=None, rough=0.45, metal=0.0, alpha=1.0, glow_tex=True):
    """tex: a name from tex/ (uses <tex>.png as colour and <tex>_e.png as glow); or plain colours"""
    if name in _mats:
        return _mats[name]
    m = bpy.data.materials.new(name)
    m.use_backface_culling = True       # one-sided: Otherside counts double-sided triangles twice
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Base Color"].default_value = lin(color) + [1]
    if tex:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(os.path.join(TEX, tex + ".png"))
        nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
        ep = os.path.join(TEX, tex + "_e.png")
        if glow_tex and emit and os.path.exists(ep):
            e = nt.nodes.new("ShaderNodeTexImage")
            e.image = bpy.data.images.load(ep)
            nt.links.new(e.outputs["Color"], b.inputs["Emission Color"])
            b.inputs["Emission Strength"].default_value = emit
    if emit and (not tex or not glow_tex):
        b.inputs["Emission Color"].default_value = lin(emit_color or color) + [1]
        b.inputs["Emission Strength"].default_value = emit
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
        try:
            m.surface_render_method = "BLENDED"
        except Exception:
            m.blend_method = "BLEND"
    _mats[name] = m
    return m


class Mesh:
    """collects faces (MML coords) with UVs and materials, then becomes one object"""

    def __init__(self):
        self.v, self.f, self.uv, self.m = [], [], [], []
        self.mats = []

    def _mi(self, m):
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def face(self, pts, m, uv=None):
        base = len(self.v)
        self.v.extend(pts)
        self.f.append(list(range(base, base + len(pts))))
        self.uv.append(uv or [(0, 0)] * len(pts))
        self.m.append(self._mi(m))

    def grid(self, P, m, uvs=None, closed_u=False, flip=False):
        """P[i][j]: rows of points; quads between them. uvs[i][j] optional"""
        ni, nj = len(P), len(P[0])
        for i in range(ni - 1):
            for j in range(nj - (0 if closed_u else 1)):
                j2 = (j + 1) % nj
                q = [P[i][j], P[i + 1][j], P[i + 1][j2], P[i][j2]]
                if uvs:
                    u = [uvs[i][j], uvs[i + 1][j], uvs[i + 1][j2] if j2 else (uvs[i + 1][j][0] + (uvs[i + 1][j][0] - uvs[i + 1][j - 1][0] if j else 0), uvs[i + 1][j][1]), uvs[i][j2] if j2 else (uvs[i][j][0] + (uvs[i][j][0] - uvs[i][j - 1][0] if j else 0), uvs[i][j][1])]
                else:
                    u = [(j / nj, i / (ni - 1)), (j / nj, (i + 1) / (ni - 1)), ((j + 1) / nj, (i + 1) / (ni - 1)), ((j + 1) / nj, i / (ni - 1))]
                if flip:
                    q, u = q[::-1], u[::-1]
                self.face(q, m, u)

    def tube(self, rings, m, vrep=1.0, urep=1.0, cap0=None, cap1=None):
        """rings: list of closed point loops (same count); quads between consecutive loops, normals outward"""
        n = len(rings[0])
        L = [0.0]
        for a, b in zip(rings, rings[1:]):
            ca = Vector(sum((Vector(p) for p in a), Vector()) / n); cb = Vector(sum((Vector(p) for p in b), Vector()) / n)
            L.append(L[-1] + (cb - ca).length)
        tot = max(L[-1], 1e-6)
        for i in range(len(rings) - 1):
            for j in range(n):
                j2 = (j + 1) % n
                q = [rings[i][j], rings[i][j2], rings[i + 1][j2], rings[i + 1][j]]
                u = [(j / n * urep, L[i] / tot * vrep), ((j + 1) / n * urep, L[i] / tot * vrep), ((j + 1) / n * urep, L[i + 1] / tot * vrep), (j / n * urep, L[i + 1] / tot * vrep)]
                self.face(q, m, u)
        for ring, cm, rev in ((rings[0], cap0, True), (rings[-1], cap1, False)):
            if cm:
                c = tuple(sum(p[k] for p in ring) / n for k in range(3))
                for j in range(n):
                    tri = [c, ring[j], ring[(j + 1) % n]]
                    self.face(tri[::-1] if rev else tri, cm, [(0.5, 0.5), (0.5 + 0.5 * math.cos(j / n * 6.283), 0.5 + 0.5 * math.sin(j / n * 6.283)), (0.5 + 0.5 * math.cos((j + 1) / n * 6.283), 0.5 + 0.5 * math.sin((j + 1) / n * 6.283))])

    def lathe(self, prof, m, c=(0, 0, 0), seg=24, vrep=1.0, urep=1.0, ry=0.0, wobble=0.0, seed=0):
        """prof: [(radius, y)] bottom->top; spun round the y axis at c"""
        rnd = random.Random(seed)
        rings = []
        ph = [rnd.random() * 6.283 for _ in range(3)]
        for r, y in prof:
            ring = []
            for k in range(seg):
                a = k / seg * 6.283 + ry
                rr = r * (1 + wobble * (math.sin(a * 3 + ph[0] + y * 0.7) * 0.6 + math.sin(a * 5 + ph[1]) * 0.4))
                ring.append((c[0] + rr * math.sin(a), c[1] + y, c[2] + rr * math.cos(a)))
            rings.append(ring)
        self.tube(rings, m, vrep, urep)

    def sweep(self, path, shape, m, up=(0, 1, 0), scale=None, vrep=1.0, urep=1.0, caps=None, twist=0.0):
        """sweep a closed 2D shape [(sx, sy)] along a 3D path (MML coords)"""
        rings = []
        for i, p in enumerate(path):
            a = Vector(path[max(0, i - 1)]); b = Vector(path[min(len(path) - 1, i + 1)])
            t = (b - a).normalized()
            u = Vector(up)
            if abs(t.dot(u)) > 0.95:
                u = Vector((1, 0, 0))
            x = t.cross(u).normalized(); y = x.cross(t).normalized()
            s = scale[i] if scale else 1.0
            tw = twist * i / max(1, len(path) - 1)
            ring = []
            for sx, sy in shape:
                rx = sx * math.cos(tw) - sy * math.sin(tw); ry_ = sx * math.sin(tw) + sy * math.cos(tw)
                q = Vector(p) + x * rx * s + y * ry_ * s
                ring.append((q.x, q.y, q.z))
            rings.append(ring)
        self.tube(rings, m, vrep, urep, cap0=caps, cap1=caps)

    def box(self, c, s, m, ry=0.0, uvs=1.0):
        hx, hy, hz = s[0] / 2, s[1] / 2, s[2] / 2
        cy, sy = math.cos(math.radians(ry)), math.sin(math.radians(ry))
        P = lambda x, y, z: (c[0] + x * cy + z * sy, c[1] + y, c[2] - x * sy + z * cy)
        v = [P(-hx, -hy, -hz), P(hx, -hy, -hz), P(hx, -hy, hz), P(-hx, -hy, hz), P(-hx, hy, -hz), P(hx, hy, -hz), P(hx, hy, hz), P(-hx, hy, hz)]
        for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (1, 2, 6, 5), (3, 0, 4, 7)):
            self.face([v[i] for i in q], m, [(0, 0), (uvs, 0), (uvs, uvs), (0, uvs)])

    def obj(self, name, smooth=True, merge=0.0005, auto_smooth=40):
        me = bpy.data.meshes.new(name)
        bm = bmesh.new()
        verts = [bm.verts.new(B(p)) for p in self.v]
        uvl = bm.loops.layers.uv.new("UVMap")
        for fi, fv in enumerate(self.f):
            try:
                f = bm.faces.new([verts[i] for i in fv])
            except ValueError:
                continue
            f.material_index = self.m[fi]
            for lp, uv in zip(f.loops, self.uv[fi]):
                lp[uvl].uv = uv
        if merge:
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=merge)
        bm.normal_update()
        bm.to_mesh(me)
        bm.free()
        for mm in self.mats:
            me.materials.append(mm)
        o = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(o)
        if smooth:
            for p in me.polygons:
                p.use_smooth = True
            try:
                mod = o.modifiers.new("smooth", "SMOOTH_BY_ANGLE")
            except Exception:
                mod = None
            try:
                me.set_sharp_from_angle(angle=math.radians(auto_smooth))
            except Exception:
                pass
        return o


def tris(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    n = 0
    for o in objs:
        if o.type != "MESH":
            continue
        me = o.evaluated_get(dg).to_mesh()
        me.calc_loop_triangles()
        n += len(me.loop_triangles)
        o.evaluated_get(dg).to_mesh_clear()
    return n


def export(name, objs, anim=False):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
        for c in o.children_recursive:
            c.select_set(True)
    path = os.path.join(OUT, name + ".glb")
    kw = dict(filepath=path, export_format="GLB", use_selection=True, export_yup=True, export_apply=True,
              export_animations=anim, export_texcoords=True, export_normals=True)
    if anim:
        kw.update(export_frame_range=False, export_force_sampling=True, export_nla_strips=False, export_skins=True)
    try:
        bpy.ops.export_scene.gltf(**kw, export_image_format="JPEG", export_image_quality=82)
    except TypeError:
        bpy.ops.export_scene.gltf(**kw)
    return path


def rig(obj, bones, keys, fps=24, length=96, name="Anim"):
    """bones: [(name, head_mml, tail_mml, parent)]; vertices weighted to the nearest bone segment.
    keys: {bone: [(frame, (rx, ry, rz) degrees, (tx, ty, tz))]} in the bone's own axes - a looping clip"""
    arm = bpy.data.armatures.new(obj.name + "_arm")
    ao = bpy.data.objects.new(obj.name + "_rig", arm)
    bpy.context.scene.collection.objects.link(ao)
    bpy.context.view_layer.objects.active = ao
    bpy.ops.object.mode_set(mode="EDIT")
    eb = {}
    for bn, h, t, par in bones:
        b = arm.edit_bones.new(bn)
        b.head, b.tail = B(h), B(t)
        if par:
            b.parent = eb[par]
        eb[bn] = b
    bpy.ops.object.mode_set(mode="OBJECT")
    # weights: nearest bone segment (soft blend between the two nearest)
    segs = [(bn, B(h), B(t)) for bn, h, t, _ in bones]
    groups = {bn: obj.vertex_groups.new(name=bn) for bn, _, _, _ in bones}
    for v in obj.data.vertices:
        p = obj.matrix_world @ v.co
        ds = []
        for bn, a, b in segs:
            ab = b - a
            tt = max(0, min(1, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
            ds.append(((p - (a + ab * tt)).length, bn))
        ds.sort()
        d0, b0 = ds[0]
        if len(ds) > 1:
            d1, b1 = ds[1]
            w0 = d1 / max(d0 + d1, 1e-9)
            groups[b0].add([v.index], w0, "REPLACE")
            groups[b1].add([v.index], 1 - w0, "REPLACE")
        else:
            groups[b0].add([v.index], 1.0, "REPLACE")
    obj.parent = ao
    mod = obj.modifiers.new("arm", "ARMATURE")
    mod.object = ao
    ao.animation_data_create()
    act = bpy.data.actions.new(name)
    ao.animation_data.action = act
    bpy.context.scene.render.fps = fps
    bpy.context.scene.frame_start, bpy.context.scene.frame_end = 0, length
    bpy.context.view_layer.objects.active = ao
    bpy.ops.object.mode_set(mode="POSE")
    for bn, ks in keys.items():
        pb = ao.pose.bones[bn]
        pb.rotation_mode = "XYZ"
        for fr, rot, tr in ks:
            # bone-local: for an upright bone, y runs along it (up): rot y spins it, rot x / z tip it, loc y lifts it
            pb.rotation_euler = tuple(math.radians(a) for a in rot)
            pb.location = tr
            pb.keyframe_insert("rotation_euler", frame=fr)
            pb.keyframe_insert("location", frame=fr)
    bpy.ops.object.mode_set(mode="OBJECT")
    return ao

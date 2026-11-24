"""Marbles (glass ball that rolls + rider floor and name tag that never turn) and the moving obstacle parts."""
import sys, math
sys.path.insert(0, "/home/claude/mr")
import bpy
from blib import *
import course as C

GOLD = ("gold", "#d9a53b", 0.3, 0.9)


def ball(name, color):
    reset()
    glass = mat("glass_" + name, color, 0.05, 0.0, alpha=0.26)
    band = mat("band_" + name, color, 0.25, 0.1, emit=0.35)
    white = mat("white", "#f4f4f4", 0.3, emit=0.15)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=C.MR)
    s = bpy.context.object
    s.data.materials.append(glass)
    bpy.ops.object.shade_smooth()
    objs = [s]
    # swirl bands round the glass, at angles that show the roll
    for (rx, ry, m, minor) in ((90, 0, band, 0.07), (90, 60, white, 0.045), (35, 90, band, 0.06), (-35, 90, white, 0.04)):
        bpy.ops.mesh.primitive_torus_add(major_radius=C.MR - 0.02, minor_radius=minor, major_segments=56, minor_segments=6,
                                         rotation=(math.radians(rx), math.radians(ry), 0))
        t = bpy.context.object
        t.data.materials.append(m)
        bpy.ops.object.shade_smooth()
        objs.append(t)
    print(name, "ball tris", tris(objs))
    export("mr_ball_" + name.lower(), objs)


def pod(name, color):
    """floor, rim, door frame and the floating name tag. Origin = the deck under the marble."""
    reset()
    m = Mesh()
    glassf = mat("floor_" + name, color, 0.15, alpha=0.6)
    gold = mat(*GOLD[:1], GOLD[1], GOLD[2], GOLD[3])
    col = mat("col_" + name, color, 0.35, emit=0.3)
    m.prism((0, 0, 0), C.FLOOR_TOP and 2.8, 0.3, glassf, n=32, y0=C.FLOOR_TOP - 0.3)
    # rim
    m.prism((0, 0, 0), 2.95, 0.26, gold, n=32, y0=C.FLOOR_TOP - 0.5)
    # name on the floor, read from inside
    png = text_png("floor_" + name.lower(), name, 512, 512, bg=color, fg="#ffffff", size=110)
    fm = mat("floorname_" + name, "#ffffff", 0.5, image=png, emit=0.3, emit_image=True)
    r = 1.3
    m.face([(-r, C.FLOOR_TOP + 0.09, r), (r, C.FLOOR_TOP + 0.09, r), (r, C.FLOOR_TOP + 0.09, -r), (-r, C.FLOOR_TOP + 0.09, -r)], fm,
           uv=[(0, 0), (1, 0), (1, 1), (0, 1)], out=(0, -5, 0))
    # the door frame, facing back (-z)
    for a in (158, 202):
        x, z = 2.72 * math.sin(math.radians(a)), 2.72 * math.cos(math.radians(a))
        m.box((x, C.FLOOR_TOP + 1.3, z), (0.22, 2.6, 0.22), gold)
    m.box((0, C.FLOOR_TOP + 2.65, -2.6), (2.3, 0.2, 0.22), gold)
    # floating name tag over the ball, readable from all four sides
    tag = text_png("tag_" + name.lower(), name, 512, 128, bg="#10141c", fg=color, border=color)
    tm = mat("tag_" + name, "#ffffff", 0.5, image=tag, emit=0.45, emit_image=True)
    y = 2 * C.MR + 2.2
    m.box((0, y, 0), (6.2, 1.9, 6.2), mat("tagbody", "#10141c", 0.5))
    for yaw in (0, 90, 180, 270):
        cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        m.sign((3.2 * sy, y, 3.2 * cy), 6.0, 1.5, yaw, tm, two=False, thick=0.02)
    m.prism((0, 0, 0), 0.5, 0.5, col, n=8, y0=y + 0.95)
    o = m.obj("pod_" + name)
    print(name, "pod tris", tris([o]))
    export("mr_pod_" + name.lower(), [o])


for n, c in zip(C.NAMES, C.COLORS):
    ball(n, c)
    pod(n, c)

# ---------------------------------------------------------------- the boarding bridge (folds away during a race)
reset()
m = Mesh()
deck = mat("bridgedeck", "#596577", 0.7)
gold = mat("gold", "#d9a53b", 0.3, 0.9)
x0 = C.HALF + 1.0
m.box((0, 0.9, -4.95), (2 * x0, 0.6, 4.9), deck)
m.box((0, 1.26, -2.55), (2 * x0, 0.12, 0.3), mat("yellow", "#f2c200", 0.4))
for k in range(C.LANES):
    x = C.lane_off(k)
    png = text_png("bridge_" + C.NAMES[k].lower(), C.NAMES[k], 512, 128, bg="#596577", fg=C.COLORS[k])
    lm = mat("bridge_" + C.NAMES[k], "#ffffff", 0.6, image=png, emit=0.3, emit_image=True)
    m.face([(x - 3, 1.32, -6.9), (x + 3, 1.32, -6.9), (x + 3, 1.32, -5.4), (x - 3, 1.32, -5.4)], lm,
           uv=[(0, 0), (1, 0), (1, 1), (0, 1)], out=(x, -5, -6))
# a rail along the back so nobody steps off onto the track behind
for k in range(17):
    x = -x0 + 2 * x0 * k / 16
    m.box((x, 1.7, -7.35), (0.15, 1.0, 0.15), gold)
m.box((0, 2.2, -7.35), (2 * x0, 0.12, 0.2), gold)
o = m.obj("bridge"); bevel(o, 0.04)
export("mr_bridge", [o])

# ---------------------------------------------------------------- gate arm: hinge at the origin, the arm along +x
reset()
m = Mesh()
red = mat("gred", "#d8283a", 0.4, emit=0.2); wht = mat("gwhite", "#eeeeee", 0.4)
m.box((0, 0.9, 0), (0.7, 1.8, 0.7), mat("gdark", "#343c4a", 0.4, 0.6))
for q in range(7):
    m.box((0.45 + 1.1 * (q + 0.5), 1.3, 0), (1.1, 0.7, 0.45), red if q % 2 == 0 else wht)
o = m.obj("gate"); bevel(o, 0.04)
export("mr_gate", [o])

# ---------------------------------------------------------------- trapdoor hatch: hinge at the origin, the hatch along +z
reset()
m = Mesh()
org = mat("hatch", "#ff8a1a", 0.45, emit=0.15); blk = mat("hblack", "#16161a", 0.6)
m.box((0, -0.15, 4.6), (8.6, 0.3, 9.2), org)
for q in range(5):
    m.box((0, 0.05, 0.9 + q * 1.9), (8.0, 0.1, 0.5), blk)
o = m.obj("hatch")
export("mr_hatch", [o])

# ---------------------------------------------------------------- elevator platform: top at the origin
reset()
m = Mesh()
# the top sits 10 cm proud of the deck it rests in, so the two never share a plane
m.box((0, -0.2, 0), (8.6, 0.6, 8.6), mat("plat", "#f2c200", 0.45))
for sx in (-1, 1):
    m.box((sx * 4.1, 0.16, 0), (0.4, 0.12, 8.6), mat("pblack", "#16161a", 0.6))
o = m.obj("elev"); bevel(o, 0.04)
export("mr_elev", [o])

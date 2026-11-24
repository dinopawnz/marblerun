"""v4 marbles: glass orbs with glowing orbit rings inside, the riders' floor, a holographic name crown;
the boarding bridge; and the light-up overlays (rail glow, trail rings, tunnel flash) in each marble's colour."""
import sys, math
sys.path.insert(0, "/home/claude/mr4")
from b4 import Mesh, mat, export, reset, tris
import assets4 as A
import course as C
import tex4

MR, FT = C.MR, C.FLOOR_TOP


def circle(r, n, y=0.0, c=(0, 0)):
    return [(c[0] + r * math.sin(k / n * 6.283), y, c[1] + r * math.cos(k / n * 6.283)) for k in range(n)]


def tube_ring(me, r, minor, m, tilt=(0, 0), y=0.0, n=64, k=8):
    """a torus made by sweeping round a circle, tilted by (rx, rz) degrees"""
    ax, az = math.radians(tilt[0]), math.radians(tilt[1])
    pts = []
    for q in range(n + 1):
        a = q / n * 6.283
        x, yy, z = r * math.sin(a), 0.0, r * math.cos(a)
        yy, z = yy * math.cos(ax) - z * math.sin(ax), yy * math.sin(ax) + z * math.cos(ax)
        x, yy = x * math.cos(az) - yy * math.sin(az), x * math.sin(az) + yy * math.cos(az)
        pts.append((x, yy + y, z))
    me.sweep(pts, [(minor * math.cos(j / k * 6.283), minor * math.sin(j / k * 6.283)) for j in range(k)], m)


def ball(name, color):
    reset()
    me = Mesh()
    glass = mat("glass_" + name, color=color, emit=0.25, emit_color=color, rough=0.05, alpha=0.24)
    glow = mat("ring_" + name, color=color, emit=3.2)
    white = mat("ringw", color="#ffffff", emit=2.0)
    prof = [(MR * math.sin(a / 24 * math.pi) + 1e-4, -MR * math.cos(a / 24 * math.pi)) for a in range(25)]
    me.lathe(prof, glass, seg=48)
    # orbit rings at angles that show the roll, plus a fine white one
    tube_ring(me, MR - 0.08, 0.09, glow, (90, 0))
    tube_ring(me, MR - 0.12, 0.06, glow, (35, 55))
    tube_ring(me, MR - 0.12, 0.06, glow, (-35, -55))
    tube_ring(me, MR - 0.05, 0.035, white, (0, 90))
    # a small glowing heart in the middle that the rings orbit
    A.shard(me, (0, -0.9, 0), 1.8, 0.45, glow, sides=6, seed=3, tip=0.5)
    A.shard(me, (0, 0.9, 0), -1.8, 0.45, glow, sides=6, seed=4, tip=0.5)
    o = me.obj("ball_" + name)
    print(name, "ball", tris([o]))
    export("mr4_ball_" + name.lower(), [o])


def pod(name, color):
    """origin = the deck under the marble. Riders stand on FLOOR_TOP; the room's walls are invisible."""
    reset()
    me = Mesh()
    ms = A.M()
    glow = mat("podglow_" + name, color=color, emit=2.6)
    floor = mat("podfloor_" + name, color="#0b0a1a", emit=0.6, emit_color=color, rough=0.2, metal=0.3)
    gold = ms["gold"]
    # the floor: a shallow glowing dish
    me.lathe([(0.01, FT - 0.28), (2.2, FT - 0.3), (2.75, FT - 0.2), (2.85, FT - 0.02), (0.01, FT - 0.0)], floor, seg=40)
    tube_ring(me, 2.86, 0.12, gold, y=FT - 0.05)
    tube_ring(me, 2.2, 0.05, glow, y=FT + 0.01)
    tube_ring(me, 1.2, 0.05, glow, y=FT + 0.01)
    # the door: an arch facing the station side (-z)
    path = [(1.15 * math.cos(math.pi * q / 16), FT + 2.4 * math.sin(math.pi * q / 16) + 0.0 * q, -2.6) for q in range(17)]
    path = [(1.15 * -math.cos(math.pi * q / 16), FT + (0 if q in (0, 16) else 0) + 2.5 * math.sin(math.pi * q / 16) + (0.4 if 0 < q < 16 else 0), -2.62) for q in range(17)]
    me.sweep(path, [(0.12 * math.cos(j / 6 * 6.283), 0.12 * math.sin(j / 6 * 6.283)) for j in range(6)], glow)
    # the name crown above the ball: a slow ring of four curved name panels and a crystal on top
    tex4.holo_text("tag4_" + name.lower(), name, w=1024, h=256, c1=color, c2="#ffffff")
    tm = mat("tag4_" + name, "tag4_" + name.lower(), emit=2.2)
    y = 2 * MR + 2.0
    for yaw in (0, 90, 180, 270):
        cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        A.text_panel(me, (3.1 * sy, y, 3.1 * cy), yaw, 4.8, 1.2, tm, curve=0.4, thick=0.06)
    tube_ring(me, 3.4, 0.07, glow, y=y + 0.75, n=48)
    tube_ring(me, 3.4, 0.07, glow, y=y - 0.75, n=48)
    A.shard(me, (0, y - 0.5, 0), 1.6, 0.35, glow, sides=5, seed=9, tip=0.5)
    o = me.obj("pod_" + name)
    print(name, "pod", tris([o]))
    export("mr4_pod_" + name.lower(), [o])


def overlays(name, color):
    # a rail segment lit up: a bright rounded bar 10 m long along +z (the game scales it with sz)
    reset()
    me = Mesh()
    g = mat("lit_" + name, color=color, emit=5.0)
    core = mat("litcore", color="#ffffff", emit=4.0)
    path = [(0, 0, -5 + q) for q in range(11)]
    me.sweep(path, [(0.55 * math.cos(j / 8 * 6.283), 0.3 * math.sin(j / 8 * 6.283) + 0.25) for j in range(8)], g, caps=g)
    me.sweep(path, [(0.15 * math.cos(j / 6 * 6.283), 0.12 * math.sin(j / 6 * 6.283) + 0.62) for j in range(6)], core, caps=core)
    export("mr4_lit_" + name.lower(), [me.obj("lit_" + name, smooth=True)])
    # a trail ring left on the floor: a glowing ring with soft spokes
    reset()
    me = Mesh()
    g = mat("trail_" + name, color=color, emit=4.0)
    tube_ring(me, 3.2, 0.18, g, y=0.12, n=40, k=6)
    tube_ring(me, 1.7, 0.1, g, y=0.12, n=28, k=6)
    for q in range(8):
        a = q / 8 * 6.283
        me.sweep([(1.7 * math.sin(a), 0.12, 1.7 * math.cos(a)), (3.2 * math.sin(a + 0.25), 0.12, 3.2 * math.cos(a + 0.25))],
                 [(0.07 * math.cos(j / 4 * 6.283), 0.07 * math.sin(j / 4 * 6.283)) for j in range(4)], g)
    export("mr4_trail_" + name.lower(), [me.obj("trail_" + name)])


for n, c in zip(C.NAMES, C.COLORS):
    ball(n, c)
    pod(n, c)
    overlays(n, c)

# a tunnel ring flaring white as marbles pass
reset()
me = Mesh()
ms = A.M()
flare = mat("flare", color="#ffffff", emit=5.0)
path = [(-math.cos(math.pi * q / 32) * (C.HALF + 3), math.sin(math.pi * q / 32) * 26, 0) for q in range(33)]
me.sweep(path, [(1.5, 0), (0.6, 0.45), (0, 0.75), (-0.6, 0.45), (-1.5, 0), (-0.6, -0.45), (0, -0.75), (0.6, -0.45)], flare)
export("mr4_flare", [me.obj("flare")])

# ---------------------------------------------------------------- the boarding bridge (folds away during a race)
reset()
ms = A.M()
me = Mesh()
x0 = C.HALF + 1.0
walk = ms["tiles"]
# a gently arched walkway, lofted, with glowing lips
rings = []
for q in range(33):
    x = -x0 + 2 * x0 * q / 32
    rings.append([(x, 0.6, -7.4), (x, 1.2, -7.4), (x, 1.2, -2.5), (x, 0.6, -2.5)])
for q in range(32):
    a, b = rings[q], rings[q + 1]
    me.face([a[1], b[1], b[2], a[2]], walk, [(a[1][0] / 6, 0), (b[1][0] / 6, 0), (b[2][0] / 6, 0.8), (a[2][0] / 6, 0.8)])
    me.face([a[0], a[3], b[3], b[0]], ms["hull"])
    me.face([a[0], b[0], b[1], a[1]], ms["glowc"]); me.face([a[3], a[2], b[2], b[3]], ms["glowc"])
for k in range(C.LANES):
    x = C.lane_off(k)
    tex4.holo_text("bridge4_" + C.NAMES[k].lower(), C.NAMES[k], w=1024, h=256, c1=C.COLORS[k], c2="#ffffff")
    lm = mat("bridge4_" + C.NAMES[k], "bridge4_" + C.NAMES[k].lower(), emit=2.0)
    me.face([(x - 3, 1.32, -6.9), (x + 3, 1.32, -6.9), (x + 3, 1.32, -5.4), (x - 3, 1.32, -5.4)][::-1], lm, [(0, 0), (1, 0), (1, 1), (0, 1)][::-1])
    me.sweep([(x - 3.3, 1.26, -2.55), (x + 3.3, 1.26, -2.55)], [(0.12 * math.cos(j / 6 * 6.283), 0.06 * math.sin(j / 6 * 6.283)) for j in range(6)], mat("bridgelane_" + C.NAMES[k], color=C.COLORS[k], emit=3.0), caps=ms["glowc"])
# a glowing handrail along the back so nobody steps off behind
rail = [(-x0 + 2 * x0 * q / 40, 2.3 + 0.08 * math.sin(q * 0.7), -7.3) for q in range(41)]
me.sweep(rail, [(0.12 * math.cos(j / 6 * 6.283), 0.12 * math.sin(j / 6 * 6.283)) for j in range(6)], ms["glowg"])
for q in range(0, 41, 4):
    p = rail[q]
    me.sweep([(p[0], 1.2, -7.3), (p[0], p[1], -7.3)], [(0.08 * math.cos(j / 6 * 6.283), 0.08 * math.sin(j / 6 * 6.283)) for j in range(6)], ms["gold"])
export("mr4_bridge", [me.obj("bridge")])
print("marbles done")

"""Builds the static world: track, supports, obstacles' frames, signs, finish, station, stands, boards.
Writes out/mr_track.glb, out/mr_scenery.glb, out/mr_ground.glb and out/colliders.json."""
import sys, math, json
sys.path.insert(0, "/home/claude/mr")
import bpy
from blib import *
import course as C

reset()
HALF, W = C.HALF, C.HALF * 2
DECK_T = 0.8
CURB_H, CURB_W = 1.4, 0.8

M = {
    "deck": mat("deck", "#161c2a", 0.55),
    "deck2": mat("deck2", "#161c2a", 0.55),
    "lift": mat("liftdeck", "#26262b", 0.6),
    "line": mat("line", "#c9d3e6", 0.4, emit=0.25),
    "red": mat("curbred", "#d8283a", 0.4),
    "white": mat("curbwhite", "#eeeeee", 0.4),
    "led": mat("led", "#3fe0ff", 0.3, emit=0.6),
    "steel": mat("steel", "#8a96a3", 0.35, 0.7),
    "dark": mat("steeldark", "#343c4a", 0.45, 0.6),
    "yellow": mat("yellow", "#f2c200", 0.45),
    "black": mat("black", "#16161a", 0.6),
    "mud": mat("mud", "#4a2f17", 0.15),
    "mud2": mat("mud2", "#5e3c1d", 0.1),
    "gold": mat("gold", "#d9a53b", 0.3, 0.9),
    "seat": mat("seat", "#2a6bff", 0.5),
    "seat2": mat("seat2", "#e0233a", 0.5),
    "concrete": mat("concrete", "#7b808a", 0.8),
}
def tint(c, k=0.32):
    h = c.lstrip("#"); base = (0x16, 0x1c, 0x2a)
    v = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    return "#%02x%02x%02x" % tuple(int(b + (x - b) * k) for x, b in zip(v, base))
LANE_MATS = [mat("lane_" + n, tint(c), 0.5) for n, c in zip(C.NAMES, C.COLORS)]
cols = []   # invisible solids for the game: {x,y,z,w,h,d,ry,rx}


def col_box(c, s, ry=0.0, rx=0.0):
    cols.append({k: round(v, 3) for k, v in dict(x=c[0], y=c[1], z=c[2], w=s[0], h=s[1], d=s[2], ry=ry, rx=rx).items()})


def rp(i, t, o, y):
    return C.run_point(i, t, o, y)


track = Mesh()
scen = Mesh()

# ---------------------------------------------------------------- deck pieces
# (run, t0, y0, t1, y1, kind)
pieces = []
def runspan(i):
    s0 = HALF if C.NODES[i][3] else 0
    s1 = C.LEN[i] - (HALF if C.NODES[(i + 1) % C.N][3] else 0)
    return s0, s1

s0, s1 = runspan(0);  pieces.append((0, s0, 0, s1, 70, "lift"))
s0, s1 = runspan(1);  pieces.append((1, s0, 70, s1, 52, "slope"))
s0, s1 = runspan(2);  pieces += [(2, s0, 52, 90, 52, "flat"), (2, 90, 48, 150, 48, "flat"), (2, 150, 44, s1, 44, "flat")]
s0, s1 = runspan(3);  pieces.append((3, s0, 44, s1, 44, "flat"))
s0, s1 = runspan(4);  pieces.append((4, s0, 44, s1, 44, "mud"))
s0, s1 = runspan(5);  pieces += [(5, s0, 44, 55.4, 44, "flat"), (5, 52, 36, s1, 36, "flat")]
s0, s1 = runspan(6);  pieces.append((6, s0, 36, s1, 36, "flat"))
s0, s1 = runspan(7);  pieces += [(7, s0, 36, 79.4, 36, "flat"), (7, 79.4, 46, s1, 46, "flat")]
for i in (8, 9, 10):
    s0, s1 = runspan(i); pieces.append((i, s0, 46, s1, 46, "flat"))
s0, s1 = runspan(11); pieces += [(11, s0, 46, 45.4, 46, "flat"), (11, 45.4, 46, 170, 0, "slope"), (11, 170, 0, s1, 0, "flat")]

def deck_piece(i, t0, y0, t1, y1, kind, k):
    top = [rp(i, t0, -HALF, y0), rp(i, t1, -HALF, y1), rp(i, t1, HALF, y1), rp(i, t0, HALF, y0)]
    bot = [(p[0], p[1] - DECK_T, p[2]) for p in top]
    dm = M["lift"] if kind == "lift" else (M["deck"] if k % 2 else M["deck2"])
    track.solid(bot, top, M["dark"], cap_mat=dm)
    # collider: a turned box through the same slope
    d = C.D[i]
    mid = rp(i, (t0 + t1) / 2, 0, (y0 + y1) / 2)
    L = t1 - t0
    pitch = math.degrees(math.atan2(y1 - y0, L))
    col_box((mid[0], mid[1] - DECK_T / 2, mid[2]), (W, DECK_T, math.hypot(L, y1 - y0) + 0.05), ry=C.heading_deg(i), rx=-pitch)
    # each lane tinted with its marble's colour
    if kind != "lift":
        for j in range(C.LANES):
            o = C.lane_off(j)
            q = [rp(i, t0 + 0.3, o - 4.2, y0 + 0.015), rp(i, t1 - 0.3, o - 4.2, y1 + 0.015), rp(i, t1 - 0.3, o + 4.2, y1 + 0.015), rp(i, t0 + 0.3, o + 4.2, y0 + 0.015)]
            track.face(q, LANE_MATS[j], out=(q[0][0], q[0][1] - 5, q[0][2]))
    # lane lines
    for j in range(1, C.LANES):
        o = (j - C.LANES / 2) * C.LANE_W
        a, b = rp(i, t0 + 0.5, o, y0), rp(i, t1 - 0.5, o, y1)
        line = [(a[0], a[1], a[2]), (b[0], b[1], b[2])]
        nn = C.normal(d)
        q = [(p[0] + nn[0] * s * 0.14, p[1] + 0.03, p[2] + nn[1] * s * 0.14) for p in (line[0], line[1]) for s in (-1, 1)]
        track.face([q[0], q[2], q[3], q[1]], M["lift"] if kind == "lift" else M["line"], out=(q[0][0], q[0][1] - 5, q[0][2]))
    # lift: chevrons across, like a chain
    if kind == "lift":
        t = t0 + 2
        while t < t1 - 1:
            yy = y0 + (y1 - y0) * (t - t0) / L
            for j in range(C.LANES):
                o = C.lane_off(j)
                a = rp(i, t, o - 2.5, yy + 0.06); b = rp(i, t, o + 2.5, yy + 0.06)
                track.box(((a[0] + b[0]) / 2, a[1], (a[2] + b[2]) / 2), (5 if abs(d[0]) < .5 else 0.5, 0.12, 0.5 if abs(d[0]) < .5 else 5), M["yellow"])
            t += 4
    # curbs, alternating red / white (yellow on the lift), and an LED strip on top
    for sd in (-1, 1):
        o = sd * (HALF + CURB_W / 2)
        seg = 6.0
        n = max(1, int(round((t1 - t0) / seg)))
        for q in range(n):
            ta = t0 + (t1 - t0) * q / n; tb = t0 + (t1 - t0) * (q + 1) / n
            if (i == 0 and ta < 4) or (i == 11 and tb > C.LEN[11] - 4):
                continue                                  # the boarding bridge crosses here
            ya = y0 + (y1 - y0) * (ta - t0) / (t1 - t0); yb = y0 + (y1 - y0) * (tb - t0) / (t1 - t0)
            bot = [rp(i, ta, o - CURB_W / 2, ya - DECK_T), rp(i, tb, o - CURB_W / 2, yb - DECK_T), rp(i, tb, o + CURB_W / 2, yb - DECK_T), rp(i, ta, o + CURB_W / 2, ya - DECK_T)]
            top = [(p[0], p[1] + DECK_T + CURB_H, p[2]) for p in bot]
            cm = M["yellow"] if kind == "lift" else (M["red"] if q % 2 else M["white"])
            if kind == "lift" and q % 2:
                cm = M["black"]
            track.solid(bot, top, cm)
        a, b = rp(i, t0, o, y0 + CURB_H + 0.05), rp(i, t1, o, y1 + CURB_H + 0.05)
        nn = C.normal(d)
        q4 = [(a[0] - nn[0] * .15, a[1], a[2] - nn[1] * .15), (b[0] - nn[0] * .15, b[1], b[2] - nn[1] * .15), (b[0] + nn[0] * .15, b[1], b[2] + nn[1] * .15), (a[0] + nn[0] * .15, a[1], a[2] + nn[1] * .15)]
        track.face(q4, M["led"], out=(a[0], a[1] - 5, a[2]))
        mid = rp(i, (t0 + t1) / 2, o, (y0 + y1) / 2 + CURB_H / 2)
        col_box(mid, (CURB_W, CURB_H + 0.2, math.hypot(t1 - t0, y1 - y0)), ry=C.heading_deg(i), rx=-math.degrees(math.atan2(y1 - y0, t1 - t0)))
    # a step's front face gets a hazard stripe
    return

for k, p in enumerate(pieces):
    deck_piece(*p, k)

# corner squares (flat), curbs on their two outer sides
for i in range(C.N):
    if not C.NODES[i][3]:
        continue
    x, z, y = C.NODES[i][0], C.NODES[i][1], C.NODES[i][2]
    top = [(x - HALF, y, z - HALF), (x + HALF, y, z - HALF), (x + HALF, y, z + HALF), (x - HALF, y, z + HALF)]
    bot = [(p[0], y - DECK_T, p[2]) for p in top]
    track.solid(bot, top, M["dark"], cap_mat=M["deck"])
    col_box((x, y - DECK_T / 2, z), (W, DECK_T, W))
    din, dout = C.D[(i - 1) % C.N], C.D[i]
    # each lane's band turns the corner: in along the old run, out along the new
    mt = C.miter(i)
    for j in range(C.LANES):
        o = C.lane_off(j)
        mx, mz = x + mt[0] * o, z + mt[1] * o
        for d, a, b in ((din, -HALF, 0), (dout, 0, HALF)):
            n = C.normal(d)
            # along d from the square's edge to the lane's turning point (+/- half a band)
            ex, ez = x + d[0] * (a if a else b), z + d[1] * (a if a else b)
            s0 = (ex - mx) * d[0] + (ez - mz) * d[1]
            s1 = 4.2 * (1 if a else -1)
            lo, hi = min(s0, s1), max(s0, s1)
            pts = [(mx + d[0] * lo + n[0] * -4.2, y + 0.015 + (0.004 if a else 0), mz + d[1] * lo + n[1] * -4.2),
                   (mx + d[0] * hi + n[0] * -4.2, y + 0.015 + (0.004 if a else 0), mz + d[1] * hi + n[1] * -4.2),
                   (mx + d[0] * hi + n[0] * 4.2, y + 0.015 + (0.004 if a else 0), mz + d[1] * hi + n[1] * 4.2),
                   (mx + d[0] * lo + n[0] * 4.2, y + 0.015 + (0.004 if a else 0), mz + d[1] * lo + n[1] * 4.2)]
            track.face(pts, LANE_MATS[j], out=(mx, y - 5, mz))
    for sx, sz in ((din[0], din[1]), (-dout[0], -dout[1])):      # the far side, and the side behind the exit
        cx, cz = x + sx * (HALF + CURB_W / 2), z + sz * (HALF + CURB_W / 2)
        L = W + 2 * CURB_W
        size = (CURB_W, CURB_H + DECK_T, L) if abs(sx) > .5 else (L, CURB_H + DECK_T, CURB_W)
        for q in range(8):
            f = (q + 0.5) / 8 - 0.5
            c = (cx + (0 if abs(sx) > .5 else f * L), y + (CURB_H - DECK_T) / 2, cz + (f * L if abs(sx) > .5 else 0))
            s = (size[0], size[1], L / 8) if abs(sx) > .5 else (L / 8, size[1], size[2])
            track.box(c, s, M["red"] if q % 2 else M["white"])
        col_box((cx, y + CURB_H / 2, cz), (size[0], CURB_H + 0.2, size[2]))
    # a tall marker post with a gold globe on the outer corner
    ox, oz = x + (din[0] - dout[0]) * (HALF + 2.5), z + (din[1] - dout[1]) * (HALF + 2.5)
    scen.prism((ox, 0, oz), 1.0, y + 9, M["dark"], n=8, y0=0)
    scen.prism((ox, 0, oz), 1.6, 1.2, M["gold"], n=8, y0=y + 9)
    scen.prism((ox, 0, oz), 0.9, 1.0, M["led"], n=8, y0=y + 10.2)

# ---------------------------------------------------------------- supports
def footprint_has_lower(x, z, top, skip_run, skip_t):
    for (i, t0, y0, t1, y1, kind) in pieces:
        d, n = C.D[i], C.normal(C.D[i])
        px, pz = x - C.P[i][0], z - C.P[i][1]
        t = px * d[0] + pz * d[1]; o = px * n[0] + pz * n[1]
        if t0 - 1 <= t <= t1 + 1 and abs(o) <= HALF + 1.5:
            yy = y0 + (y1 - y0) * (t - t0) / max(0.01, t1 - t0)
            if yy < top - 2:
                return True
    return False

def column(x, z, top):
    if top < 2.5:
        return
    scen.prism((x, 0, z), 1.3, 0.6, M["concrete"], n=8, y0=0)
    scen.prism((x, 0, z), 0.75, top - 1.1, M["steel"], n=8, y0=0.6, r_top=0.6)
    scen.box((x, top - 0.25, z), (2.6, 0.5, 2.6), M["dark"])
    col_box((x, top / 2, z), (1.4, top, 1.4))

for (i, t0, y0, t1, y1, kind) in pieces:
    n_ = max(1, int((t1 - t0) // 30))
    for q in range(n_ + 1):
        t = t0 + 2 + (t1 - t0 - 4) * q / max(1, n_)
        yy = y0 + (y1 - y0) * (t - t0) / max(0.01, t1 - t0) - DECK_T
        pts = []
        for sd in (-1, 1):
            p = rp(i, t, sd * (HALF - 4), yy)
            if footprint_has_lower(p[0], p[2], yy, i, t):
                continue
            column(p[0], p[2], yy)
            pts.append(p)
        if len(pts) == 2 and yy > 6:
            a, b = pts
            scen.box(((a[0] + b[0]) / 2, yy - 1.2, (a[2] + b[2]) / 2), (abs(a[0] - b[0]) + 1.2, 1.4, abs(a[2] - b[2]) + 1.2), M["dark"])
for i in range(C.N):
    if C.NODES[i][3]:
        x, z, y = C.NODES[i][:3]
        for sx in (-1, 1):
            for sz in (-1, 1):
                column(x + sx * (HALF - 4), z + sz * (HALF - 4), y - DECK_T)

# ---------------------------------------------------------------- signs over the runs
def gantry(i, t, y, text, fg="#ffd23f", sub=None):
    """two towers outside the curbs, a beam, and a sign on it facing the marbles"""
    png = text_png("sign_" + text.replace(" ", "_").lower(), text, 1024, 128, bg="#10141c", fg=fg, border="#d9a53b", sub=sub)
    sm = mat("sign_" + text, "#ffffff", 0.6, image=png, emit=0.45, emit_image=True)
    top = y + 13
    for sd in (-1, 1):
        p = rp(i, t, sd * (HALF + 3), 0)
        scen.box((p[0], top / 2, p[2]), (1.6, top, 1.6), M["dark"], yaw=C.heading_deg(i))
        col_box((p[0], top / 2, p[2]), (1.6, top, 1.6), ry=C.heading_deg(i))
    c = rp(i, t, 0, top)
    scen.box(c, (W + 8, 1.2, 1.4) if abs(C.D[i][0]) < .5 else (1.4, 1.2, W + 8), M["dark"])
    scen.sign((c[0], top + 2.6, c[2]), 34, 4.25, C.heading_deg(i) + 180, sm, frame=M["gold"])

for i, (name, steps) in enumerate(C.RUNS):
    if name in ("THE GATES", "THE TRAPDOORS", "THE ELEVATORS", "THE PLUNGE", "LIFT HILL"):
        continue
    ta, tb = runspan(i)
    y = C.Y[i]
    gantry(i, ta + 12, max(y, C.Y[(i + 1) % C.N]), name)
gantry(0, 30, 13, "LIFT HILL", fg="#f2c200")

# ---------------------------------------------------------------- obstacles: frames (the moving parts are separate models)
def lane_posts(i, t, y, h, mat_):
    for j in range(C.LANES + 1):
        o = (j - C.LANES / 2) * C.LANE_W
        p = rp(i, t, o, y)
        scen.box((p[0], y + h / 2, p[2]), (0.5, h, 0.5), mat_)

# the gates
lane_posts(3, C.GATE_T, 44, 3.2, M["steel"])
gantry(3, C.GATE_T, 44, "THE GATES", fg="#ff5a5a")
# the last gates, on the lip of the plunge
yl = 46 - (C.LAST_GATE_T - 45.4) * 46 / (170 - 45.4)
lane_posts(11, C.LAST_GATE_T, yl, 3.2, M["steel"])
gantry(11, C.LAST_GATE_T, 46, "THE LAST GATES", fg="#ff5a5a", sub="THEN THE PLUNGE")
# the trapdoors: a hazard frame round the hatches
for sd in (-1, 1):
    a, b = rp(5, 55.4, sd * (HALF - 0.2), 44.05), rp(5, 64.6, sd * (HALF - 0.2), 44.05)
for j in range(C.LANES + 1):
    o = (j - C.LANES / 2) * C.LANE_W
    p = rp(5, 60, o, 44)
    scen.box((p[0], 44 - 0.4, p[2]), (0.6, 0.8, 9.4) if abs(C.D[5][0]) < .5 else (9.4, 0.8, 0.6), M["yellow"])
gantry(5, 60, 44, "THE TRAPDOORS", fg="#ffb11a")
# hazard face on the upper deck's end (the drop to the lower deck)
p = rp(5, 55.4, 0, 44)
scen.box((p[0], 40, p[2]), (W, 8, 0.3) if abs(C.D[5][0]) < .5 else (0.3, 8, W), M["black"])
# the elevators: a shaft frame per lane
for j in range(C.LANES + 1):
    o = (j - C.LANES / 2) * C.LANE_W
    for tt in (70.6, 79.4):
        p = rp(7, tt, o, 36)
        scen.box((p[0], 36 + 11, p[2]), (0.6, 22, 0.6), M["yellow"] if j % 2 else M["dark"])
for tt in (70.6, 79.4):
    p = rp(7, tt, 0, 58)
    scen.box(p, (W + 1, 1, 0.8) if abs(C.D[7][0]) < .5 else (0.8, 1, W + 1), M["dark"])
p = rp(7, 79.4, 0, 41)
scen.box((p[0], 41, p[2]), (W, 10, 0.4) if abs(C.D[7][0]) < .5 else (0.4, 10, W), M["dark"])
gantry(7, 75, 50, "THE ELEVATORS", fg="#3fe0ff")
# the stairs: hazard stripes on each ledge
for tt, yy in ((90, 52), (150, 48)):
    p = rp(2, tt, 0, yy)
    for q in range(16):
        o = -HALF + W * (q + 0.5) / 16
        pp = rp(2, tt - 0.4, o, yy + 0.02)
        scen.box(pp, (0.8, 0.06, W / 16) if abs(C.D[2][0]) > .5 else (W / 16, 0.06, 0.8), M["yellow"] if q % 2 else M["black"])
    scen.box((p[0], yy - 2, p[2]), (0.3, 4, W) if abs(C.D[2][0]) > .5 else (W, 4, 0.3), M["black"])
# the mud: a glossy layer and bubbles
ta, tb = runspan(4)
mt = [rp(4, ta + 1, -HALF + 0.5, 44.08), rp(4, tb - 1, -HALF + 0.5, 44.08), rp(4, tb - 1, HALF - 0.5, 44.08), rp(4, ta + 1, HALF - 0.5, 44.08)]
track.face(mt, M["mud"], out=(mt[0][0], 0, mt[0][2]))
import random
random.seed(7)
for q in range(60):
    t = random.uniform(ta + 2, tb - 2); o = random.uniform(-HALF + 2, HALF - 2)
    if min(abs(o - C.lane_off(j)) for j in range(C.LANES)) < 4.2:
        continue                     # keep the bubbles out of the marbles' way
    p = rp(4, t, o, 44.05)
    r = random.uniform(0.3, 0.6)
    scen.prism(p, r, r * 0.8, M["mud2"], n=6, y0=44.05, r_top=r * 0.4)

# ---------------------------------------------------------------- the finish
fin = rp(11, C.FINISH_T, 0, 0)
ck = checker_png("checker", 16, 1024, 128)
ckm = mat("checker", "#ffffff", 0.5, image=ck)
q4 = [(fin[0] - HALF, 0.04, fin[2] - 1.5), (fin[0] + HALF, 0.04, fin[2] - 1.5), (fin[0] + HALF, 0.04, fin[2] + 1.5), (fin[0] - HALF, 0.04, fin[2] + 1.5)]
track.face(q4, ckm, uv=[(0, 0), (1, 0), (1, 1), (0, 1)], out=(fin[0], -5, fin[2]))
for sd in (-1, 1):
    scen.box((sd * (HALF + 3), 9, fin[2]), (2, 18, 2), M["dark"])
    scen.prism((sd * (HALF + 3), 0, fin[2]), 1.6, 1.2, M["gold"], n=8, y0=18)
    col_box((sd * (HALF + 3), 9, fin[2]), (2, 18, 2))
scen.box((0, 16, fin[2]), (W + 8, 1.4, 1.4), M["dark"])
fpng = text_png("sign_finish", "FINISH", 1024, 256, bg="#111111", fg="#ffffff", border="#d9a53b")
scen.sign((0, 18.6, fin[2]), 30, 7.5, 180, mat("sign_finish", "#ffffff", 0.6, image=fpng, emit=0.45, emit_image=True), frame=M["gold"])
scen.sign((0, 14.6, fin[2]), 30, 1.6, 180, ckm, thick=0.2)

# ---------------------------------------------------------------- the station
# the arch over the boarding bridge, the name of the game on it
for sd in (-1, 1):
    scen.box((sd * (HALF + 4), 10, -12), (3, 20, 3), M["dark"])
    scen.prism((sd * (HALF + 4), 0, -12), 2.2, 1.6, M["gold"], n=8, y0=20)
    col_box((sd * (HALF + 4), 10, -12), (3, 20, 3))
scen.box((0, 18, -12), (W + 11, 2, 2), M["dark"])
tpng = text_png("sign_title", "THE GRAND MARBLE RUN", 2048, 256, bg="#10141c", fg="#ffd23f", border="#d9a53b")
scen.sign((0, 21.2, -12), 56, 7, 180, mat("sign_title", "#ffffff", 0.6, image=tpng, emit=0.45, emit_image=True), frame=M["gold"])
wpng = text_png("sign_walkin", "WALK IN - PICK YOUR MARBLE", 2048, 256, bg="#10141c", fg="#ffffff")
scen.sign((0, 15.6, -12), 44, 3.2, 180, mat("sign_walkin", "#ffffff", 0.6, image=wpng, emit=0.4, emit_image=True))
# steps up to the bridge, both ends (the bridge itself is its own model: it folds away)
for sd in (-1, 1):
    for k in range(3):
        h = 0.4 * (k + 1)
        x = sd * (HALF + 1.0 + 4.5 - k * 1.5 - 0.75)
        scen.box((x, h / 2, -4.95), (1.5, h, 5.1), M["concrete"])
        col_box((x, h / 2, -4.95), (1.5, h, 5.1))
    scen.box((sd * (HALF + 0.6 + 0.0), 0.6, -4.95), (0.4 + 0.0, 1.2, 5.1), M["concrete"])
    col_box((sd * (HALF + 0.6), 0.6, -4.95), (0.4, 1.2, 5.1))
# race control kiosks
rpng = text_png("sign_control", "RACE CONTROL", 1024, 256, bg="#10141c", fg="#ffd23f", border="#d9a53b", sub="CLICK - TYPE THE CODE")
rcm = mat("sign_control", "#ffffff", 0.6, image=rpng, emit=0.45, emit_image=True)
for sd in (-1, 1):
    x = sd * (HALF + 12)
    scen.box((x, 0.6, -5), (5, 1.2, 4), M["dark"])
    scen.box((x, 1.45, -5), (4.4, 0.5, 3.4), M["gold"])
    scen.sign((x, 3.4, -5), 6, 1.5, 90 * -sd, rcm, frame=M["dark"])
    col_box((x, 0.9, -5), (5, 1.8, 4))
# grandstands either side of the finish
for sd in (-1, 1):
    for k in range(5):
        h = 0.9 * (k + 1)
        x = sd * (HALF + 5 + k * 2.6 + 1.3)
        scen.box((x, h / 2, fin[2] + 5), (2.6, h, 80), M["concrete"])
        scen.box((x, h + 0.2, fin[2] + 5), (2.2, 0.4, 78), M["seat"] if sd < 0 else M["seat2"])
        col_box((x, h / 2, fin[2] + 5), (2.6, h, 80))
    scen.box((sd * (HALF + 5 + 13 + 0.5), 4, fin[2] + 5), (1, 8, 80), M["dark"])
    col_box((sd * (HALF + 5 + 13 + 0.5), 4, fin[2] + 5), (1, 8, 80))

# ---------------------------------------------------------------- scoreboards (the words are live labels in the game)
stpng = text_png("sign_standings", "STANDINGS", 1024, 128, bg="#10141c", fg="#ffd23f")
stm = mat("sign_standings", "#ffffff", 0.6, image=stpng, emit=0.45, emit_image=True)
BOARDS = [
    {"x": -64, "y": 13, "z": 2, "ry": 90},          # beside the station, facing it
    {"x": 180, "y": 47, "z": 92.5, "ry": 0},         # tower in the zigzag, facing THE SPRINT side
    {"x": 180, "y": 47, "z": 87.5, "ry": 180},       # and the MUD side
]
for b in BOARDS:
    yaw = b["ry"]
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    def at(dx, dy, dz):
        return (b["x"] + dx * cy + dz * sy, b["y"] + dy, b["z"] - dx * sy + dz * cy)
    scen.box(at(0, 0, -0.35), (24, 21.5, 0.5), M["dark"], yaw=yaw)
    scen.box(at(0, 0, -0.1), (22.6, 20.2, 0.1), M["black"], yaw=yaw)
    scen.box(at(0, 10.9, -0.2), (24.6, 0.5, 0.8), M["gold"], yaw=yaw)
    scen.box(at(0, -10.9, -0.2), (24.6, 0.5, 0.8), M["gold"], yaw=yaw)
    scen.sign(at(0, 12.6, -0.2), 16, 2, yaw, stm, two=False, frame=M["gold"])
# station board legs; the zigzag board stands on a tower
for dz in (-9, 9):
    scen.box((-64, 1, 2 + dz), (1.2, 2, 1.2), M["concrete"])
    scen.box((-64.6, 2.5 / 2 + 1, 2 + dz), (0.9, 2.5, 0.9), M["dark"])
scen.prism((180, 0, 90), 3, 36, M["dark"], n=8, y0=0)
scen.prism((180, 0, 90), 4.5, 1, M["concrete"], n=8, y0=0)
scen.box((180, 47, 90), (8, 22, 4.6), M["dark"])
scen.prism((180, 0, 90), 2.6, 1.2, M["gold"], n=8, y0=58)
col_box((180, 18, 90), (6, 36, 6))

# ---------------------------------------------------------------- export
tob = track.obj("track")
sob = scen.obj("scenery")
bevel(sob, 0.05)
print("track tris", tris([tob]), "scenery tris", tris([sob]))
export("mr_track", [tob])
export("mr_scenery", [sob])

# ground: grass, a plaza round the station, paving under the zigzag
reset()
g = Mesh()
grass = mat("grass", "#3f5d34", 0.9); plaza = mat("plaza", "#666b75", 0.85); pave = mat("pave", "#4d535d", 0.85)
def quad(x0, x1, z0, z1, y, m):
    g.face([(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)], m, out=(x0, y - 5, z0))
quad(-160, 400, -360, 440, -0.06, grass)
quad(-110, 110, -140, 40, -0.03, plaza)
quad(60, 300, -170, 340, -0.045, pave)
gob = g.obj("ground")
export("mr_ground", [gob])

json.dump({"colliders": cols, "boards": BOARDS}, open("/home/claude/mr/out/world.json", "w"))
print("colliders", len(cols))

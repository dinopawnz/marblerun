"""THE GRAND MARBLE RUN v4 - the world, in Blender. Night-time Pandora: a glowing ribbon of track on living
pillars, crystal rails, banked bowls, mushroom bumpers, a tunnel of light, arches over every section.
Writes out/mr4_track.glb, mr4_struct.glb, mr4_signs.glb, mr4_station.glb, mr4_ground.glb, mr4_collide_raw.glb,
the glow overlays (rails + trail rings, one per marble colour) and out/world4.json (props, glow segments, boards)."""
import sys, math, json, random
sys.path.insert(0, "/home/claude/mr4")
import b4
from b4 import Mesh, mat, export, reset, tris
import assets4 as A
import course as C
import tex4

HALF, DECK_T, MR = C.HALF, 1.0, C.MR
RAIL_W, RAIL_H = 1.4, 1.5
rnd = random.Random(4)

reset()
ms = A.M()
A.M_stem[0], A.M_stem[1] = ms["stem"], ms["gill"]
track, struct, signs, station, colm = Mesh(), Mesh(), Mesh(), Mesh(), Mesh()
CM = mat("collide", color="#ff00ff")
swamp_m = ms["water"]
props = []            # (model, x, y, z, ry, scale, animated?)
glow_segs = []        # rail segments that light up: {a:[x,y,z], b:[x,y,z], run/sec, side}


LIFT_G = C.LIFT_TOP / C.LEN[0]
LIFT_SINK = MR * (math.sqrt(1 + LIFT_G ** 2) - 1)       # 1.1 m: the marbles ride the lift this far above its deck line


def vis_h(i, t):
    """the deck height to DRAW (the lift is drawn lower, so the marbles going up don't sink into it)"""
    y = C.height(i, t)
    return max(0.0, y - LIFT_SINK) if C.KIND[i] == "lift" else y


def face_to(me, pts, m, uv, want):
    """a face pointing along `want` (Otherside draws one side only)"""
    ax, ay, az = pts[1][0] - pts[0][0], pts[1][1] - pts[0][1], pts[1][2] - pts[0][2]
    bx, by, bz = pts[2][0] - pts[0][0], pts[2][1] - pts[0][1], pts[2][2] - pts[0][2]
    n = (ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx)
    if n[0] * want[0] + n[1] * want[1] + n[2] * want[2] < 0:
        pts, uv = pts[::-1], (uv[::-1] if uv else uv)
    me.face(pts, m, uv)


def rp(i, t, u, y):
    return C.run_point(i, t, u, y)


def hgt(i, t):
    return C.height(i, t)


def col_solid(bot, top):
    colm.tube([bot, top], CM, cap0=CM, cap1=CM)


# ---------------------------------------------------------------- deck pieces (straight bits of each run's profile)
pieces = []
for i in range(C.N):
    pr = C.profile(i)
    for (ta, ya), (tb, yb) in zip(pr, pr[1:]):
        if tb - ta > 0.01:
            if C.KIND[i] == "lift":
                ta = LIFT_SINK / LIFT_G                    # the lowered ramp comes out of the ground just ahead of the parked marbles
                ya, yb = vis_h(i, ta), vis_h(i, tb)
            pieces.append((i, ta, ya, tb, yb))


HULL = [(1.0, -0.15), (1.0, -0.45), (0.92, -1.2), (0.6, -2.3), (0.25, -2.9), (0.0, -3.05)]   # underside, as (|u| / HALF, dy)


def deck_material(i, t):
    k = C.KIND[i]
    if k == "lift":
        return ms["lift"]
    if k == "swamp":
        return swamp_m
    return ms["deck"]


def deck_piece(i, t0, y0, t1, y1):
    """the ribbon: a glowing top, rounded lips, a curved hull underneath (veined like bark)"""
    L = t1 - t0
    n = max(1, int(math.ceil(L / 8)))
    ts = [t0 + L * q / n for q in range(n + 1)]
    ys = [y0 + (y1 - y0) * (t - t0) / L for t in ts]
    m = deck_material(i, t0)
    # top: split across so the finish line / lanes can be their own strips; UVs in world metres / 24
    us = [-HALF, -HALF * 0.5, 0, HALF * 0.5, HALF]
    P = [[rp(i, t, u, y) for u in us] for t, y in zip(ts, ys)]
    UV = [[(u / 24 + 0.5, t / 24) for u in us] for t in ts]
    if C.KIND[i] == "plunge" and t0 < C.FINISH_T < t1:
        # the chequered finish line is a strip of its own
        for a, b, mm in ((t0, C.FINISH_T - 2, m), (C.FINISH_T - 2, C.FINISH_T + 2, ms["checker"]), (C.FINISH_T + 2, t1, m)):
            ya, yb = hgt(i, a + 1e-6), hgt(i, b - 1e-6)
            q = [rp(i, a, -HALF, ya), rp(i, b, -HALF, yb), rp(i, b, HALF, yb), rp(i, a, HALF, ya)]
            uv = [(0, 0), (0, 1), (16, 1), (16, 0)] if mm is ms["checker"] else [(-HALF / 24, a / 24), (-HALF / 24, b / 24), (HALF / 24, b / 24), (HALF / 24, a / 24)]
            track.face(q[::-1], mm, uv[::-1])
    else:
        track.grid(P, m, UV, flip=True)
    # lips + hull: one loft across the whole width per station
    rings = []
    for t, y in zip(ts, ys):
        ring = []
        for s, dy in HULL:
            ring.append(rp(i, t, HALF * s, y + dy))
        for s, dy in HULL[::-1][1:]:
            ring.append(rp(i, t, -HALF * s, y + dy))
        rings.append(ring)
    # open strip (not closed round): sweep faces between stations
    for q in range(n):
        A_, B_ = rings[q], rings[q + 1]
        for j in range(len(A_) - 1):
            quad = [A_[j], A_[j + 1], B_[j + 1], B_[j]]
            track.face(quad, ms["hull"], [(j / 6, ts[q] / 16), ((j + 1) / 6, ts[q] / 16), ((j + 1) / 6, ts[q + 1] / 16), (j / 6, ts[q + 1] / 16)])
    # end caps where a piece ends in mid-air (drops, the station)
    for t, y, ring, rev in ((t0, y0, rings[0], False), (t1, y1, rings[-1], True)):
        if abs(hgt(i, t - 0.01) - hgt(i, t + 0.01)) > 0.5 or (i == 0 and t == 0) or (C.KIND[i] == "plunge" and t >= C.LEN[i] - 0.01):
            top = [rp(i, t, -HALF, y), rp(i, t, HALF, y)]
            poly = [top[0]] + ring[::-1] if False else ring
            cen = rp(i, t, 0, y - 1.4)
            d = C.D[i]
            want = (d[0], 0, d[1]) if rev else (-d[0], 0, -d[1])
            for j in range(len(ring) - 1):
                face_to(track, [cen, ring[j], ring[j + 1]], ms["cryp"], [(0.5, 0.5), (j / 10, 0), ((j + 1) / 10, 0)], want)
            face_to(track, [cen, ring[-1], ring[0]], ms["cryp"], [(0.5, 0.5), (1, 1), (0, 1)], want)
    # the walkable solid (not on the steep lift)
    if C.KIND[i] != "lift":
        for q in range(n):
            if C.KIND[i] == "drop" and ts[q] < 16:
                continue
            bot = [rp(i, ts[q], -HALF, ys[q] - DECK_T), rp(i, ts[q + 1], -HALF, ys[q + 1] - DECK_T), rp(i, ts[q + 1], HALF, ys[q + 1] - DECK_T), rp(i, ts[q], HALF, ys[q] - DECK_T)]
            top = [(p[0], p[1] + DECK_T, p[2]) for p in bot]
            col_solid(bot, top)


for p in pieces:
    deck_piece(*p)
# where the lowered lift deck meets the drop: a short riser (faces the oncoming marbles)
_a, _b = LIFT_SINK, 0.0
for u0, u1 in ((-HALF, HALF),):
    q = [rp(0, C.LEN[0], u0, C.LIFT_TOP - LIFT_SINK), rp(0, C.LEN[0], u1, C.LIFT_TOP - LIFT_SINK), rp(0, C.LEN[0], u1, C.LIFT_TOP), rp(0, C.LEN[0], u0, C.LIFT_TOP)]
    face_to(track, q, ms["lift"], [(0, 0), (1, 0), (1, 0.05), (0, 0.05)], (-C.D[0][0], 0.3, -C.D[0][1]))


# ---------------------------------------------------------------- crystal rails
def rail_shape(w, h):
    """a faceted crystal wall cross-section (closed), base at 0"""
    return [(-w / 2, -0.6), (w / 2, -0.6), (w / 2, h * 0.55), (w * 0.28, h), (-w * 0.28, h), (-w / 2, h * 0.55)]


SH = rail_shape(RAIL_W, RAIL_H)


def rail_along(points, m, sprout=True, seed=0, glow=None, solid=True, inside=None):
    """a crystal wall along a list of points (MML), crystal shards sprouting from it now and then"""
    rings = []
    for q, p in enumerate(points):
        a = points[max(0, q - 1)]; b = points[min(len(points) - 1, q + 1)]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz) or 1
        nx, nz = -tz / L, tx / L
        rings.append([(p[0] + nx * sx, p[1] + sy, p[2] + nz * sx) for sx, sy in SH])
    track.tube(rings, m, vrep=len(points) / 3, urep=1, cap0=m, cap1=m)
    # the walkable solid (none round the bowls: a marble riding high on the bank would reach it)
    for q in range(len(points) - 1 if solid else 0):
        a, b = points[q], points[q + 1]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz) or 1
        nx, nz = -tz / L * RAIL_W / 2, tx / L * RAIL_W / 2
        bot = [(a[0] - nx, a[1] - 0.6, a[2] - nz), (b[0] - nx, b[1] - 0.6, b[2] - nz), (b[0] + nx, b[1] - 0.6, b[2] + nz), (a[0] + nx, a[1] - 0.6, a[2] + nz)]
        col_solid(bot, [(x, y + RAIL_H + 0.6, z) for x, y, z in bot])
    if sprout:
        r = random.Random(seed)
        acc = 0.0
        for q in range(len(points) - 1):
            a, b = points[q], points[q + 1]
            L = math.dist(a, b)
            acc += L
            if acc > 7:
                acc = r.uniform(-3, 0)
                f = r.random()
                p = [a[k] + (b[k] - a[k]) * f for k in range(3)]
                # outward: away from the track side of the rail
                tx, tz = b[0] - a[0], b[2] - a[2]
                L = math.hypot(tx, tz) or 1
                ox, oz = -tz / L, tx / L
                if inside is not None:
                    ip = inside(p)
                    if (p[0] - ip[0]) * ox + (p[2] - ip[1]) * oz < 0:
                        ox, oz = -ox, -oz
                lean = r.uniform(0.08, 0.32)
                along = r.uniform(-0.12, 0.12)
                h = r.uniform(1.6, 4.2)
                base = (p[0] + ox * RAIL_W * 0.2, p[1] + RAIL_H * 0.6, p[2] + oz * RAIL_W * 0.2)
                A.shard(track, base, h, r.uniform(0.25, 0.4), m,
                        (ox * lean + tx / L * along, oz * lean + tz / L * along), sides=5, seed=r.randrange(10000))


def run_center(i):
    """for rail_along(inside=...): the point on run i's centre line level with p"""
    def f(p):
        d = C.D[i]
        t = (p[0] - C.P[i][0]) * d[0] + (p[2] - C.P[i][1]) * d[1]
        return (C.P[i][0] + d[0] * t, C.P[i][1] + d[1] * t)
    return f


def run_edge(i, t0, t1, u, step=4.0):
    n = max(1, int(math.ceil((t1 - t0) / step)))
    return [rp(i, t0 + (t1 - t0) * q / n, u, vis_h(i, t0 + (t1 - t0) * q / n + 1e-6)) for q in range(n + 1)]


def glow_line(points, tag, seglen=10.0):
    """cut a rail into light-up segments (each a straight glowing bar on the rail's top)"""
    acc, start = 0.0, 0
    for q in range(1, len(points)):
        acc += math.dist(points[q - 1], points[q])
        if acc >= seglen or q == len(points) - 1:
            a, b = points[start], points[q]
            glow_segs.append({"a": [round(v, 2) for v in (a[0], a[1] + RAIL_H + 0.05, a[2])], "b": [round(v, 2) for v in (b[0], b[1] + RAIL_H + 0.05, b[2])], "tag": tag})
            start, acc = q, 0.0


RAILM = {"lift": ms["cryg"], "swamp": ms["cry"], "plunge": ms["cryg"]}
for i in range(C.N):
    ta, tb = C.runspan(i)
    pr = C.profile(i)
    # split the run at its drops so each rail follows its own deck height
    cuts = [ta] + [t for (t, y), (t2, y2) in zip(pr, pr[1:]) if abs(t2 - t) < 0.01 and ta < t < tb] + [tb]
    for side in (-1, 1):
        for c0, c1 in zip(cuts, cuts[1:]):
            if i == C.N - 1 and c1 > C.LEN[i] - 9:
                c1 = C.LEN[i] - 9                       # leave room for the boarding bridge
            if i == 0 and c0 < 9:
                c0 = 9
            if c1 - c0 < 2:
                continue
            pts = run_edge(i, c0 + 0.02, c1 - 0.02, side * (HALF + RAIL_W / 2))
            rail_along(pts, RAILM.get(C.KIND[i], ms["cry"] if (i + (side > 0)) % 2 else ms["cryp"]), seed=i * 10 + side, inside=run_center(i))
            if i > 0:
                glow_line(pts, "r%d%s" % (i, "L" if side < 0 else "R"))


# ---------------------------------------------------------------- corner bowls
NA, NR = 32, 16
for j in range(C.N):
    if not C.CORNER[j]:
        continue
    c = C.corner(j)
    R = c["R"]
    rings = [R * q / NR for q in range(NR + 1)]
    Pt = [[C.corner_point(c, math.pi / 2 * qa / NA, r) for r in rings] for qa in range(NA + 1)]
    UVt = [[(math.pi / 2 * qa / NA * r / 24 if r else 0, r / 24) for r in rings] for qa in range(NA + 1)]
    track.grid(Pt, ms["bowl"], UVt)
    # hull under the bowl: offset down, then a skirt at the rim
    Ph = [[C.corner_point(c, math.pi / 2 * qa / NA, r, -1.2 - 1.6 * (1 - r / R) ** 0.5) for r in rings] for qa in range(NA + 1)]
    track.grid(Ph, ms["hull"], [[(qa / 4, q / 4) for q in range(NR + 1)] for qa in range(NA + 1)], flip=True)
    skirt = [[C.corner_point(c, math.pi / 2 * qa / NA, R), C.corner_point(c, math.pi / 2 * qa / NA, R, -1.2)] for qa in range(NA + 1)]
    track.grid(skirt, ms["hull"], None, flip=True)
    # the crystal rail round the rim (no solid on the bowl itself: it would reach into a marble's room)
    rim = [C.corner_point(c, math.pi / 2 * qa / (NA * 2), R + RAIL_W / 2) for qa in range(NA * 2 + 1)]
    rim = [(p[0], C.corner_point(c, math.pi / 2 * qa / (NA * 2), R)[1], p[2]) for qa, p in enumerate(rim)]
    rail_along(rim, ms["cryp"] if j % 2 else ms["cry"], seed=j * 7, solid=False, inside=lambda p, I=c["I"]: I)
    glow_line(rim, "c%d" % j, 9.0)
    # pillars under the bowl
    for a, r in ((math.pi / 4, 0.3 * R), (math.pi / 4, 0.72 * R), (0.3, 0.6 * R), (math.pi / 2 - 0.3, 0.6 * R), (math.pi / 4, 0.95 * R)):
        p = C.corner_point(c, a, r, -1.2 - 1.6 * (1 - r / R) ** 0.5)
        pillar_spots = globals().setdefault("PILLARS", [])
        pillar_spots.append((p[0], p[2], p[1] + 0.2, 1.2, False))


# ---------------------------------------------------------------- living pillars
PILLARS = globals().setdefault("PILLARS", [])
for (i, t0, y0, t1, y1) in pieces:
    if C.KIND[i] == "lift" and t1 < 20:
        continue
    n = max(1, int((t1 - t0) // 60))
    for q in range(n + 1):
        t = t0 + 4 + (t1 - t0 - 8) * q / max(1, n)
        y = y0 + (y1 - y0) * (t - t0) / (t1 - t0) - 3.0
        p = rp(i, t, 0, y)
        PILLARS.append((p[0], p[2], y + 0.1, 1.0 if C.KIND[i] != "lift" else 0.9, True))


def pillar(x, z, top, s=1.0, seed=0, solid=True):
    """a living pillar: a root flare, a twisting trunk with glowing veins, opening into a cradle of boughs"""
    if top < 3:
        return
    r = random.Random(seed)
    nring = 8
    path = []
    for q in range(9):
        f = q / 8
        path.append((x + math.sin(f * 3 + seed) * 0.8 * s, top * f, z + math.cos(f * 2.5 + seed) * 0.8 * s))
    scale = [2.4 - 1.2 * min(1, f * 4) + 0.6 * max(0, f - 0.8) * 5 for f in (q / 8 for q in range(9))]
    struct.sweep(path, [(1.0 * s * math.cos(k / nring * 6.283) * (1 + 0.18 * math.sin(k * 3 + seed)), 1.0 * s * math.sin(k / nring * 6.283) * (1 + 0.18 * math.sin(k * 3 + seed))) for k in range(nring)],
                 ms["bark"] if seed % 3 else ms["barkp"], scale=scale, vrep=top / 8, twist=1.5)
    # roots
    for k in range(3):
        a = k / 3 * 6.283 + r.random()
        rp_ = [(x + math.sin(a) * (1.5 + 3.5 * f) * s, 1.2 * (1 - f) ** 2 + 0.05, z + math.cos(a) * (1.5 + 3.5 * f) * s) for f in (q / 6 for q in range(7))]
        struct.sweep(rp_, [(0.5 * s * math.cos(k2 / 6 * 6.283), 0.5 * s * math.sin(k2 / 6 * 6.283)) for k2 in range(6)], ms["bark"], scale=[1 - 0.8 * q / 6 for q in range(7)])
    if solid:          # (only up to well below the deck)
        colm.tube([[(x + 1.2 * math.sin(k / 8 * 6.283), 0, z + 1.2 * math.cos(k / 8 * 6.283)) for k in range(8)],
                   [(x + 1.2 * math.sin(k / 8 * 6.283), top - 2, z + 1.2 * math.cos(k / 8 * 6.283)) for k in range(8)]], CM, cap0=CM, cap1=CM)


for k, (x, z, top, s, sol) in enumerate(PILLARS):
    pillar(x, z, top, s, seed=k, solid=sol)


# ---------------------------------------------------------------- the features on each run
def deck_pt(i, s, u, dy=0.0):
    t0 = C.runspan(i)[0]
    return rp(i, t0 + s, u, hgt(i, t0 + s) + dy)


for i in range(1, C.N):
    k = C.KIND[i]
    t0, t1 = C.runspan(i)
    if k == "pinball":
        for q, (s, u) in enumerate(C.PEGS):
            p = deck_pt(i, s, u)
            A.pylon(track, p, C.PEG_R, 10.0, ms, seed=q)
            colm.tube([A.ring((p[0], p[1], p[2]), C.PEG_R, 8), A.ring((p[0], p[1] + 6, p[2]), C.PEG_R, 8)], CM, cap0=CM, cap1=CM)
    if k == "forest":
        for q, (s, u) in enumerate(C.FOREST):
            p = deck_pt(i, s, u)
            A.crystal_spire(track, p, 11, ms["cryp"] if q % 2 else ms["cry"], C.FOREST_R, seed=q + 50, n=6)
            colm.tube([A.ring(p, C.FOREST_R, 8), A.ring((p[0], p[1] + 8, p[2]), C.FOREST_R, 8)], CM, cap0=CM, cap1=CM)
    if k == "bumpers":
        for q, (s, u, r) in enumerate(C.BUMPERS):
            p = deck_pt(i, s, u)
            props.append(["mr4_bumper_" + ("a" if r < 3.2 else "b"), p[0], p[1], p[2], rnd.uniform(0, 360), 1.0, False])
            colm.tube([A.ring(p, r * 0.95, 10), A.ring((p[0], p[1] + 9, p[2]), r * 0.95, 10)], CM, cap0=CM, cap1=CM)
    if k == "funnel":
        for side in (-1, 1):
            pts = []
            for (sa, ua), (sb, ub) in zip(C.FUNNEL, C.FUNNEL[1:]):
                for q in range(6 if sb - sa > 20 else 3):
                    f = q / (6 if sb - sa > 20 else 3)
                    s_, u_ = sa + (sb - sa) * f, ua + (ub - ua) * f
                    pts.append(deck_pt(i, s_, side * u_))          # on the line the marbles bounce off (the rail is that thick)
            pts.append(deck_pt(i, C.FUNNEL[-1][0], side * C.FUNNEL[-1][1]))
            rail_along(pts, ms["cryp"] if side < 0 else ms["cry"], seed=i * 3 + side, inside=run_center(i))
            glow_line(pts, "f%s" % side, 8.0)
    if k == "split":
        pts = [deck_pt(i, C.SPLIT[0] + (C.SPLIT[1] - C.SPLIT[0]) * q / 20, 0) for q in range(21)]
        rail_along(pts, ms["cryg"], seed=77, sprout=False)          # marbles run down both sides of it: nothing sprouts
        glow_line(pts, "s", 10.0)
        for s in C.SPLIT:
            A.crystal_spire(track, deck_pt(i, s, 0), 6, ms["cryg"], C.SPLIT_R, seed=int(s), n=4)
    if k == "swamp":
        for q in range(26):
            s = rnd.uniform(4, t1 - t0 - 4); u = rnd.uniform(-HALF + 3, HALF - 3)
            p = deck_pt(i, s, u, 0.1)
            r_ = rnd.uniform(0.8, 1.6)
            pad = [(p[0], p[1], p[2])] + [(p[0] + r_ * math.sin(a / 10 * 6.0), p[1] + 0.02, p[2] + r_ * math.cos(a / 10 * 6.0)) for a in range(11)]
            for a in range(10):
                track.face([pad[0], pad[a + 2], pad[a + 1]], ms["leafg"], [(0.5, 0), (a / 10, 1), ((a + 1) / 10, 1)])
    if k == "tunnel":
        TUN = []
        s = 8.0
        while s < t1 - t0 - 4:
            p = deck_pt(i, s, 0)
            A.tunnel_ring(track, p, C.heading_deg(i), 2 * HALF + 6, 26, ms, seed=int(s))
            colm.tube  # (the rings stand outside the deck: their feet are beyond the rails)
            TUN.append([round(v, 2) for v in p])
            s += 12.0
        globals()["TUNNEL"] = TUN
    if k == "jump":
        # glowing chevrons up the kicker
        lip = t0 + C.JUMP_AT
        for q in range(6):
            s = C.JUMP_AT - C.JUMP_LEN + q * 1.6
            for u in (-24, -8, 8, 24):
                a = deck_pt(i, s, u - 5, 0.06); b = deck_pt(i, s + 1.2, u, 0.06); cc = deck_pt(i, s, u + 5, 0.06)
                a2 = deck_pt(i, s + 0.6, u - 5, 0.06); b2 = deck_pt(i, s + 1.8, u, 0.06); c2 = deck_pt(i, s + 0.6, u + 5, 0.06)
                face_to(track, [a, a2, b2, b], ms["glowg"], None, (0, 1, 0)); face_to(track, [b, b2, c2, cc], ms["glowg"], None, (0, 1, 0))


# ---------------------------------------------------------------- arches + signs over each run
def sign_arch(i, s, text, c1, c2):
    t0 = C.runspan(i)[0]
    p = rp(i, t0 + s, 0, 0)
    y = hgt(i, t0 + s)
    SPAN, TOP, LEG = 2 * HALF + 10, y + 34, y + 12
    W = A.arch(signs, (p[0], 0, p[2]), C.heading_deg(i), SPAN, TOP, ms, seed=i, leg=LEG)
    tex4.holo_text("sign4_" + text.replace(" ", "_").lower(), text, c1=c1, c2=c2)
    sm = mat("sign4_" + text, "sign4_" + text.replace(" ", "_").lower(), emit=2.0, rough=0.4)
    A.text_panel(signs, (p[0], y + 22, p[2]), C.heading_deg(i) + 180, 40, 6.25, sm, curve=1.2)
    # the panel hangs from the arch on two glowing cords
    for u in (-17, 17):
        a = rp(i, t0 + s, u, y + 25.1); b = rp(i, t0 + s, u * 0.75, A.arch_y(SPAN, TOP, LEG, u * 0.75) - 0.8)
        signs.sweep([a, b], [(0.12 * math.cos(k / 4 * 6.283), 0.12 * math.sin(k / 4 * 6.283)) for k in range(4)], ms["glowg"])
    for sd in (-1, 1):
        q = rp(i, t0 + s, sd * (HALF + 5), 0)
        colm.tube([A.ring((q[0], 0, q[2]), 1.8, 8), A.ring((q[0], y + 8, q[2]), 1.8, 8)], CM, cap0=CM, cap1=CM)


PAL = [("#5ff2ff", "#ff5fc8"), ("#b6ff5a", "#3ff6ff"), ("#ffd36b", "#ff4fd8"), ("#ff7a2e", "#ffd36b"), ("#9b6bff", "#5ff2ff")]
for i in range(1, C.N):
    sign_arch(i, 12 if C.KIND[i] not in ("tunnel",) else 2, C.RUNS[i], *PAL[i % len(PAL)])
# the lift
tex4.holo_text("sign4_lift", "LIFT HILL", c1="#ffd36b", c2="#ff7a2e")
_h40 = vis_h(0, 40)
W = A.arch(signs, (0, 0, 40), 0, 2 * HALF + 10, _h40 + 34, ms, seed=99, leg=_h40 + 12)
A.text_panel(signs, (0, _h40 + 22, 40), 180, 40, 6.25, mat("sign4_lift", "sign4_lift", emit=2.0), curve=1.2)

# ---------------------------------------------------------------- the finish
fz = C.finish = C.run_point(C.N - 1, C.FINISH_T, 0, 0)
A.arch(signs, (0, 0, fz[2]), 0, 2 * HALF + 14, 40, ms, seed=123, leg=12)
A.arch(signs, (0, 0, fz[2] + 3), 0, 2 * HALF + 12, 36, ms, seed=124, leg=12)
tex4.holo_text("sign4_finish", "FINISH", c1="#ffffff", c2="#ffd36b")
A.text_panel(signs, (0, 26, fz[2]), 180, 34, 8, mat("sign4_finish", "sign4_finish", emit=2.4), curve=1.5)
for sd in (-1, 1):
    colm.tube([A.ring((sd * (HALF + 7), 0, fz[2]), 2, 8), A.ring((sd * (HALF + 7), 10, fz[2]), 2, 8)], CM, cap0=CM, cap1=CM)

# ---------------------------------------------------------------- the station: a crystal pavilion, kiosks, boards
tex4.holo_text("sign4_title", "THE GRAND MARBLE RUN", w=1600, h=190, c1="#5ff2ff", c2="#ff5fc8")
tex4.holo_text("sign4_walkin", "WALK IN - PICK YOUR MARBLE", w=1600, h=160, c1="#ffd36b", c2="#ffffff")
tex4.holo_text("sign4_control", "RACE CONTROL", w=1024, h=270, c1="#ffd36b", c2="#ff7a2e", sub="CLICK - TYPE THE CODE")
tex4.holo_text("sign4_standings", "STANDINGS", w=1024, h=160, c1="#5ff2ff", c2="#ffd36b")
A.arch(station, (0, 0, -12), 0, 2 * HALF + 16, 34, ms, seed=7, leg=12)
A.text_panel(station, (0, 22, -12), 180, 58, 6.8, mat("sign4_title", "sign4_title", emit=2.2), curve=1.8)
A.text_panel(station, (0, 15.5, -12), 180, 40, 3.9, mat("sign4_walkin", "sign4_walkin", emit=2.0), curve=1.0)
for sd in (-1, 1):
    colm.tube([A.ring((sd * (HALF + 8), 0, -12), 2.2, 8), A.ring((sd * (HALF + 8), 10, -12), 2.2, 8)], CM, cap0=CM, cap1=CM)
# the plaza floor round the station: glowing tiles (a gently domed disc)
def disc(me, c, r, m, y=0.0, seg=48, rings_=6, rep=8):
    P = [[(c[0] + r * q / rings_ * math.sin(a / seg * 6.283), y + 0.06 * (1 - (q / rings_) ** 2), c[2] + r * q / rings_ * math.cos(a / seg * 6.283)) for a in range(seg + 1)] for q in range(rings_ + 1)]
    UV = [[(p[0] / rep, p[2] / rep) for p in row] for row in P]
    me.grid(P, m, UV)
for sd in (-1, 1):
    disc(station, (sd * (HALF + 16), 0, -6), 13, ms["tiles"], y=0.02)
# steps to the bridge (curved crystal steps)
for sd in (-1, 1):
    for k in range(3):
        h = 0.4 * (k + 1)
        x0 = sd * (HALF + 1.0 + 4.5 - k * 1.5 - 1.5); x1 = x0 + sd * 1.5
        a, b = min(x0, x1), max(x0, x1)
        bot = [(a, 0, -7.5), (b, 0, -7.5), (b, 0, -2.4), (a, 0, -2.4)]
        top = [(a, h, -7.5), (b, h, -7.5), (b, h, -2.4), (a, h, -2.4)]
        station.tube([bot, top], ms["white"], cap1=ms["tiles"])
        col_solid(bot, top)
    a, b = sorted((sd * (HALF + 0.4), sd * (HALF + 1.0)))
    bot = [(a, 0, -7.5), (b, 0, -7.5), (b, 0, -2.4), (a, 0, -2.4)]
    station.tube([bot, [(x, 1.12, z) for x, _, z in bot]], ms["white"], cap1=ms["tiles"])
    col_solid(bot, [(x, 1.2, z) for x, _, z in bot])
# race control kiosks: a crystal pedestal with a glowing panel
rcm = mat("sign4_control", "sign4_control", emit=2.0)
for sd in (-1, 1):
    x = sd * (HALF + 12)
    station.lathe([(2.6, 0), (2.7, 0.3), (2.2, 0.8), (1.6, 1.6), (1.5, 2.2), (2.1, 2.5), (0.01, 2.6)], ms["white"], c=(x, 0, -5), seg=24)
    A.crystal_cluster(station, (x, 2.4, -5), 2.4, ms["cryg"], seed=sd + 5, n=5)
    A.text_panel(station, (x, 4.6, -5), 90 * -sd, 6, 1.6, rcm, curve=0.3)
    colm.tube([A.ring((x, 0, -5), 2.6, 10), A.ring((x, 2.6, -5), 2.6, 10)], CM, cap0=CM, cap1=CM)

# scoreboards: organic frames round a dark glass face (the words are live labels in the game)
BOARDS = [
    {"x": -64, "y": 13, "z": 2, "ry": 90},
    {"x": 440, "y": 92, "z": 80, "ry": 90},
    {"x": 232, "y": 64, "z": -160, "ry": 90},
]
stm = mat("sign4_standings", "sign4_standings", emit=2.0)
glass = mat("boardglass", color="#05060f", rough=0.1, metal=0.5)
for b in BOARDS:
    yaw = b["ry"]
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    def at(dx, dy, dz):
        return (b["x"] + dx * cy + dz * sy, b["y"] + dy, b["z"] - dx * sy + dz * cy)
    face = [at(-11.5, -10.5, -0.3), at(11.5, -10.5, -0.3), at(11.5, 10.5, -0.3), at(-11.5, 10.5, -0.3)]
    station.face(face, glass); station.face(face[::-1], glass)
    frame = [at(12.2 * math.copysign(1, math.cos(a)) * min(1, abs(math.cos(a)) * 1.6), 11.2 * math.copysign(1, math.sin(a)) * min(1, abs(math.sin(a)) * 1.6), -0.3) for a in [k / 64 * 6.283 for k in range(65)]]
    station.sweep(frame, [(0.5 * math.cos(k / 8 * 6.283), 0.5 * math.sin(k / 8 * 6.283)) for k in range(8)], ms["cry"], vrep=6)
    A.text_panel(station, at(0, 13.2, -0.3), yaw, 16, 2.5, stm, curve=0.4)
    # it stands on a living trunk
    base = at(0, -10.5, -1.0)
    path = [(base[0] + math.sin(q) * 0.5, base[1] * (1 - q / 8), base[2] + math.cos(q) * 0.5) for q in range(9)][::-1]
    station.sweep(path, [(1.3 * math.cos(k / 10 * 6.283), 1.3 * math.sin(k / 10 * 6.283)) for k in range(10)], ms["bark"], scale=[2.2 - 1.2 * q / 8 for q in range(9)], vrep=4, twist=1.2)
    colm.tube([A.ring((base[0], 0, base[2]), 1.5, 8), A.ring((base[0], base[1], base[2]), 1.5, 8)], CM, cap0=CM, cap1=CM)

# ---------------------------------------------------------------- export the big pieces
def out(name, me):
    o = me.obj(name)
    print(name, tris([o]), "tris")
    export(name, [o])
FLOORS = [ms["deck"], ms["lift"], swamp_m, ms["checker"], ms["bowl"], ms["leafg"]]
track.orient_up(FLOORS)
track.orient_away([ms["hull"]], FLOORS, radius=12.0)
station.orient_up([ms["tiles"]])
out("mr4_track", track)
out("mr4_struct", struct)
out("mr4_signs", signs)
out("mr4_station", station)
cob = colm.obj("collide", smooth=False)
export("mr4_collide_raw", [cob])
print("collider", tris([cob]), "tris")

# ---------------------------------------------------------------- the ground: rolling glowing meadow
reset()
ms = A.M()
g = Mesh()
GX0, GX1, GZ0, GZ1, STEP = -320, 720, -680, 620, 20
def terrain(x, z):
    """gentle hills, flat round the station and under the low end of the track"""
    h = 2.5 * math.sin(x * 0.013 + 1) * math.cos(z * 0.011) + 1.6 * math.sin(x * 0.031 + z * 0.02) + 1.0
    d = math.hypot(x, z + 60) / 140
    return max(-0.04, h * min(1, max(0, d - 0.6) * 1.5)) - 0.04
xs = [GX0 + STEP * q for q in range(int((GX1 - GX0) / STEP) + 1)]
zs = [GZ0 + STEP * q for q in range(int((GZ1 - GZ0) / STEP) + 1)]
P = [[(x, terrain(x, z), z) for x in xs] for z in zs]
UV = [[(x / 60, z / 60) for x in xs] for z in zs]
g.grid(P, ms["moss"], UV)
g.orient_up([ms["moss"]])
gob = g.obj("ground")
export("mr4_ground", [gob])
print("ground", tris([gob]), "tris")

# ---------------------------------------------------------------- scenery props: groves of glowing life round the course
def near_track(x, z, pad=8):
    for i in range(C.N):
        t0, t1 = 0, C.LEN[i]
        d, n = C.D[i], C.normal(C.D[i])
        px, pz = x - C.P[i][0], z - C.P[i][1]
        t = px * d[0] + pz * d[1]; u = px * n[0] + pz * n[1]
        if -HALF - pad <= t <= C.LEN[i] + HALF + pad and abs(u) <= HALF + pad:
            return True
    return False


SC = [("mr4_mush_m", True, 0.8, 1.4), ("mr4_mush_c", True, 0.8, 1.5), ("mr4_mush_l", True, 0.8, 1.6), ("mr4_fern_g", True, 1.0, 1.8),
      ("mr4_fern_v", True, 1.0, 1.8), ("mr4_fronds_g", True, 1.2, 2.2), ("mr4_fronds_v", True, 1.2, 2.2), ("mr4_crystals_c", False, 0.8, 1.6),
      ("mr4_crystals_p", False, 0.8, 1.6), ("mr4_crystals_g", False, 0.8, 1.4), ("mr4_willow", True, 0.8, 1.3)]
placed = 0
tries_ = 0
while placed < 150 and tries_ < 6000:
    tries_ += 1
    x, z = rnd.uniform(GX0 + 40, GX1 - 40), rnd.uniform(GZ0 + 40, GZ1 - 40)
    if near_track(x, z, 10) or math.hypot(x, z) < 90:
        continue
    if any(math.hypot(x - p[1], z - p[3]) < 14 for p in props):
        continue
    name, anim, s0, s1 = SC[rnd.randrange(len(SC))]
    props.append([name, round(x, 1), round(terrain(x, z), 2), round(z, 1), round(rnd.uniform(0, 360)), round(rnd.uniform(s0, s1), 2), anim])
    placed += 1
# floating islands and jellyfish drifting over the course
for k in range(9):
    for _ in range(200):
        x, z = rnd.uniform(-200, 650), rnd.uniform(-600, 520)
        if not near_track(x, z, 30):
            break
    props.append(["mr4_island_" + ("a" if k % 2 else "b"), round(x, 1), round(rnd.uniform(95, 190), 1), round(z, 1), round(rnd.uniform(0, 360)), round(rnd.uniform(1.4, 2.6), 2), True])
for k in range(16):
    x, z = rnd.uniform(-150, 620), rnd.uniform(-560, 480)
    props.append(["mr4_jelly_" + ("a" if k % 2 else "b"), round(x, 1), round(rnd.uniform(60, 200), 1), round(z, 1), 0, round(rnd.uniform(1.5, 3.0), 2), True])

json.dump({"boards": BOARDS, "props": props, "glow": glow_segs, "tunnel": globals().get("TUNNEL", []),
           "finish_z": fz[2]}, open("/home/claude/mr4/out/world4.json", "w"))
print("props", len(props), "glow segments", len(glow_segs))

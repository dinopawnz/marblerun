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
LANE_MATS = [mat("lane_" + n, tint(c), 0.5) for n, c in zip(C.NAMES, C.COLORS)]     # (the lift's lanes)
M["redglow"] = mat("redglow", "#ff3048", 0.35, emit=0.7)
M["pegtop"] = mat("pegtop", "#ffe9a8", 0.3, emit=0.8)
CHECKER = mat("checker", "#ffffff", 0.5, image=checker_png("checker", 16, 1024, 128))
colm = Mesh()      # the invisible solid you walk on: ONE plain model (no meshopt) in the game
CM = mat("collide", "#ff00ff", 1.0)


def col_box(c, s, ry=0.0, rx=0.0):
    """an invisible solid box (axis aligned, or turned about y by a multiple of 90)"""
    colm.box(c, s, CM, yaw=ry)


def rp(i, t, o, y):
    return C.run_point(i, t, o, y)


def hgt(i, t):
    return C.height(i, t)


track = Mesh()
scen = Mesh()

# ---------------------------------------------------------------- deck pieces: straight bits of each run's profile
pieces = []          # (run, t0, y0, t1, y1, kind)
for i in range(C.N):
    pr = C.profile(i)
    for (ta, ya), (tb, yb) in zip(pr, pr[1:]):
        if tb - ta < 0.01:
            continue                      # a drop
        kind = "lift" if i == 0 else ("mud" if i == C.MUD else "flat")
        pieces.append((i, ta, ya, tb, yb, kind))
runspan = C.runspan

# across the deck, edge to edge: deck, a gold line inside each edge (the lift keeps its lanes)
LINE_W = 0.3
def bands(kind):
    if kind == "mud":
        return [(-HALF, HALF, M["mud"])]
    if kind == "lift":
        out, prev = [], -HALF
        edges = [(j - C.LANES / 2) * C.LANE_W for j in range(C.LANES + 1)]
        for j, e in enumerate(edges):
            out.append((prev, e - LINE_W / 2, M["lift"]))
            out.append((e - LINE_W / 2, e + LINE_W / 2, M["yellow"]))
            prev = e + LINE_W / 2
        out.append((prev, HALF, M["lift"]))
        return out
    e = HALF - 1.2
    return [(-HALF, -e - LINE_W, M["deck"]), (-e - LINE_W, -e, M["gold"]), (-e, e, M["deck"]), (e, e + LINE_W, M["gold"]), (e + LINE_W, HALF, M["deck"])]


def slab_sides(top, bot, mesh=None):
    """bottom + four sides of a slab (the top is drawn separately as strips)"""
    mesh = mesh or track
    ctr = tuple(sum(p[i] for p in top + bot) / 8 for i in range(3))
    mesh.face(list(bot), M["dark"], out=ctr)
    for q in range(4):
        r = (q + 1) % 4
        mesh.face([bot[q], bot[r], top[r], top[q]], M["dark"], out=ctr)


def deck_piece(i, t0, y0, t1, y1, kind):
    top = [rp(i, t0, -HALF, y0), rp(i, t1, -HALF, y1), rp(i, t1, HALF, y1), rp(i, t0, HALF, y0)]
    bot = [(p[0], p[1] - DECK_T, p[2]) for p in top]
    slab_sides(top, bot)
    if kind != "lift":                # (the lift is too steep to have a solid under a rolling marble's room)
        colm.solid(bot, top, CM)
    cuts = [(t0, t1, None)]
    if i == C.N - 1 and t0 < C.FINISH_T < t1:
        cuts = [(t0, C.FINISH_T - 1.5, None), (C.FINISH_T - 1.5, C.FINISH_T + 1.5, "checker"), (C.FINISH_T + 1.5, t1, None)]
    for ta, tb, special in cuts:
        ya = y0 + (y1 - y0) * (ta - t0) / (t1 - t0); yb = y0 + (y1 - y0) * (tb - t0) / (t1 - t0)
        if special == "checker":
            q = [rp(i, ta, -HALF, ya), rp(i, tb, -HALF, yb), rp(i, tb, HALF, yb), rp(i, ta, HALF, ya)]
            track.face(q, CHECKER, uv=[(0, 0), (0, 1), (1, 1), (1, 0)], out=(q[0][0], q[0][1] - 5, q[0][2]))
            continue
        for lo, hi, mm in bands(kind):
            q = [rp(i, ta, lo, ya), rp(i, tb, lo, yb), rp(i, tb, hi, yb), rp(i, ta, hi, ya)]
            track.face(q, mm, out=(q[0][0], q[0][1] - 5, q[0][2]))
    L = t1 - t0
    d = C.D[i]
    if kind == "lift":                     # chevrons across each lane, like a chain
        t = t0 + 2
        while t < t1 - 1:
            yy = y0 + (y1 - y0) * (t - t0) / L
            for j in range(C.LANES):
                o = C.lane_off(j)
                a = rp(i, t - 0.25, o - 2.5, yy + 0.1 - 0.25 * (y1 - y0) / L); b = rp(i, t + 0.25, o + 2.5, yy + 0.1 + 0.25 * (y1 - y0) / L)
                bt = [rp(i, t - 0.25, o - 2.5, yy - 0.05 - 0.25 * (y1 - y0) / L), rp(i, t + 0.25, o - 2.5, yy - 0.05 + 0.25 * (y1 - y0) / L),
                      rp(i, t + 0.25, o + 2.5, yy - 0.05 + 0.25 * (y1 - y0) / L), rp(i, t - 0.25, o + 2.5, yy - 0.05 - 0.25 * (y1 - y0) / L)]
                tp = [(p[0], p[1] + 0.17, p[2]) for p in bt]
                track.solid(bt, tp, M["yellow"])
            t += 4
    # curbs, alternating red / white (yellow / black on the lift), an LED strip on top
    for sd in (-1, 1):
        o = sd * (HALF + CURB_W / 2)
        c0 = t0
        if C.CORNER[i] and abs(t0 - runspan(i)[0]) < 1e-6:          # an inner corner: the last run's curb covers it
            din = C.D[(i - 1) % C.N]; nn_ = C.normal(d)
            if sd * (nn_[0] * din[0] + nn_[1] * din[1]) < 0:
                c0 = t0 + CURB_W
        n = max(1, int(round((t1 - c0) / 6.0)))
        for q in range(n):
            ta = c0 + (t1 - c0) * q / n; tb = c0 + (t1 - c0) * (q + 1) / n
            if (i == 0 and ta < 4) or (i == C.N - 1 and tb > C.LEN[C.N - 1] - 8.5):
                continue                                  # the boarding bridge crosses here
            ya = y0 + (y1 - y0) * (ta - t0) / L; yb = y0 + (y1 - y0) * (tb - t0) / L
            bot = [rp(i, ta, o - CURB_W / 2, ya - DECK_T), rp(i, tb, o - CURB_W / 2, yb - DECK_T), rp(i, tb, o + CURB_W / 2, yb - DECK_T), rp(i, ta, o + CURB_W / 2, ya - DECK_T)]
            top = [(p[0], p[1] + DECK_T + CURB_H, p[2]) for p in bot]
            cm = (M["black"] if q % 2 else M["yellow"]) if kind == "lift" else (M["red"] if q % 2 else M["white"])
            track.solid(bot, top, cm)
            colm.solid(bot, top, CM)
        a, b = rp(i, c0, o, y0 + (y1 - y0) * (c0 - t0) / L + CURB_H + 0.12), rp(i, t1, o, y1 + CURB_H + 0.12)
        nn = C.normal(d)
        q4 = [(a[0] - nn[0] * .15, a[1], a[2] - nn[1] * .15), (b[0] - nn[0] * .15, b[1], b[2] - nn[1] * .15), (b[0] + nn[0] * .15, b[1], b[2] + nn[1] * .15), (a[0] + nn[0] * .15, a[1], a[2] + nn[1] * .15)]
        track.face(q4, M["led"], out=(a[0], a[1] - 5, a[2]))

for p in pieces:
    deck_piece(*p)

# the stairs: a black face down each drop, hazard stripes along the lip
pr = C.profile(2)
for (ta, ya), (tb, yb) in zip(pr, pr[1:]):
    if tb - ta > 0.01:
        continue
    fq = [rp(2, ta, -HALF, ya - DECK_T), rp(2, ta, HALF, ya - DECK_T), rp(2, ta, HALF, yb), rp(2, ta, -HALF, yb)]     # below the upper slab's own end
    track.face(fq, M["black"], out=rp(2, ta - 5, 0, (ya + yb) / 2))
    for q in range(16):
        lo, hi = -HALF + 2 * HALF * q / 16, -HALF + 2 * HALF * (q + 1) / 16
        sl = (yb - ya) / 1.0
        bt = [rp(2, ta - 0.8, lo, ya + 0.0), rp(2, ta, lo, ya), rp(2, ta, hi, ya), rp(2, ta - 0.8, hi, ya)]
        bt = [(p[0], C.height(2, ta - 0.4) + 0.0, p[2]) for p in bt]
        tp = [(p[0], p[1] + 0.12, p[2]) for p in bt]
        track.solid(bt, tp, M["yellow"] if q % 2 else M["black"])

# ---------------------------------------------------------------- corner bowls
NA, NR = 28, 14
def corner_bowl(j):
    c = C.corner(j)
    I, R, din, dout = c["I"], c["R"], c["din"], c["dout"]
    def P(a, r, dy=0.0):
        # a: 0 at the entry edge, pi/2 at the exit edge; r from the inner corner
        x = I[0] + (-dout[0] * math.cos(a) + din[0] * math.sin(a)) * r
        z = I[1] + (-dout[1] * math.cos(a) + din[1] * math.sin(a)) * r
        return (x, C.corner_height(c, x, z) + dy, z)
    e = R - 1.2
    rings = [R * q / NR for q in range(NR)] + [e - LINE_W, e, R]
    rings = sorted(set(round(r, 4) for r in rings if r <= R))
    for qa in range(NA):
        a0, a1 = math.pi / 2 * qa / NA, math.pi / 2 * (qa + 1) / NA
        for r0, r1 in zip(rings, rings[1:]):
            mm = M["gold"] if abs(r0 - (e - LINE_W)) < 1e-3 else M["deck"]
            if r0 < 1e-6:
                tri = [P(a0, 0), P(a0, r1), P(a1, r1)]
                track.face(tri, mm, out=(I[0], C.corner_height(c, I[0], I[1]) - 5, I[1]))
                track.face([P(a0, 0, -DECK_T), P(a0, r1, -DECK_T), P(a1, r1, -DECK_T)], M["dark"], out=(I[0], 1e4, I[1]))
            else:
                q = [P(a0, r0), P(a0, r1), P(a1, r1), P(a1, r0)]
                track.face(q, mm, out=(q[0][0], q[0][1] - 5, q[0][2]))
                qb = [P(a0, r0, -DECK_T), P(a0, r1, -DECK_T), P(a1, r1, -DECK_T), P(a1, r0, -DECK_T)]
                track.face(qb, M["dark"], out=(q[0][0], q[0][1] + 50, q[0][2]))
        # the curved wall: red / white blocks on the rim, an LED strip on top
        b = [P(a0, R, -DECK_T), P(a1, R, -DECK_T), P(a1, R + CURB_W, -DECK_T), P(a0, R + CURB_W, -DECK_T)]
        b = [b[0], b[1], (b[2][0], b[1][1], b[2][2]), (b[3][0], b[0][1], b[3][2])]
        t = [(p[0], p[1] + DECK_T + CURB_H + 0.6, p[2]) for p in b]
        track.solid(b, t, M["red"] if qa % 2 else M["white"])
        colm.solid(b, t, CM)
        mida = [(b[0][0] * 0.5 + b[3][0] * 0.5, t[0][1] + 0.12, b[0][2] * 0.5 + b[3][2] * 0.5), (b[1][0] * 0.5 + b[2][0] * 0.5, t[1][1] + 0.12, b[1][2] * 0.5 + b[2][2] * 0.5)]
    # (no solid under the bowl itself: on the steep banks it would reach into a marble's room)
    # columns under the bowl
    for a, r in ((math.pi / 4, 0.22 * R), (math.pi / 4, 0.6 * R), (math.pi / 4, 0.92 * R), (0.25, 0.75 * R), (math.pi / 2 - 0.25, 0.75 * R), (0.55, 0.95 * R), (math.pi / 2 - 0.55, 0.95 * R)):
        p = P(a, r, -DECK_T)
        column(p[0], p[2], p[1] - 0.05)

# ---------------------------------------------------------------- supports
def footprint_has_lower(x, z, top):
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
    scen.prism((x, 0, z), 0.75, top - 1.0, M["steel"], n=8, y0=0.6, r_top=0.6)
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
            if footprint_has_lower(p[0], p[2], yy):
                continue
            column(p[0], p[2], yy)
            pts.append(p)
        if len(pts) == 2 and yy > 6:
            a, b = pts
            scen.box(((a[0] + b[0]) / 2, yy - 1.1, (a[2] + b[2]) / 2), (abs(a[0] - b[0]) + 1.2, 1.6, abs(a[2] - b[2]) + 1.2), M["dark"])
for j in range(C.N):
    if C.CORNER[j]:
        corner_bowl(j)
        ox, oz = C.P[j][0] + (C.D[j - 1][0] - C.D[j][0]) * (HALF + 2.5), C.P[j][1] + (C.D[j - 1][1] - C.D[j][1]) * (HALF + 2.5)
        top = C.corner(j)["yin"] + C.BANK + 6
        scen.prism((ox, 0, oz), 1.0, top, M["dark"], n=8, y0=0)
        scen.prism((ox, 0, oz), 1.6, 1.2, M["gold"], n=8, y0=top)
        scen.prism((ox, 0, oz), 0.9, 1.0, M["led"], n=8, y0=top + 1.2)

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
    scen.sign((c[0], top + 3.1, c[2]), 34, 4.25, C.heading_deg(i) + 180, sm, frame=M["gold"])

FG = {"THE PINBALL": "#ffd23f", "THE BUMPERS": "#ff5a5a", "THE FUNNEL": "#3fe0ff", "THE SPLIT": "#ffb11a", "THE MUD": "#d9a066", "THE STAIRS": "#ffd23f"}
for i in range(1, C.N):
    ta, tb = runspan(i)
    t = ta + 10 if i not in (3, 5, 7, 8) else ta + 6
    gantry(i, t, max(hgt(i, t), hgt(i, ta)), C.RUNS[i], fg=FG.get(C.RUNS[i], "#ffd23f"))
gantry(0, 30, hgt(0, 30), "LIFT HILL", fg="#f2c200")

# ---------------------------------------------------------------- obstacles (open paths, every one)
def deck_pt(i, t, u, dy=0.0):
    p = rp(i, t, u, hgt(i, t) + dy)
    return p
# THE PINBALL: gold posts with glowing tops
for t, u in C.PEGS:
    p = deck_pt(3, t, u)
    scen.prism(p, C.PEG_R, 3.2, M["gold"], n=10, y0=p[1] - 0.3)
    scen.prism(p, C.PEG_R * 0.8, 0.5, M["pegtop"], n=10, y0=p[1] + 2.9)
    col_box((p[0], p[1] + 1.6, p[2]), (C.PEG_R * 1.6, 3.2, C.PEG_R * 1.6))
# THE BUMPERS: big round pinball bumpers
for t, u, r in C.BUMPERS:
    p = deck_pt(5, t, u)
    scen.prism(p, r, 1.0, M["dark"], n=20, y0=p[1] - 0.3)
    scen.prism(p, r * 1.04, 0.9, M["redglow"], n=20, y0=p[1] + 0.7)
    scen.prism(p, r * 0.98, 1.2, M["white"], n=20, y0=p[1] + 1.6)
    scen.prism(p, r * 0.7, 0.5, M["gold"], n=20, y0=p[1] + 2.8, r_top=r * 0.45)
    col_box((p[0], p[1] + 1.6, p[2]), (r * 1.6, 3.2, r * 1.6))
# THE FUNNEL: two angled walls squeeze the field to the middle and let it out again
def wall(i, ta, ua, tb, ub, h, cols_):
    n = max(1, int(round(math.hypot(tb - ta, ub - ua) / 5)))
    for q in range(n):
        f0, f1 = q / n, (q + 1) / n
        t0_, t1_ = ta + (tb - ta) * f0, ta + (tb - ta) * f1
        u0_, u1_ = ua + (ub - ua) * f0, ua + (ub - ua) * f1
        dt, du = t1_ - t0_, u1_ - u0_
        L = math.hypot(dt, du); nt, nu = -du / L * 0.45, dt / L * 0.45
        sunk = DECK_T - 0.15             # bottom inside the slab, not on its underside
        bot = [rp(i, t0_ - nt, u0_ - nu, hgt(i, t0_) - sunk), rp(i, t1_ - nt, u1_ - nu, hgt(i, t1_) - sunk),
               rp(i, t1_ + nt, u1_ + nu, hgt(i, t1_) - sunk), rp(i, t0_ + nt, u0_ + nu, hgt(i, t0_) - sunk)]
        top = [(p[0], p[1] + sunk + h, p[2]) for p in bot]
        track.solid(bot, top, cols_[q % len(cols_)])
        colm.solid(bot, top, CM)
for side in (-1, 1):
    for (ta, ua), (tb, ub) in zip(C.FUNNEL, C.FUNNEL[1:]):
        wall(7, ta, side * ua, tb, side * ub, CURB_H + 0.6, [M["red"], M["white"]])
# THE SPLIT: a wall down the middle, rounded ends
wall(8, C.SPLIT[0], 0, C.SPLIT[1], 0, CURB_H + 0.6, [M["dark"]])
for t in C.SPLIT:
    p = deck_pt(8, t, 0)
    scen.prism(p, C.SPLIT_R + 0.05, CURB_H + 0.6 + 0.3, M["gold"], n=10, y0=p[1] - 0.3)
# THE MUD: a few low bubbles
import random
random.seed(7)
ta, tb = runspan(C.MUD)
bub = []
for q in range(400):
    if len(bub) >= 70:
        break
    t = random.uniform(ta + 2, tb - 2); o = random.uniform(-HALF + 2, HALF - 2)
    if any(math.hypot(t - a, o - b) < 1.6 for a, b in bub):
        continue
    bub.append((t, o))
    p = deck_pt(C.MUD, t, o)
    r = random.uniform(0.3, 0.7)
    scen.prism(p, r, 0.14, M["mud2"], n=6, y0=p[1], r_top=r * 0.55)

# ---------------------------------------------------------------- the finish
fin = rp(11, C.FINISH_T, 0, 0)
ck = checker_png("checker", 16, 1024, 128)
ckm = mat("checker", "#ffffff", 0.5, image=ck)
q4 = [(fin[0] - HALF, 0.04, fin[2] - 1.5), (fin[0] + HALF, 0.04, fin[2] - 1.5), (fin[0] + HALF, 0.04, fin[2] + 1.5), (fin[0] - HALF, 0.04, fin[2] + 1.5)]
# (the chequered line is part of the floor now - see deck_piece)
for sd in (-1, 1):
    scen.box((sd * (HALF + 3), 12.5, fin[2]), (2, 25, 2), M["dark"])
    scen.prism((sd * (HALF + 3), 0, fin[2]), 1.6, 1.2, M["gold"], n=8, y0=25)
    col_box((sd * (HALF + 3), 12.5, fin[2]), (2, 25, 2))
scen.box((0, 15.3, fin[2]), (W + 3.9, 1.4, 1.4), M["dark"])
fpng = text_png("sign_finish", "FINISH", 1024, 256, bg="#111111", fg="#ffffff", border="#d9a53b")
scen.sign((0, 20.15, fin[2]), 30, 7.5, 180, mat("sign_finish", "#ffffff", 0.6, image=fpng, emit=0.45, emit_image=True), frame=M["gold"])
scen.sign((0, 13.4, fin[2]), 30, 1.6, 180, ckm, thick=0.2)

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
    scen.box((sd * (HALF + 0.6), 0.56, -4.95), (0.4, 1.12, 5.1), M["concrete"])
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
    scen.box(at(0, 0, -0.05), (22.6, 20.2, 0.1), M["black"], yaw=yaw)
    scen.box(at(0, 10.9, -0.2), (24.6, 0.5, 0.6), M["gold"], yaw=yaw)
    scen.box(at(0, -10.9, -0.2), (24.6, 0.5, 0.6), M["gold"], yaw=yaw)
    scen.sign(at(0, 12.6, -0.2), 16, 2, yaw, stm, two=False, frame=M["gold"])
# station board legs; the zigzag board stands on a tower
for dz in (-9, 9):
    scen.box((-64, 1, 2 + dz), (1.2, 2, 1.2), M["concrete"])
    scen.box((-64.65, 2.5 / 2 + 1, 2 + dz), (0.9, 2.5, 0.9), M["dark"])
scen.prism((180, 0, 90), 3, 36, M["dark"], n=8, y0=0)
scen.prism((180, 0, 90), 4.5, 1, M["concrete"], n=8, y0=0)
scen.box((180, 47, 90), (8, 22, 4.6), M["dark"])
scen.prism((180, 0, 90), 2.0, 1.2, M["gold"], n=8, y0=58)
col_box((180, 18, 90), (6, 36, 6))

# ---------------------------------------------------------------- export
tob = track.obj("track")
sob = scen.obj("scenery")
bevel(sob, 0.05)
print("track tris", tris([tob]), "scenery tris", tris([sob]))
export("mr_track", [tob])
export("mr_scenery", [sob])
cob = colm.obj("collide")
print("collider tris", tris([cob]))
export("mr_collide_raw", [cob])

# ground: grass, a plaza round the station, paving under the zigzag
reset()
g = Mesh()
grass = mat("grass", "#3f5d34", 0.9); plaza = mat("plaza", "#666b75", 0.85); trench = mat("trench", "#2b3038", 0.9)
def quad(x0, x1, z0, z1, y, m):
    if x1 - x0 > 0.01 and z1 - z0 > 0.01:
        g.face([(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)], m, out=(x0, y - 5, z0))
GX0, GX1, GZ0, GZ1 = -160, 400, -360, 440          # the whole ground
PX0, PX1, PZ0, PZ1 = -110, 110, -140, 40           # the plaza round the station
TX, TZ0, TZ1 = C.HALF + 0.4, -100, 12               # where the track runs low: a trench under it
Y0 = -0.04
quad(GX0, GX1, GZ0, PZ0, Y0, grass); quad(GX0, GX1, PZ1, GZ1, Y0, grass)
quad(GX0, PX0, PZ0, PZ1, Y0, grass); quad(PX1, GX1, PZ0, PZ1, Y0, grass)
quad(PX0, -TX, PZ0, PZ1, Y0, plaza); quad(TX, PX1, PZ0, PZ1, Y0, plaza)
quad(-TX, TX, PZ0, TZ0, Y0, plaza); quad(-TX, TX, TZ1, PZ1, Y0, plaza)
quad(-TX, TX, TZ0, TZ1, -0.95, trench)
gob = g.obj("ground")
export("mr_ground", [gob])

json.dump({"boards": BOARDS}, open("/home/claude/mr/out/world.json", "w"))

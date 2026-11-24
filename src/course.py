"""THE GRAND MARBLE RUN - the course, shared by the Blender build and the game.

v3: real marble racing. After the lift hill everything rolls downhill and the
marbles are simulated with physics (walls, slopes, drops, obstacles and each
other). Nothing ever stops them: every obstacle leaves an open path.

Straight runs joined by flat corner squares; in each corner a curved wall
(a quarter circle round the inner corner) swings the marbles round.
Coordinates: x, y (up), z. Ground top is y 0.
"""
import json, math

LANES = 8                           # parking slots at the station / places on the lift
LANE_W = 9.0
HALF = LANES * LANE_W / 2 + 2      # 38: half the deck width
MR = 4.0                            # marble radius
FLOOR_TOP = 1.2                     # riders' floor above the deck
NAMES = ["RUBY", "COBALT", "JADE", "AMBER", "VIOLET", "FROST", "ROSE", "COPPER"]
COLORS = ["#e0233a", "#2a6bff", "#19c37a", "#ffb11a", "#9b4dff", "#8fe3ff", "#ff5fb0", "#d9783a"]

# centreline nodes: x, z, corner?  (heights are worked out below: downhill all the way)
NODES = [
    (0, 0, False),           # 0 STATION (marbles park here)
    (0, 160, False),         # 1 top of the lift hill
    (0, 300, True),          # 2
    (240, 300, True),        # 3
    (240, 150, True),        # 4
    (120, 150, True),        # 5
    (120, 30, True),         # 6
    (240, 30, True),         # 7
    (240, -120, True),       # 8
    (120, -120, True),       # 9
    (120, -240, True),       # 10
    (0, -240, True),         # 11
]
LIFT_TOP = 100.0
# how steeply each run falls (drop per metre); corners all fall CORNER_SLOPE along the middle
SLOPE = {1: 0.12, 2: 0.04, 3: 0.09, 4: 0.08, 5: 0.07, 6: 0.07, 7: 0.07, 8: 0.06, 9: 0.06, 10: 0.06}
CORNER_SLOPE = 0.05
BANK = 20.0                           # how high the corner bowls rise at their outer wall (at the middle of the turn)
LEDGE = 3.0                          # height of each stair drop
STAIRS = (90, 150)                   # where THE STAIRS drop (run 2, centreline distance)
PLUNGE_END = 150                     # THE PLUNGE reaches the ground here (run 11)
FINISH_T = 180                       # the finish line (run 11, z -60)
MUD = 4                              # the run with the mud

# obstacles, in run coordinates: t along the run, u across it (u > 0 = right of travel)
PEGS = [(t, u) for r, t in enumerate((54, 74, 94))
        for u in ((-24, 0, 24) if r % 2 == 0 else (-12, 12))]               # run 3, THE PINBALL
PEG_R = 1.1
FUNNEL = [(42, 38), (70, 17), (80, 17), (108, 38)]                         # run 7: (t, |u|) of each side wall
BUMPERS = [(52, -17, 3.4), (52, 17, 3.4), (68, 0, 3.8)]                    # run 5: t, u, radius
SPLIT = (46, 76)                                                           # run 8: a divider down the middle
SPLIT_R = 0.6

RUNS = ["LIFT HILL", "THE DROP", "THE STAIRS", "THE PINBALL", "THE MUD", "THE BUMPERS",
        "THE SPRINT", "THE FUNNEL", "THE SPLIT", "SKYLINE", "LAST TURN", "THE PLUNGE"]


def unit(dx, dz):
    m = math.hypot(dx, dz)
    return dx / m, dz / m


def normal(d):           # right-hand side of the direction of travel
    return d[1], -d[0]


N = len(NODES)
P = [(n[0], n[1]) for n in NODES]
CORNER = [n[2] for n in NODES]
D = [unit(P[(i + 1) % N][0] - P[i][0], P[(i + 1) % N][1] - P[i][1]) for i in range(N)]   # run i direction
LEN = [math.hypot(P[(i + 1) % N][0] - P[i][0], P[(i + 1) % N][1] - P[i][1]) for i in range(N)]


def runspan(i):
    """the stretch of run i that is its own deck (corner squares excluded)"""
    return (HALF if CORNER[i] else 0.0), (LEN[i] - HALF if CORNER[(i + 1) % N] else LEN[i])


ARC = math.pi / 2 * HALF             # a corner, measured round its middle
# deck heights where each run starts (YS) and ends (YE), and each corner's in/out heights
YS, YE, CIN, COUT = [0.0] * N, [0.0] * N, [0.0] * N, [0.0] * N
YS[0], YE[0] = 0.0, LIFT_TOP
_y = LIFT_TOP
for _i in range(1, N):
    _t0, _t1 = runspan(_i)
    YS[_i] = _y
    if _i == N - 1:
        YE[_i] = 0.0
        break
    _y -= SLOPE[_i] * (_t1 - _t0) + (LEDGE * len(STAIRS) if _i == 2 else 0)
    YE[_i] = _y
    CIN[_i + 1] = _y
    _y -= CORNER_SLOPE * ARC
    COUT[_i + 1] = _y
Y = [YS[i] if not CORNER[i] else (CIN[i] + COUT[i]) / 2 for i in range(N)]   # a height at each node (scenery)


def profile(i):
    """deck height along run i: list of (t, y); two points at one t = a drop"""
    t0, t1 = runspan(i)
    y0, y1 = YS[i], YE[i]
    if i == 0:
        return [(0.0, 0.0), (LEN[0], LIFT_TOP)]
    if i == 2:                                     # gentle slope + two drops
        fall = (y0 - y1) - LEDGE * len(STAIRS)
        pts, ledges = [(t0, y0)], 0
        for s in STAIRS:
            y = y0 - fall * (s - t0) / (t1 - t0) - LEDGE * ledges
            pts += [(s, y), (s, y - LEDGE)]
            ledges += 1
        return pts + [(t1, y1)]
    if i == N - 1:                                 # the plunge, then flat to the station
        return [(t0, y0), (PLUNGE_END, 0.0), (LEN[i], 0.0)]
    return [(t0, y0), (t1, y1)]


def height(i, t):
    pr = profile(i)
    if t <= pr[0][0]:
        return pr[0][1]
    for (ta, ya), (tb, yb) in zip(pr, pr[1:]):
        if ta <= t < tb:
            return ya + (yb - ya) * (t - ta) / (tb - ta) if tb > ta else yb
    return pr[-1][1]


def miter(i):
    """offset direction at node i for a lane: lane point = P + o * miter"""
    di, do = D[(i - 1) % N], D[i]
    ni, no = normal(di), normal(do)
    k = 1 + di[0] * do[0] + di[1] * do[1]
    return ((ni[0] + no[0]) / k, (ni[1] + no[1]) / k)


def lane_off(lane):
    return (lane - (LANES - 1) / 2) * LANE_W


def run_xz(i, t, u):
    d, n = D[i], normal(D[i])
    return [P[i][0] + d[0] * t + n[0] * u, P[i][1] + d[1] * t + n[1] * u]


def run_point(i, t, o, y):
    x, z = run_xz(i, t, o)
    return [x, y, z]


def heading_deg(i):
    return math.degrees(math.atan2(D[i][0], D[i][1]))


def corner(j):
    """corner square at node j: inner corner I, arc radius R round it"""
    din, dout = D[j - 1], D[j]
    px, pz = P[j]
    I = (px - din[0] * HALF + dout[0] * HALF, pz - din[1] * HALF + dout[1] * HALF)
    return {"j": j, "I": I, "R": 2 * HALF, "din": din, "dout": dout, "yin": CIN[j], "yout": COUT[j]}


def corner_height(c, x, z):
    """the corner bowl: falls from yin to yout round the turn, and rises towards the outer wall
    (most at the middle of the turn, not at all where it meets the straight runs)"""
    vx, vz = x - c["I"][0], z - c["I"][1]
    a = math.atan2(vx * c["din"][0] + vz * c["din"][1], -(vx * c["dout"][0] + vz * c["dout"][1]))
    a = max(0.0, min(math.pi / 2, a))
    r = math.hypot(vx, vz)
    return c["yin"] + (c["yout"] - c["yin"]) * a / (math.pi / 2) + BANK * math.sin(2 * a) * (min(r, c["R"]) / c["R"]) ** 2.5


def r2(v):
    return [round(a, 3) for a in v]


def sections():
    """what the simulation rolls on, in order from the top of the lift to the station"""
    out = []
    for i in range(1, N):
        t0, t1 = runspan(i)
        d, n = D[i], normal(D[i])
        walls, circles = [], []           # walls: x1 z1 x2 z2 ; circles: x z r bounce
        for side in (-1, 1):
            a, b = run_xz(i, t0, side * HALF), run_xz(i, t1 + (8 if i == N - 1 else 0), side * HALF)
            walls.append(r2(a + b))
        if i == N - 1:                     # the buffer behind the station slots
            walls.append(r2(run_xz(i, LEN[i] + MR + 0.6, -HALF) + run_xz(i, LEN[i] + MR + 0.6, HALF)))
        if i == 3:
            circles += [r2(run_xz(i, t, u) + [PEG_R, 0.55]) for t, u in PEGS]
        if i == 7:
            for side in (-1, 1):
                pts = [run_xz(i, t, side * u) for t, u in FUNNEL]
                walls += [r2(a + b) for a, b in zip(pts, pts[1:])]
        if i == 5:
            circles += [r2(run_xz(i, t, u) + [r, 0.85]) for t, u, r in BUMPERS]
        if i == 8:
            walls.append(r2(run_xz(i, SPLIT[0], 0) + run_xz(i, SPLIT[1], 0)))
            circles += [r2(run_xz(i, t, 0) + [SPLIT_R, 0.5]) for t in SPLIT]
        out.append({"type": "run", "i": i, "P": list(P[i]), "d": list(d), "n": list(n), "t0": t0, "t1": t1,
                    "prof": [r2(p) for p in profile(i)], "mu": 0.025 if i == MUD else 0.012,
                    "walls": walls, "circles": circles, "name": RUNS[i]})
        if i + 1 < N and CORNER[i + 1]:
            c = corner(i + 1)
            out.append({"type": "corner", "j": i + 1, "P": list(P[i + 1]), "I": r2(c["I"]), "R": c["R"],
                        "din": list(c["din"]), "dout": list(c["dout"]), "yin": round(c["yin"], 3), "yout": round(c["yout"], 3),
                        "bank": BANK})
    return out


def export():
    homes = [r2(run_point(0, 0, lane_off(k), 0)) for k in range(LANES)]
    tops = [r2(run_point(0, LEN[0], lane_off(k), LIFT_TOP)) for k in range(LANES)]
    return {
        "names": NAMES, "colors": COLORS, "runs": RUNS, "mr": MR, "floor_top": FLOOR_TOP, "half": HALF,
        "heading": [round(heading_deg(i), 3) for i in range(N)], "dirs": [list(D[i]) for i in range(N)],
        "runlen": [round(l, 3) for l in LEN], "homes": homes, "tops": tops,
        "sections": sections(), "finish": {"i": N - 1, "t": FINISH_T, "z": run_point(N - 1, FINISH_T, 0, 0)[2]},
        "plunge_end": PLUNGE_END,
    }


if __name__ == "__main__":
    data = export()
    json.dump(data, open("course.json", "w"))
    print(len(data["sections"]), "sections;", "homes", data["homes"][0], "->", data["tops"][0], "finish", data["finish"])

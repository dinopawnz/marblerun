"""THE GRAND MARBLE RUN v4 - the course, shared by the Blender build, the physics and the game.

A 2.7 km downhill run after a 150 m lift hill. Straight runs joined by banked corner bowls.
Every run has its own feature; nothing ever stops a marble (every obstacle leaves an open path).
Coordinates: x, y (up), z. Ground top is y 0. Runs are axis-aligned.
"""
import json, math

LANES = 8                           # parking slots at the station / places on the lift
LANE_W = 9.0
HALF = LANES * LANE_W / 2 + 2      # 38: half the deck width
MR = 4.0                            # marble radius
FLOOR_TOP = 1.2                     # riders' floor above the deck
NAMES = ["RUBY", "COBALT", "JADE", "AMBER", "VIOLET", "FROST", "ROSE", "COPPER"]
COLORS = ["#ff2d55", "#2f7bff", "#19e68c", "#ffb020", "#a24dff", "#5ff2ff", "#ff5fc8", "#ff7a2e"]

# centreline nodes: x, z, corner?
NODES = [
    (0, 0, False),           # 0  STATION (marbles park here)
    (0, 220, False),         # 1  top of the lift hill
    (0, 420, True),          # 2
    (300, 420, True),        # 3
    (300, 220, True),        # 4
    (520, 220, True),        # 5
    (520, -60, True),        # 6
    (320, -60, True),        # 7
    (320, -260, True),       # 8
    (120, -260, True),       # 9
    (120, -480, True),       # 10
    (-140, -480, True),      # 11
    (-140, -280, True),      # 12
    (0, -280, True),         # 13
]
# what each run is (index = run number; run i goes from node i to node i+1)
KIND = ["lift", "drop", "waves", "pinball", "jump", "bumpers", "tunnel", "funnel", "stairs", "split", "swamp", "forest", "last", "plunge"]
RUNS = ["LIFT HILL", "THE DROP", "THE WAVES", "THE PINBALL", "THE JUMP", "THE BUMPERS", "THE GLOW TUNNEL",
        "THE FUNNEL", "THE STAIRS", "THE SPLIT", "THE SWAMP", "CRYSTAL FOREST", "LAST TURN", "THE PLUNGE"]
LIFT_TOP = 176.0
# drop per metre along each run (features add their own drops); corners fall CORNER_SLOPE round the middle
SLOPE = {"drop": 0.12, "waves": 0.05, "pinball": 0.085, "jump": 0.09, "bumpers": 0.065, "tunnel": 0.05, "funnel": 0.065,
         "stairs": 0.035, "split": 0.05, "swamp": 0.065, "forest": 0.075, "last": 0.05}
CORNER_SLOPE = 0.04
BANK = 20.0                          # how high the corner bowls rise at their outer wall (at the middle of the turn)
LEDGE = 3.0
STAIRS = (60, 100, 140)              # stair drops (distance from the start of the run's deck)
WAVE_A, WAVE_L = 0.8, 36.0           # the waves: height and length of each roller
JUMP_UP, JUMP_AT, JUMP_LEN, JUMP_DROP = 1.0, 80.0, 9.0, 5.0   # kicker: rises JUMP_UP over JUMP_LEN, lip at JUMP_AT, then a JUMP_DROP fall
PLUNGE_END = 190                     # THE PLUNGE reaches the ground here (run 13, centreline distance)
FINISH_T = 220                       # the finish line (run 13, z -60)
MUD_MU = 0.025

# obstacles, in run coordinates: s = distance from the start of the run's deck, u = across (u > 0: right of travel)
PEGS = [(s, u) for r, s in enumerate((26, 54, 82, 108)) for u in ((-24, 0, 24) if r % 2 == 0 else (-12, 12))]   # THE PINBALL
PEG_R = 1.2
FOREST = [(s, u) for r, s in enumerate((24, 56, 88)) for u in ((-20, 20) if r % 2 == 0 else (-26, 0, 26))]        # CRYSTAL FOREST
FOREST_R = 1.3
BUMPERS = [(44, -18, 3.0), (44, 18, 3.0), (74, 0, 3.4), (128, -20, 3.0), (128, 20, 3.0)]                 # THE BUMPERS
FUNNEL = [(10, 38), (48, 16), (62, 16), (100, 38)]                                                                       # THE FUNNEL: (s, |u|)
SPLIT = (20, 120)                                                                                                        # THE SPLIT
SPLIT_R = 0.7


def unit(dx, dz):
    m = math.hypot(dx, dz)
    return dx / m, dz / m


def normal(d):           # right-hand side of the direction of travel
    return d[1], -d[0]


N = len(NODES)
P = [(n[0], n[1]) for n in NODES]
CORNER = [n[2] for n in NODES]
D = [unit(P[(i + 1) % N][0] - P[i][0], P[(i + 1) % N][1] - P[i][1]) for i in range(N)]
LEN = [math.hypot(P[(i + 1) % N][0] - P[i][0], P[(i + 1) % N][1] - P[i][1]) for i in range(N)]


def runspan(i):
    """the stretch of run i that is its own deck (corner squares excluded)"""
    return (HALF if CORNER[i] else 0.0), (LEN[i] - HALF if CORNER[(i + 1) % N] else LEN[i])


ARC = math.pi / 2 * HALF


def _feature_profile(i, t0, t1, y0):
    """the deck height along run i from y0, before the general slope is known: list of (t, y)"""
    k, s = KIND[i], SLOPE.get(KIND[i], 0.05)
    L = t1 - t0
    if k == "stairs":
        pts, y = [(t0, y0)], y0
        for st in STAIRS:
            y = y0 - s * st - LEDGE * len([q for q in STAIRS if q < st])
            pts += [(t0 + st, y), (t0 + st, y - LEDGE)]
        return pts + [(t1, y0 - s * L - LEDGE * len(STAIRS))]
    if k == "waves":
        n = int(L / 3)
        return [(t0 + L * q / n, y0 - s * L * q / n + WAVE_A * (1 - math.cos(2 * math.pi * (L * q / n) / WAVE_L)) * min(1, L * q / n / 10, (L - L * q / n) / 10) * -1)
                for q in range(n + 1)]
    if k == "jump":
        a = t0 + JUMP_AT - JUMP_LEN
        ya = y0 - s * (a - t0)
        lip = ya + JUMP_UP
        land = lip - JUMP_DROP - JUMP_UP
        return [(t0, y0), (a, ya), (t0 + JUMP_AT, lip), (t0 + JUMP_AT, land), (t1, land - s * (t1 - t0 - JUMP_AT))]
    return [(t0, y0), (t1, y0 - s * L)]


# deck heights: where each run starts/ends, and each corner's in/out heights
YS, YE, CIN, COUT = [0.0] * N, [0.0] * N, [0.0] * N, [0.0] * N
PROF = [None] * N
YS[0], YE[0] = 0.0, LIFT_TOP
PROF[0] = [(0.0, 0.0), (LEN[0], LIFT_TOP)]
_y = LIFT_TOP
for _i in range(1, N):
    _t0, _t1 = runspan(_i)
    YS[_i] = _y
    if KIND[_i] == "plunge":
        PROF[_i] = [(_t0, _y), (PLUNGE_END, 0.0), (LEN[_i], 0.0)]
        YE[_i] = 0.0
        break
    PROF[_i] = _feature_profile(_i, _t0, _t1, _y)
    _y = PROF[_i][-1][1]
    YE[_i] = _y
    CIN[_i + 1] = _y
    _y -= CORNER_SLOPE * ARC
    COUT[_i + 1] = _y
Y = [YS[i] if not CORNER[i] else (CIN[i] + COUT[i]) / 2 for i in range(N)]


def profile(i):
    return PROF[i]


def height(i, t):
    pr = PROF[i]
    if t <= pr[0][0]:
        return pr[0][1]
    for (ta, ya), (tb, yb) in zip(pr, pr[1:]):
        if ta <= t < tb:
            return ya + (yb - ya) * (t - ta) / (tb - ta) if tb > ta else yb
    return pr[-1][1]


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
    din, dout = D[j - 1], D[j]
    px, pz = P[j]
    I = (px - din[0] * HALF + dout[0] * HALF, pz - din[1] * HALF + dout[1] * HALF)
    return {"j": j, "I": I, "R": 2 * HALF, "din": din, "dout": dout, "yin": CIN[j], "yout": COUT[j]}


def corner_angle(c, x, z):
    vx, vz = x - c["I"][0], z - c["I"][1]
    a = math.atan2(vx * c["din"][0] + vz * c["din"][1], -(vx * c["dout"][0] + vz * c["dout"][1]))
    return max(0.0, min(math.pi / 2, a)), math.hypot(vx, vz)


def corner_height(c, x, z):
    a, r = corner_angle(c, x, z)
    return c["yin"] + (c["yout"] - c["yin"]) * a / (math.pi / 2) + BANK * math.sin(2 * a) * (min(r, c["R"]) / c["R"]) ** 2.5


def corner_point(c, a, r, dy=0.0):
    I, din, dout = c["I"], c["din"], c["dout"]
    x = I[0] + (-dout[0] * math.cos(a) + din[0] * math.sin(a)) * r
    z = I[1] + (-dout[1] * math.cos(a) + din[1] * math.sin(a)) * r
    return (x, corner_height(c, x, z) + dy, z)


def r2(v):
    return [round(a, 3) for a in v]


def sections():
    out = []
    for i in range(1, N):
        t0, t1 = runspan(i)
        d, n = D[i], normal(D[i])
        k = KIND[i]
        walls, circles = [], []
        for side in (-1, 1):
            a, b = run_xz(i, t0, side * HALF), run_xz(i, t1 + (8 if k == "plunge" else 0), side * HALF)
            walls.append(r2(a + b))
        if k == "plunge":
            walls.append(r2(run_xz(i, LEN[i] + MR + 0.6, -HALF) + run_xz(i, LEN[i] + MR + 0.6, HALF)))
        if k == "pinball":
            circles += [r2(run_xz(i, t0 + s, u) + [PEG_R, 0.55]) for s, u in PEGS]
        if k == "forest":
            circles += [r2(run_xz(i, t0 + s, u) + [FOREST_R, 0.5]) for s, u in FOREST]
        if k == "bumpers":
            circles += [r2(run_xz(i, t0 + s, u) + [r, 1.0]) for s, u, r in BUMPERS]
        if k == "funnel":
            for side in (-1, 1):
                pts = [run_xz(i, t0 + s, side * u) for s, u in FUNNEL]
                walls += [r2(a + b) for a, b in zip(pts, pts[1:])]
        if k == "split":
            walls.append(r2(run_xz(i, t0 + SPLIT[0], 0) + run_xz(i, t0 + SPLIT[1], 0)))
            circles += [r2(run_xz(i, t0 + s, 0) + [SPLIT_R, 0.5]) for s in SPLIT]
        out.append({"type": "run", "i": i, "P": list(P[i]), "d": list(d), "n": list(n), "t0": t0, "t1": t1,
                    "prof": [r2(p) for p in profile(i)], "mu": MUD_MU if k == "swamp" else 0.012,
                    "walls": walls, "circles": circles, "name": RUNS[i], "kind": k})
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
        "names": NAMES, "colors": COLORS, "runs": RUNS, "kinds": KIND, "mr": MR, "floor_top": FLOOR_TOP, "half": HALF,
        "heading": [round(heading_deg(i), 3) for i in range(N)], "dirs": [list(D[i]) for i in range(N)],
        "runlen": [round(l, 3) for l in LEN], "homes": homes, "tops": tops, "lift_len": LEN[0],
        "sections": sections(), "finish": {"i": N - 1, "t": FINISH_T, "z": run_point(N - 1, FINISH_T, 0, 0)[2]},
        "plunge_end": PLUNGE_END,
    }


if __name__ == "__main__":
    data = export()
    json.dump(data, open("course.json", "w"))
    print(len(data["sections"]), "sections; plunge from", round(YS[N - 1], 1), "finish", data["finish"])
    for i in range(1, N):
        print(i, RUNS[i], round(runspan(i)[1] - runspan(i)[0]), "m, y", round(YS[i], 1), "->", round(YE[i], 1))

"""THE GRAND MARBLE RUN - the course, shared by the Blender build and the game.

Straight runs joined by square corners. Every marble moves in its own lane
as a chain of straight glides (one dated glide per stretch - the proven way
to carry riders in Otherside). Heights only change in the middle of a run,
so every corner square is flat.
Coordinates: x, y (up), z. Ground top is y 0.
"""
import json, math

LANES = 8
LANE_W = 9.0
HALF = LANES * LANE_W / 2 + 2      # 38: half the deck width
MR = 4.0                            # marble radius
FLOOR_TOP = 1.2                     # riders' floor above the deck
NAMES = ["RUBY", "COBALT", "JADE", "AMBER", "VIOLET", "FROST", "ROSE", "COPPER"]
COLORS = ["#e0233a", "#2a6bff", "#19c37a", "#ffb11a", "#9b4dff", "#8fe3ff", "#ff5fb0", "#d9783a"]

# centreline nodes: x, z, deck height, corner?
NODES = [
    (0, 0, 0, False),        # 0 STATION (marbles park here)
    (0, 160, 70, False),     # 1 top of the lift hill
    (0, 300, 52, True),      # 2
    (240, 300, 44, True),    # 3
    (240, 150, 44, True),    # 4
    (120, 150, 44, True),    # 5
    (120, 30, 36, True),     # 6
    (240, 30, 36, True),     # 7
    (240, -120, 46, True),   # 8
    (120, -120, 46, True),   # 9
    (120, -240, 46, True),   # 10
    (0, -240, 46, True),     # 11
]
# each run, from node i to node i+1: a name and its steps.
# ("to", t, y, kind)  glide to centreline distance t at height y. t "END" = the lane's corner point.
# ("hold", id)        wait here (an obstacle decides how long)
STOP = MR + 0.6                      # a marble stops this far short of a gate
RUNS = [
    ("LIFT HILL", [("to", "END", 70, "lift")]),
    ("THE DROP", [("to", 102, 52, "slope"), ("to", "END", 52, "roll")]),
    ("THE STAIRS", [("to", 90, 52, "roll"), ("to", 97, 48, "ramp"), ("to", 150, 48, "roll"), ("to", 157, 44, "ramp"), ("to", "END", 44, "roll")]),
    ("THE GATES", [("to", 75 - STOP, 44, "roll"), ("hold", "gates"), ("to", "END", 44, "roll")]),
    ("THE MUD", [("to", "END", 44, "mud")]),
    ("THE TRAPDOORS", [("to", 60, 44, "roll"), ("hold", "trap"), ("to", 60, 36, "drop"), ("to", "END", 36, "roll")]),
    ("THE SPRINT", [("to", "END", 36, "roll")]),
    ("THE ELEVATORS", [("to", 75, 36, "roll"), ("hold", "lift"), ("to", 75, 46, "rise"), ("to", "END", 46, "roll")]),
    ("THE HIGH ROAD", [("to", "END", 46, "roll")]),
    ("SKYLINE", [("to", "END", 46, "roll")]),
    ("LAST TURN", [("to", "END", 46, "roll")]),
    ("THE PLUNGE", [("to", 45.4, 46, "roll"), ("hold", "last"), ("to", 170, 0, "plunge"), ("to", "END", 0, "brake")]),
]
FINISH_T = 180          # on the last run (z -60)
GATE_T = 75             # on THE GATES
LAST_GATE_T = 50        # on THE PLUNGE
TRAP_T = 60
ELEV_T = 75


def unit(dx, dz):
    m = math.hypot(dx, dz)
    return dx / m, dz / m


def normal(d):           # right-hand side of the direction of travel
    return d[1], -d[0]


N = len(NODES)
P = [(n[0], n[1]) for n in NODES]
Y = [n[2] for n in NODES]
D = [unit(P[(i + 1) % N][0] - P[i][0], P[(i + 1) % N][1] - P[i][1]) for i in range(N)]   # run i direction
LEN = [math.hypot(P[(i + 1) % N][0] - P[i][0], P[(i + 1) % N][1] - P[i][1]) for i in range(N)]


def miter(i):
    """offset direction at node i for a lane: lane point = P + o * miter"""
    di, do = D[(i - 1) % N], D[i]
    ni, no = normal(di), normal(do)
    k = 1 + di[0] * do[0] + di[1] * do[1]
    return ((ni[0] + no[0]) / k, (ni[1] + no[1]) / k)


def lane_off(lane):
    return (lane - (LANES - 1) / 2) * LANE_W


def run_point(i, t, o, y):
    d, n = D[i], normal(D[i])
    return [P[i][0] + d[0] * t + n[0] * o, y, P[i][1] + d[1] * t + n[1] * o]


def lane_t_range(i, o):
    """where a lane enters and leaves run i, in centreline distance"""
    d = D[i]
    ma, mb = miter(i), miter((i + 1) % N)
    a = (o * ma[0] * d[0] + o * ma[1] * d[1])
    b = LEN[i] + (o * mb[0] * d[0] + o * mb[1] * d[1])
    return a, b


def lane_glides(lane):
    """every glide of one marble's lap, in order"""
    o = lane_off(lane)
    out = []
    for i, (name, steps) in enumerate(RUNS):
        ta, tb = lane_t_range(i, o)
        t, y = ta, Y[i]
        m = 0.0                       # the same stretch measured down the middle (corner to corner)
        hold = None
        for s in steps:
            if s[0] == "hold":
                hold = s[1]
                continue
            t2 = tb if s[1] == "END" else s[1]
            m2 = LEN[i] if s[1] == "END" else s[1]
            y2 = s[2]
            a, b = run_point(i, t, o, y), run_point(i, t2, o, y2)
            out.append({"a": [round(v, 3) for v in a], "b": [round(v, 3) for v in b], "kind": s[3],
                        "hold": hold, "run": i, "t0": round(m, 3), "t1": round(m2, 3)})
            hold = None
            t, y, m = t2, y2, m2
    return out


def heading_deg(i):
    return math.degrees(math.atan2(D[i][0], D[i][1]))


def export():
    lanes = [lane_glides(k) for k in range(LANES)]
    fin = []
    for k in range(LANES):
        fin.append(run_point(N - 1, FINISH_T, lane_off(k), 0))
    return {
        "lanes": lanes, "names": NAMES, "colors": COLORS, "runs": [r[0] for r in RUNS],
        "heading": [round(heading_deg(i), 3) for i in range(N)],
        "finish_t": FINISH_T, "mr": MR, "floor_top": FLOOR_TOP,
        "gates": [run_point(3, GATE_T, lane_off(k), 44) for k in range(LANES)],
        "last_gates": [run_point(N - 1, LAST_GATE_T, lane_off(k), 46 - (LAST_GATE_T - 45.4) * 46 / (170 - 45.4)) for k in range(LANES)],
        "traps": [run_point(5, TRAP_T, lane_off(k), 44) for k in range(LANES)],
        "elevs": [run_point(7, ELEV_T, lane_off(k), 36) for k in range(LANES)],
        "dirs": [list(D[i]) for i in range(N)],
        "half": HALF, "runlen": [round(l, 3) for l in LEN],
    }


if __name__ == "__main__":
    data = export()
    json.dump(data, open("course.json", "w"))
    for k in (0, 7):
        g = data["lanes"][k]
        print("lane", k, "glides", len(g), "start", g[0]["a"], "end", g[-1]["b"])

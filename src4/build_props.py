"""Exports the reusable props (each its own model, placed many times by the game) and a contact-sheet render."""
import bpy, sys, math, random
sys.path.insert(0, "/home/claude/mr4")
import b4
from b4 import Mesh, export, reset, tris, rig
import assets4 as A

PROPS = {}


def start():
    reset()
    ms = A.M()
    A.M_stem[0], A.M_stem[1] = ms["stem"], ms["gill"]
    return ms


def save(name, me, anim=None):
    o = me.obj(name)
    objs = [o]
    if anim:
        bones, keys, length = anim
        ao = rig(o, bones, keys, length=length)
        objs = [ao]
    export(name, objs, anim=bool(anim))
    PROPS[name] = tris([o])
    print("  ", name, PROPS[name], "tris")


def sway(bones, amp=6, length=96, phase=0):
    """a gentle looping sway for a list of upright bones (each tips a little more than the one below)"""
    keys = {}
    for i, (bn, *_ ) in enumerate(bones):
        a = amp * (0.5 + 0.5 * i / max(1, len(bones) - 1))
        keys[bn] = [(f, (a * math.sin(6.283 * f / length + i * 0.6 + phase), 0, a * 0.6 * math.cos(6.283 * f / length + i * 0.5 + phase)), (0, 0, 0)) for f in range(0, length + 1, 8)]
    return keys


def chain(h, n, x=0.0, z=0.0, prefix="b"):
    out, prev = [], None
    for i in range(n):
        y0, y1 = h * i / n, h * (i + 1) / n
        out.append((prefix + str(i), (x, y0, z), (x, y1, z), prev))
        prev = prefix + str(i)
    return out


which = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["all"]

# --- giant mushrooms (scenery), three colours, swaying slowly
for name, capm, h, r, seed in (("mr4_mush_m", "capm", 16, 8, 1), ("mr4_mush_c", "capc", 12, 6.5, 2), ("mr4_mush_l", "capl", 9, 5, 3)):
    ms = start(); me = Mesh()
    A.mushroom(me, (0, 0, 0), h, r, ms[capm], seed=seed)
    bones = chain(h * 1.05, 3)
    save(name, me, (bones, sway(bones, 3.5), 96))

# --- bumper mushrooms (on the track: the stem is what marbles hit; the cap is above them)
for name, capm, r, seed in (("mr4_bumper_a", "capm", 3.0, 11), ("mr4_bumper_b", "capc", 3.4, 12)):
    ms = start(); me = Mesh()
    A.mushroom(me, (0, 0, 0), 13, r * 2.1, ms[capm], seed=seed, bend=0.0, stem_r=r / 1.5)
    # a glowing bounce ring round the stem at marble height
    path = [(r * 1.02 * math.sin(k / 32 * 6.283), 3.0, r * 1.02 * math.cos(k / 32 * 6.283)) for k in range(33)]
    me.sweep(path, [(0.35 * math.cos(k / 8 * 6.283), 0.35 * math.sin(k / 8 * 6.283)) for k in range(8)], ms["glowm"] if capm == "capm" else ms["glowc"])
    path = [(r * 1.02 * math.sin(k / 32 * 6.283), 1.2, r * 1.02 * math.cos(k / 32 * 6.283)) for k in range(33)]
    me.sweep(path, [(0.3 * math.cos(k / 8 * 6.283), 0.3 * math.sin(k / 8 * 6.283)) for k in range(8)], ms["glowg"])
    save(name, me)

# --- spiral ferns (sway)
for name, leaf, h, seed in (("mr4_fern_g", "leafg", 9, 4), ("mr4_fern_v", "leafv", 7, 5)):
    ms = start(); me = Mesh()
    A.fern(me, (0, 0, 0), h, ms[leaf], seed=seed)
    A.fern(me, (1.2, 0, 0.8), h * 0.8, ms[leaf], seed=seed + 10)
    A.fern(me, (-1.0, 0, 0.9), h * 0.65, ms[leaf], seed=seed + 20)
    bones = chain(h * 1.1, 3)
    save(name, me, (bones, sway(bones, 7, 72), 72))

# --- leaf beds
for name, leaf, h, seed in (("mr4_fronds_g", "leafg", 4, 6), ("mr4_fronds_v", "leafv", 3.4, 7)):
    ms = start(); me = Mesh()
    A.frond_plant(me, (0, 0, 0), h, ms[leaf], n=11, seed=seed)
    A.frond_plant(me, (1.6, 0, -0.8), h * 0.7, ms[leaf], n=8, seed=seed + 1)
    bones = chain(h, 2)
    save(name, me, (bones, sway(bones, 5, 64), 64))

# --- crystal clusters (static)
for name, cm, s, seed in (("mr4_crystals_c", "cry", 11, 21), ("mr4_crystals_p", "cryp", 9, 22), ("mr4_crystals_g", "cryg", 7, 23)):
    ms = start(); me = Mesh()
    A.crystal_cluster(me, (0, 0, 0), s, ms[cm], seed=seed, n=9)
    save(name, me)

# --- spirit willow (strands sway)
ms = start(); me = Mesh()
A.willow(me, (0, 0, 0), 30, ms, seed=31)
bones = chain(30, 3)
save("mr4_willow", me, (bones, sway(bones, 2.5, 120), 120))

# --- floating islands (bob and turn slowly)
for name, r, seed in (("mr4_island_a", 9, 41), ("mr4_island_b", 6, 42)):
    ms = start(); me = Mesh()
    A.island(me, (0, 0, 0), r, ms, seed=seed)
    bones = [("root", (0, -r * 1.6, 0), (0, r, 0), None)]
    keys = {"root": [(f, (0, 25 * math.sin(6.283 * f / 192), 0), (0, 1.4 * math.sin(6.283 * f / 192), 0)) for f in range(0, 193, 12)]}
    save(name, me, (bones, keys, 192))

# --- jellyfish lanterns (bob, tentacles wave)
for name, r, seed in (("mr4_jelly_a", 2.2, 51), ("mr4_jelly_b", 1.5, 52)):
    ms = start(); me = Mesh()
    A.jelly(me, (0, 0, 0), r, ms, seed=seed)
    bones = [("bell", (0, 0, 0), (0, r, 0), None), ("t0", (0, 0, 0), (0, -r * 1.3, 0), "bell"), ("t1", (0, -r * 1.3, 0), (0, -r * 2.8, 0), "t0")]
    L = 72
    keys = {"bell": [(f, (0, 0, 0), (0, 0.8 * math.sin(6.283 * f / L), 0)) for f in range(0, L + 1, 6)],
            "t0": [(f, (8 * math.sin(6.283 * f / L + 1), 0, 6 * math.cos(6.283 * f / L)), (0, 0, 0)) for f in range(0, L + 1, 6)],
            "t1": [(f, (14 * math.sin(6.283 * f / L + 2), 0, 10 * math.cos(6.283 * f / L + 1)), (0, 0, 0)) for f in range(0, L + 1, 6)]}
    save(name, me, (bones, keys, L))

print("PROPS", PROPS)

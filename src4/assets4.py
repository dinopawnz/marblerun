"""The v4 prop library: every shape here is grown from curves (lathes, sweeps, lofts, shards) -
no boxes, no plain cylinders. Each function adds to a Mesh at a given place, in MML coordinates."""
import math, random
from b4 import Mesh, mat


def M():
    return {
        "deck": mat("deck", "deck", emit=1.6, rough=0.25, metal=0.3),
        "bowl": mat("bowl", "bowl", emit=1.6, rough=0.25, metal=0.3),
        "lift": mat("liftdeck", "lift", emit=0.7, rough=0.3, metal=0.3),
        "hull": mat("hull", "bark_pink", emit=1.6, rough=0.6),
        "cry": mat("cry_cyan", "crystal_cyan", emit=1.3, rough=0.15, metal=0.1),
        "cryp": mat("cry_pink", "crystal_pink", emit=1.3, rough=0.15, metal=0.1),
        "cryg": mat("cry_gold", "crystal_gold", emit=1.3, rough=0.15, metal=0.2),
        "bark": mat("bark", "bark", emit=1.8, rough=0.7),
        "barkp": mat("bark_pink", "bark_pink", emit=1.0, rough=0.7),
        "capm": mat("cap_m", "cap_magenta", emit=1.4, rough=0.4),
        "capc": mat("cap_c", "cap_cyan", emit=1.4, rough=0.4),
        "capl": mat("cap_l", "cap_lime", emit=1.4, rough=0.4),
        "gill": mat("gill", color="#2a1440", emit=0.6, emit_color="#ff6ad8", rough=0.6),
        "stem": mat("stem", "stem", emit=1.0, rough=0.5),
        "leafg": mat("leaf_g", "leaf_green", emit=1.2, rough=0.5),
        "leafv": mat("leaf_v", "leaf_violet", emit=1.2, rough=0.5),
        "rock": mat("rock", "stone", emit=1.3, rough=0.85),
        "moss": mat("moss", "ground", emit=1.0, rough=0.9),
        "rain": mat("rain", "rainbow", emit=2.2, rough=0.3),
        "water": mat("swamp", "swamp", emit=1.2, rough=0.1, metal=0.2),
        "tiles": mat("tiles", "tiles", emit=1.2, rough=0.3, metal=0.2),
        "gold": mat("gold4", color="#ffcf6a", emit=0.25, emit_color="#ffb030", rough=0.25, metal=1.0),
        "dark": mat("dark4", color="#141028", rough=0.5, metal=0.4),
        "white": mat("pearl", color="#f4eeff", emit=0.4, emit_color="#d8c8ff", rough=0.3, metal=0.2),
        "glowc": mat("glow_cyan", color="#5ff2ff", emit=3.0),
        "glowm": mat("glow_mag", color="#ff4fd8", emit=3.0),
        "glowg": mat("glow_gold", color="#ffd36b", emit=3.0),
        "glowl": mat("glow_lime", color="#b6ff5a", emit=3.0),
        "jelly": mat("jelly", color="#8fd8ff", emit=1.6, emit_color="#7fe8ff", rough=0.1, alpha=0.55),
        "checker": mat("checker4", "checker", emit=0.8, rough=0.4),
    }


def ring(c, r, n, y=0.0, ry=0.0, sx=1.0, sz=1.0):
    return [(c[0] + r * sx * math.sin(k / n * 6.283 + ry), c[1] + y, c[2] + r * sz * math.cos(k / n * 6.283 + ry)) for k in range(n)]


def shard(me, base, h, r, m, lean=(0, 0), sides=6, seed=0, tip=0.25):
    """one crystal: a faceted prism with a pointed, slightly skewed tip"""
    rnd = random.Random(seed)
    lx, lz = lean
    rings = []
    rot = rnd.random() * 6.283
    for f, rr in ((0.0, r), (0.06, r * 1.04), (1 - tip, r * 0.92), (1.0, 0.0001)):
        y = h * f
        c = (base[0] + lx * y, base[1] + y, base[2] + lz * y)
        rings.append([(c[0] + rr * (0.85 + 0.3 * ((k * 37 + seed) % 7) / 7) * math.sin(k / sides * 6.283 + rot),
                       c[1] + (rnd.uniform(-0.1, 0.1) * h * tip if f == 1.0 else 0),
                       c[2] + rr * (0.85 + 0.3 * ((k * 53 + seed) % 7) / 7) * math.cos(k / sides * 6.283 + rot)) for k in range(sides)])
    me.tube(rings, m, vrep=1.0, urep=1.0, cap0=m)


def crystal_cluster(me, c, size, m, seed=0, n=7):
    rnd = random.Random(seed)
    shard(me, c, size * 1.0, size * 0.16, m, (rnd.uniform(-0.1, 0.1), rnd.uniform(-0.1, 0.1)), seed=seed)
    for k in range(n - 1):
        a = rnd.random() * 6.283; d = size * rnd.uniform(0.1, 0.28)
        lean = (math.sin(a) * rnd.uniform(0.25, 0.6), math.cos(a) * rnd.uniform(0.25, 0.6))
        shard(me, (c[0] + math.sin(a) * d, c[1] - 0.1, c[2] + math.cos(a) * d), size * rnd.uniform(0.35, 0.75), size * rnd.uniform(0.07, 0.12), m, lean, seed=seed + k + 1)


def crystal_spire(me, c, size, m, R, seed=0, n=5):
    """a tight cluster of tall crystals, all inside radius R of the axis (what the marbles bounce off)"""
    rnd = random.Random(seed)
    shard(me, c, size, R * 0.78, m, (0, 0), seed=seed, sides=6, tip=0.3)
    for k in range(n - 1):
        a = k / (n - 1) * 6.283 + rnd.uniform(-0.3, 0.3)
        d, r = R * 0.5, R * 0.36
        shard(me, (c[0] + math.sin(a) * d, c[1] - 0.05, c[2] + math.cos(a) * d), size * rnd.uniform(0.45, 0.75), r, m, (0, 0), seed=seed + k + 1, sides=5, tip=0.35)


def mushroom(me, c, h, cap_r, capm, seed=0, bend=0.6, stem_r=None, gills=True):
    """a giant glowing mushroom: a curved stem and a domed cap with gills underneath"""
    rnd = random.Random(seed)
    sr = stem_r or cap_r * 0.16
    a = rnd.random() * 6.283
    bx, bz = math.sin(a) * bend, math.cos(a) * bend
    n = 18
    rings = []
    for q in range(9):
        f = q / 8
        y = h * 0.92 * f
        off = (bx * math.sin(f * 2.4) * h * 0.08, bz * math.sin(f * 2.4) * h * 0.08)
        rr = sr * (1.5 - 0.5 * f + 0.15 * math.sin(f * 9)) if q else sr * 1.9
        rings.append(ring((c[0] + off[0], c[1] + y, c[2] + off[1]), rr, n))
    me.tube(rings, M_stem[0], vrep=3, urep=2)
    top = (c[0] + bx * math.sin(2.4) * h * 0.08, c[1] + h * 0.9, c[2] + bz * math.sin(2.4) * h * 0.08)
    # cap: outer dome
    prof = [(cap_r * 1.0, 0.0), (cap_r * 0.98, cap_r * 0.12), (cap_r * 0.86, cap_r * 0.3), (cap_r * 0.62, cap_r * 0.48), (cap_r * 0.32, cap_r * 0.58), (cap_r * 0.02, cap_r * 0.62)]
    me.lathe(prof, capm, c=top, seg=28, vrep=1, urep=2, wobble=0.05, seed=seed)
    # underside (gills): a shallow cone back to the stem
    under = [(sr * 1.2, -cap_r * 0.05), (cap_r * 0.5, -cap_r * 0.01), (cap_r * 1.0, 0.0)]
    me.lathe(under, M_stem[1] if gills else capm, c=top, seg=28, wobble=0.05, seed=seed)


M_stem = [None, None]


def fern(me, c, h, m, seed=0, curl=1.4):
    """a Pandora spiral fern: a stem that rises and curls into a spiral, leaflets down both sides"""
    rnd = random.Random(seed)
    a = rnd.random() * 6.283
    dx, dz = math.sin(a), math.cos(a)
    path = []
    for q in range(40):
        f = q / 39
        if f < 0.6:
            g = f / 0.6
            p = (c[0] + dx * g * h * 0.15, c[1] + g * h * 0.8, c[2] + dz * g * h * 0.15)
        else:
            g = (f - 0.6) / 0.4
            ang = g * curl * 6.283
            rad = h * 0.22 * (1 - g * 0.85)
            p = (c[0] + dx * (h * 0.15 + math.sin(ang) * rad), c[1] + h * 0.8 + (1 - math.cos(ang)) * rad * 0.9 - rad * 0 , c[2] + dz * (h * 0.15 + math.sin(ang) * rad))
        path.append(p)
    w = h * 0.045
    me.sweep(path, [(w * math.cos(k / 6 * 6.283), w * math.sin(k / 6 * 6.283)) for k in range(6)], m, scale=[1 - 0.8 * q / 39 for q in range(40)], vrep=4)
    # leaflets
    for q in range(3, 36, 1):
        p, p2 = path[q], path[q + 1]
        tx, ty, tz = p2[0] - p[0], p2[1] - p[1], p2[2] - p[2]
        L = math.sqrt(tx * tx + ty * ty + tz * tz) or 1
        nx, nz = -dz, dx
        ln = h * 0.26 * (1 - q / 44)
        for s in (-1, 1):
            tip = (p[0] + nx * s * ln + tx / L * ln * 0.3, p[1] + ln * 0.25, p[2] + nz * s * ln + tz / L * ln * 0.3)
            mid1 = (p[0] + nx * s * ln * 0.5 + tx / L * ln * 0.35, p[1] + ln * 0.2, p[2] + nz * s * ln * 0.5 + tz / L * ln * 0.35)
            mid2 = (p[0] + nx * s * ln * 0.5 - tx / L * ln * 0.05, p[1] + ln * 0.08, p[2] + nz * s * ln * 0.5 - tz / L * ln * 0.05)
            me.face([p, mid2, tip, mid1] if s > 0 else [p, mid1, tip, mid2], m, [(0.5, 0), (0, 0.5), (0.5, 1), (1, 0.5)] if s > 0 else [(0.5, 0), (1, 0.5), (0.5, 1), (0, 0.5)])
            me.face(([p, mid2, tip, mid1] if s > 0 else [p, mid1, tip, mid2])[::-1], m, [(0.5, 0), (1, 0.5), (0.5, 1), (0, 0.5)])
    return path


def frond_plant(me, c, h, m, n=9, seed=0):
    """a burst of long glowing leaves (like a Pandora 'helicoradian' bed)"""
    rnd = random.Random(seed)
    for k in range(n):
        a = k / n * 6.283 + rnd.random() * 0.5
        dx, dz = math.sin(a), math.cos(a)
        L = h * rnd.uniform(0.7, 1.0)
        w = L * 0.12
        pts = []
        for q in range(7):
            f = q / 6
            pts.append((c[0] + dx * L * 0.55 * f, c[1] + L * (math.sin(f * 2.2) * 0.9), c[2] + dz * L * 0.55 * f))
        nx, nz = -dz, dx
        for q in range(6):
            a0, a1 = pts[q], pts[q + 1]
            w0 = w * math.sin(math.pi * q / 6 + 0.2); w1 = w * math.sin(math.pi * (q + 1) / 6 + 0.2)
            quad = [(a0[0] - nx * w0, a0[1], a0[2] - nz * w0), (a1[0] - nx * w1, a1[1], a1[2] - nz * w1), (a1[0] + nx * w1, a1[1], a1[2] + nz * w1), (a0[0] + nx * w0, a0[1], a0[2] + nz * w0)]
            uv = [(0, q / 6), (0, (q + 1) / 6), (1, (q + 1) / 6), (1, q / 6)]
            me.face(quad, m, uv); me.face(quad[::-1], m, uv[::-1])


def rock(me, c, r, m, seed=0, flat=0.6, n=16, rows=8):
    """a lumpy boulder / island underside: a squashed, noisy sphere"""
    rnd = random.Random(seed)
    ph = [rnd.random() * 6.283 for _ in range(6)]
    rings = []
    for q in range(1, rows):
        t = q / rows * math.pi
        ring_ = []
        for k in range(n):
            a = k / n * 6.283
            nz = 1 + 0.18 * math.sin(a * 3 + ph[0] + t * 2) + 0.12 * math.sin(a * 5 + ph[1] - t * 3) + 0.1 * math.sin(t * 4 + ph[2])
            rr = r * math.sin(t) * nz
            y = -math.cos(t) * r * (flat if t < math.pi / 2 else 1.0)
            ring_.append((c[0] + rr * math.sin(a), c[1] + y, c[2] + rr * math.cos(a)))
        rings.append(ring_)
    rings = rings[::-1]
    me.tube(rings, m, vrep=1, urep=2, cap0=m, cap1=m)


def island(me, c, r, ms, seed=0):
    """a floating island: a rock hanging down to a point, a mossy top, crystals and mushrooms on it"""
    rnd = random.Random(seed)
    n = 18
    rings = []
    for q, (f, y) in enumerate(((1.0, 0.0), (0.98, -r * 0.12), (0.85, -r * 0.35), (0.62, -r * 0.65), (0.38, -r * 0.95), (0.16, -r * 1.25), (0.02, -r * 1.5))):
        rings.append([(c[0] + r * f * (1 + 0.15 * math.sin(k * 1.7 + q + seed)) * math.sin(k / n * 6.283), c[1] + y + rnd.uniform(-0.2, 0.2) * r * 0.1, c[2] + r * f * (1 + 0.15 * math.sin(k * 1.7 + q + seed)) * math.cos(k / n * 6.283)) for k in range(n)])
    me.tube(rings[::-1], ms["rock"], vrep=2, urep=3)
    top = rings[0]
    cen = (c[0], c[1] + r * 0.06, c[2])
    for k in range(n):
        me.face([cen, top[(k + 1) % n], top[k]][::-1], ms["moss"], [(0.5, 0.5), (0.5 + 0.5 * math.sin(k / n * 6.283), 0.5 + 0.5 * math.cos(k / n * 6.283)), (0.5 + 0.5 * math.sin((k + 1) / n * 6.283), 0.5 + 0.5 * math.cos((k + 1) / n * 6.283))])
    crystal_cluster(me, (c[0] + r * 0.3, c[1], c[2] - r * 0.2), r * 0.6, ms["cry"], seed=seed + 3, n=5)
    M_stem[0], M_stem[1] = ms["stem"], ms["gill"]
    mushroom(me, (c[0] - r * 0.35, c[1], c[2] + r * 0.25), r * 0.7, r * 0.3, ms["capm"], seed=seed + 5)
    frond_plant(me, (c[0] - r * 0.1, c[1], c[2] - r * 0.45), r * 0.4, ms["leafg"], n=7, seed=seed + 7)
    # hanging vines under it
    for k in range(6):
        a = rnd.random() * 6.283; d = r * rnd.uniform(0.3, 0.8)
        L = r * rnd.uniform(0.8, 1.8)
        p0 = (c[0] + math.sin(a) * d, c[1] - r * 0.3 * (1 - d / r) - r * 0.2, c[2] + math.cos(a) * d)
        path = [(p0[0] + 0.3 * math.sin(q * 0.9), p0[1] - L * q / 8, p0[2] + 0.3 * math.cos(q * 0.7)) for q in range(9)]
        me.sweep(path, [(0.12 * math.cos(j / 4 * 6.283), 0.12 * math.sin(j / 4 * 6.283)) for j in range(4)], ms["glowc"] if k % 2 else ms["glowm"], scale=[1 - q / 10 for q in range(9)])


def jelly(me, c, r, ms, seed=0, tent=8):
    """a floating jellyfish-lantern: a glowing bell and trailing tentacles"""
    prof = [(r * 0.02, r * 0.9), (r * 0.45, r * 0.82), (r * 0.8, r * 0.55), (r * 1.0, r * 0.15), (r * 0.92, 0.0), (r * 0.7, r * 0.12)]
    me.lathe(prof[::-1], ms["jelly"], c=c, seg=24, wobble=0.04, seed=seed)       # (bottom to top: faces outward)
    inner = [(r * 0.02, r * 0.55), (r * 0.35, r * 0.45), (r * 0.4, r * 0.2), (r * 0.02, r * 0.15)]
    me.lathe(inner[::-1], ms["glowm"], c=c, seg=12)
    for k in range(tent):
        a = k / tent * 6.283
        d = r * 0.7
        L = r * (2.2 + (k % 3) * 0.5)
        path = [(c[0] + math.sin(a) * d * (1 - q / 14), c[1] + 0.05 - L * q / 10, c[2] + math.cos(a) * d * (1 - q / 14)) for q in range(11)]
        me.sweep(path, [(r * 0.04 * math.cos(j / 4 * 6.283), r * 0.04 * math.sin(j / 4 * 6.283)) for j in range(4)], ms["glowc"], scale=[1 - q / 12 for q in range(11)])


def willow(me, c, h, ms, seed=0, strands=70):
    """a spirit tree: a twisting trunk, arching boughs and long glowing strands hanging down"""
    rnd = random.Random(seed)
    path = [(c[0] + math.sin(q * 0.6) * h * 0.03, c[1] + h * 0.7 * q / 10, c[2] + math.cos(q * 0.5) * h * 0.03) for q in range(11)]
    me.sweep(path, [(h * 0.05 * math.cos(k / 10 * 6.283) * (1 + 0.2 * math.sin(k * 3)), h * 0.05 * math.sin(k / 10 * 6.283) * (1 + 0.2 * math.sin(k * 3))) for k in range(10)],
             ms["bark"], scale=[1.6 - 0.8 * q / 10 for q in range(11)], vrep=3, twist=1.2)
    top = path[-1]
    tips = []
    for b in range(6):
        a = b / 6 * 6.283 + rnd.random() * 0.4
        L = h * rnd.uniform(0.35, 0.5)
        bp = [(top[0] + math.sin(a) * L * q / 8, top[1] + math.sin(q / 8 * 2.4) * h * 0.12, top[2] + math.cos(a) * L * q / 8) for q in range(9)]
        me.sweep(bp, [(h * 0.02 * math.cos(k / 6 * 6.283), h * 0.02 * math.sin(k / 6 * 6.283)) for k in range(6)], ms["bark"], scale=[1 - 0.7 * q / 8 for q in range(9)], vrep=2)
        tips += bp[3:]
        frond_plant(me, bp[-1], h * 0.14, ms["leafv"] if b % 2 else ms["leafg"], n=7, seed=seed + b)
    for s in range(strands):
        p = tips[rnd.randrange(len(tips))]
        L = h * rnd.uniform(0.35, 0.65)
        sp = [(p[0] + 0.2 * math.sin(q), p[1] - L * q / 6, p[2] + 0.2 * math.cos(q)) for q in range(7)]
        me.sweep(sp, [(0.08 * math.cos(k / 3 * 6.283), 0.08 * math.sin(k / 3 * 6.283)) for k in range(3)], ms["glowc"] if s % 3 else ms["glowm"], scale=[1 - q / 8 for q in range(7)])
    return tips


def pylon(me, c, r, h, ms, seed=0):
    """a pinball post: a crystal spire on a pearl base with a floating gold halo"""
    rnd = random.Random(seed)
    base = [(r * 1.25, 0.0), (r * 1.3, 0.25), (r * 1.1, 0.6), (r * 1.0, 1.0)]
    me.lathe(base, ms["white"], c=c, seg=16)
    shard(me, (c[0], c[1] + 0.9, c[2]), h, r * 0.95, ms["cry"], seed=seed, sides=6, tip=0.3)
    halo = [(r * 1.6 * math.cos(k / 6 * 6.283) * 0.18, r * 1.6 * math.sin(k / 6 * 6.283) * 0.18) for k in range(6)]
    path = [(c[0] + r * 1.7 * math.sin(k / 24 * 6.283), c[1] + max(h * 0.72, 2 * 4.0 + 1.5), c[2] + r * 1.7 * math.cos(k / 24 * 6.283)) for k in range(25)]   # (above the marbles)
    me.sweep(path, [(0.14 * math.cos(k / 6 * 6.283), 0.14 * math.sin(k / 6 * 6.283)) for k in range(6)], ms["glowg"])


def arch_y(span, height, leg, x):
    """height of the arch's rib above the base at distance x from the middle"""
    if abs(x) >= span / 2:
        return leg
    return leg + (height - leg) * math.sqrt(max(0.0, 1 - (2 * x / span) ** 2))


def arch(me, c, ry, span, height, ms, seed=0, leg=0.0):
    """an organic arch over the track: two ribs that stand straight up beside the track to `leg`, then
    curve in and meet overhead at `height` (so over the deck it is never narrower than `span`)"""
    cy, sy = math.cos(math.radians(ry)), math.sin(math.radians(ry))
    def W(x, y, z=0.0):
        return (c[0] + x * cy + z * sy, c[1] + y, c[2] - x * sy + z * cy)
    NL = max(2, int(leg / 8)) if leg > 0 else 0
    for side in (-1, 1):
        path = []
        for q in range(NL):                                  # the straight leg (a gentle organic sway)
            y = leg * q / NL
            path.append(W(side * (span / 2 + 0.5 * math.sin(q * 1.7 + seed)), y, side * 0.4 * math.sin(q * 1.1)))
        for q in range(17):
            f = q / 16
            a = f * math.pi / 2
            x = side * span / 2 * math.cos(a) * (1 + 0.04 * math.sin(f * 3.1))
            y = leg + (height - leg) * math.sin(a)
            path.append(W(x, y, side * 0.6 * math.sin(f * 3.1)))
        n = len(path)
        me.sweep(path, [(1.0 * math.cos(k / 8 * 6.283) * (1 + 0.25 * (k % 2)), 1.0 * math.sin(k / 8 * 6.283)) for k in range(8)], ms["bark"],
                 scale=[1.8 - 1.1 * q / (n - 1) for q in range(n)], vrep=4 * n / 17, twist=2.0 * n / 17)
        # a glowing vine wound round each rib
        vine = [(p[0] + 1.4 * math.sin(q * 1.3), p[1] + 1.2 * math.cos(q * 1.3), p[2]) for q, p in enumerate(path)]
        me.sweep(vine, [(0.16 * math.cos(k / 4 * 6.283), 0.16 * math.sin(k / 4 * 6.283)) for k in range(4)], ms["glowc"] if side > 0 else ms["glowm"])
    return W


def text_panel(me, c, ry, w, h, m, curve=0.0, thick=0.25):
    """a sign face (two-sided) with a slim frame; gently curved if curve > 0"""
    cy, sy = math.cos(math.radians(ry)), math.sin(math.radians(ry))
    n = 12
    def W(x, y, z):
        return (c[0] + x * cy + z * sy, c[1] + y, c[2] - x * sy + z * cy)
    for side in (1, -1):
        for q in range(n):
            x0, x1 = -w / 2 + w * q / n, -w / 2 + w * (q + 1) / n
            z0 = side * thick / 2 - curve * (1 - (2 * x0 / w) ** 2); z1 = side * thick / 2 - curve * (1 - (2 * x1 / w) ** 2)
            quad = [W(x0, -h / 2, z0), W(x1, -h / 2, z1), W(x1, h / 2, z1), W(x0, h / 2, z0)]
            u0, u1 = (q / n, (q + 1) / n) if side > 0 else (1 - q / n, 1 - (q + 1) / n)
            uv = [(u0, 0), (u1, 0), (u1, 1), (u0, 1)]
            if side > 0:
                me.face(quad, m, uv)
            else:
                me.face(quad[::-1], m, uv[::-1])


def tunnel_ring(me, c, ry, span, height, ms, seed=0):
    """a ring of light over the track: a finned hoop with the colour wheel along it"""
    cy, sy = math.cos(math.radians(ry)), math.sin(math.radians(ry))
    path = []
    for q in range(33):
        a = math.pi * q / 32
        x = -math.cos(a) * span / 2
        y = math.sin(a) * height
        path.append((c[0] + x * cy, c[1] + y, c[2] - x * sy))
    shape = [(1.2, 0), (0.5, 0.35), (0, 0.6), (-0.5, 0.35), (-1.2, 0), (-0.5, -0.35), (0, -0.6), (0.5, -0.35)]
    me.sweep(path, shape, ms["rain"], vrep=1, urep=1)

import json, sys, numpy as np, trimesh, time
col = trimesh.load(sys.argv[1], force='mesh')
paths = json.load(open('/tmp/paths.json'))
FT = 1.2
offs = [(dx, dz) for dx in np.linspace(-2.9, 2.9, 5) for dz in np.linspace(-2.9, 2.9, 5)]
orig, meta = [], []
for k, P in enumerate(paths):
    for s in P:
        for dx, dz in offs:
            orig.append([s[1] + dx, s[2] + FT + 6.6, s[3] + dz]); meta.append((k, s))
orig = np.array(orig); dirs = np.tile([0, -1, 0], (len(orig), 1))
locs, ri, ti = col.ray.intersects_location(orig, dirs, multiple_hits=False)
bad = {}
for L, r in zip(locs, ri):
    k, s = meta[r]
    floor = s[2] + FT
    if L[1] > floor + 0.05:
        key = (int(round(s[1] / 10) * 10), int(round(s[3] / 10) * 10))
        b = bad.setdefault(key, [0, 0, k]); b[0] += 1; b[1] = max(b[1], L[1] - floor)
for key, (n, h, k) in sorted(bad.items(), key=lambda kv: -kv[1][1])[:30]:
    print("  near x %d z %d: %d rays, up to %.2f m above the riders' floor" % (key[0], key[1], n, h))
print("SPOTS", len(bad))

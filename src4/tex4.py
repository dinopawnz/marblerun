"""Procedural textures for THE GRAND MARBLE RUN v4 ("Pandora night": bioluminescent, colourful).
Every texture is tileable and comes as a pair: <name>.png (base colour) and <name>_e.png (glow)."""
import numpy as np, os, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

TEX = "/home/claude/mr4/tex"
os.makedirs(TEX, exist_ok=True)
rng = np.random.default_rng(11)
FONTS = "/home/claude/mr4/fonts"


def hx(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)])


def vnoise(w, h, cells, seed=0):
    """tileable smooth value noise, cells = grid cells across"""
    r = np.random.default_rng(seed)
    g = r.random((cells, cells))
    ys, xs = np.mgrid[0:h, 0:w]
    fx, fy = xs / w * cells, ys / h * cells
    x0, y0 = np.floor(fx).astype(int), np.floor(fy).astype(int)
    tx, ty = fx - x0, fy - y0
    tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
    x1, y1 = (x0 + 1) % cells, (y0 + 1) % cells
    x0, y0 = x0 % cells, y0 % cells
    a, b, c, d = g[y0, x0], g[y0, x1], g[y1, x0], g[y1, x1]
    return (a * (1 - tx) + b * tx) * (1 - ty) + (c * (1 - tx) + d * tx) * ty


def fbm(w, h, base=4, octaves=5, seed=0):
    out, amp, tot = np.zeros((h, w)), 1.0, 0.0
    for o in range(octaves):
        out += vnoise(w, h, base * 2 ** o, seed + o * 17) * amp
        tot += amp; amp *= 0.5
    return out / tot


def save(name, rgb, glow=None):
    Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).save(os.path.join(TEX, name + ".png"))
    if glow is not None:
        Image.fromarray((np.clip(glow, 0, 1) * 255).astype(np.uint8)).save(os.path.join(TEX, name + "_e.png"))
    return os.path.join(TEX, name + ".png"), (os.path.join(TEX, name + "_e.png") if glow is not None else None)


def lines_from(field, k, width):
    """thin glowing contour lines of a scalar field"""
    v = np.abs(np.sin(field * k * math.pi))
    return np.clip(1 - v / width, 0, 1) ** 2


def mix(*cols_weights):
    out = 0
    for c, w in cols_weights:
        out = out + c[None, None, :] * w[..., None]
    return out


def deck(name, c1, c2, base="#0a0b22", n=1024, seed=1):
    """(veins drawn wider and brighter so they read from a distance)"""
    """the track surface: deep glossy base, a fine hex weave, flowing luminous veins in two colours"""
    f1 = fbm(n, n, 3, 5, seed)
    f2 = fbm(n, n, 2, 4, seed + 50)
    ys, xs = np.mgrid[0:n, 0:n] / n
    # hex weave
    s = 24
    q = xs * s * 2 / math.sqrt(3); r = ys * s - xs * s / math.sqrt(3)
    hexd = np.minimum(np.abs(np.sin(q * math.pi)), np.minimum(np.abs(np.sin(r * math.pi)), np.abs(np.sin((q + r) * math.pi))))
    weave = np.clip(1 - hexd / 0.08, 0, 1)
    v1 = lines_from(f1, 7, 0.12)
    v2 = lines_from(f2 + 0.31, 5, 0.09)
    B = hx(base)
    rgb = B[None, None, :] * (0.75 + 0.5 * f1[..., None]) + mix((hx(c1), v1 * 0.55), (hx(c2), v2 * 0.5), (hx("#3a2f7a"), weave * 0.35))
    glow = mix((hx(c1), v1), (hx(c2), v2 * 0.9), (hx("#2a2060"), weave * 0.25))
    return save(name, rgb, glow)


def crystal(name, top, bottom, n=512, seed=3):
    """crystal faces: a vertical colour gradient with bright streaks and sparkles"""
    ys, xs = np.mgrid[0:n, 0:n] / n
    f = fbm(n, n, 4, 4, seed)
    grad = ys[..., None]
    col = hx(top)[None, None, :] * (1 - grad) + hx(bottom)[None, None, :] * grad
    streak = np.clip(1 - np.abs(np.sin((xs * 3 + f * 0.8) * math.pi * 4)) / 0.12, 0, 1) ** 2
    spark = (rng.random((n, n)) > 0.9985).astype(float)
    spark = np.array(Image.fromarray((spark * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.4))) / 255 * 4
    rgb = col * (0.55 + 0.45 * f[..., None]) + streak[..., None] * 0.35 + spark[..., None]
    glow = col * (0.35 + 0.65 * f[..., None]) * 0.8 + streak[..., None] * 0.6 + spark[..., None]
    return save(name, rgb, glow)


def bark(name, vein="#3ff6ff", base="#1d1430", n=512, seed=5):
    """organic trunks: fibrous dark bark with glowing veins winding up it"""
    f = fbm(n, n * 2, 4, 5, seed)
    ys, xs = np.mgrid[0:n * 2, 0:n] / np.array([n * 2, n])[:, None, None]
    fib = vnoise(n, n * 2, 64, seed + 9)
    rgb = hx(base)[None, None, :] * (0.6 + 0.8 * f[..., None]) * (0.85 + 0.3 * fib[..., None])
    veins = lines_from(xs * 3 + f * 1.6, 2, 0.06) * (0.4 + 0.6 * fbm(n, n * 2, 2, 3, seed + 4))
    rgb = rgb + hx(vein)[None, None, :] * veins[..., None] * 0.6
    glow = hx(vein)[None, None, :] * veins[..., None]
    return save(name, rgb, glow)


def cap(name, c1, c2, n=512, seed=7):
    """mushroom caps: glowing gradient with bright spots"""
    ys, xs = np.mgrid[0:n, 0:n] / n
    f = fbm(n, n, 4, 4, seed)
    col = hx(c1)[None, None, :] * (1 - ys[..., None]) + hx(c2)[None, None, :] * ys[..., None]
    spots = np.zeros((n, n))
    for _ in range(60):
        cx, cy, r = rng.random(), rng.random(), rng.uniform(0.012, 0.035)
        d = np.sqrt(np.minimum(np.abs(xs - cx), 1 - np.abs(xs - cx)) ** 2 + (ys - cy) ** 2)
        spots = np.maximum(spots, np.clip(1 - d / r, 0, 1) ** 0.7)
    rgb = col * (0.6 + 0.4 * f[..., None]) + spots[..., None] * 0.8
    glow = col * (0.45 + 0.55 * f[..., None]) + spots[..., None]
    return save(name, rgb, glow)


def ground(name, n=2048, seed=9):
    """the meadow: dark teal moss, glowing specks and soft drifts of light"""
    f = fbm(n, n, 6, 6, seed)
    g = fbm(n, n, 3, 4, seed + 30)
    rgb = hx("#061a1c")[None, None, :] * (0.5 + f[..., None]) + hx("#1b0d33")[None, None, :] * g[..., None] * 0.6
    drift = np.clip((g - 0.55) * 4, 0, 1) ** 2
    specks = (rng.random((n, n)) > 0.996).astype(float)
    specks = np.array(Image.fromarray((specks * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))) / 255 * 3
    hue = fbm(n, n, 2, 2, seed + 60)
    sc = hx("#5effc8")[None, None, :] * (1 - hue[..., None]) + hx("#7a8bff")[None, None, :] * hue[..., None]
    rgb = rgb + sc * (specks[..., None] * 0.8 + drift[..., None] * 0.18)
    glow = sc * (specks[..., None] + drift[..., None] * 0.22)
    return save(name, rgb, glow)


def leaf(name, c1, c2, n=256, seed=13):
    ys, xs = np.mgrid[0:n * 2, 0:n] / np.array([n * 2, n])[:, None, None]
    col = hx(c1)[None, None, :] * (1 - ys[..., None]) + hx(c2)[None, None, :] * ys[..., None]
    rib = np.clip(1 - np.abs(xs - 0.5) / 0.03, 0, 1)
    edge = np.clip(1 - np.minimum(xs, 1 - xs) / 0.06, 0, 1)
    veins = lines_from(ys * 10 + np.abs(xs - 0.5) * 6, 1, 0.08) * 0.6
    rgb = col * 0.5 + (rib + edge + veins)[..., None] * col * 0.6
    glow = col * 0.25 + (rib + edge * 0.9 + veins)[..., None] * col
    return save(name, rgb, glow)


def rainbow(name, n=1024):
    """tunnel rings / trails: a smooth colour wheel along U, bright core along V"""
    xs = np.linspace(0, 1, n)[None, :].repeat(64, 0)
    ys = np.linspace(0, 1, 64)[:, None].repeat(n, 1)
    h = xs * 6
    rgb = np.stack([np.clip(np.abs(h - 3) - 1, 0, 1), np.clip(2 - np.abs(h - 2), 0, 1), np.clip(2 - np.abs(h - 4), 0, 1)], -1)
    core = (1 - np.abs(ys - 0.5) * 2) ** 0.6
    return save(name, rgb * (0.4 + 0.6 * core[..., None]), rgb * core[..., None])


def water(name, n=1024, seed=17):
    f = fbm(n, n, 4, 5, seed)
    rip = lines_from(f, 12, 0.08)
    rgb = hx("#032a2e")[None, None, :] * (0.6 + 0.8 * f[..., None]) + hx("#3dffd0")[None, None, :] * rip[..., None] * 0.5
    glow = hx("#2bffd0")[None, None, :] * rip[..., None] * 0.8 + hx("#0b5560")[None, None, :] * f[..., None] * 0.3
    return save(name, rgb, glow)


def tiles(name, seam="#ffd36b", base="#14102a", n=1024):
    ys, xs = np.mgrid[0:n, 0:n] / n
    f = fbm(n, n, 4, 4, 21)
    t = 8
    sx, sy = np.abs(np.sin(xs * t * math.pi)), np.abs(np.sin(ys * t * math.pi))
    seamv = np.clip(1 - np.minimum(sx, sy) / 0.04, 0, 1)
    rgb = hx(base)[None, None, :] * (0.7 + 0.6 * f[..., None]) + hx(seam)[None, None, :] * seamv[..., None] * 0.6
    glow = hx(seam)[None, None, :] * seamv[..., None]
    return save(name, rgb, glow)


def font(size, bold=True):
    for f in ("CinzelDecorative-Black.ttf", "Cinzel[wght].ttf"):
        p = os.path.join(FONTS, f)
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)


def holo_text(name, text, w=1280, h=200, c1="#5ff2ff", c2="#ff5fc8", sub=None):
    """glowing sign text: a colour gradient across the letters, a soft halo, on deep night"""
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    fs = int(h * 0.62)
    while True:
        f = font(fs)
        bb = d.textbbox((0, 0), text, font=f)
        if bb[2] - bb[0] <= w * 0.9 or fs < 12:
            break
        fs -= 6
    yoff = -h * 0.07 if sub else 0
    d.text(((w - (bb[2] - bb[0])) / 2 - bb[0], (h - (bb[3] - bb[1])) / 2 - bb[1] + yoff), text, font=f, fill=255)
    if sub:
        f2 = font(int(h * 0.15))
        b2 = d.textbbox((0, 0), sub, font=f2)
        d.text(((w - (b2[2] - b2[0])) / 2 - b2[0], h * 0.8 - b2[1]), sub, font=f2, fill=255)
    m = np.array(mask) / 255
    halo = np.array(mask.filter(ImageFilter.GaussianBlur(h * 0.05))) / 255
    xs = np.linspace(0, 1, w)[None, :]
    col = hx(c1)[None, None, :] * (1 - xs[..., None]) + hx(c2)[None, None, :] * xs[..., None]
    ys, xg = np.mgrid[0:h, 0:w]
    border = ((np.minimum(np.minimum(xg, w - 1 - xg), np.minimum(ys, h - 1 - ys)) < h * 0.03)).astype(float)
    base = hx("#070818")[None, None, :] * np.ones((h, w, 1))
    rgb = base + col * (m[..., None] * 1.0 + halo[..., None] * 0.5) + col * border[..., None] * 0.7
    glow = col * (m[..., None] + halo[..., None] * 0.6) + col * border[..., None] * 0.8
    return save(name, rgb, glow)


def solid(name, color, glow=None, n=8):
    rgb = np.ones((n, n, 3)) * hx(color)
    g = np.ones((n, n, 3)) * hx(glow) if glow else None
    return save(name, rgb, g)


def checker(name, n=8, w=1024, h=128):
    ys, xs = np.mgrid[0:h, 0:w]
    c = ((xs // (w // n) + ys // (h // 2)) % 2).astype(float)
    rgb = hx("#0a0a12")[None, None, :] * (1 - c[..., None]) + hx("#f8f4ff")[None, None, :] * c[..., None]
    return save(name, rgb, rgb * 0.5)


def stem(name, n=512, seed=23):
    """mushroom stems: pale ribbed flesh that glows from within, brighter towards the top"""
    ys, xs = np.mgrid[0:n, 0:n] / n
    f = fbm(n, n, 4, 4, seed)
    ribs = (0.5 + 0.5 * np.sin((xs * 24 + f * 1.5) * math.pi)) ** 3
    col = hx("#c9b8ff")[None, None, :] * (0.55 + 0.45 * f[..., None]) * (0.75 + 0.25 * ribs[..., None])
    glow = hx("#9a7bff")[None, None, :] * (0.25 + 0.75 * (1 - ys[..., None]) ** 2) * (0.6 + 0.4 * ribs[..., None])
    return save(name, col, glow)


def stone(name, n=1024, seed=29):
    """island rock: dark violet stone, cracks of light"""
    f = fbm(n, n, 5, 5, seed)
    g = fbm(n, n, 3, 4, seed + 7)
    cracks = lines_from(g, 5, 0.05) * (f > 0.45)
    rgb = hx("#241a3c")[None, None, :] * (0.5 + 0.9 * f[..., None]) + hx("#ff5fc8")[None, None, :] * cracks[..., None] * 0.6
    glow = hx("#ff5fc8")[None, None, :] * cracks[..., None] + hx("#3ff6ff")[None, None, :] * (lines_from(f, 7, 0.04) * 0.5)[..., None]
    return save(name, rgb, glow)


if __name__ == "__main__":
    stem("stem")
    stone("stone")
    deck("deck", "#3ff6ff", "#ff4fd8")
    deck("bowl", "#9b6bff", "#5ff2ff", base="#0c0828", seed=4)
    deck("lift", "#ffd36b", "#ff7a2e", base="#120c1c", seed=8)
    crystal("crystal_cyan", "#8ffcff", "#3a2aa8")
    crystal("crystal_pink", "#ffb3f0", "#6a1a9a", seed=6)
    crystal("crystal_gold", "#fff0a8", "#b0461e", seed=8)
    bark("bark")
    bark("bark_pink", vein="#ff5fc8", base="#1a1022", seed=12)
    cap("cap_magenta", "#ff4fd8", "#ff9a3c")
    cap("cap_cyan", "#3ff6ff", "#6a5bff", seed=8)
    cap("cap_lime", "#b6ff5a", "#20c8a0", seed=9)
    ground("ground", n=1024)
    leaf("leaf_green", "#7dff9a", "#1ac0c8")
    leaf("leaf_violet", "#c07bff", "#ff5fc8", seed=3)
    rainbow("rainbow")
    water("swamp")
    tiles("tiles")
    checker("checker")
    print("textures done")

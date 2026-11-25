// Plays grand_marble_run_v2.html (v3: physics) in a fake MML world with a fake clock, the way Otherside plays it.
const fs = require("fs"), vm = require("vm");
const html = fs.readFileSync(process.argv[2], "utf8");
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
let clock = 5_000_000;
const timers = []; let tid = 0;
const docNow = () => clock - 5_000_000 + 1000;
class El {
  constructor(t) { this.tagName = t.toUpperCase(); this.attrs = {}; this.children = []; this.parentNode = null; this.ls = {}; this.born = docNow(); }
  setAttribute(k, v) { this.attrs[k] = String(v); if (this.isConnected && this.tagName === "M-ATTR-ANIM") changedAnims++; }
  getAttribute(k) { return this.attrs[k] === undefined ? null : this.attrs[k]; }
  append(c) { if (c.parentNode) c.remove(); c.parentNode = this; this.children.push(c); if (c.tagName === "M-ATTR-ANIM") c.added = docNow(); }
  remove() { if (this.parentNode) { const a = this.parentNode.children; a.splice(a.indexOf(this), 1); this.parentNode = null; } }
  addEventListener(t, f) { (this.ls[t] = this.ls[t] || []).push(f); }
  fire(t, d) { (this.ls[t] || []).forEach((f) => f({ detail: d })); }
  get isConnected() { let n = this; while (n.parentNode) n = n.parentNode; return n === ROOT; }
}
let changedAnims = 0;
const ROOT = new El("body");
const roots = { world: new El("m-group"), race: new El("m-group") };
ROOT.append(roots.world); ROOT.append(roots.race);
const document = { createElement(t) { return new El(t); }, getElementById: (i) => roots[i], timeline: { get currentTime() { return docNow(); } } };
const win = new El("window");
const ctx = { window: win, document, Date: { now: () => clock }, Math, String, Number, Object, Array, JSON, Infinity, isFinite, console, Map, Set,
  setInterval(f, ms) { timers.push({ f, ms, next: clock + ms, rep: true, id: ++tid }); return tid; },
  setTimeout(f, ms) { timers.push({ f, ms, next: clock + Math.max(0, ms), rep: false, id: ++tid }); return tid; },
  clearTimeout(id) { const i = timers.findIndex((t) => t.id === id); if (i >= 0) timers.splice(i, 1); }, clearInterval() {} };
// the physics really takes time on the server: charge 400 ms per simulated race to the fake clock
vm.createContext(ctx);
vm.runInContext(script + ";globalThis.X={ROOM_TOP,get plan(){return plan},get phase(){return phase},marbles:()=>marbles,COURSE,WORLD,boards,get errs(){return scriptErrors+' '+lastError},progress,bridge,HOST,get REMOTES(){return REMOTES},RIDERS,liveAnims,knotAt,fx};", ctx);
const X = ctx.X, C = X.COURSE;
function advance(ms) {
  const end = clock + ms;
  for (;;) { timers.sort((a, b) => a.next - b.next || a.id - b.id); const t = timers[0]; if (!t || t.next > end) break; clock = Math.max(clock, t.next); if (t.rep) t.next += t.ms; else timers.shift(); t.f(); }
  clock = end;
}
let fails = 0; const ok = (c, m) => { console.log((c ? "PASS " : "FAIL ") + m); if (!c) fails++; };
function animVal(a, doc) {
  const st = +a.attrs.start, en = +a.attrs.end, t0 = +a.attrs["start-time"] || 0, d = +a.attrs.duration;
  if (a.attrs.loop === "true") return st;
  if (doc <= t0) return st;
  return st + (en - st) * Math.min(1, (doc - t0) / d);
}
// what a player's screen shows: walk up from a node adding positions + animation values
function screenPos(node) {
  const doc = docNow();
  const p = [0, 0, 0];
  for (let n = node; n && n !== roots.race && n !== roots.world; n = n.parentNode) {
    ["x", "y", "z"].forEach((k, j) => {
      const an = n.children.filter((c) => c.tagName === "M-ATTR-ANIM" && c.attrs.attr === k).pop();
      p[j] += an ? animVal(an, doc) : +(n.attrs[k] || 0);
    });
  }
  return p;
}
const live = () => { const out = []; const walk = (n) => { out.push(n); n.children.forEach(walk); }; walk(ROOT); return out; };
const animsNow = () => live().filter((n) => n.tagName === "M-ATTR-ANIM").length;
const movingSolids = () => live().filter((n) => n.attrs.collide === "true" && n.isConnected && (() => { for (let e = n; e; e = e.parentNode) if (e.children.some((c) => c.tagName === "M-ATTR-ANIM")) return true; return false; })()).length;

// the deck, from the course (same numbers the Blender build uses)
const S = C.sections;
function profAt(s, t) {
  const p = s.prof; if (t <= p[0][0]) return p[0][1];
  for (let q = 0; q < p.length - 1; q++) if (t >= p[q][0] && t < p[q + 1][0]) return p[q][1] + (p[q + 1][1] - p[q][1]) * (t - p[q][0]) / (p[q + 1][0] - p[q][0]);
  return p[p.length - 1][1];
}
function deckY(x, z) {
  let best = null;
  for (const s of S) {
    if (s.type === "run") {
      const dx = x - s.P[0], dz = z - s.P[1], t = dx * s.d[0] + dz * s.d[1], u = dx * s.n[0] + dz * s.n[1];
      if (t >= s.t0 - 0.01 && t <= s.t1 + 0.01 + (s.i === 11 ? 12 : 0) && Math.abs(u) <= C.half + 0.01) best = Math.max(best === null ? -1e9 : best, profAt(s, t));
    } else {
      const vx = x - s.I[0], vz = z - s.I[1], r = Math.hypot(vx, vz);
      const ain = vx * s.din[0] + vz * s.din[1], aout = -(vx * s.dout[0] + vz * s.dout[1]);
      if (r <= s.R + 0.01 && ain >= -0.01 && aout >= -0.01) {
        let a = Math.atan2(ain, aout); a = Math.max(0, Math.min(Math.PI / 2, a));
        const y = s.yin + (s.yout - s.yin) * a / (Math.PI / 2) + s.bank * Math.sin(2 * a) * Math.pow(Math.min(r, s.R) / s.R, 2.5);
        best = Math.max(best === null ? -1e9 : best, y);
      }
    }
  }
  return best;
}


// ======================= RIDER BOTS =======================
// Physics bots standing in every marble for a whole race: gravity, collisions with the marble's real solid
// floor / walls / lid (wherever the game's glides put them, hand-overs included). Two kinds: GRIPPY bots are
// carried by the floor (like a player standing still), SLIPPERY bots slide freely (the worst case), and some JUMP.
const G = +(process.argv[3] || 9.8), R = 0.35, DT = 1 / 120;
const wrap = live().find((n) => n.tagName === "M-PROMPT" && n.attrs.id !== "mr-host");
wrap.fire("prompt", { value: "2468" });
const P = X.plan;
let guard = 0; while (!P.ready && guard++ < 400) advance(400);
function solidsOf(k) {
  const out = [];
  X.marbles()[k].forEach((c) => { if (!c.parts) return; c.pod.children.forEach((s) => {
    if (s.attrs.collide !== "true") return;
    const p = screenPos(s); const ry = +(s.attrs.ry || 0) * Math.PI / 180;
    if (s.tagName === "M-CYLINDER") { out.push({ c: p, cyl: +s.attrs.radius, hy: +s.attrs.height / 2, floor: !!s.attrs["collision-interval"], chain: c }); return; }
    const w = +s.attrs.width, d = +s.attrs.depth, h = +s.attrs.height;
    if (!(w > 0 && d > 0 && h > 0)) throw new Error("solid without a size: " + s.tagName);
    out.push({ c: p, hx: w / 2, hy: h / 2, hz: d / 2, ca: Math.cos(ry), sa: Math.sin(ry), floor: !!s.attrs["collision-interval"], chain: c });
  }); });
  return out;
}
const kinds = ["grip", "slip", "jump"];
const starts = [[0, 0], [1.6, 1.6], [-1.6, -1.6], [1.6, -1.6], [-1.6, 1.6], [0, 2.3]];
const bots = [];
for (let k = 0; k < 8; k++) starts.forEach((s, i) => kinds.forEach((kind) => {
  const f = X.marbles()[k][0].pod; const p = screenPos(f);
  bots.push({ k, kind, x: p[0] + s[0], y: p[1] + 1.2 + R + 0.05, z: p[2] + s[1], vx: 0, vy: 0, vz: 0, out: null, maxRel: 0, nextJump: 2000 + i * 700 });
}));
let prevFloor = {}, steps = 0, worst = { d: 0 };
const endT = P.end;
const t0c = clock;
while (clock < endT - 500) {
  advance(DT * 1000);
  steps++;
  for (let k = 0; k < 8; k++) {
    const S = solidsOf(k);
    const fl = S.find((s) => s.floor && s.chain === X.marbles()[k][X.marbles()[k].length - 1]) || S.find((s) => s.floor);
    if (!fl) continue;
    const pf = prevFloor[k]; prevFloor[k] = fl.c.slice();
    const fv = pf ? [(fl.c[0] - pf[0]) / DT, (fl.c[1] - pf[1]) / DT, (fl.c[2] - pf[2]) / DT] : [0, 0, 0];
    bots.forEach((b) => {
      if (b.k !== k || b.out) return;
      // move
      b.vy -= G * DT;
      if (b.kind === "jump" && clock - t0c > b.nextJump && b.ground) { b.vy = fv[1] + 4.5; b.nextJump = clock - t0c + 2500; }
      b.x += b.vx * DT; b.y += b.vy * DT; b.z += b.vz * DT;
      b.ground = false;
      // collide (sphere vs boxes), a few passes
      for (let pass = 0; pass < 3; pass++) S.forEach((s) => {
        let qx, qz;
        const qy = Math.max(s.c[1] - s.hy, Math.min(b.y, s.c[1] + s.hy));
        if (s.cyl) { const ex = b.x - s.c[0], ez = b.z - s.c[2], e = Math.hypot(ex, ez), f = e > s.cyl ? s.cyl / e : 1; qx = s.c[0] + ex * f; qz = s.c[2] + ez * f; }
        else {
          const wx = b.x - s.c[0], wz = b.z - s.c[2];
          const lx = wx * s.ca - wz * s.sa, lz = wx * s.sa + wz * s.ca;           // into the box's frame
          const cx = Math.max(-s.hx, Math.min(lx, s.hx)), cz = Math.max(-s.hz, Math.min(lz, s.hz));
          qx = s.c[0] + cx * s.ca + cz * s.sa; qz = s.c[2] - cx * s.sa + cz * s.ca;  // and back
        }
        let dx = b.x - qx, dy = b.y - qy, dz = b.z - qz, d = Math.hypot(dx, dy, dz);
        if (d >= R) return;
        if (d < 1e-6 && s.cyl) { const ex = b.x - s.c[0], ez = b.z - s.c[2]; const up = s.c[1] + s.hy - b.y + R, side = s.cyl - Math.hypot(ex, ez) + R;
          if (up < side) { b.y += up; dx = 0; dy = 1; dz = 0; } else { const e = Math.hypot(ex, ez) || 1; b.x += ex / e * side; b.z += ez / e * side; dx = ex / e; dy = 0; dz = ez / e; } d = 1; }
        else if (d < 1e-6) {          // centre inside the box: push out the shortest way (in the box's frame)
          const wx = b.x - s.c[0], wz = b.z - s.c[2];
          const lx = wx * s.ca - wz * s.sa, lz = wx * s.sa + wz * s.ca;
          const opts = [[s.hx - lx + R, 1, 0, 0], [lx + s.hx + R, -1, 0, 0], [s.c[1] + s.hy - b.y + R, 0, 1, 0], [b.y - (s.c[1] - s.hy) + R, 0, -1, 0], [s.hz - lz + R, 0, 0, 1], [lz + s.hz + R, 0, 0, -1]];
          opts.sort((a, c) => a[0] - c[0]); const o = opts[0];
          const nwx = o[1] * s.ca + o[3] * s.sa, nwz = -o[1] * s.sa + o[3] * s.ca;
          b.x += nwx * o[0]; b.y += o[2] * o[0]; b.z += nwz * o[0]; dx = nwx; dy = o[2]; dz = nwz; d = 1;
        } else { const push = R - d; b.x += dx / d * push; b.y += dy / d * push; b.z += dz / d * push; }
        const nx = dx / d, ny = dy / d, nz = dz / d;
        // the surface's own velocity (all solids of a marble move together)
        const rvx = b.vx - fv[0], rvy = b.vy - fv[1], rvz = b.vz - fv[2], vn = rvx * nx + rvy * ny + rvz * nz;
        if (vn < 0) { b.vx -= vn * nx; b.vy -= vn * ny; b.vz -= vn * nz; }
        if (ny > 0.7) {
          b.ground = true;
          if (b.kind !== "slip") { const g = Math.min(1, DT * 12); b.vx += (fv[0] - b.vx) * g; b.vz += (fv[2] - b.vz) * g; }
        }
      });
      // still inside its marble?
      const c = fl.c, rx = b.x - c[0], ry_ = b.y - c[1], rz = b.z - c[2];
      const rel = Math.hypot(rx, rz);
      b.maxRel = Math.max(b.maxRel, rel);
      if (!isFinite(b.x + b.y + b.z) || rel > 3.4 || ry_ < 0.3 || ry_ > X.ROOM_TOP + 0.5) b.out = { t: ((clock - P.tLift) / 1000).toFixed(1), rel: [rx.toFixed(2), ry_.toFixed(2), rz.toFixed(2)] };
    });
  }
}
const lost = bots.filter((b) => b.out);
const byKind = {}; kinds.forEach((kd) => (byKind[kd] = bots.filter((b) => b.kind === kd && b.out).length + "/" + bots.filter((b) => b.kind === kd).length));
console.log("gravity", G, "| bots", bots.length, "| race", ((endT - P.tLift) / 1000).toFixed(0), "s | lost by kind", JSON.stringify(byKind));
lost.filter((b) => +b.out.t > 0).slice(0, 12).forEach((b) => console.log("  LOST marble", b.k, b.kind, "at", b.out.t, "s, offset", b.out.rel.join(",")));
console.log("lost after the start:", lost.filter((b) => +b.out.t > 0).length); console.log(lost.length ? "BOTS FAILED" : "ALL BOTS STAYED IN (" + bots.length + " bots, a whole race)");

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
vm.runInContext(script + ";globalThis.X={get plan(){return plan},get phase(){return phase},marbles:()=>marbles,COURSE,WORLD,boards,get errs(){return scriptErrors+' '+lastError},progress,bridge,HOST,get REMOTES(){return REMOTES},RIDERS,liveAnims,knotAt};", ctx);
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

// ---------- at load ----------
const tags = {}; live().forEach((n) => (tags[n.tagName] = (tags[n.tagName] || 0) + 1));
ok((tags["M-LABEL"] || 0) <= 30, "live text labels: " + (tags["M-LABEL"] || 0));
ok(live().filter((n) => n.tagName === "M-MODEL" && !/raw\.githubusercontent\.com\/dinopawnz\/marblerun\/[0-9a-f]{40}\/models\/mr_.*\.glb(\.gz)?$/.test(n.attrs.src)).length === 0, "every model loads from the marblerun repo, pinned (" + tags["M-MODEL"] + ")");
const podPos = (k) => screenPos(X.marbles()[k][0].pod);
ok(C.homes.every((h, k) => Math.hypot(...podPos(k).map((v, j) => v - h[j])) < 0.01), "eight marbles parked at the station");

// ---------- a race, sampled every 100 ms of screen time ----------
const wrap = live().find((n) => n.tagName === "M-PROMPT" && n.attrs.id !== "mr-host");
wrap.fire("prompt", { value: "1111" }); ok(X.phase === "IDLE", "a wrong code does nothing");
const t0 = clock;
wrap.fire("prompt", { value: "2468" }); ok(X.phase === "BOARDING", "the code starts boarding");
const P = X.plan, drawn = P.winner;
advance(100);
ok(animsNow() === 16, "boarding: just the lift glides are made (" + animsNow() + ")");
// let the physics be worked out (each try really takes ~0.4 s: charge it)
let guard = 0;
while (!P.ready && guard++ < 400) advance(400);
ok(P.ready, "the physics is worked out during boarding (" + P.tries + " tries, " + ((clock - t0) / 1000).toFixed(0) + " s of the " + ((P.tRace - t0) / 1000).toFixed(0) + " s before the first marble rolls)");
ok(P.winner === drawn, "the race that is run is won by the marble drawn at the start");
let maxAnims = 0, maxSolids = 0, maxJump = 0, jumpAt = "", maxOff = 0, offAt = "", sinkMax = 0, sinkAt = "", minGap = 99, gapAt = "";
let noFloor = 0, split = 0, splitAt = "", late = 0, lateEx = "", doorMiss = 0, handovers = 0, shutSeen = false, bridgeGone = false;
const seenAnims = new Set();
const prev = [];
const SAMPLE = 100;
while (X.phase !== "IDLE" || clock < P.tLift) {
  advance(SAMPLE);
  const tnow = clock;
  const a = animsNow(); maxAnims = Math.max(maxAnims, a);
  if (tnow % 1000 < SAMPLE) maxSolids = Math.max(maxSolids, movingSolids());
  if (X.phase === "IDLE") break;
  live().forEach((n) => {
    if (n.tagName !== "M-ATTR-ANIM" || seenAnims.has(n) || n.attrs.loop === "true") return;
    seenAnims.add(n);
    if (n.added > 0 && +n.attrs["start-time"] < n.added + 150) { late++; if (!lateEx) lateEx = (+n.attrs["start-time"] - n.added) + " ms"; }
  });
  if (bridgeGone === false && !X.bridge.isConnected) bridgeGone = true;
  const pos = [];
  for (let k = 0; k < 8; k++) {
    const list = X.marbles()[k];
    if (list.length > 1) handovers++;
    const solid = list.filter((c) => c.parts);
    if (!solid.length) noFloor++;
    const ps = solid.map((c) => screenPos(c.pod));
    for (let q = 1; q < ps.length; q++) { const d = Math.hypot(...ps[q].map((v, j) => v - ps[0][j])); if (d > split) { split = d; splitAt = "marble " + k + " at " + ((tnow - P.tLift) / 1000).toFixed(1) + " s"; } }
    if (tnow > P.tLift && solid.some((c) => !c.door)) doorMiss++;
    if (tnow > P.tLift) shutSeen = true;
    const p = ps[0] || screenPos(list[0].pod);
    pos.push(p);
    if (prev[k]) { const j = Math.hypot(...p.map((v, i) => v - prev[k][i])); if (j > maxJump) { maxJump = j; jumpAt = "marble " + k + " at " + ((tnow - P.tLift) / 1000).toFixed(1) + " s"; } }
    prev[k] = p;
    // vs the physics
    const sm = P.sim.marbles[k], st = (tnow - P.tLift) / 1000;
    if (st >= sm.samples[0][0] && (sm.parkAt === null || st <= sm.parkAt)) {
      const i = Math.min(sm.samples.length - 1, Math.round((st - sm.samples[0][0]) / P.sim.sampleDt));
      const s = sm.samples[i], d = Math.hypot(p[0] - s[1], p[2] - s[3]);
      if (d > maxOff) { maxOff = d; offAt = "marble " + k + " at " + st.toFixed(1) + " s (screen " + p.map((v) => v.toFixed(1)).join(",") + " physics " + s.slice(1).map((v) => v.toFixed(1)).join(",") + ", chains " + list.map((c) => ((c.S - P.tLift) / 1000).toFixed(1) + (c.parts ? "s" : "") + (c.look ? "l" : "")).join("/") + ", park " + ((P.m[k].park - P.tLift) / 1000).toFixed(1) + ")"; }
      if (st > sm.samples[0][0] + 0.2) {
        const dy = deckY(p[0], p[2]);
        if (dy !== null && dy - p[1] > sinkMax) { sinkMax = dy - p[1]; sinkAt = "marble " + k + " at " + st.toFixed(1) + " s (" + p.map((v) => v.toFixed(1)).join(",") + ")"; }
      }
    }
  }
  if (tnow > P.tRace) for (let i = 0; i < 8; i++) for (let j = i + 1; j < 8; j++) {
    const d = Math.hypot(...pos[i].map((v, q) => v - pos[j][q]));
    if (d < minGap) { minGap = d; gapAt = i + "/" + j + " at " + ((tnow - P.tLift) / 1000).toFixed(1) + " s"; }
  }
  if (clock - t0 > 900000) break;
}
const raceSecs = (P.end - P.tLift) / 1000;
ok(X.phase === "IDLE", "the race ends by itself (" + raceSecs.toFixed(0) + " s from the lift, winner over the line at " + ((P.m[P.winner].finish - P.tLift) / 1000).toFixed(0) + " s)");
ok(maxAnims <= 290, "animations alive at once, at most: " + maxAnims + " (Check My Game's limit is 300)");
ok(seenAnims.size > 1000, "the race used " + seenAnims.size + " glides in all - spent ones leave with their old chains");
ok(maxSolids <= 80, "moving solids at once, at most: " + maxSolids + " (warn above 80)");
ok(late === 0, "every glide is sent ahead of its start (" + late + " late" + (lateEx ? ", e.g. " + lateEx : "") + ")");
ok(changedAnims === 0, "no animation was changed after it was made");
ok(noFloor === 0, "every marble always has a floor under its riders");
ok(split < 0.05, "during a hand-over the old and new floors lie on top of each other (worst " + (split * 100).toFixed(1) + " cm, " + (splitAt || "-") + ")");
ok(handovers > 0, "chains were handed over (" + handovers + " samples mid-hand-over)");
ok(doorMiss === 0 && shutSeen && bridgeGone, "doors shut on every chain and the bridge folded away during the race");
ok(maxJump < 3.5, "no marble ever jumps (biggest move in 0.1 s: " + maxJump.toFixed(2) + " m, " + jumpAt + ")");
ok(maxOff < 0.75, "the marbles follow the physics (worst " + maxOff.toFixed(2) + " m off, " + offAt + ")");
ok(sinkMax < 0.35, "no marble sinks into the track (worst " + sinkMax.toFixed(2) + " m, " + (sinkAt || "-") + ")");
ok(minGap > 6.5, "marbles bump but never pass through each other (closest centres " + minGap.toFixed(1) + " m, " + gapAt + ")");
const home = C.homes.every((h, k) => Math.hypot(...podPos(k).map((v, j) => v - h[j])) < 0.01);
ok(home && X.bridge.isConnected && animsNow() === 0, "all parked home, bridge back, every race animation gone (" + animsNow() + ")");
ok(/WINS/.test(X.boards[0][0]._t), "the boards name the winner: " + X.boards[0][0]._t);
ok(X.errs.startsWith("0 "), "no script errors (" + X.errs + ")");

// ---------- cancel ----------
wrap.fire("prompt", { value: "2468" }); advance(60000);
wrap.fire("prompt", { value: "2468" });
ok(X.phase === "RACE", "one extra code entry does not cancel");
wrap.fire("prompt", { value: "2468" }); advance(200);
ok(X.phase === "IDLE" && animsNow() === 0, "the code twice cancels, everything home");

// ---------- clicks ----------
const hidden = (n) => { for (; n; n = n.parentNode) if (n.attrs && n.attrs.visible === "false") return true; return false; };
const prompts = live().filter((n) => n.tagName === "M-PROMPT" && n.attrs.id !== "mr-host");
const targets = []; prompts.forEach((p) => { const w = (n) => { if (n !== p) targets.push(n); n.children.forEach(w); }; w(p); });
ok(prompts.length === 2 && targets.length >= 2 && targets.every((t) => !hidden(t) && t.attrs.opacity === "0"), "the RACE CONTROL click boxes can be clicked, and can't be seen");

// ---------- the host remote ----------
const host = live().find((n) => n.attrs.id === "mr-host"), board = live().find((n) => n.attrs.id === "mr-remote");
const acks = () => JSON.parse(board.attrs["data-ack"] || '{"t":""}').t;
const game = () => JSON.parse(board.attrs["data-game"] || "{}");
win.fire("connected", { connectionId: 3 }); win.fire("connected", { connectionId: 4 }); win.fire("connected", { connectionId: 9 });
host.fire("prompt", { value: "1111 remote", connectionId: 9 });
ok(acks() === "WRONG CODE" && board.attrs["visible-to"] === "-1", "remote: a wrong PIN doesn't unlock");
host.fire("prompt", { value: "2468 remote", connectionId: 9 });
ok(acks() === "UNLOCKED" && board.attrs["visible-to"] === "9", "remote: the right PIN unlocks, and only the remote sees the board");
advance(1100);
ok(game().ph === "idle" && game().online === 2, "remote: the board reports the game");
host.fire("prompt", { value: "2468 start", connectionId: 9 });
const floorOf = (k) => X.marbles()[k][0].pod.children.find((c) => c.tagName === "M-CYLINDER");
floorOf(2).fire("collisionstart", { connectionId: 3 }); floorOf(2).fire("collisionstart", { connectionId: 4 });
advance(1100);
ok(game().ph === "boarding" && game().marbles[2].riders === 2, "remote: sees 2 riders in " + game().marbles[2].n);
host.fire("prompt", { value: "2468 auto on", connectionId: 9 });
for (let i = 0; i < 400 && !X.plan.ready; i++) advance(400);
advance(X.plan.end - clock + 1000);
ok(X.phase === "IDLE" && game().nextAt > clock, "remote: AUTO queues the next race when one ends");
advance(X.HOST.gap * 1000 + 100);
ok(X.phase === "BOARDING", "remote: the next race boards by itself");
host.fire("prompt", { value: "2468 auto off", connectionId: 9 });
host.fire("prompt", { value: "2468 cancel", connectionId: 9 }); advance(500);
ok(X.phase === "IDLE" && animsNow() === 0, "remote: CANCEL sends everything home");
ok(X.errs.startsWith("0 "), "no script errors (" + X.errs + ")");
console.log(fails ? fails + " FAILED" : "ALL PASSED");

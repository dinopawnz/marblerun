// Plays grand_marble_run_v2.html in a fake MML world with a fake clock, the way Otherside plays it.
const fs = require("fs"), vm = require("vm");
const html = fs.readFileSync(process.argv[2], "utf8");
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
let clock = 5_000_000;
const timers = []; let tid = 0;
class El {
  constructor(t) { this.tagName = t.toUpperCase(); this.attrs = {}; this.children = []; this.parentNode = null; this.ls = {}; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return this.attrs[k] === undefined ? null : this.attrs[k]; }
  append(c) { if (c.parentNode) c.remove(); c.parentNode = this; this.children.push(c); }
  remove() { if (this.parentNode) { const a = this.parentNode.children; a.splice(a.indexOf(this), 1); this.parentNode = null; } }
  addEventListener(t, f) { (this.ls[t] = this.ls[t] || []).push(f); }
  fire(t, d) { (this.ls[t] || []).forEach((f) => f({ detail: d })); }
  get isConnected() { let n = this; while (n.parentNode) n = n.parentNode; return n === ROOT; }
}
const ROOT = new El("body");
const roots = { world: new El("m-group"), race: new El("m-group") };
ROOT.append(roots.world); ROOT.append(roots.race);
const all = [];
const document = { createElement(t) { const e = new El(t); all.push(e); return e; }, getElementById: (i) => roots[i], timeline: { get currentTime() { return clock - 5_000_000 + 1000; } } };
const win = new El("window");
const ctx = { window: win, document, Date: { now: () => clock }, Math, String, Number, Object, Array, JSON, Infinity, isFinite, console,
  setInterval(f, ms) { timers.push({ f, ms, next: clock + ms, rep: true, id: ++tid }); return tid; },
  setTimeout(f, ms) { timers.push({ f, ms, next: clock + ms, rep: false, id: ++tid }); return tid; },
  clearTimeout(id) { const i = timers.findIndex((t) => t.id === id); if (i >= 0) timers.splice(i, 1); }, clearInterval() {} };
vm.createContext(ctx);
vm.runInContext(script + ";globalThis.X={get plan(){return plan},get phase(){return phase},marbles:()=>marbles,makePlan,COURSE,WORLD,boards,get errs(){return scriptErrors+' '+lastError},progress,bridge,EASE,HOST,get REMOTES(){return REMOTES},RIDERS};", ctx);
const X = ctx.X, C = X.COURSE;
function advance(ms) {
  const end = clock + ms;
  for (;;) { timers.sort((a, b) => a.next - b.next); const t = timers[0]; if (!t || t.next > end) break; clock = t.next; t.f(); if (t.rep) t.next += t.ms; else timers.shift(); }
  clock = end;
}
let fails = 0; const ok = (c, m) => { console.log((c ? "PASS " : "FAIL ") + m); if (!c) fails++; };
const EASE = X.EASE;
// what a player's screen shows: walk up from a node adding positions + animation values
function animVal(a, doc) {
  const st = +a.attrs.start, en = +a.attrs.end, t0 = +a.attrs["start-time"] || 0, d = +a.attrs.duration;
  if (doc <= t0) return st;
  const u = Math.min(1, (doc - t0) / d);
  return st + (en - st) * (EASE[a.attrs.easing] || EASE.linear)(u);
}
function screenPos(node) {
  const doc = ctx.document.timeline.currentTime;
  let p = [0, 0, 0];
  for (let n = node; n && n !== roots.race && n !== roots.world; n = n.parentNode) {
    ["x", "y", "z"].forEach((k, j) => {
      const an = n.children.find((c) => c.tagName === "M-ATTR-ANIM" && c.attrs.attr === k);
      p[j] += an ? animVal(an, doc) : +(n.attrs[k] || 0);
    });
  }
  return p;
}
const live = () => { const out = []; const walk = (n) => { out.push(n); n.children.forEach(walk); }; walk(ROOT); return out; };

// ---------- the solid track under every marble: deck tops from the invisible boxes ----------
const decks = X.WORLD.colliders.filter((c) => Math.abs(c.h - 0.8) < 0.01);
function deckTop(x, z) {
  let best = -Infinity;
  for (const c of decks) {
    const ry = c.ry * Math.PI / 180, rx = c.rx * Math.PI / 180;
    let dx = x - c.x, dz = z - c.z;
    // into the box frame: undo ry, then rx (box is turned by rx inside a ry group)
    const lx = dx * Math.cos(ry) - dz * Math.sin(ry), lz0 = dx * Math.sin(ry) + dz * Math.cos(ry);
    // along the box's length the top rises by -tan(rx)
    const lz = lz0 / Math.cos(rx);
    if (Math.abs(lx) > c.w / 2 + 0.01 || Math.abs(lz) > c.d / 2 + 0.01) continue;
    const top = c.y + 0.4 / Math.cos(rx) - lz0 * Math.tan(rx);
    best = Math.max(best, top);
  }
  return best;
}
// counts at load
const tags = {}; live().forEach((n) => tags[n.tagName] = (tags[n.tagName] || 0) + 1);
console.log("at load:", JSON.stringify(tags));
const visPrims = live().filter((n) => /^M-(CUBE|CYLINDER|SPHERE|PLANE)$/.test(n.tagName) && n.attrs.visible !== "false" && n.attrs.opacity !== "0");
ok(visPrims.length === 0, "no plain shapes anybody can see (" + visPrims.length + ")");
ok((tags["M-LABEL"] || 0) <= 30, "live text labels: " + (tags["M-LABEL"] || 0));
ok((tags["M-MODEL"] || 0) > 0 && live().filter((n) => n.tagName === "M-MODEL" && !/raw\.githubusercontent\.com\/dinopawnz\/marblerun\/[0-9a-f]{40}\/models\/mr_.*\.glb\.gz$/.test(n.attrs.src)).length === 0, "every model loads from the marblerun repo (" + tags["M-MODEL"] + ")");

// ---------- fairness ----------
const wins = new Array(8).fill(0); let winFirst = 0, maxBehind = 0, maxLastWait = 0, sumLen = 0;
for (let r = 0; r < 40000; r++) {
  const p = X.makePlan(); wins[p.winner]++;
  if (p.m.every((m, k) => k === p.winner || m.finish > p.m[p.winner].finish)) winFirst++;
  p.m.forEach((m) => { const lg = m.glides.find((g) => g.kind === "plunge"); const prev = m.glides[m.glides.indexOf(lg) - 1]; maxLastWait = Math.max(maxLastWait, lg.t0 - prev.t1); });
  sumLen += (p.end - p.tLift) / 1000;
}
console.log("wins over 40000 races:", wins.join(" "), " average race", (sumLen / 40000).toFixed(0), "s (doors shut to home)");
ok(Math.max(...wins) / Math.min(...wins) < 1.08, "every marble wins about 1 in 8");
ok(winFirst === 40000, "the drawn marble always finishes first");
console.log("   longest wait at the last gates over 40000 races:", (maxLastWait / 1000).toFixed(1), "s");

// ---------- a full race, sampled every 100 ms of screen time ----------
const wrap = live().find((n) => n.tagName === "M-PROMPT");
wrap.fire("prompt", { value: "1111" }); ok(X.phase === "IDLE", "a wrong code does nothing");
wrap.fire("prompt", { value: "2468" }); ok(X.phase === "BOARDING", "the code starts boarding");
const P = X.plan;
const animsNow = () => live().filter((n) => n.tagName === "M-ATTR-ANIM").length;
console.log("animations made for this race:", animsNow(), " moving solids:", live().filter((n) => n.attrs.collide === "true" && (() => { for (let q = n; q; q = q.parentNode) if (q === roots.race) return true; return false; })()).length);
ok(animsNow() <= 300, "animations in the world: " + animsNow());
const doorShut = () => X.marbles().every((m) => m.door && m.door.isConnected);
ok(!doorShut() && X.bridge.isConnected, "boarding: doors open, bridge out");
// every animation was made well before it starts, and none is ever changed afterwards
const made = live().filter((n) => n.tagName === "M-ATTR-ANIM" && n.attrs.loop === "false");
const minLead = Math.min(...made.map((a) => +a.attrs["start-time"] - ctx.document.timeline.currentTime));
ok(minLead > 15000, "every glide is sent " + (minLead / 1000).toFixed(0) + "+ s before it starts");
const snap = new Map(made.map((a) => [a, JSON.stringify(a.attrs)]));
let prev = null, maxOff = 0, offAt = "", maxFloat = 0, minGap = Infinity, maxV = 0, maxVy = 0, shutSeen = false, bridgeGone = false;
const cross = [];
const finZ = -60;
let elevErr = 0;
for (let t = 0; clock < P.end + 3000; t++) {
  advance(100);
  if (X.phase === "RACE" && clock > P.tLift) { if (doorShut()) shutSeen = true; if (!X.bridge.isConnected) bridgeGone = true; }
  if (clock > P.end - 50) break;
  const pos = X.marbles().map((m) => screenPos(m.pod));
  pos.forEach((p, k) => {
    // on the solid track (or above it, in the air on a ramp / drop / rise)
    const top = deckTop(p[0], p[2]);
    const g = P.m[k].glides.find((q) => clock >= q.t0 && clock < q.t1);
    if (top > -Infinity) {
      const off = top - p[1];
      if (off > maxOff) { maxOff = off; offAt = (g ? g.kind : "parked") + " marble " + k; }
      const onPart = C.traps.concat(C.elevs).some((q) => Math.hypot(q[0] - p[0], q[2] - p[2]) < 4.7);   // a hatch / lift holds it up
      if (g && /roll|slope|mud|lift|plunge|brake/.test(g.kind) && !onPart) maxFloat = Math.max(maxFloat, -off);
    } else if (!g || !/drop|rise|ramp/.test(g.kind)) { maxOff = Math.max(maxOff, 99); offAt = "no deck under marble " + k + " at " + p.map((v) => v.toFixed(1)); }
    if (prev) { maxV = Math.max(maxV, Math.hypot(p[0] - prev[k][0], p[2] - prev[k][2]) / 0.1); maxVy = Math.max(maxVy, Math.abs(p[1] - prev[k][1]) / 0.1); }
    if (prev && prev[k][2] < finZ && p[2] >= finZ && Math.abs(p[0]) < 40 && p[1] < 1) cross.push(k);
  });
  for (let a = 0; a < 8; a++) for (let b = a + 1; b < 8; b++) minGap = Math.min(minGap, Math.hypot(pos[a][0] - pos[b][0], pos[a][1] - pos[b][1], pos[a][2] - pos[b][2]));
  prev = pos;
}
ok(maxOff < 0.1, "every marble stays on (never in) the solid track" + (maxOff > 0.1 ? " - worst " + maxOff.toFixed(2) + " m into it: " + offAt : ""));
ok(maxFloat < 0.1, "rolling marbles sit on the track, not above it (worst " + maxFloat.toFixed(2) + " m)");
ok(minGap > 8.4, "marbles never touch each other (closest centres " + minGap.toFixed(1) + " m, 8 m wide)");
console.log("   fastest on screen", maxV.toFixed(1), "m/s, fastest up/down", maxVy.toFixed(1), "m/s");
ok(cross.length === 8 && cross[0] === P.winner, "the drawn marble crosses the finish line first (order " + cross.join(",") + ", drawn " + P.winner + ")");
ok(shutSeen && bridgeGone, "doors shut and the bridge folded away during the race");
ok([...snap].every(([a, s]) => JSON.stringify(a.attrs) === s), "no animation was changed after it was made");
advance(4000);
ok(X.phase === "IDLE", "race over");
const home = X.marbles().every((m, k) => { const p = screenPos(m.pod), a = C.lanes[k][0].a; return Math.hypot(p[0] - a[0], p[1] - a[1], p[2] - a[2]) < 0.01; });
ok(home && !doorShut() && X.bridge.isConnected, "all home, doors open, bridge back");
ok(animsNow() === 0, "the race's animations all left with their parts (" + animsNow() + " left)");
console.log("   boards:", X.boards[0].map((l) => l._t).join(" | "));
ok(/WINS/.test(X.boards[0][0]._t), "the boards name the winner");
// cancel
wrap.fire("prompt", { value: "2468" }); advance(40000); wrap.fire("prompt", { value: "2468" }); advance(500);
ok(X.phase === "RACE", "one extra code entry does not cancel");
wrap.fire("prompt", { value: "2468" }); advance(500);
ok(X.phase === "IDLE" && animsNow() === 0, "the code twice cancels, everything home");

// ---------- clicks: anything players click must be drawn (visible="false" can't be clicked) ----------
const hidden = (n) => { for (; n; n = n.parentNode) if (n.attrs && n.attrs.visible === "false") return true; return false; };
const prompts = live().filter((n) => n.tagName === "M-PROMPT" && n.attrs.id !== "mr-host");
const targets = []; prompts.forEach((p) => { const w = (n) => { if (n !== p) targets.push(n); n.children.forEach(w); }; w(p); });
ok(prompts.length === 2 && targets.length >= 2 && targets.every((t) => !hidden(t)), "the RACE CONTROL click boxes are drawn see-through, so they can be clicked (" + targets.length + ")");
ok(targets.every((t) => t.attrs.opacity === "0"), "and nobody can see them (opacity 0)");

// ---------- the host remote ----------
const host = live().find((n) => n.attrs.id === "mr-host"), board = live().find((n) => n.attrs.id === "mr-remote");
ok(host && host.tagName === "M-PROMPT" && board && board.attrs["visible-to"] === "-1", "hidden host prompt + remote board (seen by nobody yet)");
const acks = () => JSON.parse(board.attrs["data-ack"] || '{"t":""}').t;
const game = () => JSON.parse(board.attrs["data-game"] || "{}");
win.fire("connected", { connectionId: 3 }); win.fire("connected", { connectionId: 4 }); win.fire("connected", { connectionId: 9 });
host.fire("prompt", { value: "1111 remote", connectionId: 9 });
ok(acks() === "WRONG CODE" && board.attrs["visible-to"] === "-1", "a wrong PIN doesn't unlock");
host.fire("prompt", { value: "2468 remote", connectionId: 9 });
ok(acks() === "UNLOCKED" && board.attrs["visible-to"] === "9", "the right PIN unlocks, and only the remote sees the board");
advance(1100);
let g = game();
ok(g.ph === "idle" && g.online === 2 && g.marbles.length === 8 && g.board === 20, "the board reports the game (" + g.ph + ", " + g.online + " online)");
host.fire("prompt", { value: "2468 board 30", connectionId: 9 });
ok(X.HOST.board === 30, "BOARD 30 sets the boarding time: " + acks());
host.fire("prompt", { value: "2468 kiosks off", connectionId: 9 });
wrap.fire("prompt", { value: "2468" }); advance(100);
ok(X.phase === "IDLE", "kiosks off: the kiosk code no longer starts a race");
host.fire("prompt", { value: "2468 kiosks on", connectionId: 9 });
host.fire("prompt", { value: "2468 start", connectionId: 9 });
ok(X.phase === "BOARDING" && X.plan.tLift - clock === 33000, "START from the remote boards for 30 s: " + acks());
// riders: two players step into marble 2
const floorOf = (k) => X.marbles()[k].pod.children.find((c) => c.tagName === "M-CYLINDER");
floorOf(2).fire("collisionstart", { connectionId: 3 }); floorOf(2).fire("collisionstart", { connectionId: 4 });
advance(1100);
g = game();
ok(g.ph === "boarding" && g.marbles[2].riders === 2 && g.marbles.reduce((a, m) => a + m.riders, 0) === 2, "the remote sees 2 riders in " + g.marbles[2].n);
floorOf(2).fire("collisionend", { connectionId: 4 }); advance(1100);
ok(game().marbles[2].riders === 1, "one steps out: 1 rider");
ok(!game().winner, "the remote is never told the winner before the line");
host.fire("prompt", { value: "2468 auto on", connectionId: 9 });
ok(X.HOST.auto, "AUTO ON: " + acks());
advance(X.plan.end - clock + 1000);
ok(X.phase === "IDLE" && game().nextAt > clock, "race over: the next auto race is queued");
advance(X.HOST.gap * 1000 + 100);
ok(X.phase === "BOARDING", "the next race boards by itself");
host.fire("prompt", { value: "2468 say good luck!", connectionId: 9 }); advance(100);
ok(X.boards[0][0]._t === "GOOD LUCK!", "SAY puts a message on the scoreboards");
host.fire("prompt", { value: "2468 auto off", connectionId: 9 });
host.fire("prompt", { value: "2468 cancel", connectionId: 9 }); advance(500);
ok(X.phase === "IDLE" && animsNow() === 0 && !X.HOST.auto, "CANCEL from the remote: everything home");
host.fire("prompt", { value: "2468 dance", connectionId: 9 });
ok(/^UNKNOWN/.test(acks()), "an unknown command says so");
win.fire("disconnected", { connectionId: 9 });
ok(board.attrs["visible-to"] === "-1", "the remote leaves: nobody sees the board");
ok(X.errs.startsWith("0 "), "no script errors (" + X.errs + ")");
console.log(fails ? fails + " FAILED" : "ALL PASSED");

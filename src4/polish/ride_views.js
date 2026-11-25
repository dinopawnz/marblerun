const { simulateRace } = require("/home/claude/mr4/sim.js");
const C = require("/home/claude/mr4/course.json");
let R; do { R = simulateRace(C, Math.random, Array.from({ length: 8 }, () => 30 + Math.random() * 3), { gScale: 2.0 }); } while (!R.ok);
const m = R.marbles[R.finishOrder[3]], S = m.samples.filter((s) => m.parkAt === null || s[0] <= m.parkAt);
const out = [];
const n = +process.argv[2] || 18;
for (let q = 0; q < n; q++) {
  const i = Math.floor(S.length * (q + 0.3) / n), s = S[i];
  let j = i; while (j < S.length - 1 && Math.hypot(S[j][1] - s[1], S[j][3] - s[3]) < 25) j++;
  const a = S[j];
  const eye = [s[1], s[2] + 3.0, s[3]], look = [a[1], a[2] + 1.0, a[3]];
  out.push({ name: "ride" + String(q).padStart(2, "0"), eye, look, t: s[0] });
}
require("fs").writeFileSync("/home/claude/mr4/polish/views.json", JSON.stringify(out));
console.log(out.map((o) => o.name + " t" + o.t.toFixed(0) + " " + o.eye.map((v) => v.toFixed(0)).join(",")).join("\n"));

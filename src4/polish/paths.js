const { simulateRace } = require("/home/claude/mr4/sim.js");
const C = require("/home/claude/mr4/course.json");
const N = +process.argv[2] || 30, out = [];
let ok = 0;
for (let r = 0; r < N; r++) {
  const lift = Array.from({ length: 8 }, () => 30 + Math.random() * 3);
  const R = simulateRace(C, Math.random, lift, { gScale: 2.0 });
  if (!R.ok) continue; ok++;
  R.marbles.forEach((m) => {
    for (let i = 0; i < m.samples.length; i += 2) { const s = m.samples[i]; if (m.parkAt !== null && s[0] > m.parkAt) break; out.push([+s[1].toFixed(2), +s[2].toFixed(2), +s[3].toFixed(2), s[6], +(4 * (Math.sqrt(1 + s[4] * s[4] + s[5] * s[5]) - 1)).toFixed(3)]); }
  });
}
require("fs").writeFileSync("/home/claude/mr4/polish/paths.json", JSON.stringify(out));
console.log("races ok", ok, "/", N, "samples", out.length);

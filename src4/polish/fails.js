const { simulateRace } = require(process.argv[3] || "/home/claude/mr4/sim.js");
const C = require("/home/claude/mr4/course.json");
const N = +process.argv[2] || 30; let bad = 0;
for (let r = 0; r < N; r++) {
  const R = simulateRace(C, Math.random, Array.from({ length: 8 }, () => 30 + Math.random() * 3), { gScale: 2.0 });
  if (R.ok) continue; bad++;
  console.log("FAIL", R.marbles.map((m) => m.phase + "@" + m.sec + " (" + m.x.toFixed(0) + "," + m.y.toFixed(0) + "," + m.z.toFixed(0) + ")" + (m.finish ? " fin" + m.finish.toFixed(0) : "")).join(" | "));
}
console.log("failed", bad, "/", N);

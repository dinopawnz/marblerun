// THE GRAND MARBLE RUN - race physics. Shared by the game (pasted in by assemble.py) and the tests.
// simulateRace(C, rnd, lift) rolls all eight marbles from the top of the lift hill to their parking
// slots at the station: gravity on the slopes, rolling friction (more in the mud), air drag, drops,
// walls, the curved corner walls, pegs, bumpers, the funnel and the split - and each other.
// Times are seconds after the lift starts. Positions are the deck point under the marble's centre.
/* SIM-START */
function simulateRace(C, rnd, lift, tune) {
  const T = Object.assign({ drag: 0.0008, eBall: 0.7, eWall: 0.35, wallFriction: 0.08, noise: 0.25, noiseTau: 1.5, roll: 0.006, gScale: 1 }, tune || {});
  const G = 9.81 * T.gScale, ROLL = 5 / 7, MR = C.mr, DT = 1 / 120, SAMPLE = 0.05;
  const DRAG = T.drag, E_BALL = T.eBall, E_WALL = T.eWall, WALL_FRICTION = T.wallFriction;
  const NOISE = T.noise, NOISE_TAU = T.noiseTau;
  const S = C.sections, NS = S.length, LAST = NS - 1, FIN = C.finish.t;
  const homes = C.homes, tops = C.tops, K = homes.length;
  const lastRun = S[LAST];
  const gauss = () => { let u = 0; for (let i = 0; i < 6; i++) u += rnd(); return (u - 3) * Math.SQRT2; };

  // ---- the course, in each section's own terms
  const loc = (s, x, z) => { const dx = x - s.P[0], dz = z - s.P[1]; return [dx * s.d[0] + dz * s.d[1], dx * s.n[0] + dz * s.n[1]]; };
  function profAt(s, t) {           // deck height and slope (dy/dt) along a run
    const p = s.prof;
    if (t <= p[0][0]) return [p[0][1], p.length > 1 && p[1][0] > p[0][0] ? (p[1][1] - p[0][1]) / (p[1][0] - p[0][0]) : 0];
    for (let q = 0; q < p.length - 1; q++) {
      const a = p[q], b = p[q + 1];
      if (t >= a[0] && t < b[0]) return [a[1] + (b[1] - a[1]) * (t - a[0]) / (b[0] - a[0]), (b[1] - a[1]) / (b[0] - a[0])];
    }
    return [p[p.length - 1][1], 0];
  }
  function cornerY(s, x, z) {       // the banked bowl (same formula as course.py corner_height)
    const vx = x - s.I[0], vz = z - s.I[1];
    let a = Math.atan2(vx * s.din[0] + vz * s.din[1], -(vx * s.dout[0] + vz * s.dout[1]));
    a = Math.max(0, Math.min(Math.PI / 2, a));
    const r = Math.min(Math.hypot(vx, vz), s.R);
    return s.yin + (s.yout - s.yin) * a / (Math.PI / 2) + s.bank * Math.sin(2 * a) * Math.pow(r / s.R, 2.5);
  }
  function surface(m) {             // [deck height, downhill gradient x, z] where marble m is
    const s = S[m.sec];
    if (s.type === "corner") {
      // the marble rides on the banked bowl, but only the bank's slope ACROSS the turn pushes it
      // (as on a real banked curve); along the turn it just feels the gentle fall.
      const vx = m.x - s.I[0], vz = m.z - s.I[1], r = Math.max(0.5, Math.hypot(vx, vz));
      let a = Math.atan2(vx * s.din[0] + vz * s.din[1], -(vx * s.dout[0] + vz * s.dout[1]));
      a = Math.max(0, Math.min(Math.PI / 2, a));
      const rr = Math.min(r, s.R);
      const dydr = s.bank * Math.sin(2 * a) * 2.5 * Math.pow(rr / s.R, 1.5) / s.R;
      const dyds = (s.yout - s.yin) / (Math.PI / 2) / r;          // the fall round the turn, per metre
      const rx = vx / r, rz = vz / r;                              // outward from the inner corner
      const sg = Math.sign(s.dout[1] * s.din[0] - s.dout[0] * s.din[1]);
      const qx = -sg * rz, qz = sg * rx;                           // the way round the turn
      return [cornerY(s, m.x, m.z), dydr * rx + dyds * qx, dydr * rz + dyds * qz];
    }
    const [t] = loc(s, m.x, m.z);
    const [y, k] = profAt(s, t);
    return [y, k * s.d[0], k * s.d[1]];
  }
  function updateSection(m) {
    for (let guard = 0; guard < 3; guard++) {
      const s = S[m.sec];
      if (s.type === "run") {
        const [t] = loc(s, m.x, m.z);
        if (t > s.t1 && m.sec < LAST) { m.sec++; continue; }
        if (t < s.t0 && m.sec > 0) { m.sec--; continue; }
      } else {
        const nx = S[m.sec + 1], pv = S[m.sec - 1];
        if (loc(nx, m.x, m.z)[0] > nx.t0) { m.sec++; continue; }
        if (loc(pv, m.x, m.z)[0] < pv.t1) { m.sec--; continue; }
      }
      break;
    }
  }

  // ---- ledges (a run's sudden drops): a marble going over one rolls round its edge like a real ball,
  //      instead of its body passing into the cliff
  S.forEach((s) => {
    s.ledges = [];
    if (s.type !== "run") return;
    for (let q = 0; q < s.prof.length - 1; q++) {
      const a = s.prof[q], b = s.prof[q + 1];
      if (Math.abs(b[0] - a[0]) < 0.01 && a[1] - b[1] > 0.5) s.ledges.push([a[0], a[1], b[1]]);     // [where, top, bottom]
    }
  });
  function ledge(m) {
    const s = S[m.sec];
    if (s.type !== "run" || !s.ledges.length) return;
    const t = loc(s, m.x, m.z)[0];
    for (const [te, ye] of s.ledges) {
      const dt = t - te, dy = m.y + MR - ye, d = Math.hypot(dt, dy);
      // (centre above the edge and past it: roll round the edge; only ever forward, off the edge)
      if (dt < 0 || dt > MR || dy <= 0 || d >= MR || d < 1e-6) continue;
      const nt = dt / d, ny = dy / d, push = MR - d;
      m.x += s.d[0] * nt * push; m.z += s.d[1] * nt * push; m.y += ny * push;
      const vt = m.vx * s.d[0] + m.vz * s.d[1], vn = vt * nt + m.vy * ny;
      if (vn < 0) { m.vx -= vn * nt * s.d[0]; m.vz -= vn * nt * s.d[1]; m.vy -= vn * ny; }
    }
  }

  // the cliff under a ledge: a marble down on the lower deck can't roll back in under it
  function cliff(m) {
    const s = S[m.sec];
    if (s.type !== "run" || !s.ledges.length) return;
    const t = loc(s, m.x, m.z)[0];
    for (const [te, ye] of s.ledges) {
      // a marble whose centre is below the edge, right by the cliff face: the face is a wall
      if (m.y + MR >= ye || t >= te + MR || t < te - 2 * MR) continue;
      const push = te + MR - t;
      m.x += s.d[0] * push; m.z += s.d[1] * push;
      const vt = m.vx * s.d[0] + m.vz * s.d[1];
      if (vt < 0) { m.vx -= (1 + E_WALL) * vt * s.d[0]; m.vz -= (1 + E_WALL) * vt * s.d[1]; m.bumps++; }
    }
  }

  // ---- collisions with the course
  function hitPoint(m, cx, cz, rad, e) {        // round post (or a wall's nearest point)
    const dx = m.x - cx, dz = m.z - cz, d = Math.hypot(dx, dz), min = MR + rad;
    if (d >= min || d < 1e-6) return;
    const nx = dx / d, nz = dz / d;
    m.x = cx + nx * min; m.z = cz + nz * min;
    const vn = m.vx * nx + m.vz * nz;
    if (vn < 0) {
      const tx = -nz, tz = nx, vt = m.vx * tx + m.vz * tz;
      const vt2 = vt - Math.sign(vt) * Math.min(Math.abs(vt), WALL_FRICTION * (1 + e) * -vn);
      const vn2 = -e * vn;
      m.vx = nx * vn2 + tx * vt2; m.vz = nz * vn2 + tz * vt2;
      m.bumps++;
    }
  }
  function hitWall(m, w, e) {
    const ax = w[0], az = w[1], bx = w[2], bz = w[3];
    const ex = bx - ax, ez = bz - az, L2 = ex * ex + ez * ez;
    let u = ((m.x - ax) * ex + (m.z - az) * ez) / L2;
    u = Math.max(0, Math.min(1, u));
    hitPoint(m, ax + ex * u, az + ez * u, w[4] || 0, e);     // (w[4]: half the rail's thickness)
  }
  function collideCourse(m) {
    for (let q = Math.max(0, m.sec - 1); q <= Math.min(LAST, m.sec + 1); q++) {
      const s = S[q];
      if (s.type === "run") {
        s.walls.forEach((w) => hitWall(m, w, E_WALL));
        s.circles.forEach((c) => hitPoint(m, c[0], c[1], c[2], c[3]));
      } else {
        hitPoint(m, s.I[0], s.I[1], 0.3, E_WALL);              // the inner corner
        if (q === m.sec) {                                     // the curved outer wall
          const dx = m.x - s.I[0], dz = m.z - s.I[1], r = Math.hypot(dx, dz), max = s.R - MR;
          if (r > max) {
            const nx = -dx / r, nz = -dz / r;                  // pointing inward
            m.x = s.I[0] - nx * max; m.z = s.I[1] - nz * max;
            const vn = m.vx * nx + m.vz * nz;
            if (vn < 0) {
              const tx = -nz, tz = nx, vt = m.vx * tx + m.vz * tz;
              const vt2 = vt - Math.sign(vt) * Math.min(Math.abs(vt), WALL_FRICTION * (1 + E_WALL) * -vn);
              m.vx = nx * (-E_WALL * vn) + tx * vt2; m.vz = nz * (-E_WALL * vn) + tz * vt2;
            }
          }
        }
      }
    }
  }

  // ---- the marbles
  const M = [];
  for (let k = 0; k < K; k++) {
    const L = lift[k];                     // seconds this marble takes up the lift
    const vz = C.lift_len / L;
    M.push({ k, x: tops[k][0], y: tops[k][1], z: tops[k][2], vx: 0, vz: vz, vy: 0, sec: 0, air: false,
      on: false, rel: L, nx: 0, nz: 0, phase: "race", finish: null, parkAt: null, bumps: 0, wp: 0,
      samples: [], progress: [], secTime: [], secAt: [] });
  }
  // progress along the course (metres from the top of the lift) for the scoreboards
  const secStart = []; let acc = 0;
  S.forEach((s, q) => { secStart[q] = acc; acc += s.type === "run" ? s.t1 - s.t0 : Math.PI / 2 * C.half; });
  function progressOf(m) {
    const s = S[m.sec];
    if (s.type === "run") return secStart[m.sec] + Math.max(0, Math.min(s.t1 - s.t0, loc(s, m.x, m.z)[0] - s.t0));
    const dx = m.x - s.I[0], dz = m.z - s.I[1];
    const a = Math.atan2(dx * s.din[0] + dz * s.din[1], -(dx * s.dout[0] + dz * s.dout[1]));
    return secStart[m.sec] + Math.max(0, Math.min(1, a / (Math.PI / 2))) * Math.PI / 2 * C.half;
  }

  const finishOrder = [];
  let t = 0, nextSample = 0, ended = null;
  const firstRel = Math.min(...lift), LIMIT = firstRel + 600;
  const ON_LIFT = (m, tt) => { const f = Math.min(1, tt / m.rel); return [homes[m.k][0], homes[m.k][1] + (tops[m.k][1] - homes[m.k][1]) * f, homes[m.k][2] + (tops[m.k][2] - homes[m.k][2]) * f]; };
  while (t < LIMIT) {
    // release
    M.forEach((m) => { if (!m.on && t >= m.rel) { m.on = true; m.x = tops[m.k][0]; m.y = tops[m.k][1]; m.z = tops[m.k][2]; m.vx = gauss() * 0.4; m.vz = C.lift_len / m.rel + gauss() * 0.3; } });
    const live = M.filter((m) => m.on && m.phase !== "parked");
    live.forEach((m) => {
      const [ys, gx, gz] = surface(m);
      let ax = 0, az = 0;
      if (!m.air) { const g2 = 1 + gx * gx + gz * gz; ax -= G * ROLL * gx / g2; az -= G * ROLL * gz / g2; }
      const sp = Math.hypot(m.vx, m.vz);
      if (!m.air && sp > 1e-3) {
        const mu = S[m.sec].type === "run" ? S[m.sec].mu * T.roll / 0.012 : T.roll;
        const f = Math.min(mu * G, sp / DT);
        ax -= f * m.vx / sp; az -= f * m.vz / sp;
      }
      ax -= DRAG * sp * m.vx; az -= DRAG * sp * m.vz;
      if (m.phase === "race" && !m.air) {
        // a marble that has come to rest is shaken loose (as a real track's vibration would)
        m.slow = sp < 0.4 ? (m.slow || 0) + DT : 0;
        // (or one rocking back and forth without getting anywhere)
        const pg = progressOf(m);
        if (m.best === undefined || pg > m.best + 2) { m.best = pg; m.bestAt = t; }
        else if (t - m.bestAt > 6) { m.slow = 99; m.bestAt = t; }
        if (m.slow > 3) {
          m.slow = 0;
          const sd = S[m.sec];
          if (sd.type === "run") { const f = 3 + rnd() * 3; m.vx += sd.d[0] * f + gauss() * 1.2; m.vz += sd.d[1] * f + gauss() * 1.2; }   // on down the run
          else { m.vx += gauss() * 2.5; m.vz += gauss() * 2.5; }
        }
        // track imperfections: a gentle wandering push
        const c = Math.sqrt(2 * DT / NOISE_TAU) * NOISE;
        m.nx += -m.nx * DT / NOISE_TAU + c * gauss(); m.nz += -m.nz * DT / NOISE_TAU + c * gauss();
        ax += m.nx; az += m.nz;
      }
      if (m.phase === "brake" || m.phase === "park") {
        // after the line: the station's brakes, then each marble rolls itself into its own slot
        const s = lastRun, [tt, uu] = loc(s, m.x, m.z);
        const home = homes[m.k], hl = loc(s, home[0], home[2]);
        if (m.phase === "brake") {
          const left = Math.max(2, hl[0] - 14 - tt);
          const need = (m.vx * s.d[0] + m.vz * s.d[1]) ** 2 / (2 * left);
          const b = Math.min(5, Math.max(1.2, need));
          if (sp > 0.05) { ax -= b * m.vx / sp; az -= b * m.vz / sp; }
          if (sp < 2.2 || tt > hl[0] - 14) m.phase = "park";
        } else {
          const wp = Math.abs(uu - hl[1]) > 0.8 ? [Math.min(tt, hl[0] - 14), hl[1]] : [hl[0], hl[1]];
          const tw = s.P[0] + s.d[0] * wp[0] + s.n[0] * wp[1], tz = s.P[1] + s.d[1] * wp[0] + s.n[1] * wp[1];
          const ex = tw - m.x, ez = tz - m.z, dist = Math.hypot(ex, ez);
          const want = Math.min(5, dist * 1.2);
          const dvx = (dist > 1e-6 ? ex / dist * want : 0) - m.vx, dvz = (dist > 1e-6 ? ez / dist * want : 0) - m.vz;
          const dv = Math.hypot(dvx, dvz), cap = 3.5;
          ax = (dv > cap ? dvx / dv * cap : dvx) + 0 * ax; az = (dv > cap ? dvz / dv * cap : dvz);
          if (Math.hypot(m.x - home[0], m.z - home[2]) < 0.12 && sp < 0.4) {
            m.phase = "parked"; m.x = home[0]; m.z = home[2]; m.y = home[1]; m.vx = m.vz = m.vy = 0; m.parkAt = t;
          }
        }
      }
      m.vx += ax * DT; m.vz += az * DT;
    });
    live.forEach((m) => {
      if (m.phase === "parked") return;
      const [y0] = surface(m);
      m.x += m.vx * DT; m.z += m.vz * DT;
      updateSection(m);
      cliff(m);
      const [y1] = surface(m);
      if (m.air) {
        m.vy -= G * DT; m.y += m.vy * DT;
        if (m.y <= y1) { m.y = y1; m.air = false; m.vy = 0; }
      } else if (y1 < m.y - 0.25) {            // rolled off a drop
        m.air = true; m.vy = (y1 - y0) / DT > -2 ? (y1 - y0) / DT : 0;
        m.vy = Math.max(m.vy, -1); m.vy -= G * DT; m.y += m.vy * DT;
      } else { m.vy = (y1 - m.y) / DT; m.y = y1; }
      if (m.air) ledge(m);
      collideCourse(m);
    });
    // marble on marble (marbles still on the lift and parked ones don't move)
    M.forEach((m) => { if (!m.on) { const p = ON_LIFT(m, t); m.x = p[0]; m.y = p[1]; m.z = p[2]; } });
    for (let a = 0; a < K; a++) for (let b = a + 1; b < K; b++) {
      const A = M[a], B = M[b];
      const fa = !A.on || A.phase === "parked", fb = !B.on || B.phase === "parked";
      if (fa && fb) continue;
      const dx = B.x - A.x, dy = B.y - A.y, dz = B.z - A.z;
      const d2 = dx * dx + dy * dy + dz * dz;
      if (d2 >= 4 * MR * MR || d2 < 1e-9) continue;
      const d = Math.sqrt(d2), nx = dx / d, ny = dy / d, nz = dz / d, over = 2 * MR - d;
      const wa = fa ? 0 : fb ? 1 : 0.5, wb = 1 - wa;
      const RA = M[a], RB = M[b];
      RA.x -= nx * over * wa; RA.z -= nz * over * wa; RB.x += nx * over * wb; RB.z += nz * over * wb;
      const rv = (RB.vx - RA.vx) * nx + (RB.vz - RA.vz) * nz;
      if (rv < 0) {
        const j = -(1 + E_BALL) * rv * (fa || fb ? 1 : 0.5);
        if (!fa) { RA.vx -= j * nx * (fb ? 1 : 1); RA.vz -= j * nz; RA.bumps++; }
        if (!fb) { RB.vx += j * nx; RB.vz += j * nz; RB.bumps++; }
      }
    }
    // the line, and the record
    M.forEach((m) => {
      if (m.on && m.finish === null && m.sec === LAST && loc(lastRun, m.x, m.z)[0] >= FIN) {
        m.finish = t; finishOrder.push(m.k); m.phase = "brake";
      }
    });
    if (t >= nextSample - 1e-9) {
      M.forEach((m) => {
        if (!m.on) return;
        // a ball on a slope touches it a little above the point under its centre
        let lift = 0, gx = 0, gz = 0;
        if (!m.air) {
          [, gx, gz] = surface(m);
          const sc = S[m.sec];
          if (sc.type === "corner") {        // the bowl's full tilt (the forces above only use part of it)
            gx = (cornerY(sc, m.x + 0.25, m.z) - cornerY(sc, m.x - 0.25, m.z)) / 0.5;
            gz = (cornerY(sc, m.x, m.z + 0.25) - cornerY(sc, m.x, m.z - 0.25)) / 0.5;
          }
          lift = MR * (Math.sqrt(1 + gx * gx + gz * gz) - 1);
        }
        m.samples.push([Math.round(t * 1000) / 1000, m.x, m.y + lift, m.z, gx, gz, m.air ? 1 : 0]);
        if (m.secTime) m.secTime[m.sec] = (m.secTime[m.sec] || 0) + SAMPLE;
        m.secAt.push(m.sec);
        m.progress.push(m.finish === null ? progressOf(m) : 1e6 - m.finish);
      });
      nextSample += SAMPLE;
    }
    if (M.every((m) => m.phase === "parked")) {
      ended = t;
      M.forEach((m) => { const last = m.samples[m.samples.length - 1]; if (last[0] < t - 1e-6) { m.samples.push([Math.round(t * 1000) / 1000 + 0.001, m.x, m.y, m.z, 0, 0, 0]); m.progress.push(m.progress[m.progress.length - 1]); } });
      break;
    }
    t += DT;
  }
  return { ok: ended !== null, end: ended, finishOrder, marbles: M, sampleDt: SAMPLE, length: acc };
}

// Fit one coordinate's samples with as few straight glides as keep within tol (greedy).
function fitAxis(ts, vs, tol) {
  const out = [0];
  let i = 0;
  const n = ts.length;
  while (i < n - 1) {
    let j = i + 1, best = j;
    while (j < n) {
      let ok = true;
      const t0 = ts[i], t1 = ts[j], v0 = vs[i], v1 = vs[j];
      for (let q = i + 1; q < j; q++) {
        const f = (ts[q] - t0) / (t1 - t0);
        if (Math.abs(v0 + (v1 - v0) * f - vs[q]) > tol) { ok = false; break; }
      }
      if (!ok) break;
      best = j; j++;
    }
    out.push(best); i = best;
  }
  return out.map((q) => [ts[q], vs[q]]);       // knots: [time, value]
}
/* SIM-END */
if (typeof module !== "undefined") module.exports = { simulateRace, fitAxis };

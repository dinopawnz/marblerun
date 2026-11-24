<script>
/* THE GRAND MARBLE RUN - host remote. Types "<PIN> <command>" into the game's hidden host prompt (mr-host);
   the game answers on its remote board (mr-remote), which only remotes ever receive (visible-to).
   PIN = RACE_CODE in grand_marble_run_v2.html, 2468 unless you changed it. */
(function () {
  const { h, setText, clock } = Remote;
  const PH = { idle: ["WAITING", "idle"], boarding: ["BOARDING", "count"], lift: ["UP THE LIFT HILL", "play"], race: ["RACING", "play"], finished: ["WE HAVE A WINNER", "over"] };
  const ui = {};
  Remote.start({
    key: "mr", title: "Grand Marble Run", doc: "grand_marble_run_v2.html", boardId: "mr-remote", prefix: "mr", pin: "2468", mode: "prompt", promptId: "mr-host",
    tag: "Host remote. Start races, run them back to back, and watch who's in which marble - from anywhere.",
    build(R) {
      // ---- the race
      let p = R.panel(R.left, "The race", "eight marbles, pure luck");
      ui.phase = h("span", { class: "chip" }); ui.big = h("span", { class: "big" }); ui.what = h("span", { class: "note", style: { margin: 0 } });
      p.append(h("div", { class: "statusline" }, ui.phase, ui.big, ui.what));
      ui.bar = h("b"); p.append(h("div", { class: "bar" }, ui.bar));
      ui.st = R.stats(p, [["online", "In the world"], ["in", "In a marble"], ["board", "Boarding time"], ["winner", "Last winner"]]);
      let g = R.grid(p);
      ui.startB = R.btn(g, "START A RACE", "opens boarding - players walk into a marble", () => R.say("start"), { cls: "b-go big1" });
      ui.cancelB = R.btn(g, "CANCEL THE RACE", "every marble goes straight home", () => R.say("cancel"), { cls: "b-stop big1",
        confirm: () => (ui.ph === "idle" ? "" : "Cancel this race? The marbles go straight back to the station and anyone inside drops onto the track (harmless).") });
      R.note(p, ["Press ", { b: "START" }, " and the bridge opens for the boarding time. Then the doors shut and the lift hill carries all eight up. ",
        "A race takes about 4 minutes, start to home. The winner is drawn at random every race - 1 in 8 for every marble."]);

      // ---- running it
      p = R.panel(R.left, "Running it", "set it and forget it");
      g = R.grid(p);
      ui.autoB = R.btn(g, "AUTO RACES: OFF", "start a new race by itself after each one", () => R.say(ui.auto ? "auto off" : "auto on"), { cls: "big1" });
      ui.musicB = R.btn(g, "RACE MUSIC: ON", "the music playing inside the marbles", () => R.say(ui.music ? "music off" : "music on"), { cls: "big1" });
      ui.kioskB = R.btn(g, "KIOSKS: ON", "the RACE CONTROL kiosks at the station", () => R.say(ui.kiosks ? "kiosks off" : "kiosks on"), { cls: "big1" });
      ui.gapC = R.choices(p, "Wait between auto races", [[15, "15 s"], [30, "30 s"], [60, "1 min"], [120, "2 min"], [300, "5 min"]], (v) => R.say("gap " + v), (v) => v + " s");
      ui.boardC = R.choices(p, "Boarding time (how long the bridge is open)", [[10, "10 s"], [20, "20 s"], [30, "30 s"], [45, "45 s"], [60, "1 min"]], (v) => R.say("board " + v), (v) => v + " s");
      R.note(p, [{ b: "AUTO RACES ON" }, " = races run back to back on their own until you switch it off. ",
        { b: "KIOSKS OFF" }, " = players can't start races at the station with the code - only you, from here."]);

      // ---- the scoreboards
      p = R.panel(R.left, "The scoreboards", "put a message on all three boards for 10 s");
      const sayIn = h("input", { type: "text", maxlength: "28", placeholder: "e.g. FINAL RACE OF THE NIGHT", "aria-label": "Message for the scoreboards" });
      const send = () => { const t = sayIn.value.trim(); if (!t) return false; R.say("say " + t); sayIn.value = ""; return true; };
      sayIn.addEventListener("keydown", (e) => { if (e.key === "Enter") send(); });
      p.append(h("div", { class: "sayrow" }, sayIn, R.btn(null, "SHOW IT", null, send, { cls: "b-sky" })));
      g = R.grid(p, "narrow"); g.style.marginTop = "10px";
      ["GOOD LUCK!", "GET IN A MARBLE!", "NEXT RACE SOON", "LAST RACE!", "THANKS FOR PLAYING"].forEach((t) => R.btn(g, t, null, () => R.say("say " + t)));

      // ---- the marbles
      p = R.panel(R.right, "The marbles", "who's riding, and the live order");
      ui.tbl = R.table(p, ["#", "Marble", "Riders", "Result"], "Connect to see the marbles.");
      R.note(p, "Riders = players standing inside that marble right now. The order fills in once the race is rolling.");

      p = R.panel(R.right, "Help");
      const cheat = h("details", { class: "cheat" }, h("summary", { text: "How do I connect?" }),
        h("dl", null,
          h("dt", { text: "1. The address" }), h("dd", { text: "Paste the same wss:// address your Otherside world uses for the marble run document." }),
          h("dt", { text: "2. The PIN" }), h("dd", { text: "The race code - 2468, unless you changed RACE_CODE in the game file." }),
          h("dt", { text: "3. Connect" }), h("dd", { text: "The dot goes green when you're in control. The game itself doesn't change for players." }),
          h("dt", { text: "Nothing happens?" }), h("dd", { text: "Make sure the world has the NEW game file (this remote needs it), then reconnect." })));
      p.append(cheat);
    },
    render(R) {
      const G = R.data.game;
      if (!G) return;
      const t = R.serverNow();
      ui.ph = G.ph; ui.auto = G.auto; ui.kiosks = G.kiosks;
      const ph = PH[G.ph] || [String(G.ph).toUpperCase(), "idle"];
      setText(ui.phase, ph[0]); ui.phase.className = "chip " + ph[1];
      let big = "", what = "", frac = 0;
      if (G.ph === "boarding") { big = clock(G.closeAt - t); what = "until the doors shut"; frac = 1 - (G.closeAt - t) / (G.board * 1000); }
      else if (G.ph === "lift") { big = clock(G.raceAt - t); what = "until they roll off the top"; frac = 1 - (G.raceAt - t) / (G.raceAt - G.liftAt); }
      else if (G.ph === "race") { big = clock(t - G.raceAt); what = "racing"; frac = (t - G.raceAt) / (G.endAt - G.raceAt); }
      else if (G.ph === "finished") { big = G.winner; what = "wins! Marbles rolling home in " + clock(G.endAt - t); frac = 1; }
      else if (G.nextAt > t) { big = clock(G.nextAt - t); what = "until the next auto race"; frac = 0; }
      else { big = "READY"; what = G.kiosks ? "press START (or type the code at a kiosk)" : "press START"; }
      setText(ui.big, big); setText(ui.what, what);
      ui.bar.style.width = Math.max(0, Math.min(100, frac * 100)) + "%";
      if (G.winner) ui.lastWinner = G.winner;
      const inMarbles = (G.marbles || []).reduce((a, m) => a + (m.riders || 0), 0);
      setText(ui.st.online, G.online); setText(ui.st.in, inMarbles); setText(ui.st.board, G.board + " s"); setText(ui.st.winner, ui.lastWinner || "-");
      R.lit(ui.startB, G.ph === "boarding");
      setText(ui.autoB.lab, "AUTO RACES: " + (G.auto ? "ON" : "OFF")); R.lit(ui.autoB, G.auto);
      ui.music = G.music !== false;
      setText(ui.musicB.lab, "RACE MUSIC: " + (ui.music ? "ON" : "OFF")); R.lit(ui.musicB, ui.music);
      setText(ui.kioskB.lab, "KIOSKS: " + (G.kiosks ? "ON" : "OFF")); ui.kioskB.className = "btn big1 " + (G.kiosks ? "b-go" : "b-warn");
      ui.gapC.set(G.gap); ui.boardC.set(G.board);
      const ms = (G.marbles || []).slice();
      const racing = ms.some((m) => m.pos > 0);
      if (racing) ms.sort((a, b) => a.pos - b.pos);
      ui.tbl.render(ms, (m) => m.n,
        () => { const r = { c: [h("td", { class: "num" }), h("td"), h("td"), h("td")] }; r.el = h("tr", null, r.c); r.tm = h("span", { class: "tm" }); r.c[1].append(r.tm); return r; },
        (r, m) => {
          setText(r.c[0], m.pos ? m.pos : "");
          setText(r.tm, m.n); r.tm.style.color = m.c; r.tm.style.boxShadow = "inset 0 0 0 1px " + m.c;
          setText(r.c[2], m.riders ? m.riders : "-");
          setText(r.c[3], m.done ? (m.gap === 0 ? "WINNER" : "+" + (m.gap / 1000).toFixed(1) + " s") : racing ? "rolling" : "");
          r.c[3].className = m.done && m.gap === 0 ? "hero" : "";
        });
      if (G.errors) R.event("The game hit " + G.errors + " script error(s): " + G.lastError);
    },
  });
})();
</script>
</body>
</html>

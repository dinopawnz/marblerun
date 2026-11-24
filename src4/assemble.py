import json, re
c = json.load(open("/home/claude/mr4/course.json"))
w = json.load(open("/home/claude/mr4/out/world4.json"))
sim = open("/home/claude/mr4/sim.js").read()
sim = sim[sim.index("/* SIM-START */"):sim.index("/* SIM-END */") + len("/* SIM-END */")]
t = open("/home/claude/mr4/game_template.html").read()
t = t.replace("/*COURSE*/null", json.dumps(c, separators=(",", ":"))).replace("/*WORLD*/null", json.dumps(w, separators=(",", ":")))
t = t.replace("/*SIM*/", "\n".join("  " + l if l.strip() else "" for l in sim.split("\n")))
open("/home/claude/mr4/grand_marble_run_v4.html", "w").write(t)
print(len(t) // 1024, "KB")

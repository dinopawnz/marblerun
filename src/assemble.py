import json, re
c = json.load(open("/home/claude/mr/course.json"))
w = json.load(open("/home/claude/mr/out/world.json"))
sim = open("/home/claude/mr/sim.js").read()
sim = sim[sim.index("/* SIM-START */"):sim.index("/* SIM-END */") + len("/* SIM-END */")]
t = open("/home/claude/mr/game_template.html").read()
t = t.replace("/*COURSE*/null", json.dumps(c, separators=(",", ":"))).replace("/*WORLD*/null", json.dumps(w, separators=(",", ":")))
t = t.replace("/*SIM*/", "\n".join("  " + l if l.strip() else "" for l in sim.split("\n")))
open("/home/claude/mr/grand_marble_run_v2.html", "w").write(t)
print(len(t) // 1024, "KB")

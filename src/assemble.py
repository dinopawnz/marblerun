import json
c = json.load(open("/home/claude/mr/course.json"))
for lane in c["lanes"]:
    for g in lane:
        for k in ("hold",):
            if g[k] is None: del g[k]
w = json.load(open("/home/claude/mr/out/world.json"))
t = open("/home/claude/mr/game_template.html").read()
t = t.replace("/*COURSE*/null", json.dumps(c, separators=(",", ":"))).replace("/*WORLD*/null", json.dumps(w, separators=(",", ":")))
open("/home/claude/mr/grand_marble_run_v2.html", "w").write(t)
print(len(t) // 1024, "KB")

import sys, json
sys.argv = ["x"]
exec(open("/home/claude/mr4/render4.py").read().split('if __name__ == "__main__" and "--props"')[0])
src = open("/home/claude/mr4/render4.py").read()
exec(src[src.index("def world("):src.index("def marbles(")])
import os
V = json.load(open("/home/claude/mr4/polish/views.json"))
only = os.environ.get("ONLY")
sc = setup(samples=int(os.environ.get("SAMPLES", "12")), res=(960, 540))
world()
for v in V:
    if only and v["name"] not in only.split(","): continue
    shot(v["name"], v["eye"], v["look"], 22, sc)

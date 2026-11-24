# The Grand Marble Run

A luck-only marble race for Otherside (MML). Eight giant glass marbles you ride inside,
a 70 m lift hill, and obstacles: The Drop, The Stairs, The Gates, The Mud, The Trapdoors,
The Elevators, The Last Gates and The Plunge.

- `grand_marble_run_v2.html` - the game (paste into Otherside)
- `marble_run_remote.html` - the host remote (open in any browser; PIN = the race code, 2468)
- `models/` - every model, built in Blender, packed with meshopt + gzip
- `src/` - how they were made: `course.py` (the course), `build_world.py`, `build_marbles.py`
- `previews/` - Blender renders

The game loads its models through a link pinned to one commit (`BASE` near the top of the game),
so Otherside never serves an old copy. After changing a model: push it, then put the new commit
in `BASE`.

v3 - real physics. The marbles roll freely (no lanes), bump each other, ride the banked corners and
bounce through open obstacles (pinball posts, bumpers, a funnel, a split). The server works the race out
in advance (`src/sim.js`), draws it as dated glides, and hands each marble to a fresh chain of glides every
11 s so spent animations are thrown away. The winner is still drawn 1 in 8 first.

Checks before every release (in `src/`):
- `node verify3.js ../grand_marble_run_v2.html` - plays a whole race in a fake world: physics followed,
  no jumps, floors always under riders, hand-overs line up, animation and moving-solid budgets, the remote.
- `python3 zfight.py <models>` - finds surfaces that would flicker (two faces the same way, under 8 cm apart).

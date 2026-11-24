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

Checks before every release (in `src/`):
- `node verify.js ../grand_marble_run_v2.html` - plays whole races in a fake world: fairness, solid track,
  animations made ahead and never changed, clickable kiosks, the host remote's commands.
- `python3 zfight.py <models>` - finds surfaces that would flicker (two faces the same way, under 8 cm apart).
  `place_obstacles.py` puts the gates, hatches and lifts where they rest so they are checked against the track too.

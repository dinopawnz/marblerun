# The Grand Marble Run

A luck-only marble race for Otherside (MML). Eight giant glass marbles you ride inside,
a 70 m lift hill, and obstacles: The Drop, The Stairs, The Gates, The Mud, The Trapdoors,
The Elevators, The Last Gates and The Plunge.

- `grand_marble_run_v2.html` - the game (paste into Otherside)
- `models/` - every model, built in Blender, packed with meshopt + gzip
- `src/` - how they were made: `course.py` (the course), `build_world.py`, `build_marbles.py`
- `previews/` - Blender renders

The game loads models from the `v1` tag. After changing a model, upload it and make a new tag
(v2, v3...) and change `BASE` in the game, so Otherside never serves an old copy.

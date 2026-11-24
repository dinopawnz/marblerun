#!/bin/sh
# static models: dedup + meshopt + gzip. Animated props: dedup + gzip only (keep their skins plain). Collider: plain.
set -e
cd /home/claude/mr4
ANIM="mr4_mush_m mr4_mush_c mr4_mush_l mr4_fern_g mr4_fern_v mr4_fronds_g mr4_fronds_v mr4_willow mr4_island_a mr4_island_b mr4_jelly_a mr4_jelly_b"
for f in out/mr4_*.glb; do
  n=$(basename "$f" .glb)
  case "$n" in mr4_collide_raw|mr4_groundtest) continue;; mr4_collide) cp "$f" pack/; continue;; esac
  gltf-transform dedup "$f" /tmp/pw4/$n.a.glb >/dev/null
  if echo " $ANIM " | grep -q " $n "; then cp /tmp/pw4/$n.a.glb /tmp/pw4/$n.glb; else gltf-transform meshopt /tmp/pw4/$n.a.glb /tmp/pw4/$n.glb >/dev/null; fi
  gzip -9 -c /tmp/pw4/$n.glb > pack/$n.glb.gz
done
ls pack | wc -l; du -sh pack

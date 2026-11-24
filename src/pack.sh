#!/bin/sh
# every visual model: dedup + meshopt, then gzip (Otherside reads .glb.gz)
set -e
mkdir -p pack /tmp/packwork
for f in out/mr_*.glb; do
  n=$(basename "$f" .glb)
  gltf-transform dedup "$f" /tmp/packwork/$n.a.glb >/dev/null
  gltf-transform meshopt /tmp/packwork/$n.a.glb /tmp/packwork/$n.glb >/dev/null
  gzip -9 -c /tmp/packwork/$n.glb > pack/$n.glb.gz
done
ls -l pack | awk '{s+=$5} END {print NR-1, "files", int(s/1024), "KB"}'

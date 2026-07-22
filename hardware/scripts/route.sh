#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Eric Neuman
# route.sh — autonomous route + validate loop for one grip (KiCad 9 + Freerouting).
#   ./route.sh <right|left> [max_passes]
# Pipeline: (gen_board.py already ran) -> Specctra DSN -> Freerouting -> SES ->
#           import -> GND stitch + zone fill -> DRC(json) -> flat SVG + 3D PNG.
# The pre-routed USB pad-pair ties from gen_board.py ride through the DSN as fixed
# wires. No close_gaps step: KiCad's own connectivity is the arbiter (the old
# union-find bridger drew blind shorts), and DRC's unconnected_items reports any
# real leftovers per net.
set -euo pipefail
SIDE="${1:-right}"; PASSES="${2:-30}"
JAVA="$HOME/tools/jdk-25.0.3+9-jre/bin/java"
FR="$HOME/tools/freerouting.jar"
GEN="$(cd "$(dirname "$0")/../kicad/generated" && pwd)"
REND="$(cd "$(dirname "$0")/../../renders" && pwd)"
PCB="$GEN/thumbdeck_${SIDE}.kicad_pcb"

echo "[1] export Specctra DSN"
python3 - "$PCB" "$GEN/thumbdeck_${SIDE}.dsn" <<'PY' 2>/dev/null
import pcbnew,sys; b=pcbnew.LoadBoard(sys.argv[1]); assert pcbnew.ExportSpecctraDSN(b,sys.argv[2]), "DSN export failed"
PY
# In1.Cu is the solid GND plane — mark it as a power layer so Freerouting never
# routes signals through it (KiCad exports all layers as signal; zones aren't in
# the DSN, so FR would otherwise happily perforate the plane).
python3 - "$GEN/thumbdeck_${SIDE}.dsn" <<'PY'
import re,sys
p=sys.argv[1]; s=open(p).read()
s2=re.sub(r'\(layer In1\.Cu\s*\(type signal\)', '(layer In1.Cu\n      (type power)', s)
open(p,'w').write(s2)
print("    In1.Cu marked power:", 'yes' if s2!=s else 'NO MATCH (check DSN format)')
PY

echo "[2] Freerouting autoroute ($PASSES passes)"
rm -f "$GEN/thumbdeck_${SIDE}.ses"
timeout 900 "$JAVA" -Xss16m -jar "$FR" --gui.enabled=false \
  -de "$GEN/thumbdeck_${SIDE}.dsn" -do "$GEN/thumbdeck_${SIDE}.ses" -mp "$PASSES" -mt 4 2>&1 \
  | grep -iE "error|session completed|could not be routed" | tail -6 || true
if [ ! -s "$GEN/thumbdeck_${SIDE}.ses" ]; then
  echo "FATAL: Freerouting produced no session file — routing failed"; exit 1
fi
python3 - "$PCB" "$GEN/thumbdeck_${SIDE}.ses" <<'PY' 2>/dev/null
import pcbnew,sys
b=pcbnew.LoadBoard(sys.argv[1]); pcbnew.ImportSpecctraSES(b,sys.argv[2]); pcbnew.SaveBoard(sys.argv[1],b)
print("    imported:", len(list(b.GetTracks())), "tracks/vias")
PY

echo "[3] stitch GND + fill zones"
python3 "$(dirname "$0")/stitch.py" "$PCB" 2>/dev/null

echo "[4] DRC"
kicad-cli pcb drc --format json --severity-error \
  -o "$GEN/drc_${SIDE}.json" "$PCB" >/dev/null 2>&1 || true
python3 - "$GEN/drc_${SIDE}.json" <<'PY'
import json,sys,re; from collections import Counter
d=json.load(open(sys.argv[1])); v=d.get('violations',[]); u=d.get('unconnected_items',[])
print(f"    DRC: {len(v)} violations {dict(Counter(x['type'] for x in v))}, {len(u)} unconnected")
nets=Counter()
for it in u:
    m=re.search(r'\[([^\]]*)\]', it['items'][0]['description'] if it.get('items') else '')
    nets[m.group(1) if m else '?']+=1
if nets: print("    open nets:", dict(nets.most_common(12)))
PY

echo "[5] render (flat 2D copper + 3D top/bottom)"
kicad-cli pcb export svg --layers "F.Cu,B.Cu,F.Silkscreen,Edge.Cuts" --page-size-mode 2 \
  --exclude-drawing-sheet -o "$REND/routed_${SIDE}_2d.svg" "$PCB" >/dev/null 2>&1
kicad-cli pcb render --side top    --background opaque -o "$REND/routed_${SIDE}_top.png" "$PCB" >/dev/null 2>&1
kicad-cli pcb render --side bottom --background opaque -o "$REND/routed_${SIDE}_bottom.png" "$PCB" >/dev/null 2>&1
echo "    wrote renders/routed_${SIDE}_{2d.svg,top.png,bottom.png}"

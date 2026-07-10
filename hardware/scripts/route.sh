#!/usr/bin/env bash
# route.sh — autonomous route + validate loop for one grip (KiCad 9 + Freerouting).
#   ./route.sh <right|left> [max_passes]
# Pipeline: (gen_board.py already ran) -> Specctra DSN -> Freerouting -> SES ->
#           import -> DRC(json) -> flat SVG + 3D PNG.  No KiCad GUI, no human.
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

echo "[2] Freerouting autoroute ($PASSES passes)"
timeout 600 "$JAVA" -jar "$FR" --gui.enabled=false \
  -de "$GEN/thumbdeck_${SIDE}.dsn" -do "$GEN/thumbdeck_${SIDE}.ses" -mp "$PASSES" -mt 4 2>&1 \
  | grep -iE "session completed|unrouted" | tail -1

echo "[3] import routed SES"
python3 - "$PCB" "$GEN/thumbdeck_${SIDE}.ses" <<'PY' 2>/dev/null
import pcbnew,sys; b=pcbnew.LoadBoard(sys.argv[1]); pcbnew.ImportSpecctraSES(b,sys.argv[2]); pcbnew.SaveBoard(sys.argv[1],b)
PY

echo "[4] DRC"
kicad-cli pcb drc --format json --exit-code-violations --severity-error \
  -o "$GEN/drc_${SIDE}.json" "$PCB" >/dev/null 2>&1 || true
python3 - "$GEN/drc_${SIDE}.json" <<'PY'
import json,sys; from collections import Counter
d=json.load(open(sys.argv[1])); v=d.get('violations',[]); u=d.get('unconnected_items',[])
print(f"    DRC: {len(v)} violations, {len(u)} unconnected  {dict(Counter(x['type'] for x in v))}")
PY

echo "[5] render (flat 2D copper + 3D top/bottom)"
kicad-cli pcb export svg --layers "F.Cu,B.Cu,F.Silkscreen,Edge.Cuts" --page-size-mode 2 \
  --exclude-drawing-sheet -o "$REND/routed_${SIDE}_2d.svg" "$PCB" >/dev/null 2>&1
kicad-cli pcb render --side top    --background opaque -o "$REND/routed_${SIDE}_top.png" "$PCB" >/dev/null 2>&1
kicad-cli pcb render --side bottom --background opaque -o "$REND/routed_${SIDE}_bottom.png" "$PCB" >/dev/null 2>&1
echo "    wrote renders/routed_${SIDE}_{2d.svg,top.png,bottom.png}"

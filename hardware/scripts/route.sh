#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Eric Neuman
# route.sh — autonomous route + validate loop for one grip (KiCad 9 + Freerouting).
#   ./route.sh <right|left> [max_passes] [max_attempts]
# Pipeline: (gen_board.py already ran) -> Specctra DSN -> Freerouting -> SES ->
#           import -> GND stitch + zone fill -> DRC(json) -> flat SVG + 3D PNG.
# The pre-routed USB pad-pair ties from gen_board.py ride through the DSN as fixed
# wires. No close_gaps step: KiCad's own connectivity is the arbiter (the old
# union-find bridger drew blind shorts), and DRC's unconnected_items reports any
# real leftovers per net.
set -euo pipefail
SIDE="${1:-right}"; PASSES="${2:-30}"; ATTEMPTS="${3:-5}"
JAVA="$HOME/tools/jdk-25.0.3+9-jre/bin/java"
FR="$HOME/tools/freerouting.jar"
GEN="$(cd "$(dirname "$0")/../kicad/generated" && pwd)"
REND="$(cd "$(dirname "$0")/../../renders" && pwd)"
PCB="$GEN/thumbdeck_${SIDE}.kicad_pcb"

# v0.27: ESCALATE UNTIL CLEAN. The 20-way bridge connector put the inner corridor close
# enough to the edge that a single autoroute now lands 1-3 nets short. This file has always
# called itself a "route + validate loop" while only ever doing one pass; that was fine
# when the board had 4mm of slack and is not any more.
#
# NB retrying the SAME input is worthless: Freerouting is deterministic despite -mt 4, and
# five identical attempts produced byte-identical open-net lists (VBAT/VBUS/VBAT_CELL every
# time). Each attempt therefore RAISES the pass budget, which is what actually changes the
# search trajectory. Earlier runs that looked random were different board files, not noise.
# Each attempt restarts from the PRISTINE generated board — retrying on top of an
# already-imported SES would let the previous attempt's tracks ride through the DSN as
# fixed wires, so the router would just inherit the same dead end.
PRISTINE="$(mktemp -t thumbdeck_pristine_XXXXXX.kicad_pcb)"
cp "$PCB" "$PRISTINE"
trap 'rm -f "$PRISTINE"' EXIT
UNCONN=999
for ATTEMPT in $(seq 1 "$ATTEMPTS"); do
THIS_PASSES=$(( PASSES + (ATTEMPT - 1) * PASSES / 2 ))
if [ "$ATTEMPT" -gt 1 ]; then
  echo "[retry $ATTEMPT/$ATTEMPTS — $UNCONN net(s) open; raising to $THIS_PASSES passes]"
  cp "$PRISTINE" "$PCB"
fi

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
# v0.27: give the cell path a real trace width. KiCad exports every net in one flat
# `kicad_default` class at 0.2mm, and gen_board.py's pcbnew-API flow cannot create a
# netclass (KiCad 9 does not expose one on BOARD_DESIGN_SETTINGS via SWIG) — so this is
# where PWR actually gets applied. It matters now that the battery crosses the bridge:
# the old 0.2mm VBAT_CELL run was ~336mR all by itself, a third of the entire charge
# loop, and the ribbon + the 0.45R (max) PPTC only add to that. 0.4mm buys back ~170mR,
# which is more than the ribbon costs. NB 0.5mm was tried first and Freerouting could not
# close VBAT_CELL through the inner corridor with it; 0.4 costs only ~34mR more than 0.5
# and routes, and the PPTC dominates the loop anyway.
python3 - "$GEN/thumbdeck_${SIDE}.dsn" <<'PY'
import re,sys
p=sys.argv[1]; s=open(p).read()
PWR_NETS=["VBAT_CELL","VCELL_RAW","VBAT"]     # the cell path; VBUS is short and stays default
PWR_W=400                                      # um — keep in sync with gen_board.PWR
m=re.search(r'\(class kicad_default(.*?)\n(\s*)\(circuit', s, re.S)
if not m:
    print("    power netclass: NO MATCH (check DSN format)"); sys.exit(0)
members=m.group(1).split(); indent=m.group(2)
present=[n for n in PWR_NETS if n in members]
if not present:
    print("    power netclass: none of", PWR_NETS, "on this board"); sys.exit(0)
kept=[n for n in members if n not in present]
# rewrap the trimmed default member list, then append a real power class after the block
body="\n      ".join(" ".join(kept[i:i+10]) for i in range(0,len(kept),10))
s=s[:m.start()]+"(class kicad_default "+body+"\n"+indent+"(circuit"+s[m.end():]
close=s.index("\n  )\n  (wiring")
s=(s[:close]+"\n"+indent[:-2]+"(class power "+" ".join(present)+"\n"
   +indent+"(circuit\n"+indent+"  (use_via \"Via[0-3]_600:300_um\")\n"+indent+")\n"
   +indent+"(rule\n"+indent+f"  (width {PWR_W})\n"+indent+"  (clearance 200)\n"+indent+")\n"
   +indent[:-2]+")"+s[close:])
open(p,'w').write(s)
print(f"    power netclass: {present} at {PWR_W/1000:.1f}mm")
PY

echo "[2] Freerouting autoroute ($THIS_PASSES passes)"
rm -f "$GEN/thumbdeck_${SIDE}.ses"
timeout 900 "$JAVA" -Xss16m -jar "$FR" --gui.enabled=false \
  -de "$GEN/thumbdeck_${SIDE}.dsn" -do "$GEN/thumbdeck_${SIDE}.ses" -mp "$THIS_PASSES" -mt 4 2>&1 \
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
open(sys.argv[1] + ".unconn", "w").write(str(len(u)))
PY
UNCONN="$(cat "$GEN/drc_${SIDE}.json.unconn")"
if [ "$UNCONN" = "0" ]; then break; fi
done
rm -f "$GEN/drc_${SIDE}.json.unconn"
if [ "$UNCONN" != "0" ]; then
  echo "FATAL: $UNCONN net(s) still unrouted after $ATTEMPTS attempts —"
  echo "       raise max_passes/max_attempts, or relieve the congestion."
  exit 1
fi

echo "[5] render (flat 2D copper + 3D top/bottom)"
kicad-cli pcb export svg --layers "F.Cu,B.Cu,F.Silkscreen,Edge.Cuts" --page-size-mode 2 \
  --exclude-drawing-sheet -o "$REND/routed_${SIDE}_2d.svg" "$PCB" >/dev/null 2>&1
kicad-cli pcb render --side top    --background opaque -o "$REND/routed_${SIDE}_top.png" "$PCB" >/dev/null 2>&1
kicad-cli pcb render --side bottom --background opaque -o "$REND/routed_${SIDE}_bottom.png" "$PCB" >/dev/null 2>&1
echo "    wrote renders/routed_${SIDE}_{2d.svg,top.png,bottom.png}"

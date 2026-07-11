#!/usr/bin/env python3
"""gen_fab.py — production package for JLCPCB, one order per board.

Gate: DRC must be clean (0 error-severity violations, 0 unconnected) or this
script refuses to export. Then per side:
  fab/<side>/gerbers.zip     4-layer gerbers + Excellon drill
  fab/<side>/bom.csv         JLC BOM (Comment, Designator, Footprint, LCSC Part #)
  fab/<side>/positions.csv   JLC CPL (Designator, Mid X, Mid Y, Layer, Rotation)

Order notes (also in docs/fabrication-sourcing.md):
  * Two separate JLC orders (panelizing two different designs costs more than it saves).
  * 4-layer, 1.6mm FR-4, ENIG (mandatory: snap-dome contacts), assembly side = BOTTOM.
  * The E73 module forces Standard assembly + X-ray; stock is thin — reserve early.
  * Rotations are KiCad-native: VERIFY part orientation (esp. SOT-23-5/6, USB-C, LED
    polarity bar, E73) in JLC's DFM preview before paying — rotate there if needed.
"""
import csv
import io
import json
import os
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.abspath(os.path.join(HERE, "..", "kicad", "generated"))
FAB = os.path.join(GEN, "fab")
LAYERS = "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,Edge.Cuts"


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"FAILED: {' '.join(cmd)}\n{r.stderr[-2000:]}")
    return r


def drc_gate(pcb, side):
    out = os.path.join(GEN, f"drc_{side}.json")
    subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "--severity-error",
                    "-o", out, pcb], capture_output=True)
    d = json.load(open(out))
    nv, nu = len(d.get("violations", [])), len(d.get("unconnected_items", []))
    if nv or nu:
        sys.exit(f"{side}: DRC NOT CLEAN ({nv} violations, {nu} unconnected) — not exporting fab data")
    print(f"{side}: DRC clean")


def export(side):
    pcb = os.path.join(GEN, f"thumbdeck_{side}.kicad_pcb")
    drc_gate(pcb, side)
    out = os.path.join(FAB, side)
    import shutil
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out, exist_ok=True)

    gdir = os.path.join(out, "gerbers")
    os.makedirs(gdir, exist_ok=True)
    run(["kicad-cli", "pcb", "export", "gerbers", "--layers", LAYERS,
         "--exclude-value", "--subtract-soldermask", "-o", gdir + "/", pcb])
    run(["kicad-cli", "pcb", "export", "drill", "--format", "excellon",
         "--drill-origin", "absolute", "--excellon-separate-th", "-o", gdir + "/", pcb])
    zpath = os.path.join(out, f"thumbdeck_{side}_gerbers.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(gdir)):
            z.write(os.path.join(gdir, f), f)

    # CPL from kicad-cli pos (respects exclude_from_pos_files), JLC headers
    postmp = os.path.join(out, "_pos_raw.csv")
    run(["kicad-cli", "pcb", "export", "pos", "--format", "csv", "--units", "mm",
         "--side", "both", "--exclude-dnp", "-o", postmp, pcb])
    with open(postmp) as f:
        rows = list(csv.DictReader(f))
    os.remove(postmp)
    with open(os.path.join(out, "positions.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for r in rows:
            w.writerow([r["Ref"], r["PosX"], r["PosY"],
                        "Bottom" if r["Side"] == "bottom" else "Top",
                        f"{float(r['Rot']) % 360:.1f}"])

    # BOM grouped by value+footprint with LCSC field (read from the board)
    import pcbnew
    b = pcbnew.LoadBoard(pcb)
    groups = {}
    for fp in b.GetFootprints():
        if fp.IsExcludedFromBOM() or fp.IsExcludedFromPosFiles():
            continue
        lcsc = fp.GetFieldText("LCSC") if fp.HasFieldByName("LCSC") else ""
        key = (fp.GetValue(), str(fp.GetFPID().GetLibItemName()), lcsc)
        groups.setdefault(key, []).append(fp.GetReference())
    with open(os.path.join(out, "bom.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (val, foot, lcsc), refs in sorted(groups.items()):
            w.writerow([val, ",".join(sorted(refs)), foot, lcsc])
    n = sum(len(v) for v in groups.values())
    print(f"{side}: wrote {zpath} + bom.csv ({len(groups)} lines / {n} parts) + positions.csv ({len(rows)} placements)")


if __name__ == "__main__":
    for side in (sys.argv[1:] or ["right", "left"]):
        export(side)

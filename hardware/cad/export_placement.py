#!/usr/bin/env python3
"""export_placement.py — run with SYSTEM python3 (has KiCad pcbnew). Dumps each
grip's footprint placement + the board outline to JSON so deck3d.py (which runs in
a venv without pcbnew) can build the 3D fit-model. Keeps pcbnew out of the CAD venv.
"""
import os, json, pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.join(HERE, "..", "kicad", "generated")
OUT = os.path.join(HERE, "build")
os.makedirs(OUT, exist_ok=True)

for side in ("right", "left"):
    b = pcbnew.LoadBoard(os.path.join(GEN, f"thumbdeck_{side}.kicad_pcb"))
    comps = []
    for f in b.GetFootprints():
        pos = f.GetPosition()
        comps.append({
            "ref": f.GetReference(),
            "fp": f.GetFPIDAsString().split(":")[-1],
            "x": pcbnew.ToMM(pos.x), "y": pcbnew.ToMM(pos.y),  # KiCad Y-down
            "rot": f.GetOrientationDegrees(),
            "back": bool(f.IsFlipped()),
        })
    json.dump(comps, open(os.path.join(OUT, f"placement_{side}.json"), "w"))
    print(f"{side}: wrote {len(comps)} footprints")

#!/usr/bin/env python3
"""export_placement.py — run with SYSTEM python3 (has KiCad pcbnew). Dumps each
grip's footprint placement to JSON so deck3d.py (which runs in a venv without
pcbnew) can build the 3D fit-model. Keeps pcbnew out of the CAD venv.

Per footprint we export BOTH:
  * the bbox CENTRE + dims (fp.GetBoundingBox(False): pads + fab/courtyard
    graphics, axis-aligned in board coords) — what deck3d extrudes as the body
    envelope for most parts (pin-1-anchored footprints made the raw anchor wrong);
  * the raw anchor (ax, ay) — used by deck3d for the few parts whose true body is
    anchor-centred and whose bbox is inflated by keep-out drawings (E73 antenna).
All coords in mm, KiCad Y-down.
"""
import os, json, time, pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.join(HERE, "..", "kicad", "generated")
OUT = os.path.join(HERE, "build")
os.makedirs(OUT, exist_ok=True)


def _load(path, retries=4, wait=5):
    """The boards may be mid-write by the autorouter; retry on a bad load."""
    last = None
    for _ in range(retries):
        try:
            b = pcbnew.LoadBoard(path)
            if b.GetFootprints():
                return b
        except Exception as e:      # noqa: BLE001 — retry any load failure
            last = e
        time.sleep(wait)
    raise RuntimeError(f"could not load {path}: {last}")


for side in ("right", "left"):
    b = _load(os.path.join(GEN, f"thumbdeck_{side}.kicad_pcb"))
    comps = []
    for f in b.GetFootprints():
        pos = f.GetPosition()
        bb = f.GetBoundingBox(False)          # pads + graphics, no text
        c = bb.GetCenter()
        comps.append({
            "ref": f.GetReference(),
            "val": f.GetValue(),
            "fp": f.GetFPIDAsString().split(":")[-1],
            "x": pcbnew.ToMM(c.x), "y": pcbnew.ToMM(c.y),      # bbox centre (Y-down)
            "w": pcbnew.ToMM(bb.GetWidth()), "h": pcbnew.ToMM(bb.GetHeight()),
            "ax": pcbnew.ToMM(pos.x), "ay": pcbnew.ToMM(pos.y),  # raw anchor
            "rot": f.GetOrientationDegrees(),
            "back": bool(f.IsFlipped()),
        })
    json.dump(comps, open(os.path.join(OUT, f"placement_{side}.json"), "w"))
    print(f"{side}: wrote {len(comps)} footprints")

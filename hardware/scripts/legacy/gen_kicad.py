#!/usr/bin/env python3
"""
gen_kicad.py — emit a real, openable KiCad board + DXF outline + placement CSV
from the converged geometry (deck.py).

What this DOES produce (fully real, from the loop's converged layout):
  * <half>.kicad_pcb : board outline on Edge.Cuts, mount-hole cutouts, keep-out
    rectangles (controller / LiPo / USB-C) on Cmts.User, and a placement guide
    (ref + cross) at the exact converged centre of every switch and diode.
  * <half>_outline.dxf : the board edge, importable straight into KiCad/CAD.
  * <half>_placement.csv : ref, value, x_mm, y_mm, rotation, side.

What this deliberately does NOT do (per PROJECT_SPEC §5/§10/§13 — no fabricated
dimensions, no fake routing): it does not stamp a datasheet-verified switch
footprint, and it does not route copper. Those two are the marked TODO(user)
gates before gerber export. The board opens in KiCad as the placement+outline
starting point described in hardware/kicad/README.md.
"""
from __future__ import annotations
import os, csv, math
import deck

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "kicad", "generated"))

KICAD_LAYERS = """  (layers
    (0 "F.Cu" signal)
    (31 "B.Cu" signal)
    (32 "B.Adhes" user "B.Adhesive")
    (33 "F.Adhes" user "F.Adhesive")
    (34 "B.Paste" user)
    (35 "F.Paste" user)
    (36 "B.SilkS" user "B.Silkscreen")
    (37 "F.SilkS" user "F.Silkscreen")
    (38 "B.Mask" user)
    (39 "F.Mask" user)
    (40 "Dwgs.User" user "User.Drawings")
    (41 "Cmts.User" user "User.Comments")
    (42 "Eco1.User" user "User.Eco1")
    (43 "Eco2.User" user "User.Eco2")
    (44 "Edge.Cuts" user)
    (45 "Margin" user)
    (46 "B.CrtYd" user "B.Courtyard")
    (47 "F.CrtYd" user "F.Courtyard")
    (48 "B.Fab" user)
    (49 "F.Fab" user)
  )"""


def _fy(y, H):
    """Flip to KiCad Y-down so text/board read upright."""
    return round(H - y, 3)


def gr_line(x1, y1, x2, y2, layer, w=0.15):
    return (f'  (gr_line (start {x1} {y1}) (end {x2} {y2}) '
            f'(stroke (width {w}) (type solid)) (layer "{layer}"))')


def gr_circle(cx, cy, r, layer, w=0.15):
    return (f'  (gr_circle (center {cx} {cy}) (end {round(cx+r,3)} {cy}) '
            f'(stroke (width {w}) (type solid)) (fill none) (layer "{layer}"))')


def gr_rect(x1, y1, x2, y2, layer, w=0.12):
    return (f'  (gr_rect (start {x1} {y1}) (end {x2} {y2}) '
            f'(stroke (width {w}) (type solid)) (fill none) (layer "{layer}"))')


def gr_text(txt, x, y, layer, size=1.0, rot=0):
    return (f'  (gr_text "{txt}" (at {x} {y} {rot}) (layer "{layer}") '
            f'(effects (font (size {size} {size}) (thickness {round(size*0.15,3)}))))')


def build_pcb(geo) -> str:
    H = geo["board_h"]
    side = "R" if geo["side"] == "right" else "L"
    S = []
    S.append('(kicad_pcb (version 20221018) (generator thumbdeck_gen)')
    S.append('  (general (thickness 1.6))')
    S.append('  (paper "A4")')
    S.append(KICAD_LAYERS)
    S.append('  (setup (pad_to_mask_clearance 0))')

    # --- Edge.Cuts outline (real) ---
    o = geo["outline"]
    for i in range(len(o)):
        x1, y1 = o[i]
        x2, y2 = o[(i + 1) % len(o)]
        S.append(gr_line(x1, _fy(y1, H), x2, _fy(y2, H), "Edge.Cuts", 0.15))
    # mount holes as Edge.Cuts circular cutouts (non-plated mounting holes)
    for hole in geo["mount_holes"]:
        S.append(gr_circle(hole["x"], _fy(hole["y"], H), hole["d"] / 2, "Edge.Cuts"))

    # --- keep-out rectangles + labels (Cmts.User) ---
    for name, (x, y, w, h) in geo["keepouts"].items():
        S.append(gr_rect(x, _fy(y, H), x + w, _fy(y + h, H), "Cmts.User"))
        S.append(gr_text(name.upper().replace("_", "-"), x + w / 2, _fy(y + h / 2, H),
                         "Cmts.User", 1.0))

    # --- switch + diode placement guides at converged centres (F.SilkS) ---
    for idx, k in enumerate(geo["keys"], start=1):
        x, y = k["x"], _fy(k["y"], H)
        # cross marker at exact placement point
        S.append(gr_line(x - 1.2, y, x + 1.2, y, "F.SilkS", 0.12))
        S.append(gr_line(x, y - 1.2, x, y + 1.2, "F.SilkS", 0.12))
        S.append(gr_text(f"SW{idx}", x, y + 2.4, "F.SilkS", 0.8))
        # diode placed just below each switch (col2row), guide only
        S.append(gr_text(f"D{idx}", x + 2.6, y - 2.4, "B.SilkS", 0.7))

    # --- board silk: half + version + provisional-footprint warning ---
    S.append(gr_text(f"thumbdeck-{side} {deck.VERSION}", 4.0, _fy(H * 0.5, H),
                     "F.SilkS", 1.4, rot=90))
    S.append(gr_text("SWITCH FOOTPRINT PROVISIONAL - VERIFY vs DATASHEET",
                     geo["outer_base"] * 0.5, _fy(H * 0.5, H), "Cmts.User", 1.0))
    S.append(')')
    return "\n".join(S)


def build_dxf(geo) -> str:
    """Minimal R12 DXF: board outline as LINE entities (Edge.Cuts import)."""
    H = geo["board_h"]
    o = geo["outline"]
    lines = ["0", "SECTION", "2", "ENTITIES"]
    for i in range(len(o)):
        x1, y1 = o[i]
        x2, y2 = o[(i + 1) % len(o)]
        lines += ["0", "LINE", "8", "EdgeCuts",
                  "10", f"{x1}", "20", f"{_fy(y1, H)}", "30", "0.0",
                  "11", f"{x2}", "21", f"{_fy(y2, H)}", "31", "0.0"]
    lines += ["0", "ENDSEC", "0", "EOF"]
    return "\n".join(lines) + "\n"


def build_csv(geo):
    H = geo["board_h"]
    rows = [("ref", "value", "x_mm", "y_mm", "rot", "side", "layer")]
    for idx, k in enumerate(geo["keys"], start=1):
        rows.append((f"SW{idx}", "TACT_5x5_SPST_PROVISIONAL",
                     k["x"], _fy(k["y"], H), 0, geo["side"], "F.Cu"))
        rows.append((f"D{idx}", "1N4148W_SOD123", k["x"] + 2.6,
                     _fy(k["y"] - 2.4, H), 90, geo["side"], "F.Cu"))
    for name, (x, y, w, h) in geo["keepouts"].items():
        rows.append((name, "KEEPOUT", round(x + w / 2, 2), _fy(y + h / 2, H), 0,
                     geo["side"], "-"))
    return rows


def main():
    os.makedirs(OUT, exist_ok=True)
    for side in ("right", "left"):
        geo = deck.build(deck.Config(side=side))
        tag = side
        with open(os.path.join(OUT, f"thumbdeck_{tag}.kicad_pcb"), "w") as f:
            f.write(build_pcb(geo))
        with open(os.path.join(OUT, f"thumbdeck_{tag}_outline.dxf"), "w") as f:
            f.write(build_dxf(geo))
        with open(os.path.join(OUT, f"thumbdeck_{tag}_placement.csv"), "w", newline="") as f:
            csv.writer(f).writerows(build_csv(geo))
        print(f"wrote thumbdeck_{tag}.kicad_pcb / .dxf / _placement.csv "
              f"({geo['board_w']:.1f}x{geo['board_h']:.1f}mm, {len(geo['keys'])} keys)")


if __name__ == "__main__":
    main()

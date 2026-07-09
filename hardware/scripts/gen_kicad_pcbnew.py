#!/usr/bin/env python3
"""
gen_kicad_pcbnew.py — emit a REAL, netlisted KiCad 7 board per grip using the
pcbnew Python API (supersedes the hand-emitted gen_kicad.py placement guide).

Per grip it places:
  * the board outline on Edge.Cuts + NPTH mount-hole cutouts (from deck.py),
  * a real 2-pad Snaptron 7mm dome footprint at every switch + cluster-key centre
    (front, F.Cu),  pad1 = matrix COLUMN node, pad2 = per-key diode node,
  * a real Diode_SMD:D_SOD-323 at every switch, on the BACK (B.Cu) — there is no
    room for a diode between 8.5mm-pitch domes on the front — col2row, cathode to
    the ROW net,
  * matrix nets ROW0..8 / COL0..9 so the board opens with a correct ratsnest,
  * reserved keep-out areas (Cmts.User) for the Raytac module, LiPo, USB-C,
    charger, trackpad and the JST-GH bridge connector — the copper routing and
    the module/connector footprints are the remaining fab gate.

Finish: ENIG (snap domes need gold, not HASL). Run kicad-cli drc / export svg on
the output. See docs/matrix-and-diodes.md and docs/design-decisions.md.
"""
from __future__ import annotations
import os, csv
import pcbnew
from pcbnew import VECTOR2I, FromMM
import deck

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "kicad", "generated"))
DIODE_LIB = "/usr/share/kicad/footprints/Diode_SMD.pretty"
NROWS, NCOLS_HALF = 9, 5   # 9 shared rows; 5 cols/grip (right 0-4, left 5-9)


def _fy(y, H):
    return H - y   # KiCad Y-down so the board reads upright


def make_switch(board, ref, x, y, col_net, dnode_net):
    """2-pad Snaptron dome: centre disc (col) + outer ring node (to diode)."""
    fp = pcbnew.FOOTPRINT(board)
    fp.SetReference(ref)
    fp.SetValue("SNAP7")
    fp.SetPosition(VECTOR2I(FromMM(x), FromMM(y)))
    for num, dx, dia, net in (("1", 0.0, 2.86, col_net), ("2", 3.48, 1.5, dnode_net)):
        p = pcbnew.PAD(fp)
        p.SetNumber(num)
        p.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
        p.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        p.SetSize(VECTOR2I(FromMM(dia), FromMM(dia)))
        ls = pcbnew.LSET(); ls.AddLayer(pcbnew.F_Cu); ls.AddLayer(pcbnew.F_Mask)
        p.SetLayerSet(ls)
        p.SetPos0(VECTOR2I(FromMM(dx), FromMM(0)))
        p.SetPosition(VECTOR2I(FromMM(x + dx), FromMM(y)))
        p.SetNet(net)
        fp.Add(p)
    # 7mm dome outline (F.Fab) + tight courtyard (FP_SHAPE = footprint graphic)
    for layer, rad in ((pcbnew.F_Fab, 3.5), (pcbnew.F_CrtYd, 4.1)):
        c = pcbnew.FP_SHAPE(fp); c.SetShape(pcbnew.SHAPE_T_CIRCLE)
        c.SetCenter(VECTOR2I(FromMM(x), FromMM(y)))
        c.SetEnd(VECTOR2I(FromMM(x + rad), FromMM(y)))
        c.SetLayer(layer); c.SetWidth(FromMM(0.1)); fp.Add(c)
    board.Add(fp)
    return fp


def add_diode(board, ref, x, y, dnode_net, row_net):
    fp = pcbnew.FootprintLoad(DIODE_LIB, "D_SOD-323")
    fp.SetReference(ref); fp.SetValue("1N4148WS")
    fp.SetPosition(VECTOR2I(FromMM(x), FromMM(y)))
    board.Add(fp)                       # must be on the board BEFORE Flip()
    fp.Flip(fp.GetPosition(), False)    # to B.Cu, under the dome
    for pad in fp.Pads():
        # pad 1 = cathode (K / band) -> ROW ; pad 2 = anode -> switch node (col2row)
        pad.SetNet(row_net if pad.GetNumber() == "1" else dnode_net)
    return fp


def add_outline(board, geo):
    H = geo["board_h"]; o = geo["outline"]
    for i in range(len(o)):
        x1, y1 = o[i]; x2, y2 = o[(i + 1) % len(o)]
        s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(VECTOR2I(FromMM(x1), FromMM(_fy(y1, H))))
        s.SetEnd(VECTOR2I(FromMM(x2), FromMM(_fy(y2, H))))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(FromMM(0.15)); board.Add(s)
    for hole in geo["mount_holes"]:
        c = pcbnew.PCB_SHAPE(board); c.SetShape(pcbnew.SHAPE_T_CIRCLE)
        c.SetCenter(VECTOR2I(FromMM(hole["x"]), FromMM(_fy(hole["y"], H))))
        c.SetEnd(VECTOR2I(FromMM(hole["x"] + hole["d"] / 2), FromMM(_fy(hole["y"], H))))
        c.SetLayer(pcbnew.Edge_Cuts); c.SetWidth(FromMM(0.15)); board.Add(c)


def add_keepout(board, name, x, y, w, h, H):
    r = pcbnew.PCB_SHAPE(board); r.SetShape(pcbnew.SHAPE_T_RECT)
    r.SetStart(VECTOR2I(FromMM(x), FromMM(_fy(y, H))))
    r.SetEnd(VECTOR2I(FromMM(x + w), FromMM(_fy(y + h, H))))
    r.SetLayer(pcbnew.Cmts_User); r.SetWidth(FromMM(0.12)); board.Add(r)
    t = pcbnew.PCB_TEXT(board); t.SetText(name.upper())
    t.SetPosition(VECTOR2I(FromMM(x + w / 2), FromMM(_fy(y + h / 2, H))))
    t.SetLayer(pcbnew.Cmts_User); t.SetTextSize(VECTOR2I(FromMM(1.0), FromMM(1.0)))
    board.Add(t)


def add_text(board, txt, x, y, H, layer=pcbnew.F_SilkS, size=1.2, angle=0):
    t = pcbnew.PCB_TEXT(board); t.SetText(txt)
    t.SetPosition(VECTOR2I(FromMM(x), FromMM(_fy(y, H))))
    t.SetLayer(layer); t.SetTextSize(VECTOR2I(FromMM(size), FromMM(size)))
    if angle:
        t.SetTextAngle(pcbnew.EDA_ANGLE(angle, pcbnew.DEGREES_T))
    board.Add(t)


def build_board(geo, side):
    b = pcbnew.BOARD()
    H = geo["board_h"]
    nets = {}
    def net(n):
        if n not in nets:
            ni = pcbnew.NETINFO_ITEM(b, n); b.Add(ni); nets[n] = ni
        return nets[n]
    net("GND")
    for r in range(NROWS):
        net(f"ROW{r}")
    col_off = 0 if side == "right" else NCOLS_HALF
    for c in range(NCOLS_HALF):
        net(f"COL{col_off + c}")

    add_outline(b, geo)

    # switches = grid keys + cluster switch-features (not the trackpad)
    switches = list(geo["keys"]) + [f for f in geo.get("features", []) if f["type"] == "key"]
    rows = []
    for i, k in enumerate(switches):
        r = i // NCOLS_HALF
        c = col_off + (i % NCOLS_HALF)
        x, y = k["x"], _fy(k["y"], H)
        col_net = net(f"COL{c}"); row_net = net(f"ROW{r % NROWS}")
        dn = net(f"D_{side[0].upper()}{i+1}")
        make_switch(b, f"SW{i+1}", x, y, col_net, dn)
        add_diode(b, f"D{i+1}", x + 0.0, y - 0.2, dn, row_net)
        rows.append((f"SW{i+1}", k.get("label", "?"), f"ROW{r%NROWS}", f"COL{c}", round(x, 2), round(y, 2)))

    # reserved areas (module / power / bridge / trackpad)
    for name, (x, y, w, h) in geo["keepouts"].items():
        add_keepout(b, name, x, y, w, h, H)
    for f in geo.get("features", []):
        if f["type"] == "trackpad":
            add_keepout(b, "TRACKPAD-TPS43-opt", f["x"] - f["w"] / 2, f["y"] - f["h"] / 2,
                        f["w"], f["h"], H)

    add_text(b, f"thumbdeck-{'R' if side=='right' else 'L'} {deck.VERSION}  ENIG",
             4.0, H * 0.5, H, size=1.4, angle=90)
    add_text(b, "ROUTING + MODULE/CONN FOOTPRINTS = NEXT GATE",
             geo["outer_base"] * 0.5, 3.0, H, pcbnew.Cmts_User, 1.0)
    return b, rows


def main():
    os.makedirs(OUT, exist_ok=True)
    for side in ("right", "left"):
        geo = deck.build(deck.Config(side=side))
        board, rows = build_board(geo, side)
        pcb = os.path.join(OUT, f"thumbdeck_{side}.kicad_pcb")
        pcbnew.SaveBoard(pcb, board)
        with open(os.path.join(OUT, f"thumbdeck_{side}_placement.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(("ref", "legend", "row", "col", "x_mm", "y_mm"))
            w.writerows(rows)
        print(f"wrote {os.path.basename(pcb)} — {len(rows)} switches+diodes, "
              f"{board.GetNetCount()} nets, {geo['board_w']:.1f}x{geo['board_h']:.1f}mm")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""stitch.py <board> — tie the GND pour together with vias, then fill.

A 2-layer autoroute chops the GND pour into a big board-wide plane plus a
scatter of small islands wherever the routing is dense.  Two passes of GND
stitching vias fix connectivity:
  (a) a coarse grid where BOTH layers are the main plane  -> ties F-main<->B-main
  (b) one via inside every non-main island, landing where the OPPOSITE layer is
      main GND -> pulls each orphan island (and the GND pad it holds) into the net
Vias only ever land in solid GND on both layers, so they can't short anything.
"""
import sys, pcbnew

F, B = pcbnew.F_Cu, pcbnew.B_Cu
FM, TM = pcbnew.FromMM, pcbnew.ToMM


def main():
    b = pcbnew.LoadBoard(sys.argv[1])
    filler = pcbnew.ZONE_FILLER(b)
    filler.Fill(b.Zones())
    gnd = b.FindNet("GND").GetNetCode()

    def add_via(x, y, diam=FM(0.6)):
        v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
        v.SetDrill(min(FM(0.3), diam - FM(0.2))); v.SetWidth(diam)
        v.SetNetCode(gnd); v.SetLayerPair(F, B); b.Add(v)

    def gnd_polys(layer):
        for z in b.Zones():
            if z.GetNetname() == "GND" and z.IsOnLayer(layer):
                return z.GetFilledPolysList(layer)
        return None

    pf, pb = gnd_polys(F), gnd_polys(B)
    mf = max(range(pf.OutlineCount()), key=lambda i: pf.Outline(i).Area())
    mb = max(range(pb.OutlineCount()), key=lambda i: pb.Outline(i).Area())

    def inside(sp, idx, x, y, m=0):
        for dx, dy in (((0, 0),) if not m else ((0, 0), (m, 0), (-m, 0), (0, m), (0, -m))):
            if not sp.Contains(pcbnew.VECTOR2I(int(x + dx), int(y + dy)), idx):
                return False
        return True

    n = 0
    # (a) main-plane grid stitch — tie the board-wide F plane to the board-wide B plane
    bb = b.GetBoardEdgesBoundingBox()
    step = FM(5.0); mgn = FM(0.55)
    y = bb.GetTop() + FM(3)
    while y < bb.GetBottom() - FM(3):
        x = bb.GetLeft() + FM(3)
        while x < bb.GetRight() - FM(3):
            if inside(pf, mf, x, y, mgn) and inside(pb, mb, x, y, mgn):
                add_via(x, y); n += 1
            x += step
        y += step

    def inside_any(sp, x, y, m):
        return any(inside(sp, k, x, y, m) for k in range(sp.OutlineCount()))

    # (b) drop one via in EVERY non-main island, wherever it overlaps ANY opposite-layer
    # GND copper (main plane or another island). A via ties the two pour pieces
    # electrically, so even fragment->fragment links cascade: after a re-fill the merged
    # net reaches further, and within a few rounds every reachable island chains back to
    # the main plane. 0.5 mm vias (0.45 mm margin) so thin slivers still qualify.
    def stitch_pass(margin, viad):
        added = 0
        for layer, other_layer in ((F, B), (B, F)):
            sp = gnd_polys(layer); other = gnd_polys(other_layer)
            main_idx = max(range(sp.OutlineCount()), key=lambda i: sp.Outline(i).Area())
            for i in range(sp.OutlineCount()):
                if i == main_idx:
                    continue
                bx = sp.Outline(i).BBox(); placed = False; s = FM(0.25)
                gy = bx.GetTop() + s
                while gy < bx.GetBottom() and not placed:
                    gx = bx.GetLeft() + s
                    while gx < bx.GetRight():
                        if inside(sp, i, gx, gy, margin) and inside_any(other, gx, gy, margin):
                            add_via(gx, gy, viad); added += 1; placed = True; break
                        gx += s
                    gy += s
        return added

    for _ in range(6):
        got = stitch_pass(FM(0.45), FM(0.5))
        n += got
        filler.Fill(b.Zones())
        if not got:
            break

    pcbnew.SaveBoard(sys.argv[1], b)
    print(f"    stitched {n} GND vias")


if __name__ == "__main__":
    main()

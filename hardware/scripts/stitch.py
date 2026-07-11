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

    # obstacles the F/B pour polygons don't encode: non-GND tracks on ANY layer (the
    # 5-point pour-margin sampling lets diagonal tracks thread between sample points,
    # and a through-via crosses the inner layers regardless) and every drilled hole
    inner = [t for t in b.Tracks()
             if t.GetClass() == "PCB_TRACK" and t.GetNetCode() != gnd]
    holes = [(t.GetPosition().x, t.GetPosition().y, t.GetDrill() // 2)
             for t in b.Tracks() if t.GetClass() == "PCB_VIA"]
    for p in b.GetPads():
        if p.GetDrillSize().x > 0:
            holes.append((p.GetPosition().x, p.GetPosition().y, p.GetDrillSize().x // 2))

    def _seg_dist(px, py, t):
        x1, y1 = t.GetStart().x, t.GetStart().y
        x2, y2 = t.GetEnd().x, t.GetEnd().y
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        u = 0 if L2 == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L2))
        return ((px - (x1 + u * dx)) ** 2 + (py - (y1 + u * dy)) ** 2) ** 0.5

    CLR, H2H = FM(0.2), FM(0.25)

    # rule areas that forbid vias (board-level keepouts + footprint zones: dome
    # via keepouts, module antenna zone) and every non-GND pad (a through-via can
    # short an SMD pad on any layer)
    novia_zones = [z for z in list(b.Zones()) + [z for fp in b.GetFootprints() for z in fp.Zones()]
                   if z.GetIsRuleArea() and z.GetDoNotAllowVias()]
    # non-GND pads as bounding boxes (a radius model overstates rectangular pads
    # and vetoes every spot near fine-pitch parts like the SOT-23 charger)
    other_pads = []
    for p in b.GetPads():
        if p.GetNetCode() != gnd:
            bb = p.GetBoundingBox()
            other_pads.append((bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom()))

    def _pad_dist(x, y, pb):
        dx = max(pb[0] - x, 0, x - pb[2])
        dy = max(pb[1] - y, 0, y - pb[3])
        return (dx * dx + dy * dy) ** 0.5

    def via_ok(x, y, diam):
        r = diam // 2
        for t in inner:
            if _seg_dist(x, y, t) < r + CLR + t.GetWidth() // 2:
                return False
        hr = min(FM(0.3), diam - FM(0.2)) // 2
        for hx, hy, orad in holes:
            if abs(hx - x) < FM(2) and abs(hy - y) < FM(2):
                if ((hx - x) ** 2 + (hy - y) ** 2) ** 0.5 < hr + orad + H2H:
                    return False
        for pb in other_pads:
            if pb[0] - FM(2) < x < pb[2] + FM(2) and pb[1] - FM(2) < y < pb[3] + FM(2):
                if _pad_dist(x, y, pb) < r + CLR:
                    return False
        pt = pcbnew.VECTOR2I(int(x), int(y))
        for z in novia_zones:
            if z.Outline().Collide(pt, int(r)):
                return False
        return True

    def add_via(x, y, diam=FM(0.6)):
        if not via_ok(x, y, diam):
            return False
        v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
        v.SetDrill(min(FM(0.3), diam - FM(0.2))); v.SetWidth(diam)
        v.SetNetCode(gnd); v.SetLayerPair(F, B); b.Add(v)
        holes.append((int(x), int(y), min(FM(0.3), diam - FM(0.2)) // 2))
        return True

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
            if inside(pf, mf, x, y, mgn) and inside(pb, mb, x, y, mgn) and add_via(x, y):
                n += 1
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
                        if (inside(sp, i, gx, gy, margin) and inside_any(other, gx, gy, margin)
                                and add_via(gx, gy, viad)):
                            added += 1; placed = True; break
                        gx += s
                    gy += s
        return added

    for _ in range(6):
        got = stitch_pass(FM(0.45), FM(0.5))
        n += got
        filler.Fill(b.Zones())
        if not got:
            break

    # (c) any island still orphaned on F or B gets a via straight into the SOLID
    # In1 GND plane (passes a+b only consider F<->B overlap; the plane reaches
    # everywhere except the antenna keep-out, which has no pour to stitch anyway)
    def in1_polys():
        for z in b.Zones():
            if z.GetNetname() == "GND" and z.IsOnLayer(pcbnew.In1_Cu):
                return z.GetFilledPolysList(pcbnew.In1_Cu)
        return None
    p1 = in1_polys()
    if p1 is not None and p1.OutlineCount():
        m1 = max(range(p1.OutlineCount()), key=lambda i: p1.Outline(i).Area())

        def plane_pass(margin, viad):
            got = 0
            for layer in (F, B):
                sp = gnd_polys(layer)
                main_idx = max(range(sp.OutlineCount()), key=lambda i: sp.Outline(i).Area())
                for i in range(sp.OutlineCount()):
                    if i == main_idx:
                        continue
                    bx = sp.Outline(i).BBox(); s = FM(0.25); placed = False
                    gy = bx.GetTop() + s
                    while gy < bx.GetBottom() and not placed:
                        gx = bx.GetLeft() + s
                        while gx < bx.GetRight():
                            if (inside(sp, i, gx, gy, margin) and inside(p1, m1, gx, gy, margin)
                                    and add_via(gx, gy, viad)):
                                got += 1; placed = True; break
                            gx += s
                        gy += s
            return got

        n += plane_pass(FM(0.45), FM(0.5))
        filler.Fill(b.Zones())
        n += plane_pass(FM(0.28), FM(0.4))   # relaxed fallback for tiny pad-blob islands
        filler.Fill(b.Zones())

    # (f) last resort for islands that cannot host ANY via (dome via-keepouts,
    # congestion): tie the island to the same-layer main fill with a SHORT track,
    # but only if the whole corridor verifiably clears every non-GND track, pad,
    # hole and no-track rule area (unlike the old blind bridger).
    notrack_zones = [z for z in list(b.Zones()) + [z for fp in b.GetFootprints() for z in fp.Zones()]
                     if z.GetIsRuleArea() and z.GetDoNotAllowTracks()]

    def corridor_ok(x1, y1, x2, y2, layer, hw):
        import math as _m
        L = _m.hypot(x2 - x1, y2 - y1)
        steps = max(2, int(L / FM(0.2)))
        for k in range(steps + 1):
            x = x1 + (x2 - x1) * k / steps; y = y1 + (y2 - y1) * k / steps
            for t in inner:
                if t.GetLayer() == layer and _seg_dist(x, y, t) < hw + CLR + t.GetWidth() // 2:
                    return False
            for hx, hy, orad in holes:
                if abs(hx - x) < FM(2) and abs(hy - y) < FM(2):
                    if _m.hypot(hx - x, hy - y) < hw + orad + H2H:
                        return False
            for pb in other_pads:
                if pb[0] - FM(2) < x < pb[2] + FM(2) and pb[1] - FM(2) < y < pb[3] + FM(2):
                    if _pad_dist(x, y, pb) < hw + CLR:
                        return False
            pt = pcbnew.VECTOR2I(int(x), int(y))
            for z in notrack_zones:
                if z.Outline().Collide(pt, int(hw)):
                    return False
        return True

    def track_tie_pass(maxlen):
        import math as _m
        got = 0
        for layer in (F, B):
            sp = gnd_polys(layer)
            main_idx = max(range(sp.OutlineCount()), key=lambda i: sp.Outline(i).Area())
            main_pts = [sp.Outline(main_idx).CPoint(k) for k in range(sp.Outline(main_idx).PointCount())]
            for i in range(sp.OutlineCount()):
                if i == main_idx:
                    continue
                isl = [sp.Outline(i).CPoint(k) for k in range(sp.Outline(i).PointCount())]
                best = None
                for a in isl[::2]:
                    for c in main_pts[::2]:
                        d = _m.hypot(a.x - c.x, a.y - c.y)
                        if best is None or d < best[0]:
                            best = (d, a, c)
                if best and best[0] < maxlen:
                    d, a, c = best
                    # pull endpoints 0.2mm INTO their fills along the tie direction
                    ux, uy = (c.x - a.x) / d, (c.y - a.y) / d
                    x1, y1 = a.x - ux * FM(0.2), a.y - uy * FM(0.2)
                    x2, y2 = c.x + ux * FM(0.2), c.y + uy * FM(0.2)
                    if corridor_ok(x1, y1, x2, y2, layer, FM(0.15)):
                        t = pcbnew.PCB_TRACK(b)
                        t.SetStart(pcbnew.VECTOR2I(int(x1), int(y1)))
                        t.SetEnd(pcbnew.VECTOR2I(int(x2), int(y2)))
                        t.SetWidth(FM(0.3)); t.SetLayer(layer); t.SetNetCode(gnd); b.Add(t)
                        got += 1
        return got

    ties = track_tie_pass(FM(4.0))
    if ties:
        filler.Fill(b.Zones())
        n += ties

    pcbnew.SaveBoard(sys.argv[1], b)
    print(f"    stitched {n} GND vias")


if __name__ == "__main__":
    main()

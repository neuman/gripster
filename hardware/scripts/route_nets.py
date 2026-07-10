#!/usr/bin/env python3
"""route_nets.py <board> — deterministically finish the nets Freerouting leaves
open, with a 2-layer A* maze router on a 0.2 mm grid.

Freerouting is stochastic: on a bad seed it abandons a few congested nets. Rather
than re-roll it, we close those nets ourselves. For each still-unconnected non-GND
net we A*-search from one copper component to the nearest other, on a grid whose
blocked cells are OTHER-net copper (inflated by clearance) + rule-area keepouts +
anything outside the board outline. Same-net copper is free, so the path may start
and end on the net's own pads/tracks. Runs before the GND pour is filled.
"""
import sys, heapq, pcbnew

F, B = pcbnew.F_Cu, pcbnew.B_Cu
CELL = pcbnew.FromMM(0.2)
# inflate obstacles by rule-clearance + our half-trace + a full CELL so a track routed
# through free cell-centres can never clip a neighbour once quantised to the grid.
CLEAR = pcbnew.FromMM(0.2) + CELL
HALF = pcbnew.FromMM(0.1)       # half of our 0.2 mm trace
EDGE = pcbnew.FromMM(0.3)       # keep tracks off the board edge / keepout borders
VIA_PEN = 8                     # grid-steps of penalty per layer change


class UF:
    def __init__(s): s.p = {}
    def find(s, x):
        s.p.setdefault(x, x)
        while s.p[x] != x:
            s.p[x] = s.p[s.p[x]]; x = s.p[x]
        return x
    def union(s, a, b): s.p[s.find(a)] = s.find(b)


def components(b, code):
    """Union-find the net's tracks/vias/pads into connected copper components.
    Returns list of components, each a list of (x,y,layerset)."""
    anchors = []; uf = UF(); k = 0
    for t in b.Tracks():
        if t.GetNetCode() != code:
            continue
        if t.GetClass() == "PCB_VIA":
            p = t.GetPosition(); anchors.append([p.x, p.y, {F, B}, f"v{k}"])
        else:
            s, e = t.GetStart(), t.GetEnd(); lay = {t.GetLayer()}
            anchors.append([s.x, s.y, lay, f"t{k}"]); anchors.append([e.x, e.y, lay, f"t{k}"])
        k += 1
    for p in b.GetPads():
        if p.GetNetCode() != code:
            continue
        lays = {L for L in (F, B) if p.IsOnLayer(L)} or {F}
        anchors.append([p.GetPosition().x, p.GetPosition().y, lays, f"p{k}"]); k += 1
    T = pcbnew.FromMM(0.006)
    for i in range(len(anchors)):
        for j in range(i + 1, len(anchors)):
            a, c = anchors[i], anchors[j]
            if abs(a[0] - c[0]) <= T and abs(a[1] - c[1]) <= T and (a[2] & c[2]):
                uf.union(a[3], c[3])
    comp = {}
    for a in anchors:
        comp.setdefault(uf.find(a[3]), []).append(a)
    return list(comp.values())


def main():
    b = pcbnew.LoadBoard(sys.argv[1])
    gnd = b.FindNet("GND").GetNetCode()
    bb = b.GetBoardEdgesBoundingBox()
    X0, Y0 = bb.GetLeft(), bb.GetTop()
    NX = bb.GetWidth() // CELL + 2; NY = bb.GetHeight() // CELL + 2
    outline = pcbnew.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(outline)

    def cx(ix): return X0 + ix * CELL + CELL // 2
    def cy(iy): return Y0 + iy * CELL + CELL // 2
    def gi(x, y): return (int((x - X0) // CELL), int((y - Y0) // CELL))

    def near_edge(px, py):
        for dx, dy in ((EDGE, 0), (-EDGE, 0), (0, EDGE), (0, -EDGE)):
            if not outline.Contains(pcbnew.VECTOR2I(px + dx, py + dy), -1, True):
                return True
        return False

    # cells outside the board, or within EDGE of the outline, are permanently blocked
    edge_blocked = set()
    for ix in range(NX):
        for iy in range(NY):
            px, py = cx(ix), cy(iy)
            if not outline.Contains(pcbnew.VECTOR2I(px, py), -1, True) or near_edge(px, py):
                edge_blocked.add((ix, iy))

    # rule-area keepouts — board-level (mount holes) AND footprint-level (the E73's
    # antenna keepout lives inside U1's footprint, NOT in b.Zones()). Rasterise each
    # actual polygon inflated by EDGE, both layers.
    keepout = {F: set(), B: set()}
    rule_zones = list(b.Zones())
    for fp in b.GetFootprints():
        rule_zones += list(fp.Zones())
    for z in rule_zones:
        if not z.GetIsRuleArea():
            continue
        poly = z.Outline()
        zb = z.GetBoundingBox(); m = EDGE + CELL
        ax, ay = gi(zb.GetLeft() - m, zb.GetTop() - m); bx, by = gi(zb.GetRight() + m, zb.GetBottom() + m)
        for ix in range(max(0, ax), min(NX, bx + 1)):
            for iy in range(max(0, ay), min(NY, by + 1)):
                if poly.Collide(pcbnew.VECTOR2I(cx(ix), cy(iy)), EDGE):
                    keepout[F].add((ix, iy)); keepout[B].add((ix, iy))

    def obstacle_grid(exclude):
        """blocked cells per layer from every net except `exclude` (+ keepouts + edge)."""
        blk = {F: set(keepout[F]) | edge_blocked, B: set(keepout[B]) | edge_blocked}

        def disc(layers, x, y, r):
            rr = r + CELL
            ax, ay = gi(x - rr, y - rr); bx, by = gi(x + rr, y + rr)
            for ix in range(max(0, ax), min(NX, bx + 1)):
                for iy in range(max(0, ay), min(NY, by + 1)):
                    if (cx(ix) - x) ** 2 + (cy(iy) - y) ** 2 <= r * r:
                        for L in layers:
                            blk[L].add((ix, iy))

        def seg(layer, a, c, r):
            n = max(1, int(((a.x - c.x) ** 2 + (a.y - c.y) ** 2) ** 0.5 // (CELL // 2)))
            for s in range(n + 1):
                disc((layer,), a.x + (c.x - a.x) * s // n, a.y + (c.y - a.y) * s // n, r)

        for t in b.Tracks():
            if t.GetNetCode() == exclude:
                continue
            if t.GetClass() == "PCB_VIA":
                disc((F, B), t.GetPosition().x, t.GetPosition().y, pcbnew.FromMM(0.35) + CLEAR + HALF)
            else:
                seg(t.GetLayer(), t.GetStart(), t.GetEnd(), t.GetWidth() // 2 + CLEAR + HALF)
        for p in b.GetPads():
            if p.GetNetCode() == exclude:
                continue
            lays = tuple(L for L in (F, B) if p.IsOnLayer(L)) or (F, B)
            r = max(p.GetSize().x, p.GetSize().y) // 2 + CLEAR + HALF
            disc(lays, p.GetPosition().x, p.GetPosition().y, r)
        return blk

    def astar(blk, starts, goals):
        goalset = {(ix, iy) for ix, iy, L in goals}
        goalL = {}
        for ix, iy, L in goals:
            goalL.setdefault((ix, iy), set()).add(L)
        openq = []
        g = {}
        for ix, iy, L in starts:
            g[(ix, iy, L)] = 0; heapq.heappush(openq, (0, (ix, iy, L)))
        came = {}
        gx0 = min(goalset, key=lambda p: p[0])[0]
        while openq:
            _, cur = heapq.heappop(openq)
            ix, iy, L = cur
            if (ix, iy) in goalset and L in goalL[(ix, iy)]:
                path = [cur]
                while cur in came:
                    cur = came[cur]; path.append(cur)
                return path[::-1]
            for dix, diy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = ix + dix, iy + diy
                if 0 <= nx < NX and 0 <= ny < NY and (nx, ny) not in blk[L]:
                    nb = (nx, ny, L); ng = g[cur] + 1
                    if ng < g.get(nb, 1 << 30):
                        g[nb] = ng; came[nb] = cur
                        h = abs(nx - gx0) + 0  # cheap admissible-ish heuristic
                        heapq.heappush(openq, (ng + h, nb))
            oL = B if L == F else F
            if (ix, iy) not in blk[oL]:
                nb = (ix, iy, oL); ng = g[cur] + VIA_PEN
                if ng < g.get(nb, 1 << 30):
                    g[nb] = ng; came[nb] = cur
                    heapq.heappush(openq, (ng, nb))
        return None

    closed = failed = []
    closed = 0; failreport = []
    # iterate nets; recompute components after each success (net may need >1 bridge)
    for code in range(1, b.GetNetInfo().GetNetCount()):
        if code == gnd:
            continue
        guard = 0
        while guard < 6:
            guard += 1
            comps = components(b, code)
            if len(comps) < 2:
                break
            # choose the two components with the closest anchors
            best = None
            for i in range(len(comps)):
                for j in range(i + 1, len(comps)):
                    for a in comps[i]:
                        for c in comps[j]:
                            d = (a[0] - c[0]) ** 2 + (a[1] - c[1]) ** 2
                            if best is None or d < best[0]:
                                best = (d, a, c, i, j)
            _, a, c, i, j = best
            blk = obstacle_grid(code)
            starts = [(*gi(a[0], a[1]), L) for L in a[2]]
            goals = [(*gi(c[0], c[1]), L) for L in c[2]]
            path = astar(blk, starts, goals)
            if not path:
                failreport.append(b.GetNetInfo().GetNetItem(code).GetNetname()); break
            # lay tracks along the path (+ vias at layer changes)
            net = code
            for p in range(len(path) - 1):
                ix, iy, L = path[p]; nx, ny, nL = path[p + 1]
                if L == nL:
                    t = pcbnew.PCB_TRACK(b)
                    t.SetStart(pcbnew.VECTOR2I(cx(ix), cy(iy))); t.SetEnd(pcbnew.VECTOR2I(cx(nx), cy(ny)))
                    t.SetWidth(pcbnew.FromMM(0.2)); t.SetLayer(L); t.SetNetCode(net); b.Add(t)
                else:
                    v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(cx(ix), cy(iy)))
                    v.SetDrill(pcbnew.FromMM(0.3)); v.SetWidth(pcbnew.FromMM(0.6))
                    v.SetNetCode(net); v.SetLayerPair(F, B); b.Add(v)
            # weld path ends onto the real anchor points
            _weld(b, a, path[0], cx, cy, code)
            _weld(b, c, path[-1], cx, cy, code)
            closed += 1

    pcbnew.SaveBoard(sys.argv[1], b)
    msg = f"    maze-routed {closed} net segment(s)"
    if failreport:
        msg += "; FAILED: " + ", ".join(sorted(set(failreport)))
    print(msg)


def _weld(b, anchor, cell, cx, cy, code):
    """short track from the grid-snapped path end to the exact anchor point."""
    ix, iy, L = cell
    ax, ay, lays, _ = anchor
    layer = L if L in lays else next(iter(lays))
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(cx(ix), cy(iy))); t.SetEnd(pcbnew.VECTOR2I(ax, ay))
    t.SetWidth(pcbnew.FromMM(0.2)); t.SetLayer(layer); t.SetNetCode(code); b.Add(t)


if __name__ == "__main__":
    main()

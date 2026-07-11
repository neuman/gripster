#!/usr/bin/env python3
"""finish_route.py <board> — deterministically close every remaining unconnected
signal net after Freerouting, with an A* maze router on a 0.1 mm 2-layer grid.

Freerouting routes the bulk (the matrix) but leaves the dense E73 module fan-in
partly open (power/USB/SWD/odd columns escaping the 0.8 mm inner pads). This tool
finds the TRUE unconnected pad pairs from KiCad's own connectivity (T-junction
aware — unlike the union-find in close_gaps.py), then routes each pair on real
copper, respecting clearance to every other net, using vias to change layer. It
never touches GND (the pour + stitcher own that).

Grid model: cells = 0.1 mm. Obstacles = all OTHER-net copper (tracks/vias/pads)
grown by (their halfwidth + clearance + our halfwidth); the routed net's own
copper is free (source/goal). Board outside + edge-clearance is blocked.
"""
import sys, os, heapq, math
import numpy as np
import pcbnew
from matplotlib.path import Path as MplPath

F, B = pcbnew.F_Cu, pcbnew.B_Cu
IN2 = pcbnew.In2_Cu    # inner SIGNAL layer (In1 is the GND plane, not routed on)
# 3 routable signal layers; index 0=F, 1=In2, 2=B. Through-hole vias span all of them.
SIGLAYERS = [F, IN2, B]
LAYER_IDX = {F: 0, IN2: 1, B: 2}
NL = 3
GRID = 100000          # 0.1 mm in nm
CLEAR = 270000         # 0.27 mm: board rule 0.2 + grid/corner-cut margin
OURW = 200000          # our track width 0.2 mm (match Freerouting output)
EDGE_CLR = 250000      # 0.25 mm board-edge clearance
VIA_DIA = 500000       # 0.5 mm via
VIA_DRILL = 300000     # 0.3 mm drill
VIA_COST_CELLS = 12    # via penalty ~ 1.2 mm of travel


def mm(v): return pcbnew.ToMM(v)


def disk(rcells):
    r = int(math.ceil(rcells))
    y, x = np.ogrid[-r:r+1, -r:r+1]
    return (x*x + y*y) <= (rcells*rcells)


_DISK_CACHE = {}
def get_disk(r_nm):
    rc = max(1, int(round(r_nm / GRID)))
    if rc not in _DISK_CACHE:
        _DISK_CACHE[rc] = disk(rc)
    return _DISK_CACHE[rc], rc


class Grid:
    def __init__(self, board):
        self.b = board
        bb = board.GetBoardEdgesBoundingBox()
        self.x0 = bb.GetLeft() - GRID*2
        self.y0 = bb.GetTop() - GRID*2
        self.nx = int((bb.GetWidth()) / GRID) + 5
        self.ny = int((bb.GetHeight()) / GRID) + 5
        # inside-board mask (both layers share it) + keepout rule-areas
        self.outside = self._build_outside(board)
        self._add_keepouts(board)
        # cache all copper items once
        self.tracks = [t for t in board.Tracks() if t.GetClass() != "PCB_VIA"]
        self.vias = [t for t in board.Tracks() if t.GetClass() == "PCB_VIA"]
        self.pads = list(board.GetPads())

    def gx(self, x): return int((x - self.x0) / GRID)
    def gy(self, y): return int((y - self.y0) / GRID)
    def wx(self, ix): return int(self.x0 + ix * GRID)
    def wy(self, iy): return int(self.y0 + iy * GRID)

    def _build_outside(self, board):
        # union of Edge.Cuts segments -> polygon(s); use board polygon
        poly = pcbnew.SHAPE_POLY_SET()
        ok = board.GetBoardPolygonOutlines(poly)
        pts = []
        if ok and poly.OutlineCount() > 0:
            o = poly.Outline(0)
            for i in range(o.PointCount()):
                p = o.CPoint(i)
                pts.append((p.x, p.y))
        outside = np.ones((self.ny, self.nx), dtype=bool)
        if len(pts) >= 3:
            mpl = MplPath([(self.gx(x), self.gy(y)) for x, y in pts])
            xs, ys = np.meshgrid(np.arange(self.nx), np.arange(self.ny))
            grid_pts = np.column_stack([xs.ravel(), ys.ravel()])
            inside = mpl.contains_points(grid_pts).reshape(self.ny, self.nx)
            outside = ~inside
        # grow outside by edge clearance
        outside = self._dilate(outside, int(EDGE_CLR / GRID))
        return outside

    def _add_keepouts(self, board):
        """Block track/via keepout rule-areas (antenna, mount holes) on all layers."""
        for z in board.Zones():
            if not z.GetIsRuleArea():
                continue
            if not (z.GetDoNotAllowTracks() or z.GetDoNotAllowVias()):
                continue
            op = z.Outline()
            for oi in range(op.OutlineCount()):
                o = op.Outline(oi)
                pts = [(self.gx(o.CPoint(i).x), self.gy(o.CPoint(i).y)) for i in range(o.PointCount())]
                if len(pts) < 3:
                    continue
                mpl = MplPath(pts)
                xmn = max(0, min(p[0] for p in pts) - 3); xmx = min(self.nx, max(p[0] for p in pts) + 3)
                ymn = max(0, min(p[1] for p in pts) - 3); ymx = min(self.ny, max(p[1] for p in pts) + 3)
                if xmx <= xmn or ymx <= ymn:
                    continue
                xs, ys = np.meshgrid(np.arange(xmn, xmx), np.arange(ymn, ymx))
                gp = np.column_stack([xs.ravel(), ys.ravel()])
                inside = mpl.contains_points(gp, radius=2).reshape(ymx - ymn, xmx - xmn)
                self.outside[ymn:ymx, xmn:xmx] |= inside

    @staticmethod
    def _dilate(mask, it):
        m = mask.copy()
        for _ in range(it):
            m[1:, :] |= mask[:-1, :]; m[:-1, :] |= mask[1:, :]
            m[:, 1:] |= mask[:, :-1]; m[:, :-1] |= mask[:, 1:]
            mask = m.copy()
        return m

    def _stamp(self, arr, cx_nm, cy_nm, r_nm):
        d, rc = get_disk(r_nm)
        ix, iy = self.gx(cx_nm), self.gy(cy_nm)
        x1, x2 = ix - rc, ix + rc + 1
        y1, y2 = iy - rc, iy + rc + 1
        dx1 = max(0, -x1); dy1 = max(0, -y1)
        x1c, y1c = max(0, x1), max(0, y1)
        x2c, y2c = min(self.nx, x2), min(self.ny, y2)
        if x2c <= x1c or y2c <= y1c:
            return
        sub = d[dy1:dy1 + (y2c - y1c), dx1:dx1 + (x2c - x1c)]
        arr[y1c:y2c, x1c:x2c] |= sub

    def _stamp_seg(self, arr, p1, p2, r_nm):
        x1, y1 = p1; x2, y2 = p2
        length = math.hypot(x2 - x1, y2 - y1)
        n = max(1, int(length / (GRID)) + 1)
        for i in range(n + 1):
            t = i / n
            self._stamp(arr, x1 + (x2 - x1) * t, y1 + (y2 - y1) * t, r_nm)

    def obstacles_for(self, net_code):
        """Return a list of NL boolean grids (idx 0=F,1=In2,2=B): True=blocked for
        routing net_code. Other-net copper grown by clearance; own-net copper free.
        Through-hole vias/THT pads block ALL signal layers."""
        obs = [self.outside.copy() for _ in range(NL)]
        for t in self.tracks:
            if t.GetNetCode() == net_code:
                continue
            li = LAYER_IDX.get(t.GetLayer())
            if li is None:
                continue
            r = t.GetWidth() / 2 + CLEAR + OURW / 2
            self._stamp_seg(obs[li], (t.GetStart().x, t.GetStart().y),
                            (t.GetEnd().x, t.GetEnd().y), r)
        for v in self.vias:
            if v.GetNetCode() == net_code:
                continue
            r = 600000 / 2 + CLEAR + OURW / 2
            for li in range(NL):
                self._stamp(obs[li], v.GetPosition().x, v.GetPosition().y, r)
        for p in self.pads:
            if p.GetNetCode() == net_code:
                continue
            pr = max(p.GetSize().x, p.GetSize().y) / 2 + CLEAR + OURW / 2
            pos = p.GetPosition()
            for L in SIGLAYERS:
                if p.IsOnLayer(L):
                    self._stamp(obs[LAYER_IDX[L]], pos.x, pos.y, pr)
        return obs

    def net_copper_cells(self, net_code):
        """Cells (per layer) occupied by this net's copper -> goals/sources."""
        g = [np.zeros((self.ny, self.nx), dtype=bool) for _ in range(NL)]
        for t in self.tracks:
            if t.GetNetCode() != net_code:
                continue
            li = LAYER_IDX.get(t.GetLayer())
            if li is None:
                continue
            self._stamp_seg(g[li], (t.GetStart().x, t.GetStart().y),
                            (t.GetEnd().x, t.GetEnd().y), t.GetWidth() / 2 + GRID)
        for v in self.vias:
            if v.GetNetCode() != net_code:
                continue
            for li in range(NL):
                self._stamp(g[li], v.GetPosition().x, v.GetPosition().y, VIA_DIA / 2)
        return g


def astar(grid, obs, starts, goal):
    """obs, goal: lists of NL grids (idx 0=F,1=In2,2=B). starts: [(layer_idx,ix,iy)].
    8-connected in-layer moves + through-hole via to any other signal layer.
    Returns [(layer_idx,ix,iy)] path or None."""
    free = [obs[li] == 0 for li in range(NL)]
    ny, nx = obs[0].shape
    # own-net goal cells may sit under the target pad's own obstacle expansion -> force free
    freeg = [free[li] | goal[li] for li in range(NL)]
    # a through-hole via needs ALL signal layers clear at the cell
    via_ok = free[0] & free[1] & free[2]

    gc = []
    for li in range(NL):
        ys, xs = np.where(goal[li])
        if len(xs):
            gc.append((xs.min(), xs.max(), ys.min(), ys.max()))
    def heur(ix, iy):
        if not gc:
            return 0
        ds = []
        for (xmn, xmx, ymn, ymx) in gc:
            dx = 0 if xmn <= ix <= xmx else min(abs(ix-xmn), abs(ix-xmx))
            dy = 0 if ymn <= iy <= ymx else min(abs(iy-ymn), abs(iy-ymx))
            ds.append((dx*dx + dy*dy) ** 0.5)
        return min(ds)

    openh = []; came = {}; gsc = {}
    for (li, ix, iy) in starts:
        if 0 <= ix < nx and 0 <= iy < ny:
            s = (li, ix, iy); gsc[s] = 0.0
            heapq.heappush(openh, (heur(ix, iy), s))
    nbrs = [(-1,0,1.0),(1,0,1.0),(0,-1,1.0),(0,1,1.0),
            (-1,-1,1.414),(1,1,1.414),(-1,1,1.414),(1,-1,1.414)]
    while openh:
        _, cur = heapq.heappop(openh)
        li, ix, iy = cur
        if goal[li][iy, ix]:
            path = [cur]
            while cur in came:
                cur = came[cur]; path.append(cur)
            return path[::-1]
        base = gsc[cur]
        for dx, dy, c in nbrs:
            nxk, nyk = ix + dx, iy + dy
            if not (0 <= nxk < nx and 0 <= nyk < ny and freeg[li][nyk, nxk]):
                continue
            if dx != 0 and dy != 0 and not (freeg[li][iy, ix+dx] and freeg[li][iy+dy, ix]):
                continue
            nd = base + c; st = (li, nxk, nyk)
            if nd < gsc.get(st, 1e18):
                gsc[st] = nd; came[st] = cur
                heapq.heappush(openh, (nd + heur(nxk, nyk), st))
        # through-hole via to any other signal layer
        if via_ok[iy, ix]:
            for ol in range(NL):
                if ol == li:
                    continue
                nd = base + VIA_COST_CELLS; st = (ol, ix, iy)
                if nd < gsc.get(st, 1e18):
                    gsc[st] = nd; came[st] = cur
                    heapq.heappush(openh, (nd + heur(ix, iy), st))
    return None


def lay_path(board, grid, net, path, start_pt=None, end_pt=None):
    """Emit tracks + vias for a path. Merge collinear same-layer runs. start_pt /
    end_pt (world nm) override the first/last vertex so the copper lands exactly on
    the real source/target anchor (guarantees electrical connection)."""
    LNET = {0: F, 1: IN2, 2: B}
    # split into layer runs
    i = 0
    n = len(path)
    added_t = added_v = 0
    while i < n - 1:
        li = path[i][0]
        j = i
        while j < n - 1 and path[j+1][0] == li:
            j += 1
        # polyline path[i..j] on layer li -> simplify by direction changes
        pts = [(grid.wx(ix), grid.wy(iy)) for (_, ix, iy) in path[i:j+1]]
        if i == 0 and start_pt is not None:
            pts[0] = start_pt
        if j == n - 1 and end_pt is not None:
            pts[-1] = end_pt
        simp = [pts[0]]
        for k in range(1, len(pts)-1):
            ax = pts[k][0]-simp[-1][0]; ay = pts[k][1]-simp[-1][1]
            bx = pts[k+1][0]-pts[k][0]; by = pts[k+1][1]-pts[k][1]
            if ax*by - ay*bx != 0:  # direction change
                simp.append(pts[k])
        simp.append(pts[-1])
        for a, b in zip(simp, simp[1:]):
            if a == b:
                continue
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pcbnew.VECTOR2I(*a)); t.SetEnd(pcbnew.VECTOR2I(*b))
            t.SetWidth(OURW); t.SetLayer(LNET[li]); t.SetNet(net); board.Add(t)
            added_t += 1
        # via at the transition (end of this run) if not last
        if j < n - 1:
            ix, iy = path[j][1], path[j][2]
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(pcbnew.VECTOR2I(grid.wx(ix), grid.wy(iy)))
            v.SetDrill(VIA_DRILL); v.SetWidth(VIA_DIA)
            v.SetLayerPair(F, B); v.SetNet(net); board.Add(v)
            added_v += 1
        i = j + 1
    return added_t, added_v


def _pt_seg_d(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _seg_seg_d(a1, a2, b1, b2):
    # min distance between segment a1a2 and b1b2 (nm). Cheap: sample endpoints
    # both ways (adequate for detecting copper overlap with tolerance).
    return min(_pt_seg_d(*a1, *b1, *b2), _pt_seg_d(*a2, *b1, *b2),
               _pt_seg_d(*b1, *a1, *a2), _pt_seg_d(*b2, *a1, *a2))


class UF:
    def __init__(self, n): self.p = list(range(n))
    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]; x = self.p[x]
        return x
    def union(self, a, b): self.p[self.find(a)] = self.find(b)


def net_clusters(board, code):
    """T-junction-aware geometric clustering of a net's copper. Returns a list of
    clusters; each cluster is a list of primitives {kind,pt|seg,hw,L(set of layer)}."""
    prims = []
    for t in board.Tracks():
        if t.GetNetCode() != code:
            continue
        if t.GetClass() == "PCB_VIA":
            p = t.GetPosition()
            prims.append({"pt": (p.x, p.y), "hw": 300000, "L": set(SIGLAYERS)})
        else:
            lay = t.GetLayer()
            if lay not in LAYER_IDX:   # ignore any stray copper not on a signal layer
                continue
            s, e = t.GetStart(), t.GetEnd()
            prims.append({"seg": ((s.x, s.y), (e.x, e.y)),
                          "hw": t.GetWidth() / 2, "L": {lay}})
    for pad in board.GetPads():
        if pad.GetNetCode() != code:
            continue
        p = pad.GetPosition()
        L = {l for l in SIGLAYERS if pad.IsOnLayer(l)} or {F}
        prims.append({"pt": (p.x, p.y), "hw": max(pad.GetSize().x, pad.GetSize().y) / 2,
                      "L": L, "pad": pad})
    n = len(prims)
    uf = UF(n)
    TOL = 2000
    for i in range(n):
        for j in range(i + 1, n):
            a, b = prims[i], prims[j]
            if not (a["L"] & b["L"]):
                continue
            reach = a["hw"] + b["hw"] + TOL
            if "seg" in a and "seg" in b:
                d = _seg_seg_d(a["seg"][0], a["seg"][1], b["seg"][0], b["seg"][1])
            elif "seg" in a:
                d = _pt_seg_d(*b["pt"], *a["seg"][0], *a["seg"][1])
            elif "seg" in b:
                d = _pt_seg_d(*a["pt"], *b["seg"][0], *b["seg"][1])
            else:
                d = math.hypot(a["pt"][0] - b["pt"][0], a["pt"][1] - b["pt"][1])
            if d <= reach:
                uf.union(i, j)
    groups = {}
    for i in range(n):
        groups.setdefault(uf.find(i), []).append(prims[i])
    return list(groups.values())


def _prim_cells(grid, prim):
    """Rasterize a primitive's copper into (list of (layer_idx, ix, iy)) start cells."""
    cells = []
    if "seg" in prim:
        (ax, ay), (bx, by) = prim["seg"]
        n = max(1, int(math.hypot(bx - ax, by - ay) / GRID))
        for i in range(n + 1):
            t = i / n
            x = ax + (bx - ax) * t; y = ay + (by - ay) * t
            for L in prim["L"]:
                cells.append((LAYER_IDX[L], grid.gx(x), grid.gy(y)))
    else:
        x, y = prim["pt"]
        for L in prim["L"]:
            cells.append((LAYER_IDX[L], grid.gx(x), grid.gy(y)))
    return cells


def _stamp_cluster_goal(grid, cluster, goalF, goalB):
    arr = {0: goalF, 1: goalB}
    for prim in cluster:
        r = prim["hw"] + GRID
        if "seg" in prim:
            (a, bb) = prim["seg"]
            for L in prim["L"]:
                grid._stamp_seg(arr[LAYER_IDX[L]], a, bb, r)
        else:
            for L in prim["L"]:
                grid._stamp(arr[LAYER_IDX[L]], prim["pt"][0], prim["pt"][1], r)


def cluster_anchors(cluster):
    """Representative copper points of a cluster: (x,y,layer_idx). Prefer pad
    centres, then via points, then track endpoints."""
    pads, vias, ends = [], [], []
    for p in cluster:
        if "pad" in p:
            for L in p["L"]:
                pads.append((p["pt"][0], p["pt"][1], LAYER_IDX[L]))
        elif "pt" in p:
            for L in p["L"]:
                vias.append((p["pt"][0], p["pt"][1], LAYER_IDX[L]))
        else:
            for pt in p["seg"]:
                for L in p["L"]:
                    ends.append((pt[0], pt[1], LAYER_IDX[L]))
    return pads + vias + ends


def main():
    path = sys.argv[1]
    board = pcbnew.LoadBoard(path)
    grid = Grid(board)
    gnd = board.FindNet("GND").GetNetCode()
    ni = board.GetNetInfo()
    routed = failed = 0
    for code in range(1, ni.GetNetCount()):
        if code == gnd:
            continue
        clusters = net_clusters(board, code)
        if len(clusters) < 2:
            continue
        name = ni.GetNetItem(code).GetNetname()
        clusters.sort(key=len, reverse=True)
        anchor = clusters[0]
        for tgt in clusters[1:]:
            aA = cluster_anchors(anchor)
            aB = cluster_anchors(tgt)
            if not aA or not aB:
                failed += 1; continue
            # nearest anchor pair
            best = None
            for (bx, by, bl) in aB:
                for (ax, ay, al) in aA:
                    d = (ax-bx)**2 + (ay-by)**2
                    if best is None or d < best[0]:
                        best = (d, (ax, ay, al), (bx, by, bl))
            _, (sx, sy, sl), (tx, ty, tl) = best
            obs = grid.obstacles_for(code)
            goal = [np.zeros((grid.ny, grid.nx), dtype=bool) for _ in range(NL)]
            goal[tl][grid.gy(ty), grid.gx(tx)] = True
            starts = [(sl, grid.gx(sx), grid.gy(sy))]
            pth = astar(grid, obs, starts, goal)
            if pth is None:
                print(f"      FAIL {name}: no path")
                failed += 1
                continue
            at, av = lay_path(board, grid, board.FindNet(name), pth,
                              start_pt=(int(sx), int(sy)), end_pt=(int(tx), int(ty)))
            routed += 1
            print(f"      routed {name}: {at} segs, {av} vias")
            grid.tracks = [t for t in board.Tracks() if t.GetClass() != "PCB_VIA"]
            grid.vias = [t for t in board.Tracks() if t.GetClass() == "PCB_VIA"]
            anchor = anchor + tgt
    pcbnew.SaveBoard(path, board)
    print(f"    finish_route done: {routed} routed, {failed} failed")


if __name__ == "__main__":
    main()

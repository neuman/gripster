#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Eric Neuman
"""close_gaps.py <board> [maxgap_mm] — close the short signal stubs Freerouting
leaves behind, by reconstructing each net's copper connectivity ourselves (the
KiCad ratsnest object isn't usable from Python).

For every non-GND net we union-find its tracks/vias/pads into connected copper
components. While a net has >1 component we bridge the two whose nearest anchors
are closest — a track (plus a via when the ends are on different layers) — but
only if that gap is under the threshold. Longer gaps are real routing and are
reported, not bridged. GND is handled by the pour + stitcher, so it's skipped.
"""
import sys, math, pcbnew

F, B = pcbnew.F_Cu, pcbnew.B_Cu
TOL = 6000          # 6 um coincidence tolerance (nm)
MAXGAP = pcbnew.FromMM(float(sys.argv[2]) if len(sys.argv) > 2 else 4.0)


class UF:
    def __init__(s): s.p = {}
    def find(s, x):
        s.p.setdefault(x, x)
        while s.p[x] != x:
            s.p[x] = s.p[s.p[x]]; x = s.p[x]
        return x
    def union(s, a, b): s.p[s.find(a)] = s.find(b)


def main():
    b = pcbnew.LoadBoard(sys.argv[1])
    gnd = b.FindNet("GND").GetNetCode()
    ni = b.GetNetInfo()
    closed = skipped = 0
    report = []

    for code in range(1, ni.GetNetCount()):
        if code == gnd:
            continue
        tracks = [t for t in b.Tracks() if t.GetNetCode() == code]
        pads = [p for p in b.GetPads() if p.GetNetCode() == code]
        if not tracks and not pads:
            continue

        # anchors: list of dicts {x,y,layers,uid}; uid groups copper physically joined
        anchors = []
        uf = UF()

        def add(x, y, layers, uid):
            anchors.append({"x": x, "y": y, "L": layers, "u": uid}); uf.find(uid)

        k = 0
        for t in tracks:
            if t.GetClass() == "PCB_VIA":
                p = t.GetPosition(); add(p.x, p.y, {F, B}, f"v{k}")
            else:
                s, e = t.GetStart(), t.GetEnd(); lay = {t.GetLayer()}
                add(s.x, s.y, lay, f"t{k}"); add(e.x, e.y, lay, f"t{k}")  # same uid = joined
            k += 1
        for p in pads:
            lays = {L for L in (F, B) if p.IsOnLayer(L)}
            add(p.GetPosition().x, p.GetPosition().y, lays or {F}, f"p{k}"); k += 1

        # union coincident anchors that share a layer
        for i in range(len(anchors)):
            for j in range(i + 1, len(anchors)):
                a, c = anchors[i], anchors[j]
                if abs(a["x"] - c["x"]) <= TOL and abs(a["y"] - c["y"]) <= TOL and (a["L"] & c["L"]):
                    uf.union(a["u"], c["u"])

        # components of anchors
        comp = {}
        for a in anchors:
            comp.setdefault(uf.find(a["u"]), []).append(a)
        if len(comp) < 2:
            continue

        # while >1 component, bridge the closest pair
        groups = list(comp.values())
        while len(groups) > 1:
            best = None
            for gi in range(len(groups)):
                for gj in range(gi + 1, len(groups)):
                    for a in groups[gi]:
                        for c in groups[gj]:
                            d = math.hypot(a["x"] - c["x"], a["y"] - c["y"])
                            if best is None or d < best[0]:
                                best = (d, a, c, gi, gj)
            d, a, c, gi, gj = best
            if d > MAXGAP:
                report.append((ni.GetNetItem(code).GetNetname(), round(pcbnew.ToMM(d), 2)))
                skipped += 1
                break
            shared = a["L"] & c["L"]
            layer = next(iter(shared)) if shared else next(iter(a["L"]))
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(pcbnew.VECTOR2I(a["x"], a["y"])); t.SetEnd(pcbnew.VECTOR2I(c["x"], c["y"]))
            t.SetWidth(pcbnew.FromMM(0.2)); t.SetLayer(layer); t.SetNetCode(code); b.Add(t)
            if not shared:  # different layers -> drop a via at c
                v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(c["x"], c["y"]))
                v.SetDrill(pcbnew.FromMM(0.3)); v.SetWidth(pcbnew.FromMM(0.6))
                v.SetNetCode(code); v.SetLayerPair(F, B); b.Add(v)
            closed += 1
            groups[gi] = groups[gi] + groups.pop(gj)  # merge

    pcbnew.SaveBoard(sys.argv[1], b)
    msg = f"    closed {closed} short gaps"
    if report:
        msg += "; LEFT (too long): " + ", ".join(f"{n}={d}mm" for n, d in report)
    print(msg)


if __name__ == "__main__":
    main()

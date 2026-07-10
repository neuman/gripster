#!/usr/bin/env python3
"""inspect_board.py <board> — factual inventory of a KiCad board for review."""
import sys, pcbnew
from collections import Counter, defaultdict

b = pcbnew.LoadBoard(sys.argv[1])
b.BuildConnectivity()
print(f"=== {sys.argv[1]} ===")
bb = b.GetBoardEdgesBoundingBox()
print(f"board size: {pcbnew.ToMM(bb.GetWidth()):.1f} x {pcbnew.ToMM(bb.GetHeight()):.1f} mm")

# footprints
fps = list(b.GetFootprints())
print(f"\n-- {len(fps)} footprints --")
by_layer = Counter("B.Cu" if f.IsFlipped() else "F.Cu" for f in fps)
print("by layer:", dict(by_layer))
# group by value prefix
rows = []
for f in fps:
    ref = f.GetReference(); val = f.GetValue()
    layer = "B" if f.IsFlipped() else "F"
    p = f.GetPosition()
    rows.append((ref, val, layer, round(pcbnew.ToMM(p.x),1), round(pcbnew.ToMM(p.y),1), f.GetFPIDAsString()))
# print non-switch/diode components (the interesting ones)
print("\n-- non-SW/D components --")
for ref,val,layer,x,y,fid in sorted(rows):
    if ref[0:2] in ("SW",) or (ref[0]=="D" and ref[1:].isdigit()):
        continue
    print(f"  {ref:6} {val:16} {layer} ({x:6},{y:6})  {fid}")

print(f"\n-- switches: {sum(1 for r in rows if r[0].startswith('SW'))}, diodes: {sum(1 for r in rows if r[0][0]=='D' and r[0][1:].isdigit())} --")

# nets: pad count each
print("\n-- nets (padcount) --")
ni = b.GetNetInfo()
netpads = Counter()
for f in fps:
    for pad in f.Pads():
        netpads[pad.GetNetname()] += 1
for name,cnt in sorted(netpads.items()):
    if name=="": continue
    print(f"  {name:14} {cnt} pads")

# tracks / vias / zones
tr = [t for t in b.Tracks() if t.GetClass()!="PCB_VIA"]
vias = [t for t in b.Tracks() if t.GetClass()=="PCB_VIA"]
print(f"\n-- {len(tr)} tracks, {len(vias)} vias, {len(list(b.Zones()))} zones --")
# track widths
tw = Counter(round(pcbnew.ToMM(t.GetWidth()),3) for t in tr)
print("track widths:", dict(tw))
# via drill/size
vd = Counter((round(pcbnew.ToMM(v.GetDrillValue()),3), round(pcbnew.ToMM(v.GetWidth()),3)) for v in vias)
print("via (drill,dia):", dict(vd))

# unconnected
unc = b.GetConnectivity().GetUnconnectedCount(False)
print(f"\nunconnected ratsnest: {unc}")

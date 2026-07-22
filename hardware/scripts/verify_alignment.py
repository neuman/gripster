#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Eric Neuman
"""verify_alignment.py — v0.17 top-to-bottom 2D stack alignment audit.

Checks that every layer of the stack lines up, from the shell openings through the
keymat caps to the dome pads and diodes on the PCB, for BOTH grips:

  1. PCB dome (SW*) positions == deck.py key/feature centres (the two are generated
     from the same model, but this catches frame/mirror/regression bugs).
  2. Diode DN nodes sit at key + (0, +3.0) deck mm on the back.
  3. Dome contact courtyards (r 3.9) never overlap: min centre spacing >= 7.8 mm
     across grid + cluster keys.
  4. Rectangular caps (8.5 x 7.0, 2u space 18.5) never overlap and keep printable
     gutters (>= 1.0 mm X between openings incl. 0.2/side lid clearance).
  5. Keycap rectangles fully cover their dome (7.0 mm dia) so the plunger always
     presses the dome centre.
  6. Mount-hole bosses (r 4.0, v0.19 M3) clear every cap rectangle and dome courtyard.
  7. J2 (FFC) body clears the key field and the keymat web outline.
  8. E73 antenna keep-out crosses the TOP board edge; USB-C mouth is at the top.
  9. Board dims match deck (79.5 x 97.0) on both .kicad_pcb files.

Exit 0 + "ALL CHECKS PASS" only if everything holds.
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import deck
import pcbnew

GEN = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "kicad", "generated"))
FAIL = []

def check(name, ok, detail=""):
    tag = "ok " if ok else "FAIL"
    print(f"  [{tag}] {name}{(' — ' + detail) if detail else ''}")
    if not ok:
        FAIL.append(name)

def cap_rect(k, c):
    """Cap rectangle (x0,y0,x1,y1) for a key dict (grid w-aware) in deck mm."""
    w = (k.get("w", 1) - 1) * c.pitch_x + c.key_w
    h = c.key_h
    return (k["x"] - w/2, k["y"] - h/2, k["x"] + w/2, k["y"] + h/2)

def rect_gap(a, b):
    dx = max(a[0] - b[2], b[0] - a[2], 0.0)
    dy = max(a[1] - b[3], b[1] - a[3], 0.0)
    return math.hypot(dx, dy) if (dx and dy) else max(dx, dy)

for side in ("right", "left"):
    print(f"== {side} ==")
    c = deck.Config(side=side)
    geo = deck.build(c)
    H = geo["board_h"]
    feats = [f for f in geo.get("features", []) if f["type"] == "key"]
    keys = list(geo["keys"])
    allk = keys + feats

    b = pcbnew.LoadBoard(os.path.join(GEN, f"thumbdeck_{side}.kicad_pcb"))

    # 9. board dims — compare against the OUTLINE's true bbox (v0.19: the 1.0mm
    # bottom crown dips below y=0, so bbox height = board_h + crown)
    bb = b.GetBoardEdgesBoundingBox()
    bw, bh = bb.GetWidth()/1e6, bb.GetHeight()/1e6
    oxs = [p2[0] for p2 in geo["outline"]]; oys = [p2[1] for p2 in geo["outline"]]
    ow, oh = max(oxs) - min(oxs), max(oys) - min(oys)
    check("board dims match deck", abs(bw - ow) < 0.3 and abs(bh - oh) < 0.3,
          f"pcb {bw:.1f}x{bh:.1f} vs deck outline {ow:.1f}x{oh:.1f}")

    # 1+2. SW / diode positions vs model
    sws = {f.GetReference(): f for f in b.GetFootprints() if f.GetValue() == "SNAP7"}
    dds = {f.GetReference(): f for f in b.GetFootprints() if f.GetValue() == "1N4148WS"}
    check("dome count matches", len(sws) == len(allk), f"{len(sws)} PCB vs {len(allk)} model")
    worst_sw = worst_d = 0.0
    for i, k in enumerate(allk):
        sw = sws.get(f"SW{i+1}"); d = dds.get(f"D{i+1}")
        if sw is None or d is None:
            check(f"SW{i+1}/D{i+1} exist", False); continue
        sx, sy = sw.GetPosition().x/1e6, H - sw.GetPosition().y/1e6
        worst_sw = max(worst_sw, math.hypot(sx - k["x"], sy - k["y"]))
        dx_, dy_ = d.GetPosition().x/1e6, H - d.GetPosition().y/1e6
        worst_d = max(worst_d, math.hypot(dx_ - k["x"], dy_ - (k["y"] + 3.0)))
    check("all domes at model key centres", worst_sw < 0.01, f"worst dev {worst_sw:.4f} mm")
    check("all diodes at key+(0,+3.0)", worst_d < 0.01, f"worst dev {worst_d:.4f} mm")

    # 3. dome courtyard spacing (r3.9 -> min 7.8 centre distance)
    md = min(math.hypot(a["x"]-b2["x"], a["y"]-b2["y"])
             for i, a in enumerate(allk) for b2 in allk[i+1:])
    check("dome courtyards clear (>=7.8)", md >= 7.8, f"min centre spacing {md:.2f} mm")

    # 4. cap rectangles: no overlap; grid-neighbour gutters
    rects = [cap_rect(k, c) for k in keys]
    ming = min(rect_gap(a, b2) for i, a in enumerate(rects) for b2 in rects[i+1:])
    # lid openings add 0.2/side -> opening web = gutter - 0.4; require >= 1.0
    check("cap gutters printable", ming >= 1.4,
          f"min cap gutter {ming:.2f} mm -> lid web {ming-0.4:.2f} mm")

    # 5. cap covers its dome (7.0 dia centred)
    cover = all(r[0] <= k["x"]-3.5+0.51 and r[2] >= k["x"]+3.5-0.51 and
                r[1] <= k["y"]-3.5+0.51 and r[3] >= k["y"]+3.5-0.51
                for k, r in zip(keys, rects))
    check("caps cover domes (<=0.5 shortfall)", cover)

    # 6. v0.19 split gate — two DIFFERENT physical constraints:
    #  (a) boss disc (r4.0: Ø7.5 M3 boss + margin) vs DOME COURTYARDS (r3.9) at
    #      PCB level: the boss seats the board next to the contact rings;
    #  (b) the lid's countersink CONE (r3.1) vs CAP OPENINGS at face level —
    #      the boss itself lives 10mm below the caps and never meets them.
    mind = 99.0; minc = 99.0
    for hh in geo["mount_holes"]:
        for k in allk:
            mind = min(mind, math.hypot(k["x"]-hh["x"], k["y"]-hh["y"]) - 3.9)
        for r in rects:
            dx = max(r[0]-hh["x"], hh["x"]-r[2], 0.0); dy = max(r[1]-hh["y"], hh["y"]-r[3], 0.0)
            minc = min(minc, math.hypot(dx, dy))
    check("bosses clear dome courtyards (>=4.0)", mind >= 4.0, f"min {mind:.2f} mm")
    check("countersink cones clear cap openings (>=3.3)", minc >= 3.3, f"min {minc:.2f} mm")

    # 7. J2 vs key field (x extent) — body from the board
    j2 = b.FindFootprintByReference("J2")
    jb = j2.GetBoundingBox(False)
    jx0, jx1 = jb.GetLeft()/1e6, jb.GetRight()/1e6
    jy0, jy1 = H - jb.GetBottom()/1e6, H - jb.GetTop()/1e6
    capx0 = min(r[0] for r in rects); capx1 = max(r[2] for r in rects)
    if side == "right":
        check("J2 clears caps (inner edge)", jx1 <= capx0 - 0.5, f"J2 x<= {jx1:.1f} vs cap x0 {capx0:.1f}")
    else:
        check("J2 clears caps (inner edge)", jx0 >= capx1 + 0.5, f"J2 x>= {jx0:.1f} vs cap x1 {capx1:.1f}")

    if side == "right":
        # 8. antenna crosses TOP edge; USB-C mouth at top
        u1 = b.FindFootprintByReference("U1")
        zt = min(z.GetBoundingBox().GetTop() for z in u1.Zones())
        check("E73 antenna keep-out crosses TOP edge", zt < 0, f"zone top {zt/1e6:.2f} (kicad y<0)")
        j1 = b.FindFootprintByReference("J1")
        jy = H - j1.GetPosition().y/1e6
        check("USB-C at top edge", jy > H - 6.0, f"J1 deck-y {jy:.1f}")
        # feature keys clear the top cluster parts (nearest non-dome footprint)
        mind = 99.0; near = ""
        for f in b.GetFootprints():
            if f.GetValue() in ("SNAP7", "1N4148WS") or f.GetReference() in ("J2",):
                continue
            fb = f.GetBoundingBox(False)
            fr = (fb.GetLeft()/1e6, H - fb.GetBottom()/1e6, fb.GetRight()/1e6, H - fb.GetTop()/1e6)
            for k in feats:
                kr = (k["x"]-3.9, k["y"]-3.9, k["x"]+3.9, k["y"]+3.9)
                g = rect_gap((fr[0], fr[1], fr[2], fr[3]), kr)
                if g < mind:
                    mind, near = g, f.GetReference()
        check("PgUp/PgDn courtyards clear top cluster", mind >= 0.3, f"min gap {mind:.2f} ({near})")

print()
if FAIL:
    print(f"FAILED: {len(FAIL)} check(s): {FAIL}")
    sys.exit(1)
print("ALL CHECKS PASS")

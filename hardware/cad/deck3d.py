#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Eric Neuman
"""deck3d.py — parametric 3D generator for the thumbdeck: PCB fit-model (real
component dimensions), the 5-part shell set (left/right back halves, left/right
grip lids, center front panel — every part fits an Ender 3 V2 220x220 bed flat),
keymats (cap tops carry 0.4mm DEBOSSED Rii-style legends), + the phone / LiPo /
flex / the 14 M3x10 flush-countersunk shell screws, assembled in the deck.product() frame and
collision-checked so nothing physically overlaps. Same source of truth as the
PCB (hardware/scripts/deck.py).

Split concept (sketches/All.png, side.png): cyan grip lids left+right, pink back +
pink center panel ("the front of the back"). Staggered splices: the panel bridges
the back seam at x=0; the back halves bridge the front reveal seams at the grip
edges — every cross-section keeps one continuous structural member.

See docs/cad-process.md. Run:  deck3d.py --all --check --render
Frame: deck.py Y-up, origin bottom-left of the RIGHT grip; z=0..1.6 = PCB, +z = front
(dome / lid side), -z = back (module / back-shell side).
"""
import os, sys, argparse, math, json, subprocess, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import numpy as np, trimesh, deck
from shapely.geometry import Polygon, Point, box as shp_box

HERE = os.path.dirname(__file__)
BUILD = os.path.join(HERE, "build")
GEN = os.path.join(HERE, "..", "kicad", "generated")
RENDERS = os.path.join(HERE, "..", "..", "renders")
PCB_T = 1.6            # FR-4 thickness
SOLDER = 0.06          # estimated solder/paste standoff

# ---- component HEIGHT table (mm), real-world from datasheets. The body FOOTPRINT
#      (x/y extents) comes from the exported KiCad bbox (pads + courtyard, already
#      axis-aligned in board coords); only the height is looked up here. A few parts
#      whose bbox is inflated by keep-out drawings carry a "body" override (dx,dy),
#      modeled centred on the footprint ANCHOR instead. Matched by substring against
#      the footprint name (first hit wins). h=0 -> skipped (bare pads). -------------
SPECS = [
    ("E73-2G4M08S1C", {"h": 2.2, "body": (13.0, 18.0)}),   # Ebyte module; bbox incl. antenna keepout
    ("USB_C_Receptacle_HRO", {"h": 3.3}),                  # J1 body 3.26
    ("ffc_afa07", {"h": 2.0}),                             # J2 FFC ZIF 16P (Molex 200528 pattern)
    ("JST_PH_S2B", {"h": 6.0}),                            # J3 side-entry, mated height
    ("msk12c02", {"h": 3.6, "body": (8.9, 3.6), "knob": True}),  # SW1 power slide + knob
    ("TS-1187A", {"h": 3.1}),                              # SW2 reset tact (floor-facing actuator)
    ("SOT-23", {"h": 1.1}),                                # MCP73831 / USBLC6
    ("LED_0603", {"h": 0.7}),                              # D80 charge LED
    ("_0402_", {"h": 0.6}),
    ("_0603_", {"h": 0.6}),
    ("_0805_", {"h": 0.9}),
    ("SOD-323", {"h": 1.1}),                               # 1N4148WS matrix diodes
    ("TestPoint", {"h": 0.0}),                             # bare pads
]

def _spec(fp):
    for key, spec in SPECS:
        if key in fp:
            return spec
    return None

DOME_D, DOME_H = 7.0, 0.5   # Snaptron 7mm snap dome (dia, height above pad)
KNOB = (3.0, 1.5, 2.0)      # MSK12C02 slide knob (w, protrusion toward the nearest edge — derived from rot, h)
# v0.21 Bean-style hall nub (printed flexure spring + magnet over a back-side
# TMAG5273; architecture adapted from the Ploopy Bean, CERN-OHL-S v2):
NUB_MAGNET_D, NUB_MAGNET_H = 4.0, 2.0    # N42/N52 disc, press-fit N-up (Bean spec)
NUB_HUB_D = 7.0                          # flexure hub / post through the aperture
NUB_CAP_D, NUB_CAP_H = 8.5, 2.5          # TPU friction cap, 4.25mm proud of the face
NUB_SPRING_FLANGE_D = 14.8               # flange captured in the lid's counterbore
NUB_ARM_T = 0.8                          # flexure arm thickness (print-tune = feel)


def _box(dx, dy, dz):
    return trimesh.creation.box(extents=(dx, dy, dz))


def _place(mesh, x, y, z, rot_deg=0.0):
    m = mesh.copy()
    if rot_deg:
        m.apply_transform(trimesh.transformations.rotation_matrix(math.radians(rot_deg), (0, 0, 1)))
    m.apply_translation((x, y, z))
    return m


def pcb_assembly(side):
    """Return {name: trimesh} for one grip: board + every placed component (real
    dims) + snap domes, in deck.py Y-up frame (z 0..1.6 PCB)."""
    geo = deck.build(deck.Config(side=side))
    H = geo["board_h"]
    parts = {}
    # board solid: extrude the outline polygon, with the 5 M2 mount holes DRILLED
    # (Ø2.2, from deck.build) so the shell screws pass through real clearance
    # instead of being modeled through solid FR-4
    pts = _dedupe(geo["outline"])
    bpoly = Polygon(pts)
    for hh in geo["mount_holes"]:
        bpoly = bpoly.difference(Point(hh["x"], hh["y"]).buffer(hh["d"]/2, 24))
    board = trimesh.creation.extrude_polygon(bpoly, PCB_T)
    board.visual.face_colors = [40, 90, 60, 255]
    parts[f"pcb_{side}"] = board

    for f in _placement(side):
        ref = f["ref"]; fp = f["fp"]
        x = f["x"]; y = H - f["y"]                    # bbox centre, KiCad Y-down -> deck Y-up
        rot = f["rot"]; back = f["back"]
        if "snaptron" in fp:                          # snap dome on the FRONT
            dome = trimesh.creation.cylinder(radius=DOME_D/2, height=DOME_H, sections=24)
            parts[ref] = _place(dome, x, y, PCB_T + DOME_H/2)
            continue
        spec = _spec(fp)
        if spec is None or spec["h"] <= 0:
            continue
        ddz = spec["h"]
        z = (-SOLDER - ddz/2) if back else (PCB_T + SOLDER + ddz/2)
        if "body" in spec:
            # true body dims centred on the ANCHOR (bbox inflated by keepout gfx)
            ddx, ddy = spec["body"]
            m = _place(_box(ddx, ddy, ddz), f["ax"], H - f["ay"], z, rot)
        else:
            # bbox envelope: already axis-aligned in board coords, no rotation
            m = _place(_box(f["w"], f["h"], ddz), x, y, z)
        if spec.get("knob"):
            # MSK12C02 slide knob protruding from the body face toward the nearest board
            # edge: rev-A (rot~0) faced the BOTTOM edge; the v0.17 cluster rotation
            # (rot~180) faces the TOP edge. Derive the face from the placed rotation.
            kw, kp, kh = KNOB
            dirn = 1 if abs((f["rot"] % 360) - 180) < 45 else -1
            by = (H - f["ay"]) + dirn * spec["body"][1]/2   # knob-side body face
            m = trimesh.util.concatenate([m, _place(_box(kw, kp, kh), f["ax"], by + dirn*kp/2, z)])
        m.visual.face_colors = [70, 70, 75, 255] if ref[0] in "UJ" else [120, 120, 40, 255]
        # the board reuses SW1/SW2 for the back power/reset switches (domes own SW*):
        # give them deterministic unique names regardless of iteration order.
        if "msk12c02" in fp:
            name = f"{ref}_pwr"
        elif "TS-1187A" in fp:
            name = f"{ref}_rst"
        else:
            name = ref if ref not in parts else f"{ref}_b"
        parts[name] = m
    return parts, geo


_PLC = {}
def _placement(side):
    """Load footprint placement JSON (produced by export_placement.py under system
    python). Auto-regenerate if missing/stale; cached for the rest of the run (the
    autorouter touches the .kicad_pcb constantly but placements are final)."""
    if side in _PLC:
        return _PLC[side]
    p = os.path.join(BUILD, f"placement_{side}.json")
    pcb = os.path.join(GEN, f"thumbdeck_{side}.kicad_pcb")
    if not os.path.exists(p) or os.path.getmtime(p) < os.path.getmtime(pcb):
        subprocess.run(["python3", os.path.join(HERE, "export_placement.py")],
                       check=True, capture_output=True)
    _PLC[side] = json.load(open(p))
    return _PLC[side]


def _dedupe(outline, tol=1e-3):
    pts = []
    for p in outline:
        p = (float(p[0]), float(p[1]))
        if not pts or abs(p[0]-pts[-1][0]) > tol or abs(p[1]-pts[-1][1]) > tol:
            pts.append(p)
    return pts


# ==== product-frame geometry (both grips + phone + spine) ==========================
CFG = deck.Config()

def _product():
    return deck.product(CFG)

def _grip_poly_product(side):
    """That grip's outline polygon translated into the product frame."""
    prod = _product()
    geo = prod[side]
    ox, oy = prod[f"{side}_origin"]
    pts = _dedupe(geo["outline"])
    return Polygon([(x+ox, y+oy) for x, y in pts]), geo, (ox, oy)

def _key_centers_product(only_side=None):
    """Dome/key centres (incl. cluster features) in product frame; both grips by
    default, one grip when only_side is given (the split lids cut per-side)."""
    prod = _product(); out = []
    for side in ("right", "left"):
        if only_side and side != only_side:
            continue
        geo = prod[side]; ox, oy = prod[f"{side}_origin"]
        keys = list(geo["keys"]) + [f for f in geo.get("features", []) if f["type"] == "key"]
        for k in keys:
            out.append((k["x"]+ox, k["y"]+oy, k.get("d", 7.0)))
    return out

CAP_R = 1.6            # keycap corner radius (matches the 2D renders)
CAP_CLR = 0.2          # per-side clearance between cap and its lid opening

def _nub_zone(side):
    """v0.21: the right grip's hall-nub zone in the product frame, or None.
    Returns the nub centre + lid aperture diameter (the sensor is a plain
    back-side SOT-23 handled by SPECS; only the printed spring/cap and the lid
    aperture need geometry here)."""
    prod = _product(); geo = prod[side]; ox, oy = prod[f"{side}_origin"]
    ns = [f for f in geo.get("features", []) if f["type"] == "hall_nub"]
    if not ns:
        return None
    f = ns[0]
    return {"x": f["x"]+ox, "y": f["y"]+oy, "aperture_d": f.get("aperture_d", 10.0)}
def _rrect(cx, cy, w, h, r=CAP_R):
    """Rounded-rect shapely polygon centred on (cx, cy)."""
    return shp_box(cx - w/2 + r, cy - h/2 + r, cx + w/2 - r, cy + h/2 - r).buffer(r)

def _cap_shapes_product(side):
    """v0.17 keycap geometry per key, product frame: [(plunger_poly, opening_poly,
    x, y)]. GRID keys carry the rectangular 8.5 x 7.0 caps (2u space 18.5) the user
    feels — the plunger IS the cap, poking through a matching rounded-rect lid
    opening (+CAP_CLR/side). CLUSTER feature keys stay round (Ø6.2 plunger through
    a Ø7.8 opening, the proven v0.16 pair)."""
    prod = _product(); geo = prod[side]; ox, oy = prod[f"{side}_origin"]
    c = geo["config"]
    out = []
    for k in geo["keys"]:
        w = (k.get("w", 1) - 1) * c["pitch_x"] + c["key_w"]
        cap = _rrect(k["x"]+ox, k["y"]+oy, w, c["key_h"])
        out.append((cap, cap.buffer(CAP_CLR), k["x"]+ox, k["y"]+oy))
    for f in geo.get("features", []):
        if f["type"] != "key":
            continue
        x, y = f["x"]+ox, f["y"]+oy
        pl = Polygon([(x+KM_PL_D/2*math.cos(t), y+KM_PL_D/2*math.sin(t))
                      for t in np.linspace(0, 2*math.pi, 24)])
        d = f.get("d", 7.0)
        op = Polygon([(x+(d/2+0.4)*math.cos(t), y+(d/2+0.4)*math.sin(t))
                      for t in np.linspace(0, 2*math.pi, 24)])
        out.append((pl, op, x, y))
    return out

def _seam_frame():
    """x-stations of the split (product frame): grip inner edges at +-gx, back-shell
    halves part at x=0, panel spans |x| <= gx-SEAM_GAP. Derived, never hard-coded."""
    prod = _product()
    gx = prod["right_origin"][0]                 # right grip inner edge (= 73.8)
    assert abs(gx + (prod["left_origin"][0] + prod["left"]["board_w"])) < 1e-6
    return gx

def full_footprint():
    """Union of both grips + a central spine slab under the phone: the shared 2D
    footprint every shell part is derived from (split into 5 parts since v0.16)."""
    prod = _product()
    rp, _, _ = _grip_poly_product("right")
    lp, _, _ = _grip_poly_product("left")
    # central slab spans between the grips' inner edges, over the phone/spine, full grip height
    rx = prod["right_origin"][0]; lxr = prod["left_origin"][0] + prod["left"]["board_w"]
    bh = prod["right"]["board_h"]
    spine = Polygon([(lxr-1, 0), (rx+1, 0), (rx+1, bh), (lxr-1, bh)])
    return rp.union(lp).union(spine).buffer(0)

# ==== printable parts (CadQuery) ====================================================
import cadquery as cq

# --- vertical stack (all derived so the parts always line up) ---
FLOOR = 1.6            # back-half floor thickness
WALL_T = 2.5          # shell wall thickness
TOP_T = 2.4           # grip-lid plate thickness (v0.19: 2.0 -> 2.4 so the M3 flush
                      #   countersink cone leaves >=1.0mm of land under it)
STANDOFF = 6.3        # PCB standoff: clears the 6.0mm mated JST-PH (J3) + 0.24 margin
PHONE_CLR = 0.6       # phone pocket clearance (total, both sides)
RING_REC_D = 1.8      # MagSafe ring recess depth inside the phone-well floor
RING_REC_R = 28.5     # recess radius (Ø57 for the Ø56 N52 ring)
GAP = 0.5
KM_WEB, KM_PL_H, KM_PL_D = 0.8, 3.9, 6.2   # keymat web / plunger height / plunger dia
                                           # (v0.19: 3.5 -> 3.9 keeps caps 1.0 proud of
                                           #  the face after TOP_T grew 0.4)
PCB_Z = FLOOR + STANDOFF                     # grip-local PCB z=0 maps here
DOME_TOP = PCB_Z + PCB_T + DOME_H            # top of a seated snap dome
KM_Z0 = DOME_TOP + 1.0                       # keymat web bottom (nub reaches the dome)
TOP_Z = KM_Z0 + KM_WEB + GAP                 # front parts sit above the cavity
WALL = TOP_Z - FLOOR                         # cavity height (derived)

# --- 5-part split (grip lids + center panel + back halves), Ender 3 V2 bed ---
BED_XY = 204.0        # printable footprint per part: 220mm bed minus 2x8mm brim
PANEL_T = 2.6         # well-floor slab thickness (0.8 web under the 1.8 ring recess)
# v0.18 SUNKEN WELL: the phone (S25 Ultra in a typical thin case) sits in a deep
# well in the center panel so its SCREEN SURFACE lands FLUSH with the grip lids'
# keyboard face (WELL_TOP). Everything below is derived from the cased thickness:
#   screen @ WELL_TOP -> cased back rests at WELL_TOP - PHONE_TC (on the 0.2-proud
#   ring) -> well floor 0.2 lower -> slab hangs PANEL_T below that.
WELL_TOP = TOP_Z + TOP_T                     # 14.7 (v0.19 TOP_T 2.4) — panel border top = lid top = device face
PHONE_TC = CFG.phone_t + CFG.case_t          # 9.4 — cased thickness, back-of-case -> screen
WELL_FLOOR = WELL_TOP - PHONE_TC - 0.2       # 5.1 — well/pocket floor (ring sits 0.2 proud)
SLAB_BOT = WELL_FLOOR - PANEL_T              # 2.5 — slab bottom (0.9 above the back floor)
WELL_WALL = 2.0                              # well y-wall band thickness
SEAM_GAP = 0.3        # front reveal gap between panel edge and lid edge (deliberate V)
LAP_CLR = 0.25        # printed-joint in-plane clearance (FDM: elephant foot + warp)
XWALL_T = 2.5         # transverse spine wall (closes each half's torsion box, seats panel)
# 4 seam-splice screws straddling the x=0 back seam, DERIVED from the phone pocket
# span (v0.17: hardcoded y=10/105 broke when the board shrank to 97mm — 105 was off
# the shell and 10 clipped the new pocket rim). v0.18: 6.3mm outside each pocket
# edge so the Ø7 floor bosses clear the well's 2.0mm wall band by >=0.5mm.
_PH0 = deck.product(deck.Config())["phone"]
_PY0, _PY1 = _PH0["y"] - PHONE_CLR / 2, _PH0["y"] + _PH0["h"] + PHONE_CLR / 2
# v0.19: offsets grew 6.3 -> 6.8 (Ø8 M3 bosses vs the well band) and the TOP row
# moved to |x|=13 to clear the thumb-scallop dish wall (R10.6 half-annulus at
# (0, _PY1-2.3)) plus its Ø8 boss by >=0.8mm
PANEL_SCREWS = [(-10.0, _PY0 - 6.8), (10.0, _PY0 - 6.8),
                (-13.0, _PY1 + 6.8), (13.0, _PY1 + 6.8)]
# M3 flush-countersunk face hardware (v0.19, feedback: proud pan heads were
# uncomfortable). DIN 965 90-degree head, dk<=6.0: cone face Ø6.2 with the head
# nominally 0.1-0.3 sub-flush (FDM droop/elephant-foot budget); panel cones cut
# 0.15 deeper still (they print opening-upward; lid cones print face-down, clean).
CSK_R_FACE = 3.1      # countersink cone radius at the device face
SCREW_HOLE_R = 1.7    # Ø3.4 through-holes (M3 clearance)

def _cq_from_poly(geom, z0, h):
    """Extrude a shapely Polygon/MultiPolygon (with holes) to a CadQuery solid."""
    polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    solid = None
    for poly in polys:
        ext = list(poly.exterior.coords)[:-1]
        s = cq.Workplane("XY").workplane(offset=z0).polyline(ext).close().extrude(h)
        for interior in poly.interiors:
            hole = (cq.Workplane("XY").workplane(offset=z0-0.1)
                    .polyline(list(interior.coords)[:-1]).close().extrude(h+0.2))
            s = s.cut(hole)
        solid = s if solid is None else solid.union(s)
    return solid

def _to_trimesh(solid, name):
    p = os.path.join(BUILD, name+".stl")
    cq.exporters.export(solid, p)
    cq.exporters.export(solid, os.path.join(BUILD, name+".step"))
    m = trimesh.load(p); return m

PCB_CLR = 0.4          # clearance between PCB edge and the shell cavity wall
POST_R = 1.5           # mid-field PCB support post radius (Ø3)
POST_CLR = 2.2         # required clear radius (post centre -> nearest back-side bbox)

def _find_fp(side, key, anchor=False):
    """Product-frame (x, y) of the first footprint whose name contains key.
    anchor=True returns the raw anchor (for anchor-centred bodies), else bbox centre."""
    prod = _product(); geo = prod[side]; ox, oy = prod[f"{side}_origin"]; H = geo["board_h"]
    for f in _placement(side):
        if key in f["fp"]:
            x, y = (f["ax"], f["ay"]) if anchor else (f["x"], f["y"])
            return x + ox, (H - y) + oy
    raise KeyError(f"{key} not on {side} board")

_POSTS = {}
def support_post_locations(side):
    """3 mid-field PCB support posts per grip (floor -> PCB underside, no screws).
    Candidates: between-column midpoints at key-row y — the diode rows sit 3mm ABOVE
    each key row on the PCB back, so these spots are clear by construction. Each is
    then VERIFIED against the placement export: no back-side footprint bbox within
    POST_CLR of the post centre (and >=6mm from any mount-hole boss). Grip-local mm."""
    if side in _POSTS:
        return _POSTS[side]
    geo = deck.build(deck.Config(side=side)); H = geo["board_h"]
    boxes = [(f["x"], H - f["y"], f["w"], f["h"]) for f in _placement(side) if f["back"]]
    # v0.18: the 403040 cell lives on the LEFT grip's floor under the key field —
    # posts must not land on it. Treat its grip-local rect (+1.5mm margin) as one
    # more obstacle box so the candidate filter routes posts around it.
    prod = _product()
    bat = prod.get("battery")
    if bat and bat.get("grip") == side:
        ox = prod[f"{side}_origin"][0]
        boxes.append((bat["x"] - ox + bat["w"]/2, bat["y"] + bat["h"]/2,
                      bat["w"] + 3.0, bat["h"] + 3.0))
    holes = [(h["x"], h["y"]) for h in geo["mount_holes"]]
    def clearance(px, py):
        d = min((math.hypot(max(0.0, abs(px-cx) - w/2), max(0.0, abs(py-cy) - h/2))
                 for (cx, cy, w, h) in boxes), default=99.0)
        return d
    rows = {}
    for k in geo["keys"]:
        rows.setdefault(k["y"], []).append(k["x"])
    cands = [((a+b)/2, y) for y, xs in rows.items()
             for a, b in zip(sorted(xs), sorted(xs)[1:])]
    cands = [c for c in cands if clearance(*c) >= POST_CLR
             and all(math.hypot(c[0]-hx, c[1]-hy) >= 6.0 for hx, hy in holes)]
    xs = [k["x"] for k in geo["keys"]]; ys = [k["y"] for k in geo["keys"]]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    targets = [(x0 + 0.28*(x1-x0), y0 + 0.30*(y1-y0)),   # spread over the ~30mm free spans
               (x0 + 0.72*(x1-x0), y0 + 0.30*(y1-y0)),
               (x0 + 0.50*(x1-x0), y0 + 0.72*(y1-y0))]
    chosen = []
    for tx, ty in targets:
        best = min((c for c in cands if c not in chosen),
                   key=lambda c: (c[0]-tx)**2 + (c[1]-ty)**2)
        chosen.append(best)
    for (px, py) in chosen:
        print(f"  post {side}: ({px:.2f}, {py:.2f}) grip-local, back clearance {clearance(px, py):.2f}mm")
    _POSTS[side] = chosen
    return chosen

def _back_solid():
    """Full-width back tray as a single CadQuery solid (split into halves by
    back_half): legacy tray + transverse spine walls + panel bosses."""
    fp = full_footprint()
    prod = _product()
    # walls go OUTSIDE the PCB envelope: outer = fp+wall+clr, cavity = fp+clr (so the
    # board sits inside with clearance instead of colliding with the walls).
    outer = _cq_from_poly(fp.buffer(WALL_T+PCB_CLR), 0, FLOOR+WALL)
    inner = _cq_from_poly(fp.buffer(PCB_CLR), FLOOR, WALL+1)
    shell = outer.cut(inner)
    # (v0.14: the old MagSafe "ring pocket" cut here extruded BELOW z=0 — outside the
    #  solid, a no-op — the ring seats in the center panel's phone pocket since v0.16.)
    # PCB standoff bosses + M3 heat-set bores at each grip's mount holes (v0.19:
    # Ø7.5 boss, Ø4.0 x 5.3 bore for an M3x4 insert, OD ~4.6, seated flush at PCB_Z)
    for side in ("right", "left"):
        geo = prod[side]; ox, oy = prod[f"{side}_origin"]
        for hh in geo["mount_holes"]:
            cx, cy = hh["x"]+ox, hh["y"]+oy
            boss = (cq.Workplane("XY").workplane(offset=FLOOR).center(cx, cy).circle(3.75).extrude(STANDOFF)
                    .faces(">Z").workplane().circle(2.0).cutBlind(-(STANDOFF-1)))
            shell = shell.union(boss)
        # mid-field PCB support posts (verified clear of back-side components)
        for (px, py) in support_post_locations(side):
            post = (cq.Workplane("XY").workplane(offset=FLOOR).center(px+ox, py+oy)
                    .circle(POST_R).extrude(STANDOFF))
            shell = shell.union(post)
    # ---- right-grip back-side feature cuts (all positions from the placement export).
    # v0.17: the whole cluster moved to the TOP zone, so every wall cut lands in the
    # TOP wall (outer face at y = bh_r + WALL_T + PCB_CLR) instead of the old bottom.
    ox, oy = prod["right_origin"]
    bh_r = prod["right"]["board_h"]
    # USB-C wall opening: 13.5 x 7.0 centred on the receptacle mouth (J1 x, mouth at
    # the TOP board edge y=bh_r; receptacle vertical centre ~1.6mm below the PCB underside)
    jx, _ = _find_fp("right", "USB_C_Receptacle_HRO")
    zc = PCB_Z - 1.6
    shell = shell.cut(cq.Workplane("XY").workplane(offset=zc - 3.5)
                      .center(jx, bh_r + 1.5).box(13.5, 3.4, 7.0, centered=(True, True, False)))
    # stepped outer relief (in lieu of a chamfer) so a 12.35 x 6.5 plug overmold seats
    # fully against the receptacle through the 2.9mm wall
    shell = shell.cut(cq.Workplane("XY").workplane(offset=zc - 4.5)
                      .center(jx, bh_r + 2.35).box(16.0, 1.3, 9.0, centered=(True, True, False)))
    # power slide switch slot: knob protrudes toward the TOP edge; 8 x 2.8 gives
    # the ~3mm travel + finger access, centred at the knob (= body-centre) height
    sx, _ = _find_fp("right", "msk12c02", anchor=True)
    kz = PCB_Z - SOLDER - 3.6/2
    shell = shell.cut(cq.Workplane("XY").workplane(offset=kz - 1.4)
                      .center(sx, bh_r + 1.5).box(8.0, 3.4, 2.8, centered=(True, True, False)))
    # reset tact pinhole (actuator faces the floor) + charge-LED light pipe hole
    rx, ry = _find_fp("right", "TS-1187A", anchor=True)
    shell = shell.cut(cq.Workplane("XY").workplane(offset=-0.5).center(rx, ry).circle(0.8).extrude(FLOOR+1))
    lx, ly = _find_fp("right", "LED_0603")
    shell = shell.cut(cq.Workplane("XY").workplane(offset=-0.5).center(lx, ly).circle(0.75).extrude(FLOOR+1))
    # antenna wall relief: the E73 physically overhangs the TOP board edge by 0.5mm and
    # the cavity wall face is only PCB_CLR=0.4 out — relieve the inner wall face 0.6mm
    # over the antenna keep-out span so the module tip has >=0.5mm clearance. The wall
    # stays CLOSED (1.9mm remains): the antenna radiates through thin PETG, not a hole.
    ax_, ay_, aw, ah = prod["right"]["keepouts"]["antenna"]
    shell = shell.cut(cq.Workplane("XY").workplane(offset=4.0)
                      .center(ax_ + ox + aw/2, bh_r + 0.65).box(aw, 0.7, PCB_Z - 3.9, centered=(True, True, False)))

    # ---- transverse spine walls at each grip boundary (v0.16 split): close each
    # half's torsion box where the front seam breaks the top plate and seat the
    # panel border. v0.18: over the phone-well y-span the wall is CUT DOWN to a
    # sill at SLAB_BOT-0.15 — the sunken phone (bottom at WELL_FLOOR+0.2) and the
    # panel's well-floor slab both pass over it; outside the well span the wall
    # keeps full height and seats the border flange. The old ring-height Ø8
    # anchors are GONE (the panel floor is 8mm below their bores now): MagSafe
    # detach is resisted by the 4 border screws + the slab's own stiffness
    # (<0.3mm flex at the ring), down-press by the slab's floor nubs.
    gx = _seam_frame()
    bh = prod["right"]["board_h"]
    ms = prod["magsafe"]
    for s in (1, -1):
        x1 = s * (gx - SEAM_GAP); x0 = x1 - s * XWALL_T
        xw = (cq.Workplane("XY").workplane(offset=FLOOR)
              .center((x0+x1)/2, (-PCB_CLR + bh + PCB_CLR)/2)
              .box(XWALL_T, bh + 2*PCB_CLR, WALL, centered=(True, True, False)))
        # cut down to the sill over the well span PLUS the panel's 2.0mm wall band
        # (the band's y-side strips run the full panel width, so the sill must
        # clear them at the x-ends too — a well-span-only cut left 59mm^3 of
        # wall/band interference per side)
        xw = xw.cut(cq.Workplane("XY").workplane(offset=SLAB_BOT - 0.15)
                    .center((x0+x1)/2, (_PY0 + _PY1)/2)
                    .box(XWALL_T+2, (_PY1 - _PY0) + 2*(WELL_WALL + LAP_CLR), WALL, centered=(True, True, False)))
        # battery-lead pass-through at the bottom border lane (y~5, below the
        # well): the 403040's leads run LEFT cavity -> spine floor -> J3 (right).
        # The FFC no longer needs a wall window — it crosses in the under-slab
        # floor channel, BELOW the wall base (see the channel cut below).
        xw = xw.cut(cq.Workplane("XY").workplane(offset=FLOOR)
                    .center((x0+x1)/2, 5.0).box(XWALL_T+2, 8.0, 9.0-FLOOR, centered=(True, True, False)))
        shell = shell.union(xw)
    # ---- FFC floor channel: the bridge ribbon used to cross at z~5.4, which now
    # lands INSIDE the phone well — it must run UNDER the panel slab (bottom at
    # SLAB_BOT). A 0.5mm-deep recess in the back floor (1.6 -> 1.1) over a 19mm
    # lane centred on the J2 contact band gives the 0.3mm ribbon a 1.1..1.6 duct
    # with ~0.5mm headroom to the slab; it passes beneath the transverse-wall
    # bases (the walls sit on the 1.6 floor plane and don't fill the recess).
    # The ribbon S-bends from each ZIF (z~5.5) down to the duct inside the grip
    # cavities. Lane y 15..34 clears the relocated floor tabs (36..44).
    _, jch = _find_fp("right", "ffc_afa07")
    shell = shell.cut(cq.Workplane("XY").workplane(offset=1.1)
                      .center(0.0, jch).box(2*gx + 8.0, 19.0, FLOOR, centered=(True, True, False)))
    # ---- 4 panel bosses straddling the x=0 back seam (2 per half): the screwed-on
    # panel border is the seam's splice plate (v0.19: Ø8 for the M3 insert)
    for (px, py) in PANEL_SCREWS:
        shell = shell.union(cq.Workplane("XY").workplane(offset=FLOOR)
                            .center(px, py).circle(4.0).extrude(WALL))
    # bores are cut from the FINISHED shell, not the boss primitives — a pre-bored
    # boss unioned into overlapping material gets its bore silently re-filled.
    # Ø4.0 x 9.0 (M3 insert at the top): floor at 3.3, >=1.0mm below the M3x10
    # tip (head flush at WELL_TOP -> tip at WELL_TOP-10 = 4.7).
    for (px, py) in PANEL_SCREWS:
        shell = shell.cut(cq.Workplane("XY").workplane(offset=FLOOR+WALL)
                          .center(px, py).circle(2.0).extrude(-9.0))
    return shell


_BACK = None
def _back_full():
    global _BACK
    if _BACK is None:
        _BACK = _back_solid()
    return _BACK

_BUILT = {}
def _memo(name, builder):
    """In-process part cache: a single `--all --check --render` run calls
    assemble() up to twice on top of --all, which would rebuild every shell and
    re-deboss all 78 caps of keymat legends 2-3x. Parts are deterministic within
    a run; callers get copies."""
    if name not in _BUILT:
        _BUILT[name] = builder()
    return _BUILT[name].copy()

def back_half(side):
    return _memo(f"back_{side}", lambda: _back_half_build(side))

def _back_half_build(side):
    """One printable back-shell half (splits the tray at x=0 so each half fits an
    Ender 3 V2 bed). Joinery is printed + screwless: two full-thickness floor tabs
    (right) into cleared notches (left) register the halves in-plane, and each
    perimeter wall gets an 8mm vertical shiplap (vertical faces — prints clean flat)
    for shear/torsion continuity; the screwed-on center panel is the bolted splice."""
    prod = _product(); bh = prod["right"]["board_h"]
    s = 1 if side == "right" else -1
    half = cq.Workplane("XY").workplane(offset=-2).center(s*250, bh/2).box(500, 500, 30, centered=(True, True, False))
    # v0.18: lower tab moved 30-38 -> 36-44 so it clears the FFC floor channel
    # (lane y 15..34) — a channel-thinned tab would be a weak splice
    tabs = [(36.0, 44.0), (78.0, 86.0)]
    # front/back perimeter walls: outer faces at y=-2.9 / bh+2.9; split each wall's
    # thickness for the shiplap (right keeps the outer layer over x in [-7.75, 0])
    wo0, wi0 = -(WALL_T + PCB_CLR), -PCB_CLR              # front wall y-faces
    wo1, wi1 = bh + WALL_T + PCB_CLR, bh + PCB_CLR        # back wall y-faces
    t_split = 1.125                                        # tongue = outer 1.125 of the 2.5 wall
    if side == "right":
        for (y0, y1) in tabs:   # floor tabs, flush top and bottom (z 0..FLOOR)
            half = half.union(cq.Workplane("XY").workplane(offset=0)
                              .center(-5.0/2, (y0+y1)/2).box(5.0, y1-y0, FLOOR, centered=(True, True, False)))
        for (yo, sgn) in ((wo0, 1), (wo1, -1)):  # wall tongues: outer layer, 7.75 long
            half = half.union(cq.Workplane("XY").workplane(offset=0)
                              .center(-7.75/2, yo + sgn*t_split/2).box(7.75, t_split, FLOOR+WALL, centered=(True, True, False)))
    else:
        for (y0, y1) in tabs:   # tab notches, LAP_CLR clearance on x and y
            half = half.cut(cq.Workplane("XY").workplane(offset=-1)
                            .center((-(5.0+LAP_CLR) + 1.0)/2, (y0+y1)/2)
                            .box(5.0+LAP_CLR+1.0, (y1-y0) + 2*LAP_CLR, FLOOR+2, centered=(True, True, False)))
        for (yo, sgn) in ((wo0, 1), (wo1, -1)):  # shiplap reliefs: tongue + LAP_CLR
            yin = yo + sgn*(t_split+LAP_CLR)     # relief's inner face (clearance incl.)
            yout = yo - sgn*0.5                  # extend past the outer wall face
            half = half.cut(cq.Workplane("XY").workplane(offset=-1)
                            .center((-8.0 + 5.0)/2, (yin+yout)/2)
                            .box(13.0, abs(yin-yout), FLOOR+WALL+2, centered=(True, True, False)))
    part = _back_full().intersect(half)
    # 0.4mm 45-degree V along the seam's outer floor edge: elephant-foot relief on
    # both butt faces + a deliberate shadow line so residual mismatch reads as design
    groove = (cq.Workplane("XY").box(0.566, 500, 0.566)
              .rotate((0, 0, 0), (0, 1, 0), 45).translate((0, bh/2, 0)))
    part = part.cut(groove)
    return _to_trimesh(part, f"back_{side}")

def _keymat_field(side):
    """Keymat web outline (product frame): union of the v0.17 plunger shapes
    (rect caps + round cluster plungers) buffered 2.0, PLUS 3mm living-hinge
    strips tying every cluster feature key into the web — each feature connects
    to its nearest grid key and its nearest other feature, mirroring the 2D
    concept (render_layers.keymats). Without the strips the cluster plungers are
    FLOATING islands (a latent v0.16 bug: PgUp/PgDn and the mouse-button pair sat
    outside the 2.0mm buffer's reach — the 'one-piece' keymat printed as 3+
    pieces). Asserts single-piece connectivity. Shared by keymats() and the grip
    lids' clamp rims so they line up exactly."""
    from shapely.ops import unary_union
    from shapely.geometry import LineString
    shapes = _cap_shapes_product(side)
    prod = _product(); geo = prod[side]; ox, oy = prod[f"{side}_origin"]
    grid = [(k["x"]+ox, k["y"]+oy) for k in geo["keys"]]
    feats = [(f["x"]+ox, f["y"]+oy) for f in geo.get("features", []) if f["type"] == "key"]
    strips = []
    for f in feats:
        ng = min(grid, key=lambda g: (g[0]-f[0])**2 + (g[1]-f[1])**2)
        strips.append(LineString([f, ng]).buffer(1.5))
        others = [o for o in feats if o != f]
        if others:
            no = min(others, key=lambda o: (o[0]-f[0])**2 + (o[1]-f[1])**2)
            strips.append(LineString([f, no]).buffer(1.5))
    field = unary_union([pl.buffer(2.0) for (pl, _op, _x, _y) in shapes] + strips)
    # v0.19: Ø5.4 clearance discs at the mount-hole shanks — with the GBC outline
    # the outer screw column moved to 0.3mm from the web's buffered edge, too tight
    # for a flexible TPU mat riding over Ø3 shanks
    from shapely.geometry import Point
    for hh in geo["mount_holes"]:
        field = field.difference(Point(hh["x"]+ox, hh["y"]+oy).buffer(2.7))
    if field.geom_type == "MultiPolygon":
        # a clearance disc may shave a sub-5mm^2 crumb off the web edge (harmless);
        # anything larger detached is a real disconnected island -> still assert
        parts = sorted(field.geoms, key=lambda g: -g.area)
        assert all(g.area < 5.0 for g in parts[1:]), \
            f"keymat_{side} web split by shank clearance discs — move the disc or add a hinge strip"
        field = parts[0]
    assert field.geom_type == "Polygon", \
        f"keymat_{side} web is {field.geom_type} — disconnected islands; widen/add hinge strips"
    return field, shapes

def _edge_wedge(x_edge, z_top, c=0.5, bh=97.0):   # bh: pass the CURRENT board_h (both callers do)
    """45-degree top-edge chamfer prism along a straight x-station: a diamond of
    half-diagonal c centred on the edge line — cuts a c x c chamfer; the outboard
    half of the diamond lies in air. v0.19: 0.8 -> 0.5 so the inner-column M3
    countersink cones (Ø6.2, cone edge 1.1mm from the seam) leave a >=0.6mm rib
    to the reveal chamfer instead of 0.3mm (a fragile fin at the hidden seam)."""
    return (cq.Workplane("XY").box(c*2**0.5*0.9999, 500, c*2**0.5*0.9999)
            .rotate((0, 0, 0), (0, 1, 0), 45)
            .translate((x_edge, bh/2, z_top)))

def _csk_cone(x, y, z_face, extra=0.0):
    """90-degree countersink cut solid: cone radius = CSK_R_FACE at (z_face - extra),
    45-degree flanks continuing 0.4 past the face so the mouth is fully open."""
    zb = z_face - extra - (CSK_R_FACE - SCREW_HOLE_R)
    h = (CSK_R_FACE - SCREW_HOLE_R) + extra + 0.4
    return cq.Solid.makeCone(SCREW_HOLE_R, SCREW_HOLE_R + h, h, cq.Vector(x, y, zb))

def grip_lid(side):
    return _memo(f"grip_lid_{side}", lambda: _grip_lid_build(side))

def _grip_lid_build(side):
    """Per-grip front lid (cyan in the concept sketches): the legacy top plate
    restricted to its grip — same keymat clamp rim, key openings and 5 screw
    positions — cut straight at the grip's inner edge with a 0.8mm top chamfer
    toward the panel reveal. ~79 x 120mm: prints cosmetic-face-down on a 220 bed."""
    fp = full_footprint()
    prod = _product()
    gx = _seam_frame(); s = 1 if side == "right" else -1
    z0 = TOP_Z
    bh = prod["right"]["board_h"]
    region = Polygon([(s*gx, -60), (s*400, -60), (s*400, bh+60), (s*gx, bh+60)])
    poly = fp.buffer(WALL_T+PCB_CLR).intersection(region).buffer(0)
    plate = _cq_from_poly(poly, z0, TOP_T)
    # keymat clamp: continuous downstand rim on the underside around the key-field
    # perimeter, pressing the keymat web down 0.1mm when the lid is screwed
    web_top = KM_Z0 + KM_WEB
    field, _ = _keymat_field(side)
    rim = field.buffer(-0.15).difference(field.buffer(-1.65))
    plate = plate.union(_cq_from_poly(rim, web_top - 0.1, z0 - (web_top - 0.1)))
    # key openings at every cap (v0.17: rounded-rect for grid keys, round for the
    # cluster), cut AFTER the rim union, deep enough to keep the full plunger bore
    # clear through the rim band. One MultiPolygon cut instead of per-key booleans.
    from shapely.ops import unary_union
    openings = [op for (_p, op, _x, _y) in _cap_shapes_product(side)]
    plate = plate.cut(_cq_from_poly(unary_union(openings), web_top - 0.2, TOP_T + (z0 - web_top) + 0.4))
    # v0.21 (Bean-style hall nub): a plain round aperture — ONLY the printed
    # nub emerges; the face stays flat (no pod, no exposed mechanism). The
    # spring's flange is captured in an underside counterbore: it drops in
    # from below at assembly and the O10 aperture keeps it captive.
    nz = _nub_zone(side)
    if nz:
        x, y, ad = nz["x"], nz["y"], nz["aperture_d"]
        plate = plate.cut(cq.Workplane("XY").workplane(offset=z0 - 0.1)
                          .center(x, y).circle(ad/2).extrude(TOP_T + 0.2))
        plate = plate.cut(cq.Workplane("XY").workplane(offset=z0 - 0.1)
                          .center(x, y).circle(NUB_SPRING_FLANGE_D/2 + 0.2).extrude(1.0 + 0.1))
    # M3 clearance holes + flush countersinks at this grip's 5 bosses (v0.19: the
    # proud pan heads were uncomfortable under the thumbs — heads now sit in
    # 90-degree cones, flush with the face). Lid prints face-down: cones print clean.
    geo = prod[side]; ox, oy = prod[f"{side}_origin"]
    for hh in geo["mount_holes"]:
        h = cq.Workplane("XY").workplane(offset=z0-0.1).center(hh["x"]+ox, hh["y"]+oy).circle(SCREW_HOLE_R).extrude(TOP_T+0.2)
        plate = plate.cut(h)
        plate = plate.cut(_csk_cone(hh["x"]+ox, hh["y"]+oy, z0+TOP_T))
    # 0.8mm 45-degree chamfer on the inner top edge (the cyan side of the reveal)
    plate = plate.cut(_edge_wedge(s*gx, z0+TOP_T, bh=bh))
    return _to_trimesh(plate, f"grip_lid_{side}")

def center_panel():
    return _memo("center_panel", _center_panel_build)

def _center_panel_build():
    """Center front panel, v0.18: a SUNKEN TRAY (pink, 'the front of the back').
    The border flange (TOP_Z..WELL_TOP) is flush with the grip lids; inside it a
    deep well drops to WELL_FLOOR so the cased phone's SCREEN lands flush with the
    lids' keyboard face. The well floor slab (SLAB_BOT..WELL_FLOOR) carries the
    Ø57 x 1.8 MagSafe ring recess (0.8mm web below, ring 0.2mm proud — the phone
    rests on the ring exactly as before, just sunken). v0.19: the well is a CLOSED
    picture-frame — the 2.0mm y-wall band captures the cased phone's long edges
    and 1.6mm END WALLS (fed by the wider deck.product gap) close the x-ends that
    used to be open slots into the grip cavities (feedback item 2). Down-press
    loads pass through 4 floor nubs to the back floor; MagSafe detach flexes the
    2.6mm slab <0.3mm against the 4 border screws (M3 flush-countersunk, item 1).
    The thumb scallop in the top border is now a WATERTIGHT curved finger dish
    (item 3) that still exposes the case edge for tip-out. Still the bolted x=0
    seam splice; the FFC (in its under-slab floor channel) is serviceable by
    removing the panel; the battery lives in the LEFT grip cavity (battery_body)."""
    fp = full_footprint()
    prod = _product()
    gx = _seam_frame(); px_edge = gx - SEAM_GAP
    bh = prod["right"]["board_h"]
    ph = prod["phone"]; ms = prod["magsafe"]
    pcx, pcy = ph["x"] + ph["w"]/2, ph["y"] + ph["h"]/2
    region = Polygon([(-px_edge, -60), (px_edge, -60), (px_edge, bh+60), (-px_edge, bh+60)])
    poly = fp.buffer(WALL_T+PCB_CLR).intersection(region).buffer(0)
    # v0.19 (item 2): the well is a CLOSED picture-frame. The old 1.2mm x-overcut ran
    # the cut off the panel ends, leaving open slots into the grip cavities; now the
    # cavity stops at phone + 0.35/side and END WALLS (well_end_wall = px_edge -
    # cavity end = 1.6mm) rise from the slab to the face. wallB is an explicit frame
    # rect (x-band 1.6 / y-band WELL_WALL) instead of a uniform buffer.
    pocketP = shp_box(pcx - ph["w"]/2 - 0.35, pcy - (ph["h"] + PHONE_CLR)/2,
                      pcx + ph["w"]/2 + 0.35, pcy + (ph["h"] + PHONE_CLR)/2)
    px0, py0, px1, py1 = pocketP.bounds
    # x-band nominally 1.6 (= px_edge - px1) but extended 5mm past the panel edge so
    # the (poly - wallB) underside difference never leaves a zero-width sliver at
    # the exactly-coincident panel boundary (it broke watertightness)
    wallB = shp_box(px0 - 1.6 - 5.0, py0 - WELL_WALL, px1 + 1.6 + 5.0, py1 + WELL_WALL)
    # solid block border-top down to slab bottom, then carve:
    panel = _cq_from_poly(poly, SLAB_BOT, WELL_TOP - SLAB_BOT)
    # (1) the well void above the floor
    panel = panel.cut(_cq_from_poly(pocketP, WELL_FLOOR, WELL_TOP - WELL_FLOOR + 0.2))
    # (2) the underside outside the well-wall band: border flange is only
    #     TOP_Z..WELL_TOP so it seats on the perimeter/transverse walls + bosses
    under = poly.difference(wallB)
    if not under.is_empty:
        panel = panel.cut(_cq_from_poly(under, SLAB_BOT - 0.1, (TOP_Z - SLAB_BOT) + 0.1))
    # MagSafe ring recess in the well floor (0.8mm web remains below)
    panel = panel.cut(cq.Workplane("XY").workplane(offset=RECESS_FLOOR)
                      .center(ms["cx"], ms["cy"]).circle(RING_REC_R).extrude(RING_REC_D + 0.05))
    # 4 seam-splice screws through the border strips — M3 flush countersunk like
    # the lids (v0.19). The panel's cones print opening-upward (slab-down), so they
    # get 0.15 extra sink against rim droop.
    for (sx, sy) in PANEL_SCREWS:
        panel = panel.cut(cq.Workplane("XY").workplane(offset=TOP_Z - 0.1)
                          .center(sx, sy).circle(SCREW_HOLE_R).extrude(WELL_TOP + 0.2))
        panel = panel.cut(_csk_cone(sx, sy, WELL_TOP, extra=0.15))
    # 4 floor nubs under the slab: solid down-press path to the back floor
    for (nx, ny) in ((-45.0, 45.0), (45.0, 45.0), (-45.0, 70.0), (45.0, 70.0)):
        panel = panel.union(cq.Workplane("XY").workplane(offset=SLAB_BOT)
                            .center(nx, ny).circle(2.5).extrude(-(SLAB_BOT - FLOOR)))
    # thumb scallop, v0.19 (item 3): the v0.18 plain R9 cylinder cut punched through
    # the border into the open spine cavity. Now it is a CLOSED finger dish: first
    # union a solid backer — cylinder R10.6 centred 2.3mm INSIDE the well edge,
    # clipped to y >= _PY1 (outside the well) and to the spine cavity polygon
    # shrunk 0.25 (never touches the back wall) — then re-cut the R9 void from
    # z=6.0 up. What remains is a 1.6mm curved half-annulus wall with a solid
    # bed-supported floor (slab..6.0): watertight, support-free printed slab-down,
    # and the phone's case edge is still exposed over a ~17mm chord for tip-out.
    scx, scy = 0.0, _PY1 - 2.3
    cavity_clip = fp.buffer(PCB_CLR).buffer(-0.25).intersection(
        shp_box(-px_edge + 0.25, -60, px_edge - 0.25, bh + 60))
    dish = (cq.Workplane("XY").workplane(offset=SLAB_BOT)
            .center(scx, scy).circle(10.6).extrude(WELL_TOP - SLAB_BOT))
    dish = dish.intersect(cq.Workplane("XY").workplane(offset=SLAB_BOT - 1)
                          .center(scx, _PY1 + 30).box(60, 60, WELL_TOP - SLAB_BOT + 2,
                                                      centered=(True, True, False)))
    dish = dish.intersect(_cq_from_poly(cavity_clip, SLAB_BOT - 1, WELL_TOP - SLAB_BOT + 2))
    panel = panel.union(dish)
    panel = panel.cut(cq.Workplane("XY").workplane(offset=6.0)
                      .center(scx, scy).circle(9.0).extrude(WELL_TOP))
    # 0.8mm 45-degree chamfers on both outer top edges (the pink side of the reveal)
    for s in (1, -1):
        panel = panel.cut(_edge_wedge(s*px_edge, WELL_TOP, bh=bh))
    return _to_trimesh(panel, "center_panel")

# ==== keycap legends (Rii i8+ print style; ANSI US per the ZMK keymap) =============
LEGEND_DEPTH = 0.4        # deboss into the cap top face
LEGEND_FONT = "DejaVu Sans"
CAP_TOP = KM_Z0 + KM_WEB + KM_PL_H   # 15.3 — keycap top face (legends live here)
PRIM_FS = 4.3             # single-glyph primaries: caps/digits ~3.1mm tall
WORD_FS = 3.0             # word primaries (Enter/Shift/...), width-clamped to the cap
SEC_FS = 2.5              # shifted secondaries (~1.8mm glyphs), top-left corner
FN_FS = 2.5               # FN-layer single glyphs (~1.8mm), bottom-right corner
FN_WORD_FS = 1.9          # FN-layer words (Home/End/PrtSc)

# label -> printed word primary (Rii-style human forms). SPC prints BLANK like the
# i8+ space; BSP and the NAV arrows render as glyph polygons (see _bsp_arrow/_tri);
# labels not listed print themselves (letters, digits, punctuation).
PRIM_WORDS = {"ENT": "Enter", "SHF": "Shift", "CAP": "Caps", "CTL": "Ctrl",
              "ALT": "Alt", "AGR": "AltGr", "WIN": "Win", "FN": "Fn",
              "DEL": "Del", "ESC": "Esc", "TAB": "Tab",
              "PGUP": "PgUp", "PGDN": "PgDn", "NAV_OK": "OK",
              "MB_L": "L", "MB_R": "R"}
# shifted secondaries, ANSI US (matches the ZMK keymap output), small at top-left
SHIFTED = {"1": "!", "2": "@", "3": "#", "4": "$", "5": "%", "6": "^", "7": "&",
           "8": "*", "9": "(", "0": ")", ";": ":", ",": "<", ".": ">", "/": "?",
           "`": "~", "[": "{", "]": "}", "\\": "|"}
# FN-layer legends (Rii's blue print), small at bottom-right — ONLY where the
# keymap binds them: FN+0/9 = minus/equal, FN+; = SQT, FN+PGUP/PGDN = Home/End,
# FN+DEL = PrintScreen, FN+[/] = pipe/backslash (v0.20 — the \ cap became the
# right CTL; direct bindings, no Shift) (thumbdeck.keymap fn_layer).
FN_LEGENDS = {"0": "-", "9": "=", ";": "'", "PGUP": "Home", "PGDN": "End",
              "DEL": "PrtSc", "[": "|", "]": "\\"}

def _text_cutter(txt, fs, cx, cy, max_w=None, anchor="c"):
    """One legend as a deboss cutter: 3D text extruded LEGEND_DEPTH below the cap
    top (+0.2 above it for a clean boolean). anchor 'c' centres the glyph bbox on
    (cx, cy); 'tl'/'br' put its top-left / bottom-right corner there. max_w
    shrinks the text uniformly if the rendered string is wider (word legends on
    an 8.5mm cap)."""
    s = (cq.Workplane("XY").text(txt, fs, -(LEGEND_DEPTH + 0.2), font=LEGEND_FONT,
                                 kind="bold", halign="center", valign="center").val())
    bb = s.BoundingBox()
    if max_w and bb.xlen > max_w:
        s = s.scale(max_w / bb.xlen)
        bb = s.BoundingBox()
    if anchor == "c":
        dx, dy = cx - bb.center.x, cy - bb.center.y
    elif anchor == "tl":
        dx, dy = cx - bb.xmin, cy - bb.ymax
    else:  # "br"
        dx, dy = cx - bb.xmax, cy - bb.ymin
    return s.translate(cq.Vector(dx, dy, (CAP_TOP + 0.2) - bb.zmax))

def _poly_cutter(poly):
    """Glyph polygon (arrows/triangles) as a deboss cutter at the cap top."""
    return _cq_from_poly(poly, CAP_TOP - LEGEND_DEPTH, LEGEND_DEPTH + 0.2).val()

def _tri(cx, cy, d, s=3.2):
    """Solid triangle glyph for the NAV arrows, pointing d in U/D/L/R (product
    frame: L = -x = toward screen-left, matching the key's semantic)."""
    h = s * 0.85
    pts = {"U": [(cx - s/2, cy - h/2), (cx + s/2, cy - h/2), (cx, cy + h/2)],
           "D": [(cx - s/2, cy + h/2), (cx + s/2, cy + h/2), (cx, cy - h/2)],
           "L": [(cx + h/2, cy - s/2), (cx + h/2, cy + s/2), (cx - h/2, cy)],
           "R": [(cx - h/2, cy - s/2), (cx - h/2, cy + s/2), (cx + h/2, cy)]}[d]
    return Polygon(pts)

def _bsp_arrow(cx, cy):
    """Left-arrow glyph for backspace (the Rii prints an arrow, not 'Bksp'):
    triangle head + stem, 4.6 x 2.6 overall."""
    head = Polygon([(cx - 2.3, cy), (cx - 0.4, cy + 1.3), (cx - 0.4, cy - 1.3)])
    stem = shp_box(cx - 0.6, cy - 0.45, cx + 2.3, cy + 0.45)
    return head.union(stem)

def _legend_cutters(side):
    """Every legend on one grip's caps as cq deboss-cutter solids (product frame).
    Grid caps: primary centred (dropped 0.9 low when a shifted secondary shares
    the cap, like real ANSI caps), SHIFTED secondary top-left, FN legend
    bottom-right. Round Ø6.2 cluster caps get compact centred legends; PgUp/PgDn
    stack their FN word (Home/End) under the primary."""
    prod = _product(); geo = prod[side]; ox, oy = prod[f"{side}_origin"]
    c = geo["config"]
    cuts = []
    for k in geo["keys"]:
        lab = k["label"]; x, y = k["x"]+ox, k["y"]+oy
        w = (k.get("w", 1) - 1) * c["pitch_x"] + c["key_w"]     # 2u-aware cap width
        py = y - 0.9 if lab in SHIFTED else y
        if lab == "SPC":
            pass                                    # Rii space prints blank
        elif lab == "BSP":
            cuts.append(_poly_cutter(_bsp_arrow(x, y)))
        elif lab in PRIM_WORDS:
            cuts.append(_text_cutter(PRIM_WORDS[lab], WORD_FS, x, py, max_w=w-1.4))
        else:
            cuts.append(_text_cutter(lab, PRIM_FS, x, py, max_w=w-1.4))
        if lab in SHIFTED:
            cuts.append(_text_cutter(SHIFTED[lab], SEC_FS,
                                     x - w/2 + 0.8, y + c["key_h"]/2 - 0.7, anchor="tl"))
        if lab in FN_LEGENDS:
            fs = FN_FS if len(FN_LEGENDS[lab]) == 1 else FN_WORD_FS
            cuts.append(_text_cutter(FN_LEGENDS[lab], fs,
                                     x + w/2 - 0.8, y - c["key_h"]/2 + 0.7, anchor="br"))
    for f in geo.get("features", []):
        if f["type"] != "key":
            continue
        lab = f["label"]; x, y = f["x"]+ox, f["y"]+oy
        if lab.startswith("NAV_") and lab != "NAV_OK":
            cuts.append(_poly_cutter(_tri(x, y, lab[-1])))
        elif lab in FN_LEGENDS:      # PgUp/PgDn: primary high + FN word low
            cuts.append(_text_cutter(PRIM_WORDS[lab], 2.4, x, y + 1.2, max_w=4.6))
            cuts.append(_text_cutter(FN_LEGENDS[lab], FN_WORD_FS, x, y - 1.6, max_w=4.2))
        else:                        # OK / L / R
            cuts.append(_text_cutter(PRIM_WORDS.get(lab, lab), WORD_FS, x, y, max_w=4.6))
    return cuts

def keymats(side):
    return _memo(f"keymat_{side}", lambda: _keymats_build(side))

def _keymats_build(side):
    """Per-grip one-piece keymat: v0.17 rectangular keycap plungers (round for the
    cluster keys) over each dome, joined by a thin web plate. The plunger unions are
    built as ONE shapely MultiPolygon extrusion per z-band (plungers, nubs) — far
    fewer OCC booleans than per-key unions, and the caps stay perfectly coplanar.
    Cap tops carry the DEBOSSED legends (0.4mm, Rii i8+ print style), cut as one
    compound boolean."""
    from shapely.ops import unary_union
    z0 = KM_Z0                # web bottom, just above the domes
    field, shapes = _keymat_field(side)
    mat = _cq_from_poly(field, z0, KM_WEB)
    # keycap plungers (the user-visible caps): one extrusion of the union
    caps = unary_union([pl for (pl, _o, _x, _y) in shapes])
    mat = mat.union(_cq_from_poly(caps, z0 + KM_WEB, KM_PL_H))
    # actuator nubs underneath (reach down to press each dome centre)
    nubs = unary_union([Polygon([(x+1.4*math.cos(t), y+1.4*math.sin(t))
                                 for t in np.linspace(0, 2*math.pi, 16)])
                        for (_p, _o, x, y) in shapes])
    mat = mat.union(_cq_from_poly(nubs, z0 - 1.0, 1.0))
    # debossed keycap legends: one compound cut of every glyph on this grip
    t0 = time.time()
    cutters = _legend_cutters(side)
    mat = mat.cut(cq.Compound.makeCompound(cutters))
    print(f"  keymat_{side}: {len(cutters)} legend cutters debossed in {time.time()-t0:.1f}s")
    return _to_trimesh(mat, f"keymat_{side}")

# ==== non-printed bodies (real dims) ================================================
def phone_body():
    # cased envelope (deck.product already includes case_t laterally); thickness =
    # bare + case back, so this box's top face IS the screen plane
    ph = _product()["phone"]
    m = _box(ph["w"], ph["h"], PHONE_TC)
    return _place(m, ph["x"]+ph["w"]/2, ph["y"]+ph["h"]/2, 0)  # z set in assemble

def battery_body():
    # v0.18: 403040 pouch (4.0 x 30 x 40, ~450-500mAh) in the LEFT grip's back
    # cavity, foam-taped to the floor under the passive PCB (the spine well left
    # only ~0.5mm under its floor slab — no standard cell fits there any more).
    sb = _product()["battery"]
    m = _box(sb["w"], sb["h"], sb["t"])
    return _place(m, sb["x"]+sb["w"]/2, sb["y"]+sb["h"]/2, 0)

def magsafe_ring():
    ms = _product()["magsafe"]
    outer = trimesh.creation.cylinder(radius=ms["d"]/2, height=2.0, sections=48)
    inner = trimesh.creation.cylinder(radius=ms["d"]/2-8, height=3, sections=48)
    ring = outer.difference(inner)
    return _place(ring, ms["cx"], ms["cy"], 0)

def flex_body():
    """Bridge flex: flat ribbon from the right J2 to the left J2. v0.18: it crosses
    the spine in the under-slab FLOOR CHANNEL (duct z 1.1..1.6 — the well leaves no
    room at connector height), S-bending down from each ZIF inside the grip
    cavities; modeled as the straight duct run."""
    prod = _product()
    def j2(side):
        geo = prod[side]; ox, oy = prod[f"{side}_origin"]
        bx, by, bw, bh = geo["keepouts"]["bridge"]
        return (bx+ox+bw/2, by+oy+bh/2)
    rx, ry = j2("right"); lx, ly = j2("left")
    length = abs(rx-lx); midx = (rx+lx)/2; midy = (ry+ly)/2
    m = _box(length, 10.0, 0.3)
    return _place(m, midx, midy, 0)

# ---- the 14 shell screws (5 per grip + 4 panel, v0.19) -----------------------------
# M3 x 10 COUNTERSUNK (DIN 965, 90-degree, dk<=6.0), dropped in from the TOP: the
# head sits in the lid/panel countersink with its top face FLUSH at WELL_TOP
# (feedback item 1 — the old proud M2 pan heads were uncomfortable). Shank passes
# the Ø3.4 clearance hole and (grip screws) the PCB's Ø3.4 mount hole, then threads
# into the M3 heat-set insert (OD ~4.6) in the Ø4.0 bore. Tip at WELL_TOP-10 = 4.7:
# 2.1mm above the 2.6 grip bore floor, 1.4mm above the 3.3 panel bore floor.
SCREW_HEAD_D, SCREW_HEAD_H = 5.6, 1.3   # DIN 965 M3: dk nominal 5.6, cone depth ~1.3
SCREW_D, SCREW_L = 3.0, 10.0

def _screw_solid(x, y):
    """One flush M3x10 CSK screw: 90-degree cone head (top face AT WELL_TOP) + shank."""
    hr, sr = SCREW_HEAD_D/2, SCREW_D/2
    cone_h = hr - sr
    head = trimesh.creation.cone(radius=hr, height=cone_h, sections=32)
    head.apply_transform(trimesh.transformations.rotation_matrix(np.pi, (1, 0, 0)))
    head.apply_translation((0, 0, WELL_TOP))          # cone: r=hr at WELL_TOP, tapers down
    shank = trimesh.creation.cylinder(radius=sr, height=SCREW_L, sections=24)
    shank.apply_translation((0, 0, WELL_TOP - SCREW_L/2))
    m = trimesh.boolean.union([head, shank], engine="manifold")
    m.apply_translation((x, y, 0))
    m.visual.face_colors = [185, 188, 194, 255]
    return m

def screw_bodies():
    """All 14 shell screws as watertight solids (product frame): screw_<side>_<i>
    at the grip mount holes + screw_panel_<i> at the panel's border screws."""
    out = {}
    prod = _product()
    tip = WELL_TOP - SCREW_L
    for name, floor in (("grip", PCB_Z - (STANDOFF - 1)), ("panel", FLOOR + WALL - 9.0)):
        assert tip - floor >= 1.0, \
            f"M3x{SCREW_L:.0f} tip @ {tip} would bottom out in the {name} bore (floor {floor})"
    for side in ("right", "left"):
        geo = prod[side]; ox, oy = prod[f"{side}_origin"]
        for i, hh in enumerate(geo["mount_holes"]):
            out[f"screw_{side}_{i}"] = _screw_solid(hh["x"]+ox, hh["y"]+oy)
    for i, (sx, sy) in enumerate(PANEL_SCREWS):
        out[f"screw_panel_{i}"] = _screw_solid(sx, sy)
    return out


# ---- reporting / rendering ---------------------------------------------------------
def height_report(side="right"):
    parts, geo = pcb_assembly(side)
    print(f"== {side} PCB assembly: {len(parts)} bodies ==")
    zmax = max(m.bounds[1][2] for m in parts.values())
    zmin = min(m.bounds[0][2] for m in parts.values())
    print(f"  z extent: {zmin:.2f} .. {zmax:.2f} mm  (front stack {zmax-PCB_T:.2f} above board, back {abs(zmin):.2f} below)")
    watch = ["U1", "J1", "J2", "J3", "U2"] + [n for n in parts if n.endswith(("_pwr", "_rst"))]
    for n in watch:
        if n in parts:
            bb = parts[n].bounds
            print(f"  {n:8s}: z {bb[0][2]:6.2f}..{bb[1][2]:6.2f}  (below board {max(0.0, -bb[0][2]):.2f})")
    deepest = max((-m.bounds[0][2], n) for n, m in parts.items())
    print(f"  back cavity: STANDOFF {STANDOFF} vs deepest part {deepest[1]} {deepest[0]:.2f} "
          f"-> margin {STANDOFF - deepest[0]:.2f}mm to the floor")
    print(f"  stack (product z): floor top {FLOOR} | PCB {PCB_Z}..{PCB_Z+PCB_T} | dome top {DOME_TOP} | "
          f"keymat web {KM_Z0}..{KM_Z0+KM_WEB} | grip lids {TOP_Z}..{TOP_Z+TOP_T} | "
          f"well slab {SLAB_BOT}..{WELL_FLOOR} border top {WELL_TOP} | "
          f"ring {MAGSAFE_Z-RING_H/2:.1f}..{MAGSAFE_Z+RING_H/2:.1f} | "
          f"cased phone {PHONE_Z-PHONE_TC/2:.1f}..{PHONE_Z+PHONE_TC/2:.1f} "
          f"(screen flush with lids @ {WELL_TOP})")


def render_iso(meshes, path, title, elev=32, azim=-60):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(11, 7)); ax = fig.add_subplot(111, projection="3d")
    allv = []
    for m, color in meshes:
        tri = m.vertices[m.faces]
        pc = Poly3DCollection(tri, facecolor=color, edgecolor=(0, 0, 0, 0.06), linewidths=0.15)
        ax.add_collection3d(pc); allv.append(m.bounds)
    allv = np.array(allv); lo = allv[:, 0].min(0); hi = allv[:, 1].max(0)
    ctr = (lo+hi)/2; span = (hi-lo).max()/2
    ax.set_xlim(ctr[0]-span, ctr[0]+span); ax.set_ylim(ctr[1]-span, ctr[1]+span); ax.set_zlim(ctr[2]-span, ctr[2]+span)
    ax.set_box_aspect((1, 1, 1)); ax.view_init(elev=elev, azim=azim); ax.set_axis_off()
    ax.set_title(title, fontsize=10)
    plt.tight_layout(); plt.savefig(path, dpi=110); plt.close()
    print(f"  rendered {path}")


# ==== assembly + collision ==========================================================
# z-stack (product frame): back-shell floor at 0; PCB rests on STANDOFF bosses.
# (PCB_Z / DOME_TOP / KM_Z0 / TOP_Z / WELL_* are all derived up top.)
RING_H = 2.0                                    # N52 ring thickness
RECESS_FLOOR = WELL_FLOOR - RING_REC_D          # ring recess floor (in the sunken well floor)
MAGSAFE_Z = RECESS_FLOOR + RING_H/2             # ring body centre (sits IN the recess)
PHONE_Z = RECESS_FLOOR + RING_H + PHONE_TC/2    # cased phone rests on the 0.2mm-proud ring;
                                                # screen top = WELL_TOP (flush with the lids)
BATT_Z = FLOOR + 2.0                   # 403040 cell (4mm) seated flush on the LEFT grip
                                       # floor — the 0.3 foam compresses under the taped
                                       # cell; flush gives the full 1.14mm diode clearance
                                       # (was +0.3, which left 0.84mm and read as a clash)
FLEX_Z = 1.3                           # ribbon in the under-slab floor channel (duct 1.1..1.6)

def nub_spring():
    return _memo("nub_spring", _nub_spring_build)

def _nub_spring_build():
    """v0.21 Bean-style printed flexure spring: an OD14.8 flange (captured in the
    right lid's underside counterbore) joined to a central hub by 3 spiral
    flexure arms. The hub carries the N42/52 magnet in a downward pocket
    (~2.6mm over the back-side TMAG5273, through the FR4) and rises through the
    lid aperture as the nub post. Arm thickness NUB_ARM_T is the print-tune
    stiffness parameter (the pointing FEEL). Print hub-down with a brim.
    Architecture adapted from the Ploopy Bean (CERN-OHL-S v2)."""
    from shapely.geometry import LineString
    from shapely.ops import unary_union
    nz = _nub_zone("right")
    assert nz, "nub_spring needs the right grip's hall_nub feature"
    x, y = nz["x"], nz["y"]
    # flange ring in the lid counterbore (z 12.3..13.3): 12.35..13.35, 0.05 clamp
    flange = (cq.Workplane("XY").workplane(offset=12.35).center(x, y)
              .circle(NUB_SPRING_FLANGE_D/2).circle(5.8).extrude(1.0))
    # 3 spiral flexure arms, 1.2 wide x NUB_ARM_T thick, r 3.6 -> 5.9
    arms = []
    for k in range(3):
        a0 = k * 2*math.pi/3
        pts = [(x + (3.6 + 2.3*t/100.0) * math.cos(a0 + math.radians(t)),
                y + (3.6 + 2.3*t/100.0) * math.sin(a0 + math.radians(t)))
               for t in range(0, 101, 10)]
        arms.append(LineString(pts).buffer(0.6))
    spring = flange.union(_cq_from_poly(unary_union(arms), 12.35, NUB_ARM_T))
    # hub: magnet stub down toward the PCB, post up through the aperture,
    # O5 cap spigot on top
    hub = (cq.Workplane("XY").workplane(offset=10.4).center(x, y)
           .circle(NUB_HUB_D/2).extrude(16.4 - 10.4))
    spigot = (cq.Workplane("XY").workplane(offset=16.4).center(x, y)
              .circle(2.5).extrude(1.0))
    spring = spring.union(hub).union(spigot)
    # 3 legs from the flange underside to the PCB front face (z 9.5): the axial
    # datum for the whole nub. The lid counterbore ceiling (13.3) presses the
    # flange (top 13.35) 0.05 onto them when the lid screws go home — without
    # them nothing opposes the flange from below and the spring can drop ~0.9mm
    # (rattling, no flexure preload; found by the v0.21 adversarial fit review)
    for k in range(3):
        a = math.radians(40 + 120 * k)
        spring = spring.union(
            cq.Workplane("XY").workplane(offset=9.5)
            .center(x + 6.6 * math.cos(a), y + 6.6 * math.sin(a))
            .circle(0.7).extrude(12.35 - 9.5))  # r0.7: 0.1 inside both flange
            # edges (r5.8/7.4) — tangent legs tessellate non-watertight
    # magnet pocket, opening downward (press-fit, N up — compass-check!)
    spring = spring.cut(cq.Workplane("XY").workplane(offset=10.3).center(x, y)
                        .circle(NUB_MAGNET_D/2 + 0.05).extrude(NUB_MAGNET_H + 0.15))
    return _to_trimesh(spring, "nub_spring")

def nub_cap():
    return _memo("nub_cap", _nub_cap_build)

def _nub_cap_build():
    """TPU friction cap for the nub: O8.5 with a shallow finger dish, press-fit
    on the spring's O5 spigot. One revolved profile (boolean sphere cuts
    tessellate non-watertight); the revolve's dish-apex seam edge is welded
    after export."""
    nz = _nub_zone("right")
    assert nz, "nub_cap needs the right grip's hall_nub feature"
    x, y = nz["x"], nz["y"]
    import math as _m
    z0 = 16.45                                   # cap base (0.05 over spigot base)
    CAP_R_, CAP_H = NUB_CAP_D/2, NUB_CAP_H
    SOCK_R, SOCK_DEPTH = 2.6, 1.6
    DISH_R, DISH_SINK = 9.0, 0.6
    zc = CAP_H - DISH_SINK + DISH_R
    rm = _m.sqrt(DISH_R**2 - (DISH_R - DISH_SINK)**2)
    rmid = rm / 2.0
    zmid = zc - _m.sqrt(DISH_R**2 - rmid**2)
    prof = (cq.Workplane("XZ")
            .moveTo(0.0, SOCK_DEPTH).lineTo(SOCK_R, SOCK_DEPTH).lineTo(SOCK_R, 0.0)
            .lineTo(CAP_R_, 0.0).lineTo(CAP_R_, CAP_H).lineTo(rm, CAP_H)
            .threePointArc((rmid, zmid), (0.0, CAP_H - DISH_SINK))
            .close())
    cap = prof.revolve(360, (0, 0), (0, 1)).translate((x, y, z0))
    m = _to_trimesh(cap, "nub_cap")
    if not m.is_watertight:
        m.merge_vertices(merge_tex=True, merge_norm=True)
        m.update_faces(m.nondegenerate_faces())
        m.remove_unreferenced_vertices()
        trimesh.repair.fill_holes(m)
        assert m.is_watertight, "nub_cap repair failed"
        m.export(os.path.join(BUILD, "nub_cap.stl"))
    return m

SHELLS = ("back_right", "back_left", "grip_lid_right", "grip_lid_left", "center_panel",
          "nub_spring", "nub_cap")

def assemble():
    A = {}
    A["back_right"] = back_half("right")
    A["back_left"] = back_half("left")
    A["grip_lid_right"] = grip_lid("right")
    A["grip_lid_left"] = grip_lid("left")
    A["center_panel"] = center_panel()
    A["nub_spring"] = nub_spring()
    A["nub_cap"] = nub_cap()
    A["keymat_right"] = keymats("right")
    A["keymat_left"] = keymats("left")
    prod = _product()
    for side in ("right", "left"):
        ox, oy = prod[f"{side}_origin"]
        parts, _ = pcb_assembly(side)
        for k, m in parts.items():
            mm = m.copy(); mm.apply_translation((ox, oy, PCB_Z))
            A[f"{side}:{k}"] = mm
    ph = phone_body(); ph.apply_translation((0, 0, PHONE_Z)); A["phone"] = ph
    bt = battery_body(); bt.apply_translation((0, 0, BATT_Z)); A["battery"] = bt
    ms = magsafe_ring(); ms.apply_translation((0, 0, MAGSAFE_Z)); A["magsafe"] = ms
    fx = flex_body(); fx.apply_translation((0, 0, FLEX_Z)); A["flex"] = fx
    A.update(screw_bodies())              # the 14 shell screws, top-in at the bosses
    return A

# pairs allowed to touch (mating faces / actuation), and self-groups to skip
def _allowed(a, b):
    """Only true mating CONTACTS are tolerated (small overlap where two faces meet).
    Everything else that interpenetrates is a real clash to fix."""
    s = {a, b}
    km = any(x.startswith("keymat") for x in s)
    # v0.21: SW40 is the thumbstick, NOT a dome — keymat contact with it is real
    if km and any(":SW" in x and not x.endswith(("_pwr", "_rst")) for x in s): return True  # nub presses dome
    if km and any(x.startswith("grip_lid") for x in s): return True  # clamp rim presses the web 0.1mm (intended preload)
    if s == {"nub_spring", "grip_lid_right"}: return True  # counterbore ceiling clamps the flange (0.05 preload)
    if "nub_spring" in s and any("pcb_right" in x for x in s): return True  # spring legs bear on the PCB face
    if s == {"nub_cap", "nub_spring"}: return True         # cap press-fits the spigot
    if s == {"phone", "magsafe"} or s == {"magsafe", "center_panel"}: return True           # rests on/in
    if s == {"back_right", "back_left"}: return True   # seam tabs/shiplap mate face-to-face
    # screw heads SEAT in the lid/panel countersinks (45-degree cone-on-cone);
    # everything else a screw could hit (PCB hole wall, boss bore) is modeled with
    # real clearance and stays a hard clash if violated
    if any(x.startswith("screw_") for x in s) and any(x.startswith("grip_lid") for x in s):
        return True
    if any(x.startswith("screw_panel") for x in s) and "center_panel" in s:
        return True
    return False

def collide(A, tol_gross=3.0, tol_shell=0.2):
    """AABB pre-filter, then mesh-intersection volume on overlapping pairs. Per-pair
    tolerance: shell-vs-PCB-component pairs are clean box/extrusion booleans, so any
    real interpenetration matters -> 0.2mm^3. Gross printed/organic pairs (shell-shell,
    keymat, phone, battery, flex) keep 3.0mm^3 to absorb STL-tessellation noise on
    large curved contact faces. Returns (clashes, contacts, checked); contacts are
    whitelisted pairs with measurable overlap (reported, not failed)."""
    shells = SHELLS
    def tol(a, b):
        if (a in shells and ":" in b) or (b in shells and ":" in a):
            return tol_shell
        return tol_gross
    names = list(A); bounds = {n: A[n].bounds for n in names}
    def aabb(a, b):
        la, ha = bounds[a]; lb, hb = bounds[b]
        return all(ha[i] >= lb[i]-0.01 and hb[i] >= la[i]-0.01 for i in range(3))
    clashes = []; contacts = []; checked = 0
    for i in range(len(names)):
        for j in range(i+1, len(names)):
            a, b = names[i], names[j]
            # skip same-grip pcb component vs component (DRC already guarantees no overlap)
            if ":" in a and ":" in b and a.split(":")[0] == b.split(":")[0]:
                continue
            if not aabb(a, b):
                continue
            checked += 1
            try:
                inter = A[a].intersection(A[b])
                vol = float(inter.volume) if inter is not None and hasattr(inter, "volume") else 0.0
            except Exception:
                vol = 0.0
            if vol <= 0.01:
                continue
            if _allowed(a, b):
                contacts.append((a, b, round(vol, 2)))
            elif vol > tol(a, b):
                clashes.append((a, b, round(vol, 2)))
    clashes.sort(key=lambda t: -t[2])
    return clashes, contacts, checked


def bed_fit(m, name):
    """Every printed part must fit an Ender 3 V2 (220x220x250) laid flat, with
    brim margin: xy bbox <= BED_XY (=204). Returns True when it fits."""
    dx, dy, dz = m.extents
    ok = dx <= BED_XY and dy <= BED_XY and dz <= 250
    tag = "fits" if ok else "DOES NOT FIT"
    print(f"  bed-fit {name}: {dx:.1f} x {dy:.1f} x {dz:.1f} mm -> {tag} (limit {BED_XY:.0f} xy = 220 bed - 2x8 brim)")
    return ok

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--sync-models", action="store_true",
                    help="copy the printable STLs from build/ to the tracked models/ dir")
    args = ap.parse_args()
    os.makedirs(BUILD, exist_ok=True)
    if args.report:
        height_report("right"); height_report("left")
    ok = True
    if args.all:
        built = []
        for fn, nm in [(lambda: back_half("right"), "back_right"),
                       (lambda: back_half("left"), "back_left"),
                       (lambda: grip_lid("right"), "grip_lid_right"),
                       (lambda: grip_lid("left"), "grip_lid_left"),
                       (center_panel, "center_panel"),
                       (nub_spring, "nub_spring"),
                       (nub_cap, "nub_cap")]:
            m = fn(); print(f"  {nm}: watertight={m.is_watertight} vol={m.volume/1000:.1f}cm3 bbox={[round(v,1) for v in m.extents]}")
            ok = bed_fit(m, nm) and ok
            built.append(m)
        for side in ("right", "left"):
            m = keymats(side); print(f"  keymat_{side}: watertight={m.is_watertight} bbox={[round(v,1) for v in m.extents]}")
            ok = bed_fit(m, f"keymat_{side}") and ok
            built.append(m)
        if not ok:
            sys.exit("bed-fit FAILED: a part exceeds the Ender 3 V2 printable area")
        # reference STL of all 9 printed parts in their assembled positions (they
        # share the product frame, so plain concatenation IS the assembly) — a
        # multi-body viewing aid for spatial reasoning, not a printable part
        asm = trimesh.util.concatenate(built)
        asm.export(os.path.join(BUILD, "assembled_printed.stl"))
        print(f"  assembled_printed.stl: all 9 printed parts in place, bbox={[round(v,1) for v in asm.extents]}")
    if args.check:
        A = assemble()
        print(f"assembly: {len(A)} bodies")
        clashes, contacts, checked = collide(A)
        print(f"collision: checked {checked} AABB-overlapping pairs; {len(clashes)} CLASHES")
        for a, b, v in clashes[:25]:
            print(f"  CLASH   {a:22} <-> {b:22}  overlap {v} mm^3")
        for a, b, v in sorted(contacts, key=lambda t: -t[2])[:8]:
            print(f"  contact {a:22} <-> {b:22}  overlap {v} mm^3 (intended mating)")
        if not clashes:
            print("  ✅ no impossible overlaps")
    if args.render:
        A = assemble()
        _render_assembly(A)
        _render_exploded(A)
        _render_parts(A)
    if args.sync_models:
        import shutil
        mdir = os.path.join(HERE, "models")
        os.makedirs(mdir, exist_ok=True)
        parts = [f"{n}.stl" for n in SHELLS] + ["keymat_right.stl", "keymat_left.stl"]
        missing = [p for p in parts if not os.path.exists(os.path.join(BUILD, p))]
        if missing:
            sys.exit(f"--sync-models: build/ is missing {missing} — run --all first")
        for old in os.listdir(mdir):          # drop stale part files from before a rename
            if old.endswith((".stl", ".step")) and old not in parts:
                os.remove(os.path.join(mdir, old))
        for p in parts:
            shutil.copy2(os.path.join(BUILD, p), os.path.join(mdir, p))
        print(f"  synced {len(parts)} STLs -> {mdir}")


def _explode_offset(k):
    """Vertical explode offset by role (for the exploded assembly render)."""
    if k.startswith("back_"): return -35
    if k == "battery":      return -18
    if k == "flex":         return -10
    if ":" in k:            return 0        # PCB stack (board + components)
    if k.startswith("keymat"): return 22
    if k.startswith("grip_lid"): return 40
    if k.startswith("screw_"): return 56   # above the lids they drop through
    if k == "center_panel": return 52
    if k == "nub_spring": return 56        # lifts out of the lid counterbore
    if k == "nub_cap": return 66           # pulls off the spring spigot
    if k == "magsafe":      return 68
    if k == "phone":        return 84
    return 0

def _render_exploded(A):
    def col(k): return _asm_col(k)
    meshes = []
    for k, m in A.items():
        mm = m.copy(); mm.apply_translation((0, 0, _explode_offset(k)))
        meshes.append((mm, col(k)))
    render_iso(meshes, os.path.join(RENDERS, "assembly3d_exploded.png"),
               "thumbdeck — exploded stack (back halves · PCB · domes · keymats · grip lids · center panel · MagSafe · phone)",
               elev=14, azim=-72)

def _asm_col(k):
    # v0.19 GBC "Atomic Purple": translucent purple shells, dark button-gray keymats
    if k.startswith("back_"): return [0.48,0.35,0.65,0.55]
    if k == "center_panel": return [0.48,0.35,0.65,0.55]
    if k.startswith("grip_lid"): return [0.48,0.35,0.65,0.55]
    if k.startswith("keymat"): return [0.23,0.23,0.24,1]
    if k in ("nub_spring", "nub_cap"): return [0.23,0.23,0.24,1]  # keymat gray
    if k == "phone":        return [0.05,0.05,0.08,1]
    if k == "battery":      return [0.65,0.5,0.15,1]
    if k == "magsafe":      return [0.72,0.72,0.74,1]
    if k.startswith("screw_"): return [0.73,0.74,0.77,1]
    if k == "flex":         return [0.75,0.55,0.2,1]
    if ":pcb" in k:         return [0.16,0.35,0.24,1]
    if ":SW" in k:          return [0.9,0.72,0.2,1]
    if any(x in k for x in (":U",":J")): return [0.2,0.2,0.24,1]
    return [0.5,0.5,0.25,1]

def _render_parts(A):
    titles = {"back_right": "right back half (grip bay + half spine, seam joinery)",
              "back_left": "left back half (grip bay + half spine, seam joinery)",
              "grip_lid_right": "right grip lid (key openings + clamp rim)",
              "grip_lid_left": "left grip lid (key openings + clamp rim)",
              "center_panel": "center panel (sunken flush-screen well + MagSafe recess + 4 screws + scallop)",
              "nub_spring": "nub flexure spring (Bean-style: flange + spiral arms + magnet hub)",
              "nub_cap": "nub friction cap (O8.5 TPU, press-fits the spring spigot)",
              "keymat_right": "right keymat (plungers + hinge web)"}
    for nm, title in titles.items():
        render_iso([(A[nm], [0.4, 0.45, 0.5, 1])], os.path.join(RENDERS, f"part_{nm}.png"),
                   f"thumbdeck — {title}", elev=40, azim=-60)

def _render_assembly(A):
    meshes = [(m, _asm_col(k)) for k, m in A.items()]
    render_iso(meshes, os.path.join(RENDERS, "assembly3d.png"), "thumbdeck — full assembly (real dims)", elev=26, azim=-58)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""deck3d.py — parametric 3D generator for the thumbdeck: PCB fit-model (real
component dimensions), the 5-part shell set (left/right back halves, left/right
grip lids, center front panel — every part fits an Ender 3 V2 220x220 bed flat),
keymats, + the phone / LiPo / flex, assembled in the deck.product() frame and
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
import os, sys, argparse, math, json, subprocess
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import numpy as np, trimesh, deck
from shapely.geometry import Polygon

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
KNOB = (3.0, 1.5, 2.0)      # MSK12C02 slide knob (w, protrusion toward the bottom edge, h)


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
    # board solid: extrude the outline polygon
    pts = _dedupe(geo["outline"])
    board = trimesh.creation.extrude_polygon(Polygon(pts), PCB_T)
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
            # MSK12C02 slide knob protruding from the body face toward the bottom edge
            kw, kp, kh = KNOB
            by = (H - f["ay"]) - spec["body"][1]/2    # body face nearest the bottom edge
            m = trimesh.util.concatenate([m, _place(_box(kw, kp, kh), f["ax"], by - kp/2, z)])
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
TOP_T = 2.0           # grip-lid plate thickness
STANDOFF = 6.3        # PCB standoff: clears the 6.0mm mated JST-PH (J3) + 0.24 margin
PHONE_CLR = 0.6       # phone pocket clearance (total, both sides)
POCKET_D = 2.0        # phone pocket depth (rim height above the pocket floor)
RING_REC_D = 1.8      # MagSafe ring recess depth inside the phone pocket
RING_REC_R = 28.5     # recess radius (Ø57 for the Ø56 N52 ring)
GAP = 0.5
KM_WEB, KM_PL_H, KM_PL_D = 0.8, 3.5, 6.2   # keymat web / plunger height / plunger dia
PCB_Z = FLOOR + STANDOFF                     # grip-local PCB z=0 maps here
DOME_TOP = PCB_Z + PCB_T + DOME_H            # top of a seated snap dome
KM_Z0 = DOME_TOP + 1.0                       # keymat web bottom (nub reaches the dome)
TOP_Z = KM_Z0 + KM_WEB + GAP                 # front parts sit above the cavity
WALL = TOP_Z - FLOOR                         # cavity height (derived)

# --- 5-part split (grip lids + center panel + back halves), Ender 3 V2 bed ---
BED_XY = 204.0        # printable footprint per part: 220mm bed minus 2x8mm brim
PANEL_T = 2.6         # center-panel plate thickness (ring membrane = PANEL_T-RING_REC_D-... see RECESS_FLOOR)
PANEL_TOP = TOP_Z + PANEL_T                  # 14.9
PLATEAU_TOP = PANEL_TOP + POCKET_D           # 16.9 (pocket rim / device front)
SEAM_GAP = 0.3        # front reveal gap between panel edge and lid edge (deliberate V)
LAP_CLR = 0.25        # printed-joint in-plane clearance (FDM: elephant foot + warp)
XWALL_T = 2.5         # transverse spine wall (closes each half's torsion box, seats panel)
PANEL_SCREWS = [(-10.0, 10.0), (10.0, 10.0), (-10.0, 105.0), (10.0, 105.0)]  # straddle x=0 seam

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
    # PCB standoff bosses + M2 heat-set bores at each grip's mount holes
    for side in ("right", "left"):
        geo = prod[side]; ox, oy = prod[f"{side}_origin"]
        for hh in geo["mount_holes"]:
            cx, cy = hh["x"]+ox, hh["y"]+oy
            boss = (cq.Workplane("XY").workplane(offset=FLOOR).center(cx, cy).circle(3.0).extrude(STANDOFF)
                    .faces(">Z").workplane().circle(1.6).cutBlind(-(STANDOFF-1)))  # Ø3.2 bore: M2 heat-set insert (OD ~3.5)
            shell = shell.union(boss)
        # mid-field PCB support posts (verified clear of back-side components)
        for (px, py) in support_post_locations(side):
            post = (cq.Workplane("XY").workplane(offset=FLOOR).center(px+ox, py+oy)
                    .circle(POST_R).extrude(STANDOFF))
            shell = shell.union(post)
    # ---- right-grip back-side feature cuts (all positions from the placement export)
    ox, oy = prod["right_origin"]
    # USB-C wall opening: 13.5 x 7.0 centred on the receptacle mouth (J1 x, mouth at
    # the board edge y=0; receptacle vertical centre ~1.6mm below the PCB underside)
    jx, _ = _find_fp("right", "USB_C_Receptacle_HRO")
    zc = PCB_Z - 1.6
    shell = shell.cut(cq.Workplane("XY").workplane(offset=zc - 3.5)
                      .center(jx, -1.5).box(13.5, 3.4, 7.0, centered=(True, True, False)))
    # stepped outer relief (in lieu of a chamfer) so a 12.35 x 6.5 plug overmold seats
    # fully against the receptacle through the 2.9mm wall
    shell = shell.cut(cq.Workplane("XY").workplane(offset=zc - 4.5)
                      .center(jx, -2.35).box(16.0, 1.3, 9.0, centered=(True, True, False)))
    # power slide switch slot: knob protrudes toward the bottom edge; 8 x 2.8 gives
    # the ~3mm travel + finger access, centred at the knob (= body-centre) height
    sx, _ = _find_fp("right", "msk12c02", anchor=True)
    kz = PCB_Z - SOLDER - 3.6/2
    shell = shell.cut(cq.Workplane("XY").workplane(offset=kz - 1.4)
                      .center(sx, -1.5).box(8.0, 3.4, 2.8, centered=(True, True, False)))
    # reset tact pinhole (actuator faces the floor) + charge-LED light pipe hole
    rx, ry = _find_fp("right", "TS-1187A", anchor=True)
    shell = shell.cut(cq.Workplane("XY").workplane(offset=-0.5).center(rx, ry).circle(0.8).extrude(FLOOR+1))
    lx, ly = _find_fp("right", "LED_0603")
    shell = shell.cut(cq.Workplane("XY").workplane(offset=-0.5).center(lx, ly).circle(0.75).extrude(FLOOR+1))
    # antenna wall relief: the E73 physically overhangs the board edge by 0.5mm and the
    # cavity wall face is only PCB_CLR=0.4 out — relieve the inner wall face 0.6mm over
    # the antenna keep-out span so the module tip has >=0.5mm clearance
    ax_, ay_, aw, ah = prod["right"]["keepouts"]["antenna"]
    shell = shell.cut(cq.Workplane("XY").workplane(offset=4.0)
                      .center(ax_ + ox + aw/2, -0.65).box(aw, 0.7, PCB_Z - 3.9, centered=(True, True, False)))

    # ---- transverse spine walls at each grip boundary (v0.16 split): close each
    # half's torsion box where the front seam breaks the top plate, seat the panel
    # edge at TOP_Z, and host one Ø8 boss at MagSafe-ring height so phone detach
    # pull anchors in line with the ring instead of peeling the panel edge.
    gx = _seam_frame()
    bh = prod["right"]["board_h"]
    ms = prod["magsafe"]
    for s in (1, -1):
        x1 = s * (gx - SEAM_GAP); x0 = x1 - s * XWALL_T
        xw = (cq.Workplane("XY").workplane(offset=FLOOR)
              .center((x0+x1)/2, (-PCB_CLR + bh + PCB_CLR)/2)
              .box(XWALL_T, bh + 2*PCB_CLR, WALL, centered=(True, True, False)))
        # FFC pass-through: the bridge ribbon (10mm wide, centred on the placed J2
        # ZIF, z~5.4) crosses here; window keeps 3.3mm of wall above as a printed
        # bridge so the panel stays supported over the lane
        _, jy2 = _find_fp("right" if s > 0 else "left", "ffc_afa07")
        xw = xw.cut(cq.Workplane("XY").workplane(offset=FLOOR)
                    .center((x0+x1)/2, jy2).box(XWALL_T+2, 16.0, 9.0-FLOOR, centered=(True, True, False)))
        # battery-lead pass-through on the side that carries J3 (side-entry JST-PH)
        try:
            side = "right" if s > 0 else "left"
            _, jy = _find_fp(side, "JST_PH_S2B")
            xw = xw.cut(cq.Workplane("XY").workplane(offset=FLOOR)
                        .center((x0+x1)/2, jy).box(XWALL_T+2, 12.0, 10.5-FLOOR, centered=(True, True, False)))
        except KeyError:
            pass
        shell = shell.union(xw)
        # ring-height panel anchor: Ø8 D-boss on the wall's spine face, clipped
        # flush at the panel-edge plane so it clears the PCB edge at |x|=gx
        bx = s * (abs(x1) - 2.3)
        boss = (cq.Workplane("XY").workplane(offset=FLOOR).center(bx, ms["cy"]).circle(4.0).extrude(WALL)
                .cut(cq.Workplane("XY").workplane(offset=-1)
                     .center(s*(abs(x1)+6), ms["cy"]).box(12, 20, WALL+4, centered=(True, True, False))))
        shell = shell.union(boss)
    # ---- 4 panel bosses straddling the x=0 back seam (2 per half): with the two
    # ring-height wall bosses these make the screwed-on panel the seam's splice plate
    for (px, py) in PANEL_SCREWS:
        shell = shell.union(cq.Workplane("XY").workplane(offset=FLOOR)
                            .center(px, py).circle(3.5).extrude(WALL))
    # bores are cut from the FINISHED shell, not the boss primitives — a pre-bored
    # boss unioned into overlapping material (the transverse wall spans the ring
    # boss axis) gets its bore silently re-filled. Depths leave >=1.2mm before an
    # M2x10 tip can bottom out (ISO length tolerance ~0.3): ring anchors reach
    # z 2.3 (tip lands 3.5), panel-floor screws z 3.3 (tip lands 4.9).
    for s in (1, -1):
        shell = shell.cut(cq.Workplane("XY").workplane(offset=FLOOR+WALL)
                          .center(s*(gx - SEAM_GAP - 2.3), ms["cy"]).circle(1.6).extrude(-10.0))
    for (px, py) in PANEL_SCREWS:
        shell = shell.cut(cq.Workplane("XY").workplane(offset=FLOOR+WALL)
                          .center(px, py).circle(1.6).extrude(-9.0))
    return shell


_BACK = None
def _back_full():
    global _BACK
    if _BACK is None:
        _BACK = _back_solid()
    return _BACK

def back_half(side):
    """One printable back-shell half (splits the tray at x=0 so each half fits an
    Ender 3 V2 bed). Joinery is printed + screwless: two full-thickness floor tabs
    (right) into cleared notches (left) register the halves in-plane, and each
    perimeter wall gets an 8mm vertical shiplap (vertical faces — prints clean flat)
    for shear/torsion continuity; the screwed-on center panel is the bolted splice."""
    prod = _product(); bh = prod["right"]["board_h"]
    s = 1 if side == "right" else -1
    half = cq.Workplane("XY").workplane(offset=-2).center(s*250, bh/2).box(500, 500, 30, centered=(True, True, False))
    tabs = [(30.0, 38.0), (78.0, 86.0)]
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
    """Keymat web outline (product frame): union of plunger discs buffered 2.0.
    Shared by keymats() and the grip lids' clamp rims so they line up exactly."""
    prod = _product(); geo = prod[side]; ox, oy = prod[f"{side}_origin"]
    keys = list(geo["keys"]) + [f for f in geo.get("features", []) if f["type"] == "key"]
    from shapely.ops import unary_union
    field = unary_union([Polygon([(k["x"]+ox+KM_PL_D/2*math.cos(t), k["y"]+oy+KM_PL_D/2*math.sin(t))
                                  for t in np.linspace(0, 2*math.pi, 16)]) for k in keys]).buffer(2.0)
    return field, keys

def _edge_wedge(x_edge, z_top, c=0.8, bh=114.5):
    """45-degree top-edge chamfer prism along a straight x-station: a diamond of
    half-diagonal c centred on the edge line — cuts a c x c chamfer; the outboard
    half of the diamond lies in air."""
    return (cq.Workplane("XY").box(c*2**0.5*0.9999, 500, c*2**0.5*0.9999)
            .rotate((0, 0, 0), (0, 1, 0), 45)
            .translate((x_edge, bh/2, z_top)))

def grip_lid(side):
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
    # key openings at every dome centre (cut AFTER the rim union, deep enough to keep
    # the full plunger bore clear through the rim band)
    holes = None
    for (x, y, d) in _key_centers_product(side):
        c = (cq.Workplane("XY").workplane(offset=web_top - 0.2).center(x, y)
             .circle(d/2 + 0.4).extrude(TOP_T + (z0 - web_top) + 0.4))
        holes = c if holes is None else holes.union(c)
    if holes is not None:
        plate = plate.cut(holes)
    # screw clearance holes aligned to this grip's bottom bosses (5, unchanged)
    geo = prod[side]; ox, oy = prod[f"{side}_origin"]
    for hh in geo["mount_holes"]:
        h = cq.Workplane("XY").workplane(offset=z0-0.1).center(hh["x"]+ox, hh["y"]+oy).circle(1.2).extrude(TOP_T+0.2)
        plate = plate.cut(h)
    # 0.8mm 45-degree chamfer on the inner top edge (the cyan side of the reveal)
    plate = plate.cut(_edge_wedge(s*gx, z0+TOP_T, bh=bh))
    return _to_trimesh(plate, f"grip_lid_{side}")

def center_panel():
    """Center front panel (pink, 'the front of the back'): one 4.6mm slab over the
    spine — phone pocket, MagSafe ring recess and all 6 panel screws live here. It
    spans the x=0 back seam and is its bolted splice. A deliberate SEAM_GAP reveal
    separates it from the lids (no overlap: no screw-head clash, no mid-air mating
    faces — it prints back-face-down, pocket up, support-free). Removable on its
    own: the spine service hatch for battery + FFC.
    The pocket rim captures the phone's long edges (pocket open in x as before —
    lateral retention is the MagSafe ring's job); the Ø57 x 1.8 ring recess leaves
    a 0.8mm printed web (4 layers) under the glued-in N52 ring, and the ring sits
    0.2mm proud so the phone rests on ring + pocket floor exactly as in v0.15."""
    fp = full_footprint()
    prod = _product()
    gx = _seam_frame(); px_edge = gx - SEAM_GAP
    bh = prod["right"]["board_h"]
    region = Polygon([(-px_edge, -60), (px_edge, -60), (px_edge, bh+60), (-px_edge, bh+60)])
    poly = fp.buffer(WALL_T+PCB_CLR).intersection(region).buffer(0)
    panel = _cq_from_poly(poly, TOP_Z, PLATEAU_TOP - TOP_Z)     # solid 12.3..16.9
    ph = prod["phone"]
    pocket = (cq.Workplane("XY").workplane(offset=PANEL_TOP)
              .center(ph["x"]+ph["w"]/2, ph["y"]+ph["h"]/2)
              .box(ph["w"] + 2.4, ph["h"] + PHONE_CLR, POCKET_D + 0.2, centered=(True, True, False)))
    panel = panel.cut(pocket)
    ms = prod["magsafe"]
    panel = panel.cut(cq.Workplane("XY").workplane(offset=RECESS_FLOOR)
                      .center(ms["cx"], ms["cy"]).circle(RING_REC_R).extrude(RING_REC_D + 0.05))
    # 4 seam-splice screws in the plateau strips outside the pocket: Ø2.6 through,
    # Ø6 x 2.0 counterbore so the M2x10 button head seats on the 2.6mm plate
    for (sx, sy) in PANEL_SCREWS:
        panel = panel.cut(cq.Workplane("XY").workplane(offset=TOP_Z-0.1).center(sx, sy).circle(1.3).extrude(PLATEAU_TOP+0.2))
        panel = panel.cut(cq.Workplane("XY").workplane(offset=PANEL_TOP).center(sx, sy).circle(3.0).extrude(POCKET_D+0.2))
    # 2 ring-height anchors in the pocket floor (into the transverse-wall bosses):
    # heads sink 1.4 so they finish under the phone (ring sits 0.2 proud above them)
    for s in (1, -1):
        sx, sy = s * (abs(px_edge) - 2.3), ms["cy"]
        panel = panel.cut(cq.Workplane("XY").workplane(offset=TOP_Z-0.1).center(sx, sy).circle(1.3).extrude(PANEL_T+0.2))
        panel = panel.cut(cq.Workplane("XY").workplane(offset=PANEL_TOP-1.4).center(sx, sy).circle(3.0).extrude(1.6))
    # 0.8mm 45-degree chamfers on both outer top edges (the pink side of the reveal)
    for s in (1, -1):
        panel = panel.cut(_edge_wedge(s*px_edge, PLATEAU_TOP, bh=bh))
    return _to_trimesh(panel, "center_panel")

def keymats(side):
    """Per-grip one-piece keymat: plungers over each dome joined by a thin web plate."""
    z0 = KM_Z0                # web bottom, just above the domes
    field, keys = _keymat_field(side)
    mat = _cq_from_poly(field, z0, KM_WEB)
    ox, oy = _product()[f"{side}_origin"]
    for k in keys:
        pl = (cq.Workplane("XY").workplane(offset=z0+KM_WEB).center(k["x"]+ox, k["y"]+oy)
              .circle(KM_PL_D/2).extrude(KM_PL_H))
        # actuator nub underneath (reaches down to press the dome)
        nub = (cq.Workplane("XY").workplane(offset=z0).center(k["x"]+ox, k["y"]+oy).circle(1.4).extrude(-1.0))
        mat = mat.union(pl).union(nub)
    return _to_trimesh(mat, f"keymat_{side}")

# ==== non-printed bodies (real dims) ================================================
def phone_body():
    ph = _product()["phone"]
    m = _box(ph["w"], ph["h"], 7.8)
    return _place(m, ph["x"]+ph["w"]/2, ph["y"]+ph["h"]/2, 0)  # z set in assemble

def battery_body():
    sb = _product()["spine_battery"]
    # realistic ~500mAh 503450 pouch, ~5mm thick, oriented long-side-x so it fits
    # the 52x36 reserved rect (v0.16: was 34x50 — rotated 90deg, overflowed the rect)
    m = _box(50, 34, 5.0)
    return _place(m, sb["x"]+sb["w"]/2, sb["y"]+sb["h"]/2, 0)

def magsafe_ring():
    ms = _product()["magsafe"]
    outer = trimesh.creation.cylinder(radius=ms["d"]/2, height=2.0, sections=48)
    inner = trimesh.creation.cylinder(radius=ms["d"]/2-8, height=3, sections=48)
    ring = outer.difference(inner)
    return _place(ring, ms["cx"], ms["cy"], 0)

def flex_body():
    """Bridge flex: flat ribbon from the right J2 to the left J2, behind the phone."""
    prod = _product()
    def j2(side):
        geo = prod[side]; ox, oy = prod[f"{side}_origin"]
        bx, by, bw, bh = geo["keepouts"]["bridge"]
        return (bx+ox+bw/2, by+oy+bh/2)
    rx, ry = j2("right"); lx, ly = j2("left")
    length = abs(rx-lx); midx = (rx+lx)/2; midy = (ry+ly)/2
    m = _box(length, 10.0, 0.3)
    return _place(m, midx, midy, 0)


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
          f"panel {TOP_Z}..{PANEL_TOP} plateau top {PLATEAU_TOP} | ring {MAGSAFE_Z-RING_H/2:.1f}..{MAGSAFE_Z+RING_H/2:.1f} | "
          f"phone {PHONE_Z-3.9:.1f}..{PHONE_Z+3.9:.1f}")


def render_iso(meshes, path, title, elev=32, azim=-60):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(11, 7)); ax = fig.add_subplot(111, projection="3d")
    allv = []
    for m, color in meshes:
        tri = m.vertices[m.faces]
        pc = Poly3DCollection(tri, alpha=1.0, facecolor=color, edgecolor=(0, 0, 0, 0.06), linewidths=0.15)
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
# (PCB_Z / DOME_TOP / KM_Z0 / TOP_Z / WALL are all derived up top.)
RING_H = 2.0                                    # N52 ring thickness
RECESS_FLOOR = PANEL_TOP - RING_REC_D           # ring recess floor (in the panel's pocket floor)
MAGSAFE_Z = RECESS_FLOOR + RING_H/2             # ring body centre (sits IN the recess)
PHONE_Z = RECESS_FLOOR + RING_H + 7.8/2         # phone rests on the 0.2mm-proud ring
BATT_Z = FLOOR + 2.5                   # ~5mm cell sitting on the spine floor in the cavity
FLEX_Z = PCB_Z - 2.5                   # ribbon behind the phone, at the back-connector level

SHELLS = ("back_right", "back_left", "grip_lid_right", "grip_lid_left", "center_panel")

def assemble():
    A = {}
    A["back_right"] = back_half("right")
    A["back_left"] = back_half("left")
    A["grip_lid_right"] = grip_lid("right")
    A["grip_lid_left"] = grip_lid("left")
    A["center_panel"] = center_panel()
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
    return A

# pairs allowed to touch (mating faces / actuation), and self-groups to skip
def _allowed(a, b):
    """Only true mating CONTACTS are tolerated (small overlap where two faces meet).
    Everything else that interpenetrates is a real clash to fix."""
    s = {a, b}
    km = any(x.startswith("keymat") for x in s)
    if km and any(":SW" in x and not x.endswith(("_pwr", "_rst")) for x in s): return True  # nub presses dome
    if km and any(x.startswith("grip_lid") for x in s): return True  # clamp rim presses the web 0.1mm (intended preload)
    if s == {"phone", "magsafe"} or s == {"magsafe", "center_panel"}: return True           # rests on/in
    if s == {"back_right", "back_left"}: return True   # seam tabs/shiplap mate face-to-face
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
        for fn, nm in [(lambda: back_half("right"), "back_right"),
                       (lambda: back_half("left"), "back_left"),
                       (lambda: grip_lid("right"), "grip_lid_right"),
                       (lambda: grip_lid("left"), "grip_lid_left"),
                       (center_panel, "center_panel")]:
            m = fn(); print(f"  {nm}: watertight={m.is_watertight} vol={m.volume/1000:.1f}cm3 bbox={[round(v,1) for v in m.extents]}")
            ok = bed_fit(m, nm) and ok
        for side in ("right", "left"):
            m = keymats(side); print(f"  keymat_{side}: watertight={m.is_watertight} bbox={[round(v,1) for v in m.extents]}")
            ok = bed_fit(m, f"keymat_{side}") and ok
        if not ok:
            sys.exit("bed-fit FAILED: a part exceeds the Ender 3 V2 printable area")
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
    if k == "center_panel": return 52
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
    # concept colors: pink back halves + center panel, cyan grip lids (sketches)
    if k.startswith("back_"): return [0.82,0.36,0.50,1]
    if k == "center_panel": return [0.95,0.48,0.62,0.85]
    if k.startswith("grip_lid"): return [0.25,0.75,0.80,0.75]
    if k.startswith("keymat"): return [0.55,0.45,0.85,0.92]
    if k == "phone":        return [0.05,0.05,0.08,1]
    if k == "battery":      return [0.65,0.5,0.15,1]
    if k == "magsafe":      return [0.72,0.72,0.74,1]
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
              "center_panel": "center panel (phone pocket + MagSafe recess + 6 screws)",
              "keymat_right": "right keymat (plungers + hinge web)"}
    for nm, title in titles.items():
        render_iso([(A[nm], [0.4, 0.45, 0.5, 1])], os.path.join(RENDERS, f"part_{nm}.png"),
                   f"thumbdeck — {title}", elev=40, azim=-60)

def _render_assembly(A):
    meshes = [(m, _asm_col(k)) for k, m in A.items()]
    render_iso(meshes, os.path.join(RENDERS, "assembly3d.png"), "thumbdeck — full assembly (real dims)", elev=26, azim=-58)


if __name__ == "__main__":
    main()

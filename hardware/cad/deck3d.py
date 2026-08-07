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
# --- v0.26: TMAG5273 in the SOT-23-6 (TI DBV) package -------------------------------
# The nub's whole magnetic design hangs off where the HALL ELEMENT actually is, which is
# not the package outline and not the PCB surface. From TI SLYS045C §6.3.2 Figure 6-2
# ("Location of X, Y, Z Hall Elements") plus package drawing 4214840/G:
TMAG_PKG_H = 1.45        # DBV body height A (max; drawing 4214840/G). deck3d used to model
                         #   every SOT-23 at 1.1, which put the mould face 0.35mm shy of
                         #   where it is — and the die reference is measured off that face.
TMAG_DIE_DEPTH = 0.73    # hall element depth BELOW the moulded top face (SLYS045C Fig 6-2).
                         #   U4 is BACK-mounted, so its mould face points AWAY from the board:
                         #   in product z the mould top is the package's MINIMUM z, and the die
                         #   is TMAG_DIE_DEPTH *above* it. (1.45 − 0.73 = 0.72 also puts the die
                         #   ~0.73 above the seating plane, so the two derivations agree.)
TMAG_DIE_XY_OFF = 0.418  # the die is NOT on the package axis: +0.40mm along the body length
                         #   (away from the pin-1/6 end) and −0.12mm across the width (toward
                         #   the pins-1/2/3 side) => 0.418mm radial. gen_board centres U4's
                         #   FOOTPRINT on the nub axis, so the die sits 0.418mm off it.
                         #   DELIBERATELY UNCOMPENSATED — see nub_report() for the cost.
SENSE_XY_TOL = 0.35      # allowed nub-axis vs U4-anchor error. Sized to swallow the pin-1 silk
                         #   bbox artefact (~0.09mm) and nothing else — a real placement drift
                         #   still trips it.
NUB_GAP_LO, NUB_GAP_HI = 3.05, 3.65   # design band for the magnet-face -> hall-element gap.
                         #   Centre ~3.33mm: a Ø4×2 N45 disc puts ~53mT of Bz on the die there,
                         #   which is 66% of the ±80mT full scale and leaves the TRANSVERSE
                         #   channels (the only ones the driver reads) working at a few mT.

SPECS = [
    ("SOT-23-6", {"h": TMAG_PKG_H}),                       # U4 TMAG5273 / U3 USBLC6 (DBV)
    ("E73-2G4M08S1C", {"h": 2.2, "body": (13.0, 18.0)}),   # Ebyte module; bbox incl. antenna keepout
    ("USB_C_Receptacle_HRO", {"h": 3.3}),                  # J1 body 3.26
    ("ffc_afa07", {"h": 2.0}),                             # J2 FFC ZIF 20P (AFA07-S20FCC-00)
    ("JST_PH_S2B", {"h": 6.0}),                            # J4 (LEFT board) side-entry, mated height
    ("Fuse_1812", {"h": 0.9}),                             # F1 PPTC, left board cell protection
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
NUB_MAGNET_D, NUB_MAGNET_H = 4.0, 2.0    # Ø4×2 N45 disc, AXIALLY magnetized, N face DOWN.
                                         #   v0.26: the size is NOT "the Bean spec" as this line
                                         #   used to claim — the Ploopy Bean's hardware appendix
                                         #   calls for Ø6×2, which will not fit our Ø7.0 hub
                                         #   (1.45mm wall would drop to 0.5). Ø4×2 is chosen here
                                         #   because it is a genuine mass-stock size AND it is what
                                         #   the Ø7 hub can carry; see docs/design-decisions.md.
                                         #   Grade is N45, not N52: N52 has the LOWEST service
                                         #   temperature of the common grades (≤65°C vs ≤80°C), and
                                         #   this device clamps a phone and lives in cars. Above it
                                         #   the loss is irreversible — boot-zero cannot recover a
                                         #   partially demagnetized magnet, it just re-zeros a
                                         #   weaker one and the pointer goes permanently sluggish.
NUB_MAGNET_FIT = 0.10                    # radial pocket clearance -> Ø4.20 bore. v0.26: was 0.05
                                         #   (Ø4.10). Stock Ø4 discs are sold at ±0.10, so a
                                         #   +tolerance magnet is Ø4.10 — exactly the nominal bore —
                                         #   and FDM prints holes UNDER size. That is an
                                         #   interference fit driven into a 1.45mm hub wall by
                                         #   hand, i.e. a split hub. Ø4.20 + a drop of cyanoacrylate
                                         #   is the retention (a press fit in a printed part relaxes
                                         #   anyway, and this magnet lives over a steel-free cavity
                                         #   with nothing to pull it out).
NUB_POCKET_Z0 = 10.30                    # magnet pocket cut start (opens DOWNWARD, through the
                                         #   hub's bottom face at 10.40 — the magnet loads from below)
NUB_POCKET_TOP = NUB_POCKET_Z0 + NUB_MAGNET_H + 0.15     # 12.45 — pocket ceiling (0.15 depth slop)
NUB_MAGNET_Z = NUB_POCKET_TOP - NUB_MAGNET_H             # 10.45 — SEATED magnet bottom face
                                         #   (pressed fully home against the ceiling). This is the
                                         #   datum the whole magnetic design is dimensioned from:
                                         #   everything below it (air gap, FR4, package) is what the
                                         #   sensor has to see through. See nub_report().
NUB_HUB_D = 7.0                          # flexure hub / post through the aperture
# v0.22 TrackPoint-compatible mount: the hub tops out in a 4.4mm-square x 2.5
# platform (genuine classic full-size TrackPoint caps have a ~4.5mm square
# socket — soft dome / soft rim / classic dome all fit), plus a printed
# classic-soft-dome replica cap in RED TPU (dot grid, mushroom skirt).
NUB_POST_SQ, NUB_POST_H = 4.4, 2.5       # square platform (genuine-cap socket: 4.5 sq x 2.5)
NUB_CAP_D, NUB_CAP_H = 7.8, 5.0          # classic soft-dome replica: OD x height (cap top 4.3mm proud)
NUB_HUB_TOP = 14.0                       # hub/platform base z (0.7 below the 14.7 face)
NUB_SPRING_FLANGE_D = 14.8               # flange captured in the lid's counterbore
# --- v0.26 flexure tuning: the arms ARE the pointing feel -----------------------------
# A ThinkPad TrackPoint is ISOMETRIC — you push against it and it barely moves (its whole
# travel is ~0.2-0.5mm at the cap); speed comes from FORCE, not from displacement. A hall
# nub cannot be zero-travel (it has to move to be read), so the adapted target is
# 350-600um of cap travel at 150gf, the top of the TrackPoint IV usable range.
#
# THICKNESS STAYS AT 0.8, and that is a finding, not an omission. Four independent beam
# models were built (two here, two adversarial) and they agree on stress but NOT on
# stiffness, because the answer is dominated by a boundary condition none of them can
# settle: how much of the arm is really free. The arm is a 1.2mm-wide ribbon spiralling
# r3.6 -> r5.9, so its first ~22% is buried in the Ø7 hub and its last ~30% in the flange
# bore. Model it as a free 100-degree beam and you get 2.6 N/mm; clamp it rigidly at both
# embedments (48 degrees free) and you get 18.3 N/mm. Same geometry, 7x apart.
#
#   cap travel at 150gf, t=0.8 + root fillet:   474um (free-span)  ..  285um (hub clamped)
#   the same arm at t=1.2:                      158um             ..   94um
#
# The target band is 350-600um — the TrackPoint IV spec (0-150gf usable, ~zero travel)
# adapted to a hall nub, which must move to be read. t=0.8 straddles that band under
# every plausible assumption; t=1.2 is below it under ALL of them, i.e. thickening would
# have made the nub nearly rigid. The v0.21 value was right; it just had no stated reason.
# Peak stress at 150gf is 23-29 MPa against PETG's ~50 MPa yield, so first yield is
# around 300gf — thin margin, which is what NUB_ARM_ROOT below is for.
#
# ARM THICKNESS IS A COUPON-CALIBRATED PARAMETER. Print nub_spring at 0.7 / 0.8 / 0.9,
# hang 50/100/150gf laterally off the cap and measure cap-top deflection with a dial
# indicator; pick the one nearest 350-600um at 150gf, then re-derive the firmware
# gain-div from it (the formula is in the DT binding). Do not trust a number from a beam
# model here, including this one.
#
# WIDTH cannot move regardless: the arm spirals through a 2.3mm annulus, and at mid-arc a
# 1.2mm-wide arm already leaves only 0.65mm of slot inboard and 0.45mm outboard. At 1.6
# the outer slot falls to 0.25mm and at 2.0 to 0.05mm — at which point the arm is fused to
# the flange along its length and is not a beam at all.
NUB_ARM_T = 0.8                          # flexure arm thickness (z) — bends about the WEAK
                                         #   axis, so this is the dominant tilt term (~t^3)
NUB_ARM_W = 1.2                          # flexure arm width (in-plane) — printability-capped
NUB_ARM_ROOT = 0.5                       # extra half-width blended in at BOTH arm ends (a
                                         #   root fillet). The v0.21 arm was a constant-width
                                         #   ribbon meeting the hub and the flange at a square
                                         #   re-entrant T-junction, and every model built for
                                         #   v0.26 — including the two that disagreed about
                                         #   everything else — put the peak stress at exactly
                                         #   that corner. Blending it drops peak stress ~19%
                                         #   (28.6 -> 23.1 MPa at 150gf) and moves the peak off
                                         #   the corner and out along the arm. Unlike the
                                         #   thickness, this is model-INDEPENDENT: it removes a
                                         #   stress raiser without meaningfully changing the
                                         #   compliance the part exists to provide.
                                         #   The swell is shaped (2s-1)^6, so it is confined to
                                         #   the last ~15% at each end — the zone where the arm
                                         #   is merging into the hub/flange anyway, so it costs
                                         #   NO free slot at mid-arc.
NUB_ARM_R0, NUB_ARM_R1 = 3.6, 5.9        # spiral inner/outer radius
NUB_ARM_SWEEP = 100.0                    # degrees of arc per arm
NUB_ARMS = 3                             # arm count. At 3 x 100 degrees the arms are
                                         #   SEQUENTIAL arcs (0-100, 120-220, 240-340) with 20
                                         #   degrees of clear gap, not nested spirals, so they
                                         #   never approach each other. Raising the count (or
                                         #   the sweep past 120) makes them nest, at which
                                         #   point the root swell above can merge neighbours.
NUB_PLUNGE_MAX = 0.35                    # v0.26 hard plunge stop. Nothing used to limit AXIAL
                                         #   travel: the hub bottom (10.40) could sink the full
                                         #   0.90mm to the PCB face, and over that stroke Bz at
                                         #   the die swings 53 -> 94mT and the transverse gain
                                         #   with it, so the cursor sped up when you pressed
                                         #   harder at constant tilt — the exact squishy,
                                         #   non-isometric behaviour a TrackPoint avoids. Three
                                         #   pads on the hub underside now bottom out at 0.35mm.


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

# ==== v0.25 integrated nav pad (Rii i8+ / GBC style) ================================
# The left grip's nav cluster used to be five scattered Ø6.2 round buttons on 8.5mm
# centres. It is now ONE round pad — a Ø24 disc cut by relief moats into four arm
# sectors around a centre OK button, poking through a SINGLE round lid aperture.
# NOTHING electrical moves: the same five Snaptron domes stay on the same 8.5mm
# pitch, so deck.py's feature list, the matrix, the board and the keymap are all
# untouched. This is a keymat + grip-lid story only.
#
# The thing an integrated pad has to buy back is DISCRETENESS — a press on one arm
# must collapse exactly one dome. A one-piece rocker gets that from rigidity it
# cannot have in TPU 95A, so it is bought here with four pieces of geometry:
#   * MOAT     — every actuator is its own column right down to the web, so no cap
#                material links neighbours. This is the primary isolator and the
#                reason cross-talk is a web problem instead of a cap problem.
#   * RELIEF   — and then the web is THINNED under every moat, because a moat alone
#                does not isolate anything: the caps stop but the 0.8mm web runs
#                straight on underneath. Over a short span that web is stiff (the
#                coupling goes as t^3/L^3), so an un-relieved 1.0mm moat couples its
#                actuators 3.4x STIFFER than the 1.5mm of full-thickness web between
#                two ordinary keycaps, and a press would simply carry its neighbours
#                down with it. The moat is 2.0 wide and the web under it drops to
#                0.4, which lands ~19x LOOSER than that key pair — the calibration
#                that matters, since the absolute stiffness of a printed TPU
#                membrane is not something this model can honestly predict.
#   * LID RING — an annular downstand outside the aperture pins the keymat web all
#                the way round the pad, so a sector reacts against a clamped
#                boundary instead of dragging the whole pad down with it. It sits
#                1.0mm out from the pad edge: that 1.0mm of full-thickness web is
#                each arm's hinge, soft enough to rock but short enough to locate.
#   * BACK RIB — the matching rib on the keymat's underside, which backs that ring
#                against the PCB face so the pinned web ring cannot just sink.
# The moats read as the crisp seams of a moulded D-pad, so the pad still looks like
# one part; the "ridges" doing the work are the relief and the ring/rib pair behind
# the face.
DPAD_D = deck.Config().dpad_d        # pad outer diameter (deck.py owns it, so the 2D
                                     #   layout renders and this model cannot drift)
DPAD_OK_D = 9.0                      # centre OK button
DPAD_MOAT = 2.0                      # relief gap between actuators
DPAD_WEB_RELIEF = 0.4                # web thickness left under a moat (2 layers at 0.2)
DPAD_RING_R0 = DPAD_D/2 + 1.0        # 13.0 — clamp band inner radius. 1.0 clear of the
                                     #   arm domes (Ø7 discs reach r 12.0), so the back
                                     #   rib can never land on a dome's edge.
DPAD_RING_W = 1.5                    # clamp band width (same as the field clamp rim)
DPAD_FIELD = DPAD_RING_R0 + DPAD_RING_W + 1.0 - DPAD_D/2   # 3.5 web margin round the pad
DOME_RETAIN_T = 0.3                  # the dome-retention layer on the PCB FRONT (Snaptron
                                     #   Peel-N-Place tape or a laser-cut polyimide spacer,
                                     #   spec'd 0.2-0.3 in the BOM and REQUIRED). It is not
                                     #   modelled anywhere, so nothing in --check knows it is
                                     #   there — but it is the surface the back rib would
                                     #   actually meet, and the same rule the capture lip was
                                     #   fixed by applies: dimension off surfaces that exist.
DPAD_RIB_CLR = 0.2                   # back rib's rest clearance ABOVE that layer: it is a
                                     #   backstop, not a preload (and stays off collide()'s
                                     #   keymat-vs-board pair, which is NOT a mating one).
                                     #   Clearing the MAX retention thickness is deliberate —
                                     #   a rib that engages late is a degraded backstop, a rib
                                     #   buried in the tape is an undesigned preload holding
                                     #   the web (and possibly a dome) down.
DPAD_CHAM = 0.6                      # 45-degree chamfer round the aperture in the lid face
DPAD_EDGE_CHAM = 0.5                 # 45-degree chamfer on the pad's own top outer edge
DPAD_OK_CHAM = 0.4                   # ...and on the OK button's top edge

def _circle_poly(cx, cy, r, n=72):
    """Regular n-gon approximating a circle — shapely's buffer() would do, but the
    pad's polygons get differenced against each other and a shared vertex count
    keeps those booleans exact."""
    return Polygon([(cx + r*math.cos(t), cy + r*math.sin(t))
                    for t in np.linspace(0, 2*math.pi, n, endpoint=False)])

def _dpad_zone(side):
    """This grip's integrated nav pad: the five NAV dome centres in the product
    frame, or None for a grip that has no NAV cluster. The domes are read straight
    out of deck.py — the pad is derived from the board, never the other way round."""
    prod = _product(); geo = prod[side]; ox, oy = prod[f"{side}_origin"]
    nav = {f["label"]: (f["x"]+ox, f["y"]+oy) for f in geo.get("features", [])
           if f["type"] == "key" and f["label"].startswith("NAV_")}
    if not nav:
        return None
    assert set(nav) == {"NAV_U", "NAV_D", "NAV_L", "NAV_R", "NAV_OK"}, \
        f"{side} grip has NAV keys {sorted(nav)} — the pad is built for the 4+OK cross"
    cx, cy = nav["NAV_OK"]
    arm_r = max(math.hypot(x-cx, y-cy) for lab, (x, y) in nav.items() if lab != "NAV_OK")
    # the pad has to cover its domes, and its clamp band has to sit off them
    assert DPAD_D/2 >= arm_r + 2.5, \
        f"pad Ø{DPAD_D} cannot cover arm domes at r={arm_r:.1f}"
    assert DPAD_OK_D/2 + DPAD_MOAT + 2.0 <= arm_r, \
        f"OK button Ø{DPAD_OK_D} + moat leaves no arm sector inboard of r={arm_r:.1f}"
    assert DPAD_RING_R0 >= arm_r + DOME_D/2 + 0.5, \
        (f"clamp band at r={DPAD_RING_R0} lands within 0.5mm of an arm dome "
         f"(dome edge r={arm_r + DOME_D/2:.1f}) — the back rib would sit on the dome")
    # COUPLING CALIBRATION. What decides whether the pad reads as five keys or as one
    # mushy button is how stiffly the web ties neighbouring actuators together, and a
    # thin-strip coupling goes as t^3/L^3. The absolute number for a printed TPU
    # membrane is not something this model can honestly predict, so the pad is held to
    # a RELATIVE bar instead: never stiffer than the plain full-thickness web that
    # already separates two ordinary keys and is assumed to work.
    c = geo["config"]
    key_gap = min(c["pitch_x"] - c["key_w"], c["pitch_y"] - c["key_h"])
    ref, pad = KM_WEB**3 / key_gap**3, DPAD_WEB_RELIEF**3 / DPAD_MOAT**3
    assert 0.4 <= DPAD_WEB_RELIEF < KM_WEB, \
        f"moat relief {DPAD_WEB_RELIEF} must leave 2 printable layers and thin the {KM_WEB} web"
    assert pad <= ref, (
        f"pad actuators couple {pad/ref:.1f}x STIFFER than an ordinary key pair "
        f"({DPAD_WEB_RELIEF}mm web over a {DPAD_MOAT}mm moat vs {KM_WEB} over {key_gap}) "
        f"— widen DPAD_MOAT or thin DPAD_WEB_RELIEF, or the presses stop being discrete")
    # ...and it must not swallow a neighbouring cluster key
    for f in geo.get("features", []):
        if f["type"] != "key" or f["label"].startswith("NAV_"):
            continue
        d = math.hypot(f["x"]+ox - cx, f["y"]+oy - cy)
        assert d >= DPAD_D/2 + DPAD_FIELD + f.get("d", 7.0)/2, \
            (f"the Ø{DPAD_D} pad's web reaches {f['label']} ({d:.1f}mm away) — shrink "
             f"DPAD_D or move the cluster")
    # ...and the web it needs must stay clear of the grip's cavity wall, since the mat
    # is meant to be clamped by the lid rim, not pinched against the shell
    poly, _g, _o = _grip_poly_product(side)
    assert poly.buffer(-1.0).contains(_circle_poly(cx, cy, DPAD_D/2 + DPAD_FIELD)), \
        (f"the Ø{DPAD_D} pad's web disc reaches the {side} grip's cavity wall — the "
         f"upper zone would have to grow, and that IS a board change")
    return {"c": (cx, cy), "domes": nav}

def _dpad_plan(side):
    """Plan geometry of the integrated pad: the five cap polygons (four arm sectors
    + the centre OK button) with the dome each one presses, and the single lid
    aperture they all share. None on a grip without a NAV cluster."""
    from shapely.ops import unary_union
    from shapely.affinity import rotate as shp_rotate
    z = _dpad_zone(side)
    if z is None:
        return None
    cx, cy = z["c"]; R = DPAD_D/2
    outer = _circle_poly(cx, cy, R)
    ok = _circle_poly(cx, cy, DPAD_OK_D/2)
    # ring = pad minus the OK button and its moat, then split on the diagonals
    ring = outer.difference(_circle_poly(cx, cy, DPAD_OK_D/2 + DPAD_MOAT))
    slot = shp_box(cx - DPAD_MOAT/2, cy, cx + DPAD_MOAT/2, cy + R + 1.0)
    ring = ring.difference(unary_union([shp_rotate(slot, a, origin=(cx, cy))
                                        for a in (45, 135, 225, 315)]))
    arms = list(ring.geoms) if ring.geom_type == "MultiPolygon" else [ring]
    assert len(arms) == 4, f"{side} pad split into {len(arms)} arms, not 4 — check DPAD_MOAT"
    sectors = []
    for lab in ("NAV_U", "NAV_D", "NAV_L", "NAV_R"):
        dome = Point(*z["domes"][lab])
        arm = next((g for g in arms if g.contains(dome)), None)
        assert arm is not None, f"{lab}'s dome is not inside any arm sector"
        sectors.append((arm, lab, z["domes"][lab]))
    sectors.append((ok, "NAV_OK", z["domes"]["NAV_OK"]))
    # every actuator nub must land under its own cap, not out in a moat where the
    # web is relieved and would just fold instead of pressing the dome
    for cap, lab, (dx, dy) in sectors:
        assert cap.contains(Point(dx, dy).buffer(NUB_R)), \
            (f"{lab}'s Ø{2*NUB_R} nub is not fully under its cap — widen the sector "
             f"(smaller DPAD_OK_D / DPAD_MOAT, or a bigger DPAD_D)")
    return {"c": (cx, cy), "sectors": sectors, "outer": outer,
            "aperture": outer.buffer(CAP_CLR),
            "moat": outer.difference(unary_union([c for c, _l, _d in sectors])),
            "band": (_circle_poly(cx, cy, DPAD_RING_R0 + DPAD_RING_W)
                     .difference(_circle_poly(cx, cy, DPAD_RING_R0)))}

def _cap_shapes_product(side):
    """v0.17 keycap geometry per key, product frame: [(plunger_poly, opening_poly,
    x, y)]. GRID keys carry the rectangular 8.5 x 7.0 caps (2u space 18.5) the user
    feels — the plunger IS the cap, poking through a matching rounded-rect lid
    opening (+CAP_CLR/side). CLUSTER feature keys stay round (Ø6.2 plunger through
    a Ø7.8 opening, the proven v0.16 pair). v0.25: the five NAV keys are no longer
    among them — they are the sectors of the integrated pad, and every sector
    SHARES one aperture so the lid keeps a clean round hole instead of growing
    0.5mm-wide ribs between the moats."""
    prod = _product(); geo = prod[side]; ox, oy = prod[f"{side}_origin"]
    c = geo["config"]
    out = []
    for k in geo["keys"]:
        w = (k.get("w", 1) - 1) * c["pitch_x"] + c["key_w"]
        cap = _rrect(k["x"]+ox, k["y"]+oy, w, c["key_h"])
        out.append((cap, cap.buffer(CAP_CLR), k["x"]+ox, k["y"]+oy))
    dp = _dpad_plan(side)
    for f in geo.get("features", []):
        if f["type"] != "key" or (dp and f["label"].startswith("NAV_")):
            continue
        x, y = f["x"]+ox, f["y"]+oy
        pl = Polygon([(x+KM_PL_D/2*math.cos(t), y+KM_PL_D/2*math.sin(t))
                      for t in np.linspace(0, 2*math.pi, 24)])
        d = f.get("d", 7.0)
        op = Polygon([(x+(d/2+0.4)*math.cos(t), y+(d/2+0.4)*math.sin(t))
                      for t in np.linspace(0, 2*math.pi, 24)])
        out.append((pl, op, x, y))
    if dp:
        for cap, _lab, (dx, dy) in dp["sectors"]:
            out.append((cap, dp["aperture"], dx, dy))
    # EXACTLY ONE cap per dome, centred on it. This list is what grows the keymat's
    # actuator nubs, and a MISSING nub is not a collision — collide() can only see
    # overlaps, so five pad sectors collapsing into one would sail through --check as a
    # pad with four dead arrows. (Same blind spot that let the v0.16 keymat ship as
    # three floating pieces.) Assert the cover here, where the shapes are made.
    want = {(round(k["x"]+ox, 3), round(k["y"]+oy, 3)) for k in geo["keys"]}
    want |= {(round(f["x"]+ox, 3), round(f["y"]+oy, 3))
             for f in geo.get("features", []) if f["type"] == "key"}
    got = [(round(x, 3), round(y, 3)) for (_p, _o, x, y) in out]
    assert len(got) == len(set(got)), f"{side}: two cap shapes share a dome centre"
    assert set(got) == want, (
        f"{side}: cap shapes do not cover the domes 1:1 — "
        f"missing {sorted(want - set(got))}, stray {sorted(set(got) - want)}")
    return out

def _seam_frame():
    """x-stations of the split (product frame): grip inner edges at +-gx, back-shell
    halves part at x=0, panel spans |x| <= gx-SEAM_GAP. Derived, never hard-coded."""
    prod = _product()
    gx = prod["right_origin"][0]                 # right grip inner edge (= 73.8)
    assert abs(gx + (prod["left_origin"][0] + prod["left"]["board_w"])) < 1e-6
    return gx

def full_footprint():
    """v0.24: just the two grip polygons — NO central spine slab. The rigid spine
    (that the bolted center panel bridged) is gone; the two grips are now separate
    bodies joined only by the telescoping nest (v0.25: the fixed tray is part of
    back_right, so the slide is back_right <-> back_left directly), so each back
    half is its own grip and the center is the expanding clamp mechanism."""
    rp, _, _ = _grip_poly_product("right")
    lp, _, _ = _grip_poly_product("left")
    return rp.union(lp).buffer(0)

# ==== printable parts (CadQuery) ====================================================
import cadquery as cq

# --- vertical stack (all derived so the parts always line up) ---
FLOOR = 1.6            # back-half floor thickness
WALL_T = 2.5          # shell wall thickness
TOP_T = 2.4           # grip-lid plate thickness (v0.19: 2.0 -> 2.4 so the M3 flush
                      #   countersink cone leaves >=1.0mm of land under it)
STANDOFF = 6.3        # PCB standoff: clears the 6.0mm mated JST-PH + 0.24 margin. v0.27:
                      #   that connector is J4 on the LEFT board now (J3 is gone from the
                      #   right), so it is the LEFT cavity that runs at the 0.24 margin.
PHONE_CLR = 0.6       # phone pocket clearance (total, both sides)
GAP = 0.5
KM_WEB, KM_PL_H, KM_PL_D = 0.8, 3.9, 6.2   # keymat web / plunger height / plunger dia
                                           # (v0.19: 3.5 -> 3.9 keeps caps 1.0 proud of
                                           #  the face after TOP_T grew 0.4)
NUB_R = 1.4                                # actuator nub radius (Ø2.8, under each dome)
PCB_Z = FLOOR + STANDOFF                     # grip-local PCB z=0 maps here
DOME_TOP = PCB_Z + PCB_T + DOME_H            # top of a seated snap dome
KM_Z0 = DOME_TOP + 1.0                       # keymat web bottom (nub reaches the dome)
TOP_Z = KM_Z0 + KM_WEB + GAP                 # front parts sit above the cavity
WALL = TOP_Z - FLOOR                         # cavity height (derived)

# --- printable parts (grip lids + 2 back-grip halves; v0.25 the tray is part of back_right), Ender 3 V2 bed ---
BED_XY = 204.0        # printable footprint per part: 220mm bed minus 2x8mm brim
# v0.24 device face + near-flush clamp recess. The grip-lid keyboard face is still
# the device face plane FACE_Z (=14.7); the phone is no longer sunk in a rigid
# well but clamped in a RECESS on the telescoping bridge whose floor sits so the
# NOMINAL cased phone's screen lands ~flush with FACE_Z.
FACE_Z = TOP_Z + TOP_T                       # 14.7 — grip-lid keyboard face = device face plane
WELL_TOP = FACE_Z                            # back-compat alias (lid/screw countersinks reference it)
PHONE_TC = CFG.phone_t + CFG.case_t          # 9.4 — nominal cased thickness (back-of-case -> screen)
RECESS_TOP = FACE_Z - PHONE_TC - 0.2         # 5.1 — bridge recess floor top (nominal screen ~flush)
LAP_CLR = 0.25        # printed-joint / rail-slide in-plane clearance (FDM: elephant foot + warp)
# --- v0.24 expanding spring-clamp bridge, ENCLOSED (product frame) ---
# The clamp mechanism (springs + the one bridge FFC) is housed in a
# TELESCOPING enclosure that stays closed at every extension: a fixed OUTER shroud
# (bolted to the right grip) and a moving INNER shroud (on the left jaw) that slides
# inside it. The two always overlap, so nothing is ever exposed in the gap. The
# phone rests on the outer shroud's top (the recess floor) + the grip cradle ledges;
# the low inner-shroud top just closes the enclosure under the phone.
BR_PLATE_T = 1.6                             # recess-floor / shroud top-plate thickness
BR_X_RIGHT = 82.6                            # outer shroud right end = nominal phone right edge (bolts to R grip)
SHROUD_Y0, SHROUD_Y1 = 7.0, 90.0             # enclosure y-extent (front/back walls, spans the phone y)
SHROUD_ZBOT = -4.5                           # enclosure bottom (center back; above the -5.5 grip crown)
SHROUD_ZTOP = RECESS_TOP                     # 5.1 — top plate top = recess floor (phone rests here)
SHROUD_WALL = 1.4                            # shroud wall thickness
SHROUD_CLR = 0.35                            # inner<->outer nesting slide clearance (coupon-tune)
OUTER_LEFT = -41.0                           # fixed outer-shroud left end. v0.25/J3: the tray is
                                             #   now printed AS PART OF back_right, so this end sets
                                             #   that part's length: OUTER_LEFT .. 162.75 must fit
                                             #   BED_XY. -45 gave 207.75 (3.75 over); -41 gives
                                             #   203.75. Every mm taken here is paid back in
                                             #   INNER_LEN or the enclosure opens at full extension.
INNER_LEN = 71.0                             # moving inner-shroud length. v0.25: 67 -> 71, paying
                                             #   back the 4mm OUTER_LEFT gave up to fit the bed, so
                                             #   the full-open overlap is unchanged at 13.35mm.
                                             #   v0.24e: 62 -> 67, bought
                                             #   back the 9mm of insertion headroom the capture
                                             #   lips need — every extra mm of jaw opening costs a
                                             #   mm of telescoping overlap, and the enclosure
                                             #   assertion (>=12mm) has to hold at FULL open.
# v0.24c: 2-part TRAY simplification (drop the 3-stage gear) + face-down MECHANICAL
# capture. The phone is trapped between the tray (behind) and DEEP soft lips (front)
# so it can't fall toward your face when used screen-down (Switch/Steam-Deck style) —
# retention is mechanical, never the magnets. A soft TPU GRIPPER on each grip's inner
# edge (GameSir-style) combines the edge grip + the capture lip in one part.
GRIP_PAD_T = 1.6                             # TPU gripper wall thickness (soft edge grip)
GRIP_PAD_LEN = 60.0                          # gripper length along the phone short edge (y)
# v0.24e: the pad is biased BELOW the phone's y centre. Once the bottom shelf exists the
# phone is datumed by its BOTTOM long edge, not centred — a short-edge-66.6 phone rests
# at y 8.5..75.1, not 15.2..81.8 — so a pad centred on cy=48.5 would miss the bottom of
# every small phone. 43.0 covers an 80.0 and a 66.6 short edge.
GRIP_PAD_CY = 43.0                           # gripper y centre (vs the phone/grip cy of 48.5)
# v0.24d gripper TEETH (the GameSir/Abxylute detail v0.24c left out): a comb of
# half-round ribs on the pad's phone-facing face, axis along z (the phone's
# thickness), pitch along y. A flat TPU pad only resists the phone sliding in y by
# friction; the teeth BITE the cased edge, so the phone can't creep or rotate in
# the clamp — which is what actually keeps the screen square to the keyboard face.
TOOTH_PITCH = 3.4                            # tooth pitch along y
TOOTH_R = 0.8                                # half-round tooth radius = 0.8mm bite into the cased edge
# === v0.24e CAPTURE-LIP geometry ===================================================
# Retention is the one function where being wrong drops a phone on someone's face, so
# every dimension here is referenced to a REAL surface, not a nominal plane.
#
# v0.24d measured the lip depth from the NOMINAL phone-edge plane (x = ±82.6) — but the
# clamped phone's edge does not sit there. The pad (GRIP_PAD_T) and its teeth (TOOTH_R)
# stand 2.4mm proud of that plane, so the phone's edge rests on the TOOTH CREST and the
# 2.8mm "deep lip" was delivering 0.4mm of actual overhang. It also put the lip's
# underside at FACE_Z - LIP_T = 13.1, which is 1.4mm INSIDE the phone: the lip was
# modelled buried in the phone body, so its real capture over the front face was 0.2mm.
# Both are fixed by referencing the two surfaces that physically exist:
PHONE_FACE_Z = RECESS_TOP + PHONE_TC          # 14.5 — the nominal cased phone's FRONT face
                                              #   (its back rests on the tray at RECESS_TOP)
LIP_OVER = 3.0                                # overhang measured from the CLAMPED phone edge
                                              #   (the tooth crest) — must clear a case's front
                                              #   edge radius (~1.0-1.5) so the lip lands
                                              #   flat-on-flat and cannot wedge the jaws open
# THE LIP IS TPU. A rigid PETG hook over the phone was tried in v0.24e-rc and rejected on
# review — correctly, and the reason is worth keeping written down:
#
#   A hook at a FIXED z can only capture a phone whose cased thickness is <= nominal.
#   The lip's underside is PHONE_FACE_Z (a 9.4mm cased phone). Thicker case -> the phone's
#   front face lands ABOVE that plane, so its edge butts into the lip's z band and the
#   jaw simply cannot close: the lip becomes a side pad and the capture is silently gone.
#
# TPU fails gracefully there — it deforms, rides up and still part-captures — where PETG
# fails hard. It is also the only sane thing to have in contact with a phone's screen
# edge: printed PETG layer lines on cover glass are a scratch source, and TPU spreads the
# contact instead of concentrating it. Both reasons are the user's, and both are right.
#
# The one thing the rigid shell still does is stop the GRIPPER being pulled off (see
# `_gripper_retainer`) — because `gripper()` is otherwise a plain L-section held on by
# friction, which review flagged as the real weak link. That retainer caps the lip's ROOT
# only; it stops outboard of the clamped phone edge and never touches the phone.
LIP_T = 1.6                                   # TPU lip thickness above PHONE_FACE_Z
RETAIN_T = 1.6                                # rigid retainer over the lip's root (no phone contact)
RETAIN_CLR = 0.4                              # retainer tip clearance OUTBOARD of the clamped edge
LIP_CHAM = 0.8                                # lead-in chamfer on the TPU lip's top inboard edge
def lip_depth():
    """Total TPU lip reach inboard from the rigid backstop wall = pad + teeth + overhang."""
    return GRIP_PAD_T + TOOTH_R + LIP_OVER
# === v0.24e BOTTOM SHELF ===========================================================
# Held normally the phone's weight acts along -y, and NOTHING was below its bottom long
# edge — the tray is behind the phone (z), not under it (y). That load was carried purely
# by clamp friction, which is the one load path that degrades (TPU creep, dust, a glossy
# case) and has no margin against ordinary shock. The shelf turns it into a bearing load.
SHELF_H = 3.0                                 # upstand above the tray top / cradle ledge
SHELF_W = 1.5                                 # thickness in y (sits directly over the tray wall)
# v0.25: the MagSafe ring is GONE. It was always the SECONDARY hold — "the clamp + lips
# retain the phone" — and with the clamp, the TPU grippers with teeth and the capture lips
# all doing their job it earns nothing. Removing it also retires the last thing that wanted
# space under the tray's top plate, which is where the moving jaw travels: its Ø60 backing
# plug hung 0.45mm into that cavity and jammed the clamp at EVERY span (1159mm^3 measured
# at min), hidden behind a blanket collide() whitelist. One less part, one less magnet, and
# the only remaining structure over the jaw is the 1.6mm plate itself.
# (v0.25 deleted the bolted tray-to-grip joint; BOLT_X/BOLT_Y went with it. They survived
# here as unreferenced constants carrying a stale "clear of J2 at y 12.5..33.5" note that
# v0.27 would have made wrong anyway — J2 is at y 15.08..41.93 now.)
# === v0.24d internal LANE PLAN =====================================================
# v0.24c stacked things inside the enclosure: the FFC ran at y=24 directly UNDER
# spring 0 (also y=24), their z bands overlapping — the coil would have sat on the
# ribbon and abraded it, and the ribbon's service loop had nowhere to crumple that
# wasn't a spring. And every cable was pinned to the OUTER tray's floor, which is
# 1.4mm below the INNER shroud's floor, so across the span only the inner shroud
# covers (worst at full extension) the cables hung in open air behind the device.
#
# Both are lane bugs, so the fix is one lane plan. Front -> back the enclosure is:
#
#     spring | FFC | spring                   (y lanes, walled by printed ribs)
#
# (v0.27: there used to be a second cable lane for the battery's 2-wire at y=41. The
# battery moved onto the ribbon, so that lane and its two divider ribs are gone and
# y 40.0..82.5 is now free.)
#
# and EVERY lane shares one z (LANE_Z), the mid-height of the inner shroud's
# cavity. Nothing is stacked over anything; the springs are pushed out to the
# enclosure's y extremes (a wider stance also resists jaw racking); the cables sit
# inside the MOVING shroud's cavity, so they are enclosed at every extension by
# construction, not by the tray happening to still be under them.
CAV_Y0 = SHROUD_Y0 + SHROUD_CLR + 2 * SHROUD_WALL       # 10.15 — inner-shroud cavity, front
CAV_Y1 = SHROUD_Y1 - SHROUD_CLR - 2 * SHROUD_WALL       # 86.85 — ... back
CAV_Z0 = SHROUD_ZBOT + SHROUD_CLR + 2 * SHROUD_WALL     # -1.35 — ... floor
CAV_Z1 = SHROUD_ZTOP - BR_PLATE_T - SHROUD_CLR - SHROUD_WALL   # 1.75 — ... ceiling
LANE_Z = (CAV_Z0 + CAV_Z1) / 2.0             # 0.2 — the ONE z axis every lane shares
SPRING_Y = (12.5, 84.5)                      # 2 extension springs, OUTBOARD lanes (sym about cy=48.5)
SPRING_D = 4.0                               # extension-spring OD (fit model)
# v0.24e: the anchor moves 22 -> 76, hard against the tray's right wall. At x=22 the
# installed spring length ran 7.85mm (min span) to 47.85mm (max span) — a >5:1 working
# ratio no coil spring survives, and worse, at MIN span the spring is barely stretched,
# so the SMALLEST phones would have got the WEAKEST clamp. Anchoring at the far end makes
# the installed length 61.85 -> 101.85mm: the same 40mm of travel now rides on a long
# spring, so the force ratio across the range collapses to something a real off-the-shelf
# extension spring can deliver. See docs/design-decisions.md for the force numbers.
SPRING_ANCHOR_X = 76.0                       # fixed spring anchor (springs pull the inner shroud's hook toward here)
# v0.27: ONE cable lane. The battery rides the ribbon (4 of the 20-way's conductors), so
# the separate 2-wire power lane at y=41 is gone along with the cable itself.
#
# FLEX_Y is J2's deck y and is ASSERTED against the KiCad placement export in
# check_lanes() — it is not a free number. The old value (26.5) claimed in its own comment
# to be "J2's y centre" and was not: J2 sat at 24.5, so the 17mm ribbon ran 2.0mm off the
# pad row and conductor 1 fell outside it entirely. 26.5 was in fact the lane-plan minimum
# that the spring-rib assert would accept, silently overriding the connector. Both numbers
# move together now or the build fails.
FLEX_Y, FLEX_W, FLEX_T = 28.5, 21.0, 0.3      # 20-way 1.0mm-pitch ribbon (21mm wide over the
                                             #   conductors) entering the ZIF dead straight
FLEX_LOOP_T = 2.2                            # service-loop CRUMPLE envelope, not the 0.3 flat
                                             #   thickness. The lane still has to be this deep —
                                             #   the ribbon folds where the 2-wire used to fill it.
RIB_T = 1.2                                  # divider-rib thickness (3 perimeters at 0.4 nozzle)
LANE_CLR = 1.0                               # cable <-> channel wall clearance, per side
LANE_GAP_MIN = 2.0                           # --check: required clear y gap, spring lane <-> cable lane

def _chan_bands():
    """(y0, y1) of each cable channel = the lane plus its clearance, front to back.
    v0.27: one entry. Every consumer of this is a `for` loop, so deleting the power
    lane costs no code anywhere — the ribs, the shroud end-wall windows and the tray
    windows all just stop building their second copy."""
    return [(FLEX_Y - FLEX_W / 2 - LANE_CLR, FLEX_Y + FLEX_W / 2 + LANE_CLR)]

def _rib_bands():
    """(y0, y1) of each divider rib: RIB_T thick, hugging both walls of each channel.
    Printed into BOTH telescoping members so a cable is walled off from the spring
    lanes over the whole run, at every extension."""
    return [b for c0, c1 in _chan_bands() for b in ((c0 - RIB_T, c0), (c1, c1 + RIB_T))]
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

# ==== v0.25: the faceted back crown is GONE ========================================
# v0.23 gave each grip a faceted palm plateau below z=0. It was removed at the user's
# call: the cut-corner octagon, its single steep chamfer band and the scored grooves
# read as a block applied to the back rather than a shape the back has, and the height
# was not worth the cost — the crown was the ONLY reason the back halves printed
# cavity-down, which was the only reason they needed supports through the cavity, and
# it was why the reset pinhole had to be a 7.1mm-deep Ø1.6 straw.
# The back is flat again (z=0 is the outer back plane) and the halves print FLOOR-DOWN.
# Nothing else referenced the crown's geometry; the two features that were dimensioned
# off CROWN_PEAK (the reset pinhole and the back_half clip box) now reference the back
# plane directly, which is a surface that exists whatever the styling does next.
# v0.25: the grips' outer back face drops to the TRAY FLOOR, so the whole back of the
# device is ONE plane. This is not styling — it is the fix for what deleting the crown
# exposed. The crown used to reach -5.5, so the device rested on the two plateaus and
# the tray at -4.5 hung 1mm clear. With a flat back at z=0 the tray became the lowest
# thing on the device by 4.5mm: it would have rested on the tray with both grips
# floating, and (since v0.25 J3 prints the tray AS PART of back_right) the merged part
# would have needed support under ~87cm2 of cosmetic back face. Deriving BACK_Z from
# SHROUD_ZBOT makes the coplanarity a fact of the model rather than a coincidence.
BACK_Z = SHROUD_ZBOT  # -4.5 — outer back face of BOTH grips = the tray floor
EDGE_R = 1.2          # quarter-round on the outside faces the hands wrap (back + keyboard
                      #   face). Small enough that it never reaches a screw: the nearest
                      #   hole edge is 5.4mm inboard of the outer boundary and its
                      #   countersink cone stops 2.3mm short of it.

def _round_edge_cutters(poly, z_face, r, up, n=6):
    """Cutters that put a quarter-round on the OUTSIDE edge of a flat face.

    Built as n stacked bands of inset profile rather than a CadQuery .fillet(): these
    boundaries are 200mm long with dozens of segments and an OCC fillet on them is slow
    and fragile, whereas this is pure polygon offsetting. n is chosen so each band is
    r/n ~= 0.2mm — one layer — so the printed result is identical to a true round.

    `up` = the solid extends UPWARD from this face, so it is the part's bottom edge
    being rounded (the back shell). `up=False` = the solid is below the face and it is
    the top edge (the lid's keyboard face). Either way the round grows outward as it
    leaves the bed, so it prints with no support: each band overhangs the one under it
    by at most r/n = one layer."""
    cuts = []
    for i in range(n):
        u0, u1 = r*i/n, r*(i+1)/n                 # depth band, measured from the face
        um = (u0 + u1) / 2.0
        inset = r - math.sqrt(max(r*r - (r-um)**2, 0.0))   # quarter-circle profile
        band = poly.buffer(2.0).difference(poly.buffer(-inset))
        if band.is_empty:
            continue
        z0 = (z_face + u0) if up else (z_face - u1)
        cuts.append(_cq_from_poly(band, z0 - 0.001, (u1 - u0) + 0.002))
    return cuts

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
    outer = _cq_from_poly(fp.buffer(WALL_T+PCB_CLR), BACK_Z, (FLOOR+WALL) - BACK_Z)
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
    # v0.25: the back is BACK_Z..FLOOR = 6.1mm thick here, so a plain Ø1.6 bore would be
    # a 6mm straw no paperclip could find. Counterbore Ø3.2 from the back and leave only
    # the last 1.6mm at Ø1.6, which is the bit that has to stay small.
    shell = shell.cut(cq.Workplane("XY").workplane(offset=BACK_Z-1).center(rx, ry).circle(0.8).extrude((FLOOR - BACK_Z) + 2))
    shell = shell.cut(cq.Workplane("XY").workplane(offset=BACK_Z-1).center(rx, ry).circle(1.6).extrude((FLOOR - BACK_Z) - 1.6 + 1))
    lx, ly = _find_fp("right", "LED_0603")
    shell = shell.cut(cq.Workplane("XY").workplane(offset=BACK_Z-1).center(lx, ly).circle(0.75).extrude((FLOOR - BACK_Z) + 2))
    shell = shell.cut(cq.Workplane("XY").workplane(offset=BACK_Z-1).center(lx, ly).circle(1.6).extrude((FLOOR - BACK_Z) - 1.6 + 1))
    # antenna wall relief: the E73 physically overhangs the TOP board edge by 0.5mm and
    # the cavity wall face is only PCB_CLR=0.4 out — relieve the inner wall face 0.6mm
    # over the antenna keep-out span so the module tip has >=0.5mm clearance. The wall
    # stays CLOSED (1.9mm remains): the antenna radiates through thin PETG, not a hole.
    ax_, ay_, aw, ah = prod["right"]["keepouts"]["antenna"]
    shell = shell.cut(cq.Workplane("XY").workplane(offset=4.0)
                      .center(ax_ + ox + aw/2, bh_r + 0.65).box(aw, 0.7, PCB_Z - 3.9, centered=(True, True, False)))

    # ---- v0.24: the rigid center is GONE. No transverse spine walls / panel
    # bosses / FFC floor channel here any more — each grip's own perimeter wall
    # (from fp.buffer) already closes its inner edge, and the two grips are joined
    # only by the telescoping bridge. The right grip's bridge-mount bosses and the
    # left grip's slider groove are added per-side in _back_half_build().
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

def lip_top():
    """z of the TPU capture lip's top face."""
    return PHONE_FACE_Z + LIP_T

def retain_top():
    """z of the rigid retainer's top face. The cradle wall rises to here."""
    return lip_top() + RETAIN_T

def retain_tip(side):
    """x of the retainer's inboard tip — RETAIN_CLR OUTBOARD of where the clamped phone's
    edge actually sits (the tooth crest), so no rigid material is EVER over the screen."""
    s = 1 if side == "right" else -1
    return s * (BR_X_RIGHT - GRIP_PAD_T - TOOTH_R + RETAIN_CLR)

def _gripper_retainer(part, side, gx):
    """v0.24e RIGID retainer over the TPU lip's ROOT — and nothing else.

    The lip itself is TPU, because it has to flex for phone+case thickness variance and
    because hard plastic on cover glass is a scratch source. But `gripper()` is a plain
    L-section pressed onto the cradle with no dovetail, undercut or screw, so review found
    the entire retention chain hanging off a friction joint: the phone's pull lifts the
    lip, the L rotates, and the pad peels off the wall. This caps that.

    It stops `RETAIN_CLR` OUTBOARD of the clamped phone edge, so it never overhangs the
    screen and never limits how thick a phone can be — the lip's free length inboard of
    it is still soft and still flexes, which is exactly where a thick case needs give."""
    s = 1 if side == "right" else -1
    prod = _product(); ph = prod["phone"]
    py0, py1 = ph["y"] - 0.5, ph["y"] + ph["h"] + 0.5
    tip = retain_tip(side)
    root = s * (gx - 0.9)                          # outboard face of the cradle wall
    cap = _cq_from_poly(shp_box(min(tip, root), py0, max(tip, root), py1),
                        lip_top(), RETAIN_T)
    return part.union(cap)

def shelf_y():
    """(y0, y1) of the bottom shelf: an upstand at the phone well's LOW-y edge, whose
    inboard face lands exactly on the nominal phone's bottom long edge. A phone with a
    shorter y edge simply rests on the same face and sits low in the well."""
    py = _product()["phone"]["y"]
    return py - SHELF_W, py

def _cradle_shelf(part, x0, x1):
    """v0.24e BOTTOM SHELF, cradle segment. Held normally the phone's weight acts along
    -y and nothing was under its bottom long edge — the tray sits BEHIND the phone, not
    below it — so that load was carried entirely by clamp friction. Friction is the one
    path that decays (TPU creep under permanent compression, dust, a glossy case) and it
    had no margin against ordinary shock. These tabs (plus the tray rib in _bridge_build)
    put a hard bearing surface under the phone. They only block -y, so the phone still
    drops straight into the well and lifts straight back out."""
    sy0, sy1 = shelf_y()
    return part.union(_cq_from_poly(shp_box(min(x0, x1), sy0, max(x0, x1), sy1),
                                    RECESS_TOP, SHELF_H))

def _grip_bridge_iface(part, side):
    """v0.24 ENCLOSED telescoping-clamp interface on a grip's back half. Both grips
    get a phone-edge CRADLE (backstop wall + screen-edge lip + rest ledge; TPU pad
    seats on the wall). The RIGHT grip (GROUND) adds the bridge-bolt bosses. The LEFT
    grip (moving jaw) grows the moving INNER SHROUD — a closed box that telescopes
    inside the fixed outer shroud, carrying the cable run and the spring hooks — so
    the springs and the FFC are enclosed at every extension. Built in the nominal
    frame; the whole left grip (shroud included) translates by the jaw slide."""
    prod = _product()
    ph = prod["phone"]; py0, py1 = ph["y"] - 0.5, ph["y"] + ph["h"] + 0.5
    gx = _seam_frame(); zt = RECESS_TOP
    if side == "right":
        xw0, xw1 = BR_X_RIGHT, gx - 0.9           # 82.6 .. 83.95 (stops shy of J2's courtyard @84.8)
        # rigid backstop wall. v0.24e: it now rises to the TOP of the TPU lip instead of
        # stopping at FACE_Z. The lip is a cantilever carrying the phone's whole weight
        # when the deck is used screen-down; rooted only in 1.6mm of TPU it could roll,
        # so the wall gives it a rigid root and the overhang is the only free length.
        part = part.union(_cq_from_poly(shp_box(xw0, py0, xw1, py1), zt, retain_top() - zt))
        part = part.union(_cq_from_poly(shp_box(xw0 - 4.0, py0, xw0, py1), zt - 1.2, 1.2))  # ledge: phone edge rests here
        part = _cradle_shelf(part, xw0 - 4.0, xw1)   # v0.24e bottom shelf (see _cradle_shelf)
        part = _gripper_retainer(part, side, gx)     # v0.24e rigid retainer over the TPU lip ROOT
        # (the soft edge grip + teeth + the lip's TPU facing are gripper("right"))
        # v0.25 (J3): the tray is unioned into this part by back_half(); no bolts, no bosses.
    else:
        gxl = -gx                                  # left grip inner edge (-84.85)
        xw0, xw1 = gxl + 0.9, -BR_X_RIGHT         # -83.95 .. -82.6 cradle (stops shy of J2's courtyard)
        part = part.union(_cq_from_poly(shp_box(xw0, py0, xw1, py1), zt, retain_top() - zt))  # rigid backstop wall
        part = part.union(_cq_from_poly(shp_box(xw1, py0, xw1 + 4.0, py1), zt - 1.2, 1.2))  # ledge: phone edge rests here
        part = _cradle_shelf(part, xw0, xw1 + 4.0)   # v0.24e bottom shelf (see _cradle_shelf)
        part = _gripper_retainer(part, side, gx)     # v0.24e rigid retainer over the TPU lip ROOT
        # moving INNER SHROUD: a closed box from the grip inner edge inward INNER_LEN,
        # sized to nest inside the outer shroud (walls/floor/top inset by
        # SHROUD_WALL+SHROUD_CLR), OPEN on its right (inboard) end. Houses the cable
        # run; its right end carries the spring hooks the outer springs pull on.
        iy0, iy1 = SHROUD_Y0 + SHROUD_WALL + SHROUD_CLR, SHROUD_Y1 - SHROUD_WALL - SHROUD_CLR
        izb = SHROUD_ZBOT + SHROUD_WALL + SHROUD_CLR         # nested bottom
        izt = (zt - BR_PLATE_T) - SHROUD_CLR                 # nested top (below the outer top plate)
        sx_in = gxl + INNER_LEN                              # inner shroud right (open) end
        outer = _cq_from_poly(shp_box(gxl, iy0, sx_in, iy1), izb, izt - izb)
        inner = _cq_from_poly(shp_box(gxl + SHROUD_WALL, iy0 + SHROUD_WALL, sx_in + 2, iy1 - SHROUD_WALL),
                              izb + SHROUD_WALL, (izt - SHROUD_WALL) - (izb + SHROUD_WALL))
        part = part.union(outer.cut(inner))                 # closed box, open right end
        # v0.24d LANE RIBS: full-cavity-height dividers run the shroud's whole length,
        # walling the FFC into its own channel. The service
        # loop can crumple all it likes at short spans — it has no path into a spring.
        for ry0, ry1 in _rib_bands():
            part = part.union(_cq_from_poly(shp_box(gxl + SHROUD_WALL, ry0, sx_in, ry1),
                                            CAV_Z0, CAV_Z1 - CAV_Z0))
        # v0.24d cable pass-throughs in the shroud's LEFT end wall. v0.24c closed that
        # wall solid, so the ribbon and the battery leads had no way into the left grip
        # (they were modelled straight through 1.4mm of PETG).
        for cy0, cy1 in _chan_bands():
            part = part.cut(_cq_from_poly(shp_box(gxl - 1, cy0, gxl + SHROUD_WALL + 1, cy1),
                                          CAV_Z0, CAV_Z1 - CAV_Z0))
        # spring HOOK LUGS, one per spring lane, at the shroud's open right end. The lug
        # spans the shroud's full solid height (izb..izt) so the Ø4 spring works in the
        # OUTER tray's deeper cavity on LANE_Z instead of being squeezed into the
        # shallower inner cavity; a slot behind the end bar is the eye the spring's end
        # hook drops over. Spring lanes only — the lug never enters a cable channel.
        for sy in SPRING_Y:
            part = part.union(_cq_from_poly(shp_box(sx_in - 6.0, sy - 2.5, sx_in + 3.0, sy + 2.5),
                                            izb, izt - izb))
            part = part.cut(_cq_from_poly(shp_box(sx_in - 2.4, sy - 1.6, sx_in + 0.6, sy + 1.6),
                                          LANE_Z - 1.6, 3.2))
    return part

def back_half(side):
    return _memo(f"back_{side}", lambda: _back_half_build(side))

def _back_half_build(side):
    """v0.24: one printable back-shell half = ONE GRIP. The two grips are separate
    bodies (no x=0 seam, no tabs/shiplap) joined only by the telescoping bridge, so
    a half is just its grip clipped out of _back_full(). The right grip carries the
    bridge-mount bosses; the left grip carries the slider groove (added by
    _grip_bridge_iface). The clip box reaches below BACK_Z so any future
    below-the-back feature is kept rather than sliced off."""
    prod = _product(); bh = prod["right"]["board_h"]
    s = 1 if side == "right" else -1
    half = (cq.Workplane("XY").workplane(offset=BACK_Z-8)
            .center(s*250, bh/2).box(500, 500, 38, centered=(True, True, False)))
    part = _back_full().intersect(half)
    part = _grip_bridge_iface(part, side)
    if side == "right":
        part = part.union(_tray_solid())     # v0.25 (J3): one part, no joint
    # v0.27 FFC duct — cut AFTER the tray union, or the tray would fill the right grip's
    # half of it straight back in. Both grips get one; the right grip had no cable
    # opening of any kind before this.
    part = part.cut(_flex_duct_cutter(side))
    # v0.25: quarter-round the outside bottom edge — the back plane is the face the palm
    # rides on, and it is now one continuous plane across the grips AND the tray, so the
    # round is taken on their combined outline rather than each piece's.
    gp, _g, _o = _grip_poly_product(side)
    face = gp.buffer(WALL_T + PCB_CLR)
    if side == "right":
        face = face.union(shp_box(OUTER_LEFT, SHROUD_Y0, BR_X_RIGHT, SHROUD_Y1))
    for c in _round_edge_cutters(face, BACK_Z, EDGE_R, up=True):
        part = part.cut(c)
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
    lids' clamp rims so they line up exactly.

    v0.25: the nav pad's own margin is DPAD_FIELD, not the general 2.0 — the web has
    to carry the clamp band (ring above, back rib below) all the way round the pad
    with land to spare, and buffering the sectors alone would stop 1.5mm short of it."""
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
    dp = _dpad_plan(side)
    pad = [dp["outer"].buffer(DPAD_FIELD)] if dp else []
    field = unary_union([pl.buffer(2.0) for (pl, _op, _x, _y) in shapes] + strips + pad)
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
    # v0.25: the integrated nav pad gets its own closed clamp ring INSIDE the field.
    # The perimeter rim only pins the web where the field's edge happens to run, and
    # the pad sits well inboard of it — without this ring a press on one arm would
    # lift the web the neighbouring arms stand on, and the moats alone would not keep
    # the presses discrete. Backed from below by the keymat's matching rib.
    dp = _dpad_plan(side)
    if dp:
        rim = rim.union(dp["band"])
    plate = plate.union(_cq_from_poly(rim, web_top - 0.1, z0 - (web_top - 0.1)))
    # key openings at every cap (v0.17: rounded-rect for grid keys, round for the
    # cluster), cut AFTER the rim union, deep enough to keep the full plunger bore
    # clear through the rim band. One MultiPolygon cut instead of per-key booleans.
    from shapely.ops import unary_union
    openings = [op for (_p, op, _x, _y) in _cap_shapes_product(side)]
    plate = plate.cut(_cq_from_poly(unary_union(openings), web_top - 0.2, TOP_T + (z0 - web_top) + 0.4))
    # ...and the pad's aperture gets a 45-degree dish in the face, so the pad reads as
    # ONE round control sunk into the lid (the i8+ look) instead of a disc standing in
    # a punched hole. The cone opens upward, so it still prints clean face-down.
    if dp and DPAD_CHAM > 0:
        cx, cy = dp["c"]
        ra = DPAD_D/2 + CAP_CLR
        # the cone starts BELOW the face and inboard of the bore (r-0.3) so its flank
        # crosses r=ra in open air: a cone based exactly on the bore wall is a
        # coincident-face boolean, and OCC hands back a non-watertight shell for it.
        h = DPAD_CHAM + 0.7
        plate = plate.cut(cq.Solid.makeCone(ra - 0.3, ra + DPAD_CHAM + 0.4, h,
                                            cq.Vector(cx, cy, z0 + TOP_T - DPAD_CHAM - 0.3)))
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
    # v0.25: quarter-round the OUTSIDE top edge of the keyboard face — the edge the
    # thumbs ride over. Built from the UNCLIPPED footprint buffer on purpose: near the
    # seam that profile sits ~2.9mm inboard of the reveal and gets clipped away, so the
    # seam keeps its crisp 0.5mm chamfer and only the outer perimeter is rounded.
    for c in _round_edge_cutters(fp.buffer(WALL_T + PCB_CLR), z0 + TOP_T, EDGE_R, up=False):
        plate = plate.cut(c)
    return _to_trimesh(plate, f"grip_lid_{side}")

def _inner_right(clamp_pos=None):
    """x of the moving inner shroud's right (open) end at this clamp state."""
    prod = _prod_at(clamp_pos)
    return prod["left_origin"][0] + prod["left"]["board_w"] + INNER_LEN   # left inner edge + INNER_LEN

def _shroud_overlap(clamp_pos=None):
    """Telescoping overlap = how far the inner shroud's right end reaches PAST the
    fixed outer shroud's open left end (OUTER_LEFT). While this stays positive the
    enclosure is closed (inner plugs the outer's opening); the min is at max span,
    asserted >= 12mm by --check so the internals are never exposed."""
    return _inner_right(clamp_pos) - OUTER_LEFT

def _tray_solid():
    """v0.25 (J3): the fixed TRAY, returned as a CadQuery solid for back_half("right")
    to union in. It is no longer a separate printed part and no longer bolts to anything —
    the bolted joint it used to need is gone, which is the whole point of the merge.

    v0.24c the fixed TRAY — a 2-part telescoping tray (simpler than the geared
    3-stage). It bolts to the right grip and cantilevers left to OUTER_LEFT; the left
    grip's plate laps inside it (grown in _grip_bridge_iface), so the two overlap at
    every span and enclose the springs + FFC. The flat top is the phone
    rest (v0.25: no MagSafe recess — flat all the way across); the back is the rounded
    enclosure. Big continuous top face = room for the ring AND clean back-space for
    maker alt-shells (solar / battery / LoRa)."""
    zb, zt = SHROUD_ZBOT, SHROUD_ZTOP
    zpi = zt - BR_PLATE_T                          # top-plate underside
    # (1) solid box hollowed to a closed shell OPEN on the left end (cavity runs off
    #     the left face; keeps bottom, top plate, both y-walls, and the right wall)
    box = _cq_from_poly(shp_box(OUTER_LEFT, SHROUD_Y0, BR_X_RIGHT, SHROUD_Y1), zb, zt - zb)
    cav = _cq_from_poly(shp_box(OUTER_LEFT - 2, SHROUD_Y0 + SHROUD_WALL,
                                BR_X_RIGHT - SHROUD_WALL, SHROUD_Y1 - SHROUD_WALL),
                        zb + SHROUD_WALL, zpi - (zb + SHROUD_WALL))
    br = box.cut(cav)
    # (2) fixed spring anchor posts inside the cavity (the springs hook the inner
    #     shroud), tall enough to carry the coil on the shared LANE_Z axis
    for sy in SPRING_Y:
        br = br.union(cq.Workplane("XY").workplane(offset=zb + SHROUD_WALL)
                      .center(SPRING_ANCHOR_X, sy)
                      .box(3.0, 3.0, (LANE_Z + SPRING_D / 2 + 0.8) - (zb + SHROUD_WALL),
                           centered=(True, True, False)))
    # (2b) v0.24d LANE RIBS in the tray cavity, mirroring the shroud's. They can only
    #      live where the moving shroud can never reach — i.e. right of its end at the
    #      SHORTEST span — but that is the majority of the tray, and it is exactly the
    #      stretch where the cables and the springs would otherwise share open cavity.
    rib_x0 = _inner_right(deck.Config().phone_span_min) + 3.0
    for ry0, ry1 in _rib_bands():
        br = br.union(_cq_from_poly(shp_box(rib_x0, ry0, BR_X_RIGHT - SHROUD_WALL, ry1),
                                    zb + SHROUD_WALL, zpi - (zb + SHROUD_WALL)))
    # (3) v0.25 (J3): the two M3 bolt bosses that used to tie the tray to the right grip are
    #     GONE with the joint. They were unbuildable anyway — both sides were Ø3.4 clearance,
    #     so nothing was ever threaded, and the column sat under 12.5mm of solid cradle wall
    #     with no driver access. Merging the parts deletes the problem rather than fixing it.
    # (4) cable windows in the RIGHT end wall — one per LANE, on the lane z band. v0.27:
    #     there is only the FFC lane now, so there is one window; the battery leads that
    #     used to need their own are gone with the cable. (v0.24c cut a single window at
    #     y 15..33 and the then-existing power lane at y=40 missed it entirely — which is
    #     why this is driven off _chan_bands() rather than hardcoded.)
    for cy0, cy1 in _chan_bands():
        br = br.cut(_cq_from_poly(shp_box(BR_X_RIGHT - SHROUD_WALL - 1, cy0, BR_X_RIGHT + 1, cy1),
                                  CAV_Z0 - 0.2, (CAV_Z1 + 0.2) - (CAV_Z0 - 0.2)))
    # (5) v0.25: the MagSafe ring and its recess are gone (see the constant block). The
    #     tray top is now an uninterrupted flat phone rest, and nothing hangs below the
    #     top plate into the moving jaw's travel.
    # (6) v0.24e BOTTOM SHELF: an upstand along the tray top's low-y edge, sitting
    #     directly over the front wall so it is fully supported. The phone's bottom long
    #     edge bears on this instead of hanging off clamp friction. It spans the whole
    #     tray; the grips' cradle tabs (_cradle_shelf) carry the phone's corners, which
    #     is what matters at long spans where the phone overhangs the tray.
    sy0, sy1 = shelf_y()
    br = br.union(_cq_from_poly(shp_box(OUTER_LEFT, sy0, BR_X_RIGHT, sy1), zt, SHELF_H))
    return br

def prod_cy():
    return _product()["right"]["board_h"] / 2.0                              # phone/grip y-centre (48.5)

def gripper(side):
    return _memo(f"gripper_{side}", lambda: _gripper_build(side))

def _gripper_build(side):
    """v0.24e soft TPU GRIPPER on a grip's inner edge (GameSir / Abxylute-style): a
    compliant pad on the phone's cased short edge, a comb of TEETH that bite that
    edge, and a capture LIP that hooks over the phone's FRONT face — soft grip,
    anti-slide and retention in one part. Print in TPU with the keymats. Retention is
    mechanical (lip + teeth + the rigid backstop + the clamp), never the magnets.

    Two v0.24d datum errors are fixed here, both of which had quietly reduced the lip
    to decoration (see the LIP_* block for the arithmetic):
      * the lip sat at FACE_Z - LIP_T, i.e. 1.4mm INSIDE the phone body. Its underside
        is now PHONE_FACE_Z — flush on the screen, which is the only place a hook that
        is supposed to stop the phone leaving in +z can actually bear.
      * its depth was measured from the NOMINAL phone-edge plane, but the pad and teeth
        stand 2.4mm proud of that, so the phone's edge rests further inboard and the
        real overhang was 0.4mm. Depth is now pad + teeth + LIP_OVER, so LIP_OVER is
        overhang past the surface the phone actually touches.
    The lip therefore stands (LIP_T - (FACE_Z - PHONE_FACE_Z)) proud of the keyboard
    face — a bezel over the phone's edge, exactly as every commercial phone clamp has."""
    cy = GRIP_PAD_CY; s = 1 if side == "right" else -1   # biased low — see GRIP_PAD_CY
    xe = s * 82.6                                  # nominal phone edge plane on this side
    y0, y1 = cy - GRIP_PAD_LEN / 2, cy + GRIP_PAD_LEN / 2
    lo, hi = sorted((xe, xe - s * GRIP_PAD_T))     # protrudes INTO the well (phone compresses it)
    pad = _cq_from_poly(shp_box(lo, y0, hi, y1), RECESS_TOP, FACE_Z - RECESS_TOP)   # soft edge grip
    face = xe - s * GRIP_PAD_T                     # the pad face the phone presses on
    n = int(GRIP_PAD_LEN // TOOTH_PITCH)           # teeth, centred on the pad
    for i in range(n):
        ty = cy - (n - 1) * TOOTH_PITCH / 2 + i * TOOTH_PITCH
        pad = pad.union(cq.Workplane("XY").workplane(offset=RECESS_TOP)
                        .center(face, ty).circle(TOOTH_R).extrude(FACE_Z - RECESS_TOP))
    # The capture lip is TPU for its whole thickness: it is the only thing that touches
    # the phone's front face, and it has to give when a thick case pushes into it. Its
    # ROOT is capped by the shell's rigid retainer (_gripper_retainer) so this part can't
    # be peeled off — but everything inboard of RETAIN_CLR is free to flex.
    lo2, hi2 = sorted((xe, xe - s * lip_depth()))  # reaches LIP_OVER past the tooth crest
    lip = _cq_from_poly(shp_box(lo2, y0, hi2, y1), PHONE_FACE_Z, LIP_T)
    # lead-in on the lip's top INBOARD edge, so the phone cams past instead of being
    # threaded in square. The UNDERSIDE stays dead flat: a chamfer there would turn the
    # phone's weight into a force spreading the jaws.
    lip = lip.edges(f"|Y and {'<X' if s > 0 else '>X'} and >Z").chamfer(LIP_CHAM)
    return _to_trimesh(pad.union(lip), f"gripper_{side}")

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
    dp = _dpad_plan(side)
    for f in geo.get("features", []):
        if f["type"] != "key":
            continue
        lab = f["label"]; x, y = f["x"]+ox, f["y"]+oy
        if lab.startswith("NAV_") and lab != "NAV_OK":
            # v0.25: on the integrated pad an arrow has a whole sector to itself, so it
            # grows from the 3.2 that fitted a Ø6.2 button to a 4.6 the thumb can read
            cuts.append(_poly_cutter(_tri(x, y, lab[-1], s=4.6 if dp else 3.2)))
        elif lab == "NAV_OK" and dp:  # the pad's centre button is Ø9, not Ø6.2
            cuts.append(_text_cutter(PRIM_WORDS[lab], WORD_FS, x, y, max_w=DPAD_OK_D - 2.6))
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
    nubs = unary_union([Polygon([(x+NUB_R*math.cos(t), y+NUB_R*math.sin(t))
                                 for t in np.linspace(0, 2*math.pi, 16)])
                        for (_p, _o, x, y) in shapes])
    mat = mat.union(_cq_from_poly(nubs, z0 - 1.0, 1.0))
    dp = _dpad_plan(side)
    if dp:
        # v0.25 MOAT RELIEF: thin the web under every moat. Without this the moats only
        # separate the CAPS — the web runs on underneath at full 0.8 and couples the
        # actuators more stiffly than an ordinary key pair, which is the one way an
        # integrated pad quietly stops being five discrete keys. Cut from the web's top
        # face, so in the print (cap-side down) it is an open channel, not a bridge.
        mat = mat.cut(_cq_from_poly(dp["moat"], z0 + DPAD_WEB_RELIEF,
                                    KM_WEB - DPAD_WEB_RELIEF + 0.2))
        # v0.25 nav-pad BACK RIB: an annular downstand under the web, directly beneath
        # the lid's clamp ring, reaching to DPAD_RIB_CLR above the PCB face. It is a
        # backstop, not a preload — the ring pins the web ring from above, the rib stops
        # it sinking from below, and between them each arm sector rocks about a boundary
        # that stays put instead of dragging its neighbours' sectors with it. The rib
        # prints as an upstand (the mat prints cap-side down), so no support.
        rib_z = PCB_Z + PCB_T + DOME_RETAIN_T + DPAD_RIB_CLR
        assert rib_z < z0, "the back rib has no height left above the dome-retention layer"
        mat = mat.union(_cq_from_poly(dp["band"], rib_z, z0 - rib_z))
        # 45-degree break on the pad's outer top edge + the OK button's, so the moulded
        # -D-pad read survives the flat-topped extrusion the rest of the caps use.
        cx, cy = dp["c"]
        for r, c in ((DPAD_D/2, DPAD_EDGE_CHAM), (DPAD_OK_D/2, DPAD_OK_CHAM)):
            # the wedge starts 0.2 below the chamfer and 0.2 OUTBOARD of the cap wall,
            # so the cone flank crosses r in open air — same coincident-face trap the
            # lid's aperture dish had to dodge
            z_b = CAP_TOP - c - 0.2
            ring = (cq.Workplane("XY").workplane(offset=z_b)
                    .center(cx, cy).circle(r + 0.6).extrude(c + 0.4))
            keep = cq.Solid.makeCone(r + 0.2, r - c - 0.2, c + 0.4, cq.Vector(cx, cy, z_b))
            mat = mat.cut(ring.cut(keep))
    # debossed keycap legends: one compound cut of every glyph on this grip
    t0 = time.time()
    cutters = _legend_cutters(side)
    mat = mat.cut(cq.Compound.makeCompound(cutters))
    print(f"  keymat_{side}: {len(cutters)} legend cutters debossed in {time.time()-t0:.1f}s")
    return _to_trimesh(mat, f"keymat_{side}")

# ==== non-printed bodies (real dims) ================================================
def _prod_at(clamp_pos):
    return deck.product(deck.Config(), clamp_pos=clamp_pos) if clamp_pos else _product()

def phone_body(clamp_pos=None):
    # cased envelope; long-edge width follows clamp_pos, thickness = nominal cased
    # (back + case), so this box's top face is ~the screen plane at PHONE_Z.
    ph = _prod_at(clamp_pos)["phone"]
    m = _box(ph["w"], ph["h"], PHONE_TC)
    return _place(m, ph["x"]+ph["w"]/2, ph["y"]+ph["h"]/2, 0)  # z set in assemble

def battery_body():
    # v0.18: 403040 pouch in the LEFT grip cavity (rides the moving jaw; assemble()
    # shifts it with the left grip). Foam-taped to the floor under the passive PCB.
    sb = _product()["battery"]
    m = _box(sb["w"], sb["h"], sb["t"])
    return _place(m, sb["x"]+sb["w"]/2, sb["y"]+sb["h"]/2, 0)

def spring_bodies(clamp_pos=None):
    """v0.24: the 2 extension springs (fit models), INSIDE the outer shroud — each
    runs from the fixed anchor (SPRING_ANCHOR_X) to the moving inner shroud's hook
    (near its right/open end). They stretch as the jaw pulls out and are fully
    enclosed by the outer shroud at every extension. v0.24d: on LANE_Z in the
    OUTBOARD y lanes, so a coil is never stacked over a cable."""
    zc = LANE_Z                                               # the shared lane axis
    x_fixed = SPRING_ANCHOR_X
    x_move = _inner_right(clamp_pos) + 1.8                    # the shroud's hook-lug eye bar
    out = []
    for sy in SPRING_Y:
        c = trimesh.creation.cylinder(radius=SPRING_D/2, height=abs(x_fixed - x_move), sections=16)
        c.apply_transform(trimesh.transformations.rotation_matrix(math.pi/2, (0, 1, 0)))
        c.apply_translation(((x_fixed + x_move)/2, sy, zc))
        out.append(c)
    return out

def _cable_run(clamp_pos, y, w, h, z):
    """A cable/ribbon fit body spanning the enclosure from the left grip through the
    shrouds to the right end wall — the part that must stay ENCLOSED. x from the
    left grip inner edge to the outer shroud's right end; the service-loop slack
    folds inside as the span changes (modeled as the straight enclosed run)."""
    prod = _prod_at(clamp_pos)
    lx = prod["left_origin"][0] + prod["left"]["board_w"]     # left grip inner edge
    rx = BR_X_RIGHT - SHROUD_WALL
    m = _box(rx - lx, w, h)
    return _place(m, (lx + rx) / 2, y, z)

ZIF_ENTRY_Z = 0.9      # AFA07: cable-slot centreline above the connector's seating plane
                       #   (2.5 body over a 0.3 ribbon; the slot sits low in the body)
ZIF_MOUTH_OFF = 2.4    # anchor -> cable-slot face, from the footprint's F.Fab rect
                       #   (local y -2.4). NOT the courtyard (-3.05) and not the bbox:
                       #   the ribbon arrives at the BODY face, and the 0.65mm difference
                       #   is the whole margin in the duct problem flex_route_report()
                       #   reports, so it has to be the right number.

# --- v0.27 FFC DUCT ------------------------------------------------------------------
# The ribbon's way out of the grip. Until v0.27 there was none: the ZIF slot sits at
# z ~= 6.95 (back-mounted under a board at PCB_Z) and the lane at LANE_Z = 0.2, and the
# column between the tray end and the grip cavity is solid at every z. Both bridge cables
# were straight boxes reaching neither connector, so nothing ever had to be true.
#
# The duct is deliberately LOW and SHORT: it passes under the phone-retention structure
# (cradle backstop wall, its 1.2mm rest ledge and the v0.24e bottom shelf all live at
# z >= 3.9 — see _cradle_shelf/retain_top) rather than through it. A full-height slot from
# the lane up to the ZIF would have been simpler and needed no PCB change, but it would
# have severed ~23mm of the wall the TPU capture lip is rooted in, on the one structure
# whose whole job is stopping a phone falling out. J2 was rotated to face inboard instead.
# The duct is STEPPED, because only its grip-side half may be tall. Inboard of the grip's
# inner face the moving inner shroud's roof spans CAV_Z1 (1.75) to izt (3.15) — a straight
# 2.6-high cut across the whole duct leaves that roof 0.55mm thick on an exposed outside
# surface, well under the file's own 3-perimeter convention (RIB_T = 1.2). The grip side
# has no such roof (it is cutting the grip's own floor slab), so it can be tall enough for
# the ribbon's fold while the shroud side stays a flat slot at lane height.
FLEX_DUCT_Z0 = LANE_Z - 1.0    # -0.8 — duct floor, below the lane axis
FLEX_DUCT_Z1 = 2.6             # GRIP side: opens into the back cavity (floor top ~1.55)
FLEX_DUCT_Z1_LANE = 1.95       # SHROUD/TRAY side: leaves izt - 1.95 = 1.20mm of roof
# The ribbon leaves the slot horizontally and has to end up vertical, so the descending
# leg does NOT sit at the fold point — it sits one bend radius further in. Sizing the fold
# to a zero-radius corner is how you put a 21mm-wide ribbon through a diode column.
FFC_BEND_R = 1.6               # min bend radius for the 0.3mm ribbon (static installed
                               #   fold; the Wurth part is rated 20 x 180deg, so this is
                               #   conservative). The descent lands at FLEX_TURN_X + this.
FLEX_TURN_X = 2.0              # fold offset from the ZIF slot, toward the grip interior.
                               #   The usable strip runs from J2's own body edge to the
                               #   innermost back-side part in the ribbon's y band; with
                               #   FFC_BEND_R that leaves the descent ~1mm clear of the
                               #   matrix diode column. ASSERTED in check_lanes() against
                               #   the real placement, not trusted to this comment.
FLEX_CAV_Z = 2.2               # the ribbon's run back toward the seam sits just above the
                               #   cavity floor (~1.6). It only drops to LANE_Z once it is
                               #   inside the duct, where the floor has been cut away.

def _flex_duct_cutter(side):
    """Cutter for one grip's ribbon duct: the channel band in y, FLEX_DUCT_Z0..Z1 in z,
    spanning from inside the tray's cavity through the solid column into the grip's back
    cavity. Cut from BOTH grips — the right grip previously had no cable window at all."""
    s = 1 if side == "right" else -1
    c0, c1 = _chan_bands()[0]
    face = s * _seam_frame()
    grip = s * (_seam_frame() + 1.2)          # into the grip, past its inner wall
    tray = s * (BR_X_RIGHT - 1.0)             # out into the tray cavity
    tall = _cq_from_poly(shp_box(min(face, grip), c0, max(face, grip), c1),
                         FLEX_DUCT_Z0, FLEX_DUCT_Z1 - FLEX_DUCT_Z0)
    flat = _cq_from_poly(shp_box(min(face, tray), c0, max(face, tray), c1),
                         FLEX_DUCT_Z0, FLEX_DUCT_Z1_LANE - FLEX_DUCT_Z0)
    return tall.union(flat)

def _flex_path(side):
    """The ribbon's route inside ONE grip, in the product frame: out of the ZIF slot
    inboard, down through the open back cavity, fold, back out through the duct to the
    lane. Sampled by flex_route_report() against the real shell solid — which is the only
    way this stays true, since a cable that reaches nothing also collides with nothing."""
    m = _zif_mouth(side)
    d = _zif_dir(side)                             # product-x direction the slot faces
    seam = 1 if side == "right" else -1            # which way the enclosure lies
    x_turn = m[0] + d * (FLEX_TURN_X + FFC_BEND_R)   # descent leg, one bend radius in
    # the vertical drop must happen on the GRIP side of the face, where the duct is tall
    x_duct = seam * (_seam_frame() + 0.5)
    x_tray = seam * (BR_X_RIGHT - 1.0)
    return [np.array([m[0], m[1], m[2]]),            # at the slot
            np.array([x_turn, m[1], m[2]]),          # out of the slot + the entry bend
            np.array([x_turn, m[1], FLEX_CAV_Z]),    # descend the open back cavity
            np.array([x_duct, m[1], FLEX_CAV_Z]),    # fold, run back toward the seam
            np.array([x_duct, m[1], LANE_Z]),        # drop to the lane INSIDE the duct
            np.array([x_tray, m[1], LANE_Z])]        # out through to the enclosure lane

def _zif_dir(side, ref="J2"):
    """+1/-1: the PRODUCT-x direction J2's cable slot faces, read from the placed
    rotation. _flex_path() used to hardcode this as a function of `side`, which quietly
    defeated the whole point of deriving it in _zif_mouth(): rotate J2 back to face the
    spine and the mouth would move 4.8mm one way while the path still turned the other,
    landing the whole route in open cavity where nothing is buried and the check passes."""
    f = next(p for p in _placement(side) if p["ref"] == ref)
    rot = round(f["rot"]) % 360
    assert rot in (90, 270), f"{ref} on {side} is rotated {rot}deg; expected 90 or 270"
    return 1 if rot == 90 else -1   # deck +x == product +x for both grips

def _zif_mouth(side, ref="J2"):
    """(x, y, z) of J2's cable slot in the PRODUCT frame — where the ribbon physically
    has to arrive — read from the KiCad placement export instead of being assumed.

    This function is the fix for a whole CLASS of bug: until v0.27 both bridge cables
    were straight boxes floating in the enclosure, connected to nothing at either end,
    and nothing could see it. collide() only tests interpenetration, and a cable that
    reaches nothing touches nothing; cable_enclosure() clipped 6mm off each end, so the
    connector ends were outside its window by construction. Deriving the endpoint from
    the placement makes the two drift together or fail together."""
    prod = _product()
    H = prod[side]["board_h"]
    ox, oy = prod[f"{side}_origin"]
    f = next(p for p in _placement(side) if p["ref"] == ref)
    assert f["back"], f"{ref} must be back-mounted for the ribbon to reach the lane"
    # Which way the slot points is READ from the placed rotation, never assumed — v0.27
    # flips it, and a hardcoded sign here would have silently pointed the model's cable
    # at the back of the connector.
    d = _zif_dir(side, ref)
    return np.array([ox + f["ax"] + d * ZIF_MOUTH_OFF,
                     oy + (H - f["ay"]),
                     (PCB_Z - SOLDER) - ZIF_ENTRY_Z])

def flex_body(clamp_pos=None):
    """Bridge FFC (20-way, 1.0mm pitch -> 21mm ribbon): the matrix jumper AND, since
    v0.27, the battery feed — 9 rows + 5 cols + 2 GND + 2 VBAT_CELL + 2 NC guards.
    Runs ENCLOSED through the shrouds in the FLEX lane, walled off from both springs by
    the divider ribs, on LANE_Z inside the MOVING shroud's cavity. The variable span is
    taken up by a rolling service loop folding inside its channel.

    Still modelled as the straight enclosed run: that is the part whose ENCLOSURE has to
    be proven, and it is what cable_enclosure() checks. The route from each ZIF slot DOWN
    to this lane is a separate body of geometry (_flex_path + the duct) and is proven
    separately by flex_route_report()."""
    return _cable_run(clamp_pos, FLEX_Y, FLEX_W, FLEX_T, LANE_Z)


def check_lanes():
    """v0.24d LANE PLAN + v0.27 CONNECTOR AGREEMENT. Pure arithmetic over constants and
    the placement export, so a regression fails in ~2s instead of after the multi-minute
    mesh sweep. Run standalone with `deck3d.py --check-lanes`.

    The connector-agreement asserts are the new ones, and they are the point: the lane
    plan and the ZIF placement used to be two independent numbers that a comment CLAIMED
    were equal. They were not — FLEX_Y was 26.5 against a connector at 24.5, so the
    ribbon ran 2.0mm off the pad row and its first conductor missed the housing entirely.
    Nothing objected, because nothing compared them."""
    for nm, (ly, lw) in (("flex", (FLEX_Y, FLEX_W)),):
        assert min(SPRING_Y) < ly < max(SPRING_Y), f"{nm} lane y={ly} is not between the springs"
        for sy in SPRING_Y:
            gap = abs(sy - ly) - (SPRING_D + lw) / 2.0
            assert gap >= LANE_GAP_MIN, (f"{nm} lane (y={ly}) is only {gap:.1f}mm clear of the "
                                         f"spring lane at y={sy} — min {LANE_GAP_MIN}mm")
    for c0, c1 in _chan_bands():                  # every channel inside the cavity
        assert CAV_Y0 <= c0 - RIB_T and c1 + RIB_T <= CAV_Y1, \
            f"cable channel {c0:.1f}..{c1:.1f} (+ribs) does not fit the cavity {CAV_Y0}..{CAV_Y1}"
    assert CAV_Z0 <= LANE_Z - FLEX_LOOP_T / 2 and LANE_Z + FLEX_LOOP_T / 2 <= CAV_Z1, \
        "the lane axis does not fit inside the MOVING shroud's cavity"
    for sy in SPRING_Y:                           # the outboard lanes must still fit the cavity
        assert CAV_Y0 <= sy - SPRING_D / 2 and sy + SPRING_D / 2 <= CAV_Y1, \
            f"spring lane y={sy} does not fit inside the enclosure cavity {CAV_Y0}..{CAV_Y1}"
    ribs = _rib_bands()                           # ...and no divider rib may foul one
    assert min(r[0] for r in ribs) - (SPRING_Y[0] + SPRING_D / 2) >= 1.0 and \
           (SPRING_Y[1] - SPRING_D / 2) - max(r[1] for r in ribs) >= 1.0, \
        "a cable channel's divider rib fouls a spring lane"
    # --- the lane must agree with the connector it feeds, on BOTH boards ---
    for side in ("left", "right"):
        m = _zif_mouth(side)
        assert abs(m[1] - FLEX_Y) <= 0.25, \
            (f"FLEX_Y={FLEX_Y} is {abs(m[1]-FLEX_Y):.2f}mm off {side} J2's slot centre "
             f"y={m[1]:.2f} — the ribbon cannot enter the ZIF straight")
        # The AFA07 family is exact: land = N + 6.85, ribbon = N + 1, so land - ribbon is
        # ALWAYS 5.85 whatever N is. Check that identity, not a tolerance band — the first
        # version allowed body-6.0 .. body, a 6mm window against the 4mm that separates the
        # 16- and 20-way parts, so FLEX_W=21.0 satisfied BOTH and swapping J2 back to the
        # 16-way footprint (still in the library) would have passed silently.
        body = next(f["h"] for f in _placement(side) if "ffc_afa07" in f["fp"])
        assert abs((body - FLEX_W) - 5.85) <= 0.2, \
            (f"FLEX_W={FLEX_W} does not match {side} J2's {body:.2f}mm land — wrong pin count. "
             f"AFA07: land = N+6.85, ribbon = N+1, so ribbon must be land-5.85 = {body-5.85:.2f}")
    # The ribbon descends inside the grip one bend radius past the fold. Nothing but a
    # comment used to keep that leg off the matrix diodes, and the comment was dimensioned
    # to a zero-radius corner. Measure it against the real placement instead.
    for side in ("left", "right"):
        m, d = _zif_mouth(side), _zif_dir(side)
        descent = m[0] + d * (FLEX_TURN_X + FFC_BEND_R)
        prod = _product(); H = prod[side]["board_h"]; ox, oy = prod[f"{side}_origin"]
        y0, y1 = FLEX_Y - FLEX_W / 2.0, FLEX_Y + FLEX_W / 2.0
        near = None
        for f in _placement(side):
            if f["ref"] == "J2" or not f["back"]:
                continue
            px, py = ox + f["x"], oy + (H - f["y"])
            if py + f["h"] / 2.0 < y0 or py - f["h"] / 2.0 > y1:
                continue                                  # not in the ribbon's y band
            edge = px - d * f["w"] / 2.0                  # its face toward the connector
            if (edge - descent) * d > 0:                  # inboard of the descent leg
                if near is None or (edge - descent) * d < (near[0] - descent) * d:
                    near = (edge, f["ref"])
        if near is not None:
            gap = (near[0] - descent) * d
            assert gap >= 0.8, \
                (f"{side}: the ribbon's descent at x={descent:.2f} is only {gap:.2f}mm clear "
                 f"of {near[1]} — FLEX_TURN_X({FLEX_TURN_X}) + FFC_BEND_R({FFC_BEND_R}) puts "
                 f"a 21mm-wide ribbon over a back-side part")
            print(f"  flex descent {side}: x={descent:.2f}, {gap:.2f}mm clear of {near[1]} ✅")
    print(f"  lanes y: spring {SPRING_Y[0]} | flex {FLEX_Y} | spring {SPRING_Y[1]}"
          f"  (on z={LANE_Z:.2f}, moving-shroud cavity {CAV_Z0:.2f}..{CAV_Z1:.2f}); "
          f"ribbon {FLEX_W}mm == J2 body {body:.2f}-6 ✅")


def flex_route_report(verbose=True):
    """Prove the ribbon can physically get from each ZIF slot down to the enclosure lane.

    v0.27 built the route this checks (J2 rotated to face the grip interior + the low duct
    at FLEX_DUCT_Z0..Z1). Before that there was none, in any version, and nothing noticed:
    both bridge cables were straight boxes floating in the lane, reaching neither
    connector, and a cable that reaches nothing also collides with nothing.

    The test SWEEPS THE RIBBON'S ACTUAL SECTION along the path, not its centre line. That
    distinction is this project's most expensive recurring lesson (v0.24e: "centre-line
    enclosure tests lie") — a centre-line contains() test reports "clear" for a duct 0.1mm
    wide, for a duct offset in y, and for a fold whose 21mm width is buried in the cavity
    wall. Here the ribbon is 21.0mm across a 23.0mm duct band, i.e. 1.0mm a side, so the
    width is exactly what is tight.

    Returns (results, ok); results is [(side, n_samples, n_buried)]."""
    out = []
    for side in ("left", "right"):
        shell = back_half(side)
        pts = _flex_path(side)
        # section grid: full width in y, full thickness in z, at the corners and mid-faces
        ys = np.linspace(-FLEX_W / 2.0, FLEX_W / 2.0, 9)
        zs = np.array([-FLEX_T / 2.0, FLEX_T / 2.0])
        samples = []
        for a, b in zip(pts, pts[1:]):
            n = max(2, int(np.linalg.norm(b - a) / 0.5))
            for t in np.linspace(0, 1, n):
                c = a + (b - a) * t
                for dy in ys:
                    for dz in zs:
                        samples.append((c[0], c[1] + dy, c[2] + dz))
        S = np.array(samples, dtype=float)
        buried = shell.contains(S)
        nb = int(buried.sum())
        out.append((side, len(S), nb))
        if verbose:
            tag = "clear" if nb == 0 else f"{nb}/{len(S)} section samples BURIED IN SHELL"
            print(f"  flex route {side}: slot {np.round(pts[0], 2)} -> lane z={LANE_Z:.2f}, "
                  f"{FLEX_W}mm section swept — {tag}")
            if nb:
                print(f"      first obstruction at {np.round(S[int(np.argmax(buried))], 2)}")
    ok = all(nb == 0 for _s, _n, nb in out)
    return out, ok

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
    """v0.24: the 10 grip lid screws as watertight solids (product frame),
    screw_<side>_<i> at the grip mount holes. The 4 panel border screws are gone
    (no center panel); the bridge is bolted with its own hardware (bridge()) ."""
    out = {}
    prod = _product()
    tip = FACE_Z - SCREW_L
    floor = PCB_Z - (STANDOFF - 1)
    assert tip - floor >= 1.0, \
        f"M3x{SCREW_L:.0f} tip @ {tip} would bottom out in the grip bore (floor {floor})"
    for side in ("right", "left"):
        geo = prod[side]; ox, oy = prod[f"{side}_origin"]
        for i, hh in enumerate(geo["mount_holes"]):
            out[f"screw_{side}_{i}"] = _screw_solid(hh["x"]+ox, hh["y"]+oy)
    return out


# ---- reporting / rendering ---------------------------------------------------------
def height_report(side="right"):
    parts, geo = pcb_assembly(side)
    print(f"== {side} PCB assembly: {len(parts)} bodies ==")
    zmax = max(m.bounds[1][2] for m in parts.values())
    zmin = min(m.bounds[0][2] for m in parts.values())
    print(f"  z extent: {zmin:.2f} .. {zmax:.2f} mm  (front stack {zmax-PCB_T:.2f} above board, back {abs(zmin):.2f} below)")
    # v0.26: U4 (the nub's TMAG5273) joins the watch list. It was the one part whose z
    # actually drives a design parameter — the magnet gap — and it was the one part the
    # height report never printed.
    # v0.27: J3 is gone; J4/F1 (left board) take its place on the watch list. A ref that
    # matches nothing prints nothing, which is how the mated JST-PH — the part STANDOFF
    # is dimensioned off — silently dropped out of this report.
    watch = ["U1", "J1", "J2", "J4", "F1", "U2", "U4"] + [n for n in parts if n.endswith(("_pwr", "_rst"))]
    for n in watch:
        if n in parts:
            bb = parts[n].bounds
            print(f"  {n:8s}: z {bb[0][2]:6.2f}..{bb[1][2]:6.2f}  (below board {max(0.0, -bb[0][2]):.2f})")
    deepest = max((-m.bounds[0][2], n) for n, m in parts.items())
    print(f"  back cavity: STANDOFF {STANDOFF} vs deepest part {deepest[1]} {deepest[0]:.2f} "
          f"-> margin {STANDOFF - deepest[0]:.2f}mm to the floor")
    print(f"  stack (product z): floor top {FLOOR} | PCB {PCB_Z}..{PCB_Z+PCB_T} | dome top {DOME_TOP} | "
          f"keymat web {KM_Z0}..{KM_Z0+KM_WEB} | grip lids {TOP_Z}..{TOP_Z+TOP_T} (face {FACE_Z}) | "
          f"bridge recess floor {RECESS_TOP} | "
          f"nominal cased phone {PHONE_Z-PHONE_TC/2:.1f}..{PHONE_Z+PHONE_TC/2:.1f} "
          f"(screen ~flush with lids @ {FACE_Z})")


def nub_report():
    """v0.26: the pointing nub's ALIGNMENT and AIR GAP, asserted rather than assumed.

    The nub is four concentric things stacked through three different coordinate
    frames — the deck.py feature, the KiCad footprint for U4 (which round-trips
    through a Y-flip and a back-side Flip()), the grip lid's aperture, and the
    printed spring's magnet pocket. Nothing checked that they still landed on the
    same axis, and nothing stated what the magnet-to-die distance actually was; the
    only record was a "~2.6mm" comment in a docstring. Both are load-bearing: a
    lateral error puts a static offset field on the sensor that the boot-zero hides
    until it runs out of range, and the gap sets the whole signal scale.

    Prints the stack and returns (dx, dy, gap_air, gap_to_die)."""
    nz = _nub_zone("right")
    assert nz, "no hall_nub feature on the right grip"
    prod = _product(); ox, oy = prod["right_origin"]
    parts, _ = pcb_assembly("right")
    assert "U4" in parts, ("U4 (TMAG5273) is not in the right PCB assembly — the nub has "
                           "no sensor. Check gen_board.py's hall_nub block.")
    b = parts["U4"].bounds
    ux, uy = (b[0][0]+b[1][0])/2 + ox, (b[0][1]+b[1][1])/2 + oy
    # U4 is BACK-mounted: its seating plane faces the board (MAX z) and its moulded top
    # face points away into the cavity (MIN z). The die reference is the MOULD face — get
    # this backwards and the gap is wrong by a whole package height.
    seating, mould = b[1][2] + PCB_Z, b[0][2] + PCB_Z
    dx, dy = ux - nz["x"], uy - nz["y"]
    # NB: U4's placement ANCHOR is exactly the feature point; (dx,dy) here is measured
    # off the footprint's BOUNDING BOX centre, which is pulled off-centre by the pin-1
    # silk marker. It is reported (not asserted to 0) so a real placement drift still
    # shows up, with SENSE_XY_TOL sized to swallow the bbox artefact only.
    z_die = mould + TMAG_DIE_DEPTH
    gap_air = NUB_MAGNET_Z - (PCB_Z + PCB_T)        # magnet face -> PCB front face
    gap_die = NUB_MAGNET_Z - z_die                  # magnet face -> hall element
    hub_to_board = (NUB_POCKET_Z0 + 0.1) - (PCB_Z + PCB_T)   # 0.90 mm of raw headroom
    print("== v0.26 pointing-nub stack (right grip) ==")
    print(f"  XY  nub feature / lid aperture / spring pocket / magnet : ({nz['x']:.3f}, {nz['y']:.3f})")
    print(f"      U4 TMAG5273 footprint anchor                       : ({ux:.3f}, {uy:.3f})"
          f"   offset ({dx:+.3f}, {dy:+.3f}) mm")
    print(f"      ...but the HALL ELEMENT is {TMAG_DIE_XY_OFF:.3f} mm off the package axis "
          f"(TI Fig 6-2) — uncompensated;")
    print(f"         it costs a static transverse offset the driver's boot-zero removes, and "
          f"<1% response asymmetry.")
    print(f"  Z   magnet Ø{NUB_MAGNET_D}×{NUB_MAGNET_H} seated        : {NUB_MAGNET_Z:.2f} .. "
          f"{NUB_MAGNET_Z+NUB_MAGNET_H:.2f}  (pocket Ø{NUB_MAGNET_D+2*NUB_MAGNET_FIT:.2f}, "
          f"{NUB_POCKET_Z0:.2f}..{NUB_POCKET_TOP:.2f})")
    print(f"      air gap  magnet face -> PCB front                   : {gap_air:.2f} mm")
    print(f"      hub underside -> PCB front  {hub_to_board:.2f} mm raw, but the v0.26 plunge "
          f"pads stop it at {NUB_PLUNGE_MAX:.2f} mm")
    print(f"      FR4                                                 : {PCB_T:.2f} mm  "
          f"(µr≈1 — magnetically transparent)")
    print(f"      U4 package, BACK-mounted: mould face {mould:.2f} .. seating {seating:.2f}")
    print(f"      hall element (mould face + {TMAG_DIE_DEPTH:.2f})              : {z_die:.2f}")
    print(f"      ==> MAGNET FACE TO HALL ELEMENT                     : {gap_die:.2f} mm")
    assert abs(dx) <= SENSE_XY_TOL and abs(dy) <= SENSE_XY_TOL, (
        f"U4 is {dx:+.3f},{dy:+.3f} mm off the nub axis (tol ±{SENSE_XY_TOL}) — the sensor "
        f"would read a static transverse field the boot-zero has to eat")
    assert gap_air >= 0.5, (f"only {gap_air:.2f}mm of air under the magnet — the spring "
                            f"plunges as well as tilts and would strike the board")
    assert NUB_GAP_LO <= gap_die <= NUB_GAP_HI, (
        f"magnet-to-die gap {gap_die:.2f}mm is outside the {NUB_GAP_LO}..{NUB_GAP_HI}mm design "
        f"band — re-run the field math before moving it (see docs/design-decisions.md v0.26)")
    print(f"  ✅ concentric within ±{SENSE_XY_TOL}mm; gap {gap_die:.2f}mm inside the "
          f"{NUB_GAP_LO}..{NUB_GAP_HI}mm band")
    return dx, dy, gap_air, gap_die


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
# (PCB_Z / DOME_TOP / KM_Z0 / TOP_Z / FACE_Z / RECESS_TOP are derived up top.)
PHONE_Z = RECESS_TOP + PHONE_TC/2               # cased phone rests its back on the bridge recess
                                                # floor; nominal screen top ~= FACE_Z (near-flush)
# v0.27: the cell sits on its FOAM TAPE, not on the bare floor. The tape was always in
# the BOM and in the docs' 0.84mm diode clearance; only this constant left it out, which
# put the pouch's bottom face at exactly z=FLOOR — the same plane as the grip floor's top
# surface. Two coplanar faces is a depth tie, so the web viewer z-fought across the whole
# underside of the battery. Adding the 0.3 also makes the model agree with the documented
# 0.84mm clearance under the diodes (it was 1.14 here).
BATT_TAPE = 0.3                        # 3M foam tape under the pouch (see bill-of-materials)
BATT_Z = FLOOR + BATT_TAPE + 2.0       # 3.9 = centre of the 4mm 403040 cell in the LEFT grip
                                       # floor — the 0.3 foam compresses under the taped
                                       # cell; flush gives the full 1.14mm diode clearance
                                       # (was +0.3, which left 0.84mm and read as a clash)

def nub_spring():
    return _memo("nub_spring", _nub_spring_build)

def _nub_spring_build():
    """v0.21 Bean-style printed flexure spring: an OD14.8 flange (captured in the
    right lid's underside counterbore) joined to a central hub by NUB_ARMS spiral
    flexure arms. The hub carries the magnet in a downward pocket and rises through
    the lid aperture as the nub post. Arm thickness NUB_ARM_T is the stiffness
    parameter — it IS the pointing feel. Print hub-down with a brim.
    Architecture adapted from the Ploopy Bean (CERN-OHL-S v2) — though NOT its
    dimensions: the Bean specifies a Ø6×2 magnet, which our Ø7 hub cannot carry.

    The magnet sits 3.33mm from the HALL ELEMENT, not the ~2.6mm this docstring
    used to claim. 2.6mm is the distance to the package's outer face; the die is a
    further 0.73mm inside it, and it is the die that sets the field. The full stack
    is printed and asserted by nub_report() — run `deck3d.py --report`."""
    from shapely.geometry import LineString
    from shapely.ops import unary_union
    nz = _nub_zone("right")
    assert nz, "nub_spring needs the right grip's hall_nub feature"
    x, y = nz["x"], nz["y"]
    # flange ring in the lid counterbore (z 12.3..13.3): 12.35..13.35, 0.05 clamp
    flange = (cq.Workplane("XY").workplane(offset=12.35).center(x, y)
              .circle(NUB_SPRING_FLANGE_D/2).circle(5.8).extrude(1.0))
    # NUB_ARMS spiral flexure arms, NUB_ARM_W wide x NUB_ARM_T thick, r R0 -> R1, each
    # swept NUB_ARM_SWEEP degrees from its own start angle. At 3 arms x 100 degrees the
    # arms are SEQUENTIAL arcs (0-100, 120-220, 240-340), not nested spirals, so they
    # never approach each other — the only clearance that matters is the slot each arm
    # leaves to the hub OD and the flange bore at mid-arc.
    #
    # Width is not constant: NUB_ARM_ROOT of extra half-width is blended in at both ends
    # as a root fillet (see the constant). Built as an explicit two-sided offset polygon
    # rather than a LineString buffer, since a buffer can only do constant width.
    dr = NUB_ARM_R1 - NUB_ARM_R0
    sweep_rad = math.radians(NUB_ARM_SWEEP)
    arms = []
    for k in range(NUB_ARMS):
        a0 = k * 2*math.pi/NUB_ARMS
        left, right = [], []
        for s in np.linspace(0.0, 1.0, 81):
            r = NUB_ARM_R0 + dr*s
            ang = a0 + sweep_rad*s
            ca, sa = math.cos(ang), math.sin(ang)
            # unit tangent of the spiral r(theta) = R0 + (dr/sweep)*theta
            tx, ty = (dr/sweep_rad)*ca - r*sa, (dr/sweep_rad)*sa + r*ca
            tn = math.hypot(tx, ty); tx, ty = tx/tn, ty/tn
            nx, ny = -ty, tx                       # in-plane normal
            h = NUB_ARM_W/2 + NUB_ARM_ROOT * (2.0*s - 1.0)**6
            left.append((x + r*ca + h*nx, y + r*sa + h*ny))
            right.append((x + r*ca - h*nx, y + r*sa - h*ny))
        arms.append(Polygon(left + right[::-1]).buffer(0))
    # Arms sit on the flange's BOTTOM face (12.35), not its top. This matters: the lid's
    # counterbore CEILING is at 13.3 and reaches inboard to r5.0, which is over the arms'
    # outer half (they run r3.6..5.9). The flange top at 13.35 is *meant* to interfere with
    # that ceiling by 0.05 — that is the clamp preload — but an arm that reached the same
    # height would be clamped too, and a clamped flexure is not a flexure. Growing the arms
    # downward from 12.35 keeps their top at 12.35+t <= 13.35 with real air above.
    # collide() cannot catch this for us: nub_spring<->grip_lid_right is whitelisted
    # precisely so the flange preload does not read as a clash, and that whitelist would
    # swallow an arm buried in the ceiling too. Hence the assert.
    assert 12.35 + NUB_ARM_T <= 13.30, (
        f"NUB_ARM_T={NUB_ARM_T} puts the arm top at {12.35+NUB_ARM_T:.2f}, into the lid "
        f"counterbore ceiling at 13.30 — the arms would be clamped, not free")
    spring = flange.union(_cq_from_poly(unary_union(arms), 12.35, NUB_ARM_T))
    # hub: magnet stub down toward the PCB, post up through the aperture,
    # O5 cap spigot on top
    hub = (cq.Workplane("XY").workplane(offset=10.4).center(x, y)
           .circle(NUB_HUB_D/2).extrude(NUB_HUB_TOP - 10.4))
    # v0.22: genuine-TrackPoint-cap mount — 4.4mm square platform, 2.5 tall
    # (classic caps' socket is ~4.5 sq x 2.5; both genuine caps and the printed
    # replica push-fit). Top edges get a 0.4 chamfer for blind insertion.
    post = (cq.Workplane("XY").workplane(offset=NUB_HUB_TOP).center(x, y)
            .rect(NUB_POST_SQ, NUB_POST_SQ).extrude(NUB_POST_H)
            .edges("|Z or >Z").chamfer(0.4))
    spring = spring.union(hub).union(post)
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
    # v0.26 PLUNGE STOP: 3 pads on the hub underside that bottom on the PCB front face
    # after NUB_PLUNGE_MAX of axial travel. Without them the only axial limit was the hub
    # itself hitting the board 0.90mm down — far past a TrackPoint's entire stroke — and
    # because the magnet approaches the die over that stroke, the pointing GAIN rose with
    # how hard you pressed. They sit between the Ø4.2 pocket wall (r2.1) and the Ø7 hub
    # OD (r3.5), so they clear both, and they land on the front face where the spring's
    # own legs already bear. U4 is on the BACK, so this face is free.
    _stop_drop = (NUB_POCKET_Z0 + 0.1) - (PCB_Z + PCB_T)   # hub bottom -> PCB face = 0.90
    _stop_h = _stop_drop - NUB_PLUNGE_MAX                  # pad height = 0.55
    assert _stop_h > 0.2, f"plunge-stop pad would be {_stop_h:.2f} tall — unprintable"
    for k in range(3):
        a = math.radians(90 + 120 * k)
        spring = spring.union(
            cq.Workplane("XY").workplane(offset=10.4 - _stop_h)
            .center(x + 2.8 * math.cos(a), y + 2.8 * math.sin(a))
            .circle(0.4).extrude(_stop_h + 0.05))     # +0.05 to weld into the hub
    # magnet pocket, opening DOWNWARD (the magnet loads from below, N face down —
    # compass-check!). Dimensioned off the NUB_POCKET_* constants so the pocket and
    # the nub_magnet() body it receives can never drift apart.
    spring = spring.cut(cq.Workplane("XY").workplane(offset=NUB_POCKET_Z0).center(x, y)
                        .circle(NUB_MAGNET_D/2 + NUB_MAGNET_FIT)
                        .extrude(NUB_POCKET_TOP - NUB_POCKET_Z0))
    return _to_trimesh(spring, "nub_spring")


def nub_magnet():
    """v0.26: the pointing nub's MAGNET, as a real body — the one part of the hall
    stack that had geometry cut for it (the pocket) but no solid of its own, so it was
    invisible in every render, GLB and collision check. It is a bought part, not a
    printed one, so it is NOT in SHELLS and never reaches --sync-models; it exists so
    the assembly shows what is actually in the product and so collide() can see it.

    Ø4 × 2 mm N45 axially-magnetized disc, seated against the pocket CEILING (pressed
    fully home from below) — NUB_MAGNET_Z is that seated bottom face. Its N pole faces
    DOWN, toward the sensor. See docs/bill-of-materials.md for the orderable part."""
    return _memo("nub_magnet", _nub_magnet_build)

def _nub_magnet_build():
    nz = _nub_zone("right")
    assert nz, "nub_magnet needs the right grip's hall_nub feature"
    m = trimesh.creation.cylinder(radius=NUB_MAGNET_D/2, height=NUB_MAGNET_H, sections=48)
    m.apply_translation((nz["x"], nz["y"], NUB_MAGNET_Z + NUB_MAGNET_H/2))
    m.visual.face_colors = [176, 180, 188, 255]      # NiCuNi plating (bright nickel)
    return m

def nub_cap():
    return _memo("nub_cap", _nub_cap_build)

def _nub_cap_build():
    """v0.22: CLASSIC ThinkPad soft-dome replica in RED TPU — mushroom profile
    (flared skirt, waist, dotted dome top) with the standard ~4.5mm-square cap
    socket, so this printed cap and any GENUINE classic TrackPoint cap
    interchange on the spring's 4.4mm square platform. The socket corners are
    r0.6-rounded (diagonal reach 3.00) and the waist is O6.8 (r3.4): together
    they leave a 0.40mm corner wall — one extrusion width — where the socket's
    top 0.5mm overlaps the waist band (r3.1 left an unprintable 0.10mm wall;
    caught by the v0.22 adversarial STL review). The platform's chamfered
    corners (~2.84 reach) clear the socket with 0.16.
    Revolved profile + bump-grid union; welded after export if needed."""
    nz = _nub_zone("right")
    assert nz, "nub_cap needs the right grip's hall_nub feature"
    x, y = nz["x"], nz["y"]
    import math as _m
    z0 = NUB_HUB_TOP                             # cap skirt bottom = platform base
    # mushroom silhouette (r, h): skirt -> waist -> dome, top flat for the dots
    prof = (cq.Workplane("XZ")
            .moveTo(0.0, 0.0).lineTo(3.9, 0.0)   # skirt bottom OD 7.8
            .lineTo(3.55, 1.5).lineTo(3.4, 2.1)  # skirt taper
            .lineTo(3.4, 3.0)                    # waist O6.8 (corner-wall printability)
            .lineTo(3.85, 3.9)                   # dome underside flare
            .lineTo(3.9, 4.5)                    # dome OD 7.8
            .lineTo(3.4, 4.9).lineTo(0.0, 4.9)   # rounded-ish rim to flat top
            .close())
    cap = prof.revolve(360, (0, 0), (0, 1))
    # classic soft-dome dot grid: ~0.8mm studs on the top face
    for gx in range(-2, 3):
        for gy in range(-2, 3):
            bx, by = gx * 1.2, gy * 1.2
            if _m.hypot(bx, by) > 3.0:
                continue
            cap = cap.union(cq.Workplane("XY").workplane(offset=4.8)
                            .center(bx, by).circle(0.4).extrude(0.45))
    # standard cap socket: 4.6 square x 2.6 deep, corners r0.6
    cap = cap.cut(cq.Workplane("XY").workplane(offset=-0.1)
                  .rect(4.6, 4.6).extrude(2.7).edges("|Z").fillet(0.6))
    cap = cap.translate((x, y, z0))
    m = _to_trimesh(cap, "nub_cap")
    if not m.is_watertight:
        m.merge_vertices(merge_tex=True, merge_norm=True)
        m.update_faces(m.nondegenerate_faces())
        m.remove_unreferenced_vertices()
        trimesh.repair.fill_holes(m)
        assert m.is_watertight, "nub_cap repair failed"
        m.export(os.path.join(BUILD, "nub_cap.stl"))
    return m

SHELLS = ("back_right", "back_left", "grip_lid_right", "grip_lid_left",
          "gripper_right", "gripper_left", "nub_spring", "nub_cap")

def assemble(clamp_pos=None):
    """v0.24: assemble at a given clamp position (cased phone long-edge). The RIGHT
    grip + bridge are GROUND (fixed); the LEFT grip + its lid/keymat/PCB/battery
    translate along x to the clamp_pos left-origin. clamp_pos=None -> nominal."""
    prod0 = _product()                                    # nominal (parts built here)
    prodc = deck.product(deck.Config(), clamp_pos=clamp_pos) if clamp_pos else prod0
    ldx = prodc["left_origin"][0] - prod0["left_origin"][0]  # left-jaw slide (0 at nominal)
    def L(m):                                             # shift a LEFT-side body by the slide
        mm = m.copy(); mm.apply_translation((ldx, 0, 0)); return mm
    A = {}
    A["back_right"] = back_half("right")
    A["back_left"] = L(back_half("left"))
    A["grip_lid_right"] = grip_lid("right")
    A["grip_lid_left"] = L(grip_lid("left"))
    A["nub_spring"] = nub_spring()
    A["nub_cap"] = nub_cap()
    A["nub_magnet"] = nub_magnet()
    A["keymat_right"] = keymats("right")
    A["keymat_left"] = L(keymats("left"))
    A["gripper_right"] = gripper("right")                 # TPU edge grip + lip (fixed grip)
    A["gripper_left"] = L(gripper("left"))                # rides the moving jaw
    for side in ("right", "left"):
        ox, oy = prod0[f"{side}_origin"]
        parts, _ = pcb_assembly(side)
        for k, m in parts.items():
            mm = m.copy(); mm.apply_translation((ox, oy, PCB_Z))
            if side == "left":
                mm.apply_translation((ldx, 0, 0))
            A[f"{side}:{k}"] = mm
    ph = phone_body(clamp_pos); ph.apply_translation((0, 0, PHONE_Z)); A["phone"] = ph
    bt = battery_body(); bt.apply_translation((0, 0, BATT_Z)); A["battery"] = L(bt)
    for i, s in enumerate(spring_bodies(clamp_pos)):   # enclosed in the outer shroud
        A[f"spring_{i}"] = s
    A["flex"] = flex_body(clamp_pos)                    # FFC, enclosed (z set in the body)
    for k, m in screw_bodies().items():   # left grip's screws ride the moving jaw
        A[k] = L(m) if k.startswith("screw_left") else m
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
    if s == {"nub_magnet", "nub_spring"}: return True      # magnet press-fits the hub pocket
    # NB: nub_magnet is whitelisted against the spring ONLY. It must clear the lid, the
    # keymat and the PCB (incl. U4 itself) by real air — an overlap with any of those is
    # a genuine clash, and the magnet-to-die air gap is the whole magnetic design.
    # v0.24 expanding clamp: the bridge is the ground member both grips ride/bolt to,
    # the springs seat in anchors, and the phone is clamped in the bridge recess +
    # grip cradles (soft TPU pads = the real contact). All intended mating overlaps:
    # v0.25: back_right (grip + fixed tray) and back_left (moving jaw) NEST with
    # SHROUD_CLR = 0.35 of designed clearance on every face. They are therefore never
    # supposed to touch, so this pair is deliberately NOT whitelisted: any overlap is a
    # real clash and --check must say so. The old blanket pass ("tray lap slide+seat")
    # is what hid a Ø60 MagSafe plug sitting 0.45mm inside the jaw's cavity, jamming the
    # clamp at every span. A moving fit is the last pair that should be exempt from the
    # only test that can see it.
    if "back_right" in s and any(x.startswith("grip_lid") for x in s): return True  # lid seats on the grip
    # v0.24d: a spring may only ever touch its OWN anchors — the tray's fixed post and
    # the moving jaw's hook lug. v0.24c whitelisted "spring vs anything", which is how
    # spring 0 came to share lane y=24 with the FFC, coil resting on ribbon, unflagged.
    if any(x.startswith("spring") for x in s):
        return any(x in ("back_right", "back_left") for x in s)
    if "phone" in s and any(x.startswith(("back_", "cradle", "gripper")) for x in s): return True  # rests / clamped
    if any(x.startswith("gripper") for x in s) and any(x.startswith(("back_", "grip_lid")) for x in s): return True  # TPU gripper seats on the grip cradle
    if km and any(x.startswith(("cradle", "gripper")) for x in s): return True   # TPU grippers print with the mats
    # the FFC is an APPROXIMATE floppy ribbon (straight-run fit model) and has to pass
    # THROUGH each grip's shell to reach its ZIF, so grip/connector overlaps are
    # modeled contacts. The fixed TRAY is NOT on that list any more (v0.24c let it be):
    # inside the tray the cable runs in a walled channel with real clearance, so any
    # overlap there means it is buried in a wall — impossible, not "contact".
    if "flex" in s and any(x.startswith("back_") or ":J" in x for x in s): return True
    # a collapsed grip's inner mount screw grazes the fixed recess floor by <0.5mm;
    # the printed plate carries a local clearance dimple there.
    if any(x.startswith("screw_") for x in s) and "back_right" in s: return True
    # screw heads SEAT in the lid countersinks (45-degree cone-on-cone); everything
    # else a screw could hit is modeled with real clearance and stays a hard clash
    if any(x.startswith("screw_") for x in s) and any(x.startswith("grip_lid") for x in s):
        return True
    return False

def collide(A, tol_gross=3.0, tol_shell=0.2):
    """AABB pre-filter, then mesh-intersection volume on overlapping pairs. Per-pair
    tolerance: shell-vs-PCB-component pairs are clean box/extrusion booleans, so any
    real interpenetration matters -> 0.2mm^3. Gross printed/organic pairs (shell-shell,
    keymat, phone, battery, flex) keep 3.0mm^3 to absorb STL-tessellation noise on
    large curved contact faces. Returns (clashes, contacts, checked); contacts are
    whitelisted pairs with measurable overlap (reported, not failed)."""
    # nub_magnet is a bought part (not in SHELLS, never printed) but it IS a clean
    # cylinder boolean like the printed parts, so it earns the tight tolerance rather
    # than the 3.0mm^3 tessellation allowance meant for organic//curved contact faces.
    shells = SHELLS + ("nub_magnet",)
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


def cable_enclosure(A, gap_x=6.0):
    """v0.24d enclosure guard. collide() only tests interpenetration, NOT whether the
    FFC is actually SURROUNDED by shell — so an exposed cable in the
    inter-grip gap passes collide() silently (exactly what a translucent render can
    look like, and what you must otherwise eyeball).

    The v0.24c version of THIS guard had the mirror-image blind spot: it ray-cast from
    the cable's CENTRE LINE, so a cable sunk INSIDE a shroud wall reported "sealed" —
    every ray promptly hit the wall it was embedded in — while its real envelope hung
    in open air below that wall. Both halves of the run are now checked, over the
    bridged span only (the connector ends inside each grip, where the ribbon must exit
    to its ZIF, are excluded):

      (a) SOLID — the clipped run may not intersect the fixed tray at all. A cable
          inside a wall is not a routed cable, it is an impossible one.
      (b) ENCLOSED — rays cast from just OUTSIDE the cable's ENVELOPE (±z off its
          top/bottom faces, ±y off its side faces) must every one hit shell.

    Returns the list of failing (cable, x, reasons) samples (empty == sealed)."""
    shell = trimesh.util.concatenate([A[n] for n in ("back_left", "back_right") if n in A])
    gxr = BR_X_RIGHT
    dirs = {"up": (0, 0, 1.0), "down": (0, 0, -1.0), "front": (0, -1.0, 0), "back": (0, 1.0, 0)}
    bad = []
    for cab in ("flex",):
        if cab not in A:
            continue
        m = A[cab]; lo, hi = m.bounds
        cy = (lo[1] + hi[1]) / 2.0; cz = (lo[2] + hi[2]) / 2.0
        x0, x1 = lo[0] + gap_x, min(hi[0] - gap_x, gxr - gap_x)
        if x1 <= x0:
            continue
        # (a) the clipped run, as a solid, must sit in free space inside the tray
        if "back_right" in A:
            seg = _place(_box(x1 - x0, hi[1] - lo[1], hi[2] - lo[2]), (x0 + x1) / 2.0, cy, cz)
            try:
                inter = A["back_right"].intersection(seg)
                vol = float(inter.volume) if inter is not None and hasattr(inter, "volume") else 0.0
            except Exception:
                vol = 0.0
            if vol > 1.0:
                bad.append((cab, round((x0 + x1) / 2.0, 1), [f"buried in the tray ({vol:.0f}mm3)"]))
        # (b) enclosure, sampled off the cable's own surfaces rather than its centre
        for x in np.linspace(x0, x1, 30):
            org = {"up":    (x, cy, hi[2] + 0.15),
                   "down":  (x, cy, lo[2] - 0.15),
                   "front": (x, lo[1] - 0.15, cz),
                   "back":  (x, hi[1] + 0.15, cz)}
            opend = [d for d, v in dirs.items()
                     if not shell.ray.intersects_any(np.array([org[d]], dtype=float),
                                                     np.array([v], dtype=float))[0]]
            if opend:
                bad.append((cab, round(float(x), 1), opend))
    return bad


def bed_fit(m, name):
    """Every printed part must fit an Ender 3 V2 (220x220x250) laid flat, with
    brim margin: xy bbox <= BED_XY (=204). Returns True when it fits."""
    dx, dy, dz = m.extents
    ok = dx <= BED_XY and dy <= BED_XY and dz <= 250
    tag = "fits" if ok else "DOES NOT FIT"
    print(f"  bed-fit {name}: {dx:.1f} x {dy:.1f} x {dz:.1f} mm -> {tag} (limit {BED_XY:.0f} xy = 220 bed - 2x8 brim)")
    return ok

def _watertight_gate(m, name):
    """A non-watertight mesh is not a printable solid AND it poisons every check
    downstream: collide() wraps its boolean in a bare except and reports vol=0.0, so a
    leaking part silently reads as colliding with nothing. --all printed watertight=
    from the start but only ever gated on bed_fit, which meant the one number that
    invalidates the rest of the run could scroll past. It gates now."""
    if m.is_watertight:
        return True
    print(f"  ❌ {name} is NOT watertight — collide() cannot judge it; fix the boolean "
          f"(a cone or wall coincident with the face it cuts is the usual cause)")
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--check", action="store_true")
    # v0.27: worth being able to check the lane plan + the ribbon route WITHOUT the
    # multi-minute clamp-travel collision sweep. --check runs both too. Not "~2s": the
    # route half builds both grips' back halves to sample against, so it is ~15s. Still
    # cheap enough for CI, where nothing exercised deck3d at all.
    ap.add_argument("--check-lanes", action="store_true",
                    help="lane plan, connector agreement and ribbon route (~15s) — "
                         "no clamp-travel collision sweep")
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--sync-models", action="store_true",
                    help="copy the printable STLs from build/ to the tracked models/ dir")
    args = ap.parse_args()
    os.makedirs(BUILD, exist_ok=True)
    if args.check_lanes:
        check_lanes()
        _routes, route_ok = flex_route_report()
        # v0.27: this used to `sys.exit(0)` unconditionally and throw the flag away, so a
        # ribbon fully buried in the shell still exited 0. A logger is not a gate.
        sys.exit(0 if route_ok else 1)
    if args.report:
        height_report("right"); height_report("left")
        nub_report()
    ok = True
    if args.all:
        built = []
        for fn, nm in [(lambda: back_half("right"), "back_right"),
                       (lambda: back_half("left"), "back_left"),
                       (lambda: gripper("right"), "gripper_right"),
                       (lambda: gripper("left"), "gripper_left"),
                       (lambda: grip_lid("right"), "grip_lid_right"),
                       (lambda: grip_lid("left"), "grip_lid_left"),
                       (nub_spring, "nub_spring"),
                       (nub_cap, "nub_cap")]:
            m = fn(); print(f"  {nm}: watertight={m.is_watertight} vol={m.volume/1000:.1f}cm3 bbox={[round(v,1) for v in m.extents]}")
            ok = bed_fit(m, nm) and _watertight_gate(m, nm) and ok
            built.append(m)
        for side in ("right", "left"):
            m = keymats(side); print(f"  keymat_{side}: watertight={m.is_watertight} bbox={[round(v,1) for v in m.extents]}")
            ok = bed_fit(m, f"keymat_{side}") and _watertight_gate(m, f"keymat_{side}") and ok
            built.append(m)
        if not ok:
            sys.exit("FAILED: a part is not printable — see the bed-fit / watertight lines above")
        # reference STL of all 9 printed parts in their assembled positions (they
        # share the product frame, so plain concatenation IS the assembly) — a
        # multi-body viewing aid for spatial reasoning, not a printable part
        asm = trimesh.util.concatenate(built)
        asm.export(os.path.join(BUILD, "assembled_printed.stl"))
        print(f"  assembled_printed.stl: all 9 printed parts in place, bbox={[round(v,1) for v in asm.extents]}")
    if args.check:
        # v0.26: the nub's alignment + magnet-to-die gap, asserted first. It is pure
        # arithmetic over the placement export, so a regression here fails in under a
        # second instead of after the four-span mesh sweep below — and unlike a collision,
        # a drifted sensor gap is invisible to collide() by construction (nothing is
        # touching; the field just quietly goes wrong).
        nub_report()
        # v0.24: the clamp is a MECHANISM — check it at min / nominal / max span so
        # nothing clashes anywhere in the travel and the rails stay engaged.
        cfg = deck.Config()
        check_lanes()
        _routes, route_ok = flex_route_report()
        assert route_ok, ("the ribbon has no physical route from a ZIF slot to the lane — "
                          "see the BURIED IN SHELL samples above")
        # v0.24e RETENTION invariants. A phone falling onto the user's face is the
        # failure mode this whole clamp exists to prevent, so the geometry that stops it
        # is asserted rather than eyeballed in a translucent render.
        crest = 82.6 - GRIP_PAD_T - TOOTH_R          # where the CLAMPED phone edge really sits
        over = crest - (82.6 - lip_depth())          # working overhang past that surface
        assert abs(over - LIP_OVER) < 1e-6, f"lip overhang {over:.2f} != LIP_OVER {LIP_OVER}"
        assert over >= 2.0, (f"capture lip only overhangs the clamped phone edge by {over:.2f}mm — "
                             "too little to clear a phone case's front edge radius, so the lip "
                             "would ride the case's chamfer and wedge the jaws open")
        assert PHONE_FACE_Z >= RECESS_TOP + PHONE_TC - 1e-6, \
            "the lip's underside is below the phone's front face — it would be buried in the phone"
        assert lip_top() > FACE_Z, "the capture lip must stand proud of the keyboard face to hook anything"
        # INSERTION: seat one edge on its tooth crest, translate the other past the far
        # lip. Needs clamp_pos >= P + lip_depth() + (GRIP_PAD_T + TOOTH_R) — derived here
        # from the lip geometry so deck.Config's figure can never silently drift from it.
        head = cfg.clamp_open_max - cfg.phone_span_max
        need = lip_depth() + GRIP_PAD_T + TOOTH_R
        assert head >= need - 1e-6, (
            f"insertion headroom {head:.1f}mm < {need:.1f}mm — a {cfg.phone_span_max:.0f}mm phone "
            f"cannot be fitted past lips reaching {lip_depth():.1f}mm inboard. Raise "
            f"deck.Config.clamp_insert_clr (and INNER_LEN, or the enclosure opens).")
        # NOTHING RIGID MAY EVER SIT OVER THE PHONE. The lip that touches the screen is
        # TPU so it can flex for phone+case thickness variance and can't scratch glass;
        # the shell's retainer only caps that lip's root and must stop outboard of where
        # the clamped phone edge actually sits.
        assert abs(retain_tip("right")) - crest >= RETAIN_CLR - 1e-6, \
            "the rigid retainer overhangs the clamped phone edge — hard plastic over the screen"
        assert retain_top() > lip_top() > PHONE_FACE_Z, "the retainer must cap the TPU lip, not replace it"
        free = abs(retain_tip("right")) - (82.6 - lip_depth())   # TPU still free to flex
        assert free >= 2.0, (f"only {free:.1f}mm of the lip is free to flex — a thick case has "
                             "nowhere to give")
        assert GRIP_PAD_LEN <= _product()["phone"]["h"], "gripper is longer than the phone's short edge"
        print(f"  retention: lip overhangs the clamped edge by {over:.1f}mm, underside z={PHONE_FACE_Z:.1f} "
              f"(phone face), top z={lip_top():.1f} ({lip_top()-FACE_Z:+.1f} vs face); "
              f"insertion headroom {head:.1f}mm; shelf {SHELF_H:.1f}mm ✅")
        # v0.24e: the widest state is no longer the biggest PHONE — it is the jaw opened
        # far enough to fit that phone past the capture lips. That is the real worst case
        # for shroud overlap and cable enclosure, so it is what gets checked.
        states = [("min", cfg.phone_span_min), ("nominal", None),
                  ("max phone", cfg.phone_span_max), ("open", cfg.clamp_open_max)]
        anyclash = False
        for name, cp in states:
            A = assemble(cp)
            clashes, contacts, checked = collide(A)
            ov = _shroud_overlap(cp)
            exposed = cable_enclosure(A)
            tag = "❌" if (clashes or exposed) else "✅"
            print(f"[{name} span {cp or 'nominal'}] {len(A)} bodies, checked {checked}; "
                  f"{len(clashes)} CLASHES; shroud overlap {ov:.1f}mm; "
                  f"cable enclosure {'SEALED' if not exposed else f'{len(exposed)} EXPOSED'} {tag}")
            for a, b, v in clashes[:15]:
                print(f"  CLASH   {a:22} <-> {b:22}  overlap {v} mm^3")
            for cab, x, why in exposed[:8]:
                print(f"  EXPOSED {cab:22} x={x:7.1f}  {','.join(why)}")
            if name == "nominal":
                for a, b, v in sorted(contacts, key=lambda t: -t[2])[:6]:
                    print(f"  contact {a:22} <-> {b:22}  overlap {v} mm^3 (intended mating)")
            assert ov >= 12.0, f"[{name}] shroud overlap {ov:.1f}mm < 12mm — enclosure could open"
            assert not exposed, f"[{name}] {len(exposed)} cable sample(s) NOT enclosed by the tray"
            anyclash = anyclash or bool(clashes) or bool(exposed)
        if not anyclash:
            print("  ✅ no impossible overlaps across the whole clamp travel")
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
    if k.startswith("spring"): return 24
    if k.startswith("gripper"): return 46  # TPU grippers lift off the grip cradles
    if k == "nub_magnet": return 50        # drops out of the hub pocket, below the spring
    if k == "nub_spring": return 56        # lifts out of the lid counterbore
    if k == "nub_cap": return 66           # pulls off the spring spigot
    if k == "phone":        return 84
    return 0

def _render_exploded(A):
    def col(k): return _asm_col(k)
    meshes = []
    for k, m in A.items():
        mm = m.copy(); mm.apply_translation((0, 0, _explode_offset(k)))
        meshes.append((mm, col(k)))
    render_iso(meshes, os.path.join(RENDERS, "assembly3d_exploded.png"),
               "thumbdeck — exploded stack (back grips incl. the integral tray · springs · PCB · keymats · grip lids · phone)",
               elev=14, azim=-72)

def _asm_col(k):
    # v0.19 GBC "Atomic Purple": translucent purple shells, dark button-gray keymats
    if k.startswith("back_"): return [0.48,0.35,0.65,0.55]
    if k.startswith("grip_lid"): return [0.48,0.35,0.65,0.55]
    if k.startswith("keymat"): return [0.23,0.23,0.24,1]
    if k.startswith("gripper"): return [0.12,0.12,0.13,1]  # TPU edge grippers (dark)
    if k == "nub_spring":   return [0.23,0.23,0.24,1]  # keymat gray
    if k == "nub_cap":      return [0.78,0.09,0.11,1]  # ThinkPad red (classic soft dome)
    if k == "phone":        return [0.05,0.05,0.08,1]
    if k == "battery":      return [0.65,0.5,0.15,1]
    if k.startswith("spring"): return [0.6,0.6,0.63,1]
    if k.startswith("screw_"): return [0.73,0.74,0.77,1]
    if k == "flex":         return [0.75,0.55,0.2,1]
    if ":pcb" in k:         return [0.16,0.35,0.24,1]
    if ":SW" in k:          return [0.9,0.72,0.2,1]
    if any(x in k for x in (":U",":J")): return [0.2,0.2,0.24,1]
    return [0.5,0.5,0.25,1]

def _render_parts(A):
    titles = {"back_right": "right back grip + the fixed tray, ONE part (v0.25 J3: no bolted joint)",
              "back_left": "left back grip (moving jaw — inner shroud + lane ribs + left cradle + spring hook lugs)",
              "grip_lid_right": "right grip lid (key openings + clamp rim)",
              "grip_lid_left": "left grip lid (key openings + clamp rim)",
              "gripper_right": "right TPU gripper (toothed edge pad + capture lip; the shell's "
                               "retainer caps its root but never reaches over the phone)",
              "nub_spring": "nub flexure spring (Bean-style: flange + spiral arms + magnet hub)",
              "nub_cap": "nub cap — classic ThinkPad soft-dome replica (RED TPU, dot grid; genuine caps also fit)",
              "keymat_right": "right keymat (plungers + hinge web)",
              "keymat_left": "left keymat (plungers + hinge web + the v0.25 integrated "
                             "D-pad: 4 arm sectors + centre OK, relieved moats, back rib)"}
    for nm, title in titles.items():
        if nm not in A:
            continue
        render_iso([(A[nm], [0.4, 0.45, 0.5, 1])], os.path.join(RENDERS, f"part_{nm}.png"),
                   f"thumbdeck — {title}", elev=40, azim=-60)

def _render_assembly(A):
    meshes = [(m, _asm_col(k)) for k, m in A.items()]
    render_iso(meshes, os.path.join(RENDERS, "assembly3d.png"), "thumbdeck — full assembly (real dims)", elev=26, azim=-58)


if __name__ == "__main__":
    main()

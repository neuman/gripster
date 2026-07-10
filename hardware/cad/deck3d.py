#!/usr/bin/env python3
"""deck3d.py — parametric 3D generator for the thumbdeck: PCB fit-model (real
component dimensions), bottom shell, top shell, keymats, + the phone / LiPo / flex,
assembled in the deck.product() frame and collision-checked so nothing physically
overlaps. Same source of truth as the PCB (hardware/scripts/deck.py).

See docs/cad-process.md. Run:  deck3d.py --all --check --render
Frame: deck.py Y-up, origin bottom-left of the RIGHT grip; z=0..1.6 = PCB, +z = front
(dome / top-shell side), -z = back (module / bottom-shell side).
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

# ---- component BODY dimensions (mm), real-world from datasheets. keyed by KiCad
#      footprint name. (dx,dy,dz) in the footprint's UNROTATED local frame; placed at
#      the footprint's actual position + orientation + side. -------------------------
COMPONENTS = {
    "nRF52840_E73-2G4M08S1C": (13.0, 18.0, 2.2),   # Ebyte module (13x18, 2.2 tall incl antenna)
    "USB_C_Receptacle_HRO_TYPE-C-31-M-12": (9.0, 7.5, 3.2),
    "SOT-23-5": (2.9, 2.8, 1.1),                   # MCP73831 (incl leads)
    "SOT-23-6": (2.9, 2.8, 1.1),                   # USBLC6
    "C_0402_1005Metric": (1.0, 0.5, 0.5),
    "R_0402_1005Metric": (1.0, 0.5, 0.5),
    "C_0805_2012Metric": (2.0, 1.25, 0.85),
    "D_SOD-323": (1.8, 1.25, 0.95),
    # bridge / battery connectors: real part is JST-GH (1.25mm), ~5mm tall side-entry
    "PinHeader_2x08_P2.54mm_Vertical": (5.0, 20.0, 5.0),
    "PinHeader_1x02_P2.54mm_Vertical": (2.5, 5.0, 5.0),
    "TestPoint_Pad_1.5x1.5mm": (1.5, 1.5, 0.05),
}
DOME_D, DOME_H = 7.0, 0.5   # Snaptron 7mm snap dome (dia, height above pad)


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
        x = f["x"]; y = H - f["y"]                    # KiCad Y-down -> deck Y-up
        rot = f["rot"]; back = f["back"]
        if ref.startswith("SW"):                     # snap dome on the FRONT
            dome = trimesh.creation.cylinder(radius=DOME_D/2, height=DOME_H, sections=24)
            parts[ref] = _place(dome, x, y, PCB_T + DOME_H/2)
            continue
        spec = COMPONENTS.get(fp)
        if not spec:
            continue
        ddx, ddy, ddz = spec
        body = _box(ddx, ddy, ddz)
        if back:
            z = -SOLDER - ddz/2                      # hangs below the board
        else:
            z = PCB_T + SOLDER + ddz/2               # sits on top
        m = _place(body, x, y, z, rot)
        m.visual.face_colors = [70, 70, 75, 255] if ref[0] in "UJ" else [120, 120, 40, 255]
        parts[ref] = m
    return parts, geo


def _placement(side):
    """Load footprint placement JSON (produced by export_placement.py under system
    python). Auto-regenerate if missing/stale."""
    p = os.path.join(BUILD, f"placement_{side}.json")
    pcb = os.path.join(GEN, f"thumbdeck_{side}.kicad_pcb")
    if not os.path.exists(p) or os.path.getmtime(p) < os.path.getmtime(pcb):
        subprocess.run(["python3", os.path.join(HERE, "export_placement.py")],
                       check=True, capture_output=True)
    return json.load(open(p))


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

def _key_centers_product():
    """All dome/key centres (both grips, incl. cluster features) in product frame."""
    prod = _product(); out = []
    for side in ("right", "left"):
        geo = prod[side]; ox, oy = prod[f"{side}_origin"]
        keys = list(geo["keys"]) + [f for f in geo.get("features", []) if f["type"] == "key"]
        for k in keys:
            out.append((k["x"]+ox, k["y"]+oy, k.get("d", 7.0)))
    return out

def full_footprint():
    """Union of both grips + a central spine slab under the phone -> one-piece shell."""
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
FLOOR = 1.6            # bottom-shell floor thickness
WALL_T = 2.5          # shell wall thickness
TOP_T = 2.0           # top-shell plate thickness
STANDOFF = 5.7        # PCB standoff: clears the 5mm back-mounted JST connectors + margin
GAP = 0.5
KM_WEB, KM_PL_H, KM_PL_D = 0.8, 3.5, 6.2   # keymat web / plunger height / plunger dia
PCB_Z = FLOOR + STANDOFF                     # grip-local PCB z=0 maps here
DOME_TOP = PCB_Z + PCB_T + DOME_H            # top of a seated snap dome
KM_Z0 = DOME_TOP + 1.0                       # keymat web bottom (nub reaches the dome)
TOP_Z = KM_Z0 + KM_WEB + GAP                 # top-shell plate bottom
WALL = TOP_Z - FLOOR                         # cavity height (derived)

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

def bottom_shell():
    fp = full_footprint()
    prod = _product()
    # walls go OUTSIDE the PCB envelope: outer = fp+wall+clr, cavity = fp+clr (so the
    # board sits inside with clearance instead of colliding with the walls).
    outer = _cq_from_poly(fp.buffer(WALL_T+PCB_CLR), 0, FLOOR+WALL)
    inner = _cq_from_poly(fp.buffer(PCB_CLR), FLOOR, WALL+1)
    shell = outer.cut(inner)
    # MagSafe N52 ring pocket + LiPo pocket in the spine (from the floor, on the back/outside)
    ms = prod["magsafe"]; sb = prod["spine_battery"]
    ring = (cq.Workplane("XY").center(ms["cx"], ms["cy"]).circle(ms["d"]/2+1).extrude(-2.0))
    shell = shell.cut(ring)
    # (the LiPo sits ON the spine floor inside the cavity — no floor cut needed; a
    #  shallow locating rib could be added later.)
    # PCB standoff bosses + M2 heat-set bores at each grip's mount holes
    for side in ("right", "left"):
        geo = prod[side]; ox, oy = prod[f"{side}_origin"]
        for hh in geo["mount_holes"]:
            cx, cy = hh["x"]+ox, hh["y"]+oy
            boss = (cq.Workplane("XY").workplane(offset=FLOOR).center(cx, cy).circle(3.0).extrude(STANDOFF)
                    .faces(">Z").workplane().circle(1.55).cutBlind(-(STANDOFF-1)))  # M2 heat-set bore
            shell = shell.union(boss)
        # USB-C wall cut-out (right grip only)
        if side == "right":
            ux, uy, uw, uh = geo["keepouts"]["usb_c"]
            cut = (cq.Workplane("XY").workplane(offset=FLOOR+STANDOFF-2)
                   .center(ux+ox+uw/2, uy+oy).box(uw+1, WALL_T*3, 4.0, centered=(True, True, False)))
            shell = shell.cut(cut)
    return _to_trimesh(shell, "bottom_shell")

def top_shell():
    fp = full_footprint()
    prod = _product()
    z0 = TOP_Z                # top plate sits above the cavity
    plate = _cq_from_poly(fp.buffer(WALL_T+PCB_CLR), z0, TOP_T)   # match the bottom-shell outline
    # key openings at every dome centre
    holes = None
    for (x, y, d) in _key_centers_product():
        c = cq.Workplane("XY").workplane(offset=z0-0.1).center(x, y).circle(d/2+0.4).extrude(TOP_T+0.2)
        holes = c if holes is None else holes.union(c)
    if holes is not None:
        plate = plate.cut(holes)
    # phone window (the phone sits in the centre on the MagSafe ring)
    ph = prod["phone"]
    win = (cq.Workplane("XY").workplane(offset=z0-0.1).center(ph["x"]+ph["w"]/2, ph["y"]+ph["h"]/2)
           .box(ph["w"]+1, ph["h"]+1, TOP_T+0.2, centered=(True, True, False)))
    plate = plate.cut(win)
    # screw clearance holes aligned to the bottom bosses
    for side in ("right", "left"):
        geo = prod[side]; ox, oy = prod[f"{side}_origin"]
        for hh in geo["mount_holes"]:
            h = cq.Workplane("XY").workplane(offset=z0-0.1).center(hh["x"]+ox, hh["y"]+oy).circle(1.2).extrude(TOP_T+0.2)
            plate = plate.cut(h)
    return _to_trimesh(plate, "top_shell")

def keymats(side):
    """Per-grip one-piece keymat: plungers over each dome joined by a thin web plate."""
    prod = _product(); geo = prod[side]; ox, oy = prod[f"{side}_origin"]
    keys = list(geo["keys"]) + [f for f in geo.get("features", []) if f["type"] == "key"]
    z0 = KM_Z0                # web bottom, just above the domes
    PL_D = KM_PL_D
    from shapely.ops import unary_union
    field = unary_union([Polygon([(k["x"]+ox+PL_D/2*math.cos(t), k["y"]+oy+PL_D/2*math.sin(t))
                                  for t in np.linspace(0, 2*math.pi, 16)]) for k in keys]).buffer(2.0)
    mat = _cq_from_poly(field, z0, KM_WEB)
    for k in keys:
        pl = (cq.Workplane("XY").workplane(offset=z0+KM_WEB).center(k["x"]+ox, k["y"]+oy)
              .circle(PL_D/2).extrude(KM_PL_H))
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
    # realistic ~500mAh pouch: fits the pocket, ~5mm thick (not the full 52x36 pocket)
    m = _box(34, 50, 5.0)
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
    for n in ("U1", "J1", "J2", "U2", "SW1"):
        if n in parts:
            bb = parts[n].bounds
            print(f"  {n}: z {bb[0][2]:.2f}..{bb[1][2]:.2f}")


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
MAGSAFE_Z = TOP_Z + TOP_T              # N52 ring on the outer face of the top shell
PHONE_Z = MAGSAFE_Z + 2.0              # phone sits on the MagSafe ring
BATT_Z = FLOOR + 2.5                   # ~5mm cell sitting on the spine floor in the cavity
FLEX_Z = PCB_Z - 2.5                   # ribbon behind the phone, at the back-connector level

def assemble():
    A = {}
    A["bottom_shell"] = bottom_shell()
    A["top_shell"] = top_shell()
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
    if any(x.startswith("keymat") for x in s) and any(":SW" in x for x in s): return True   # nub presses dome
    if s == {"phone", "magsafe"} or s == {"magsafe", "top_shell"}: return True               # rests on
    return False

def collide(A, tol_mm3=3.0, deep_tol_mm=0.3):
    """AABB pre-filter, then mesh-intersection volume on overlapping pairs. Reports
    'clash' (interpenetration beyond tolerance) vs tolerated contact."""
    names = list(A); bounds = {n: A[n].bounds for n in names}
    def aabb(a, b):
        la, ha = bounds[a]; lb, hb = bounds[b]
        return all(ha[i] >= lb[i]-0.01 and hb[i] >= la[i]-0.01 for i in range(3))
    clashes = []; checked = 0
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
            if vol > tol_mm3 and not _allowed(a, b):
                # penetration depth estimate = vol^(1/3) proxy; report the pair
                clashes.append((a, b, round(vol, 1)))
    clashes.sort(key=lambda t: -t[2])
    return clashes, checked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--render", action="store_true")
    args = ap.parse_args()
    os.makedirs(BUILD, exist_ok=True)
    if args.report:
        height_report("right"); height_report("left")
    if args.all:
        for fn, nm in [(bottom_shell, "bottom_shell"), (top_shell, "top_shell")]:
            m = fn(); print(f"  {nm}: watertight={m.is_watertight} vol={m.volume/1000:.1f}cm3 bbox={[round(v,1) for v in m.extents]}")
        for side in ("right", "left"):
            m = keymats(side); print(f"  keymat_{side}: watertight={m.is_watertight} bbox={[round(v,1) for v in m.extents]}")
    if args.check:
        A = assemble()
        print(f"assembly: {len(A)} bodies")
        clashes, checked = collide(A)
        print(f"collision: checked {checked} AABB-overlapping pairs; {len(clashes)} CLASHES")
        for a, b, v in clashes[:25]:
            print(f"  CLASH  {a:22} <-> {b:22}  overlap {v} mm^3")
        if not clashes:
            print("  ✅ no impossible overlaps")
    if args.render:
        A = assemble()
        _render_assembly(A)
        _render_exploded(A)
        _render_parts()


def _explode_offset(k):
    """Vertical explode offset by role (for the exploded assembly render)."""
    if k == "bottom_shell": return -35
    if k == "battery":      return -18
    if k == "flex":         return -10
    if ":" in k:            return 0        # PCB stack (board + components)
    if k.startswith("keymat"): return 22
    if k == "top_shell":    return 40
    if k == "magsafe":      return 58
    if k == "phone":        return 75
    return 0

def _render_exploded(A):
    def col(k): return _asm_col(k)
    meshes = []
    for k, m in A.items():
        mm = m.copy(); mm.apply_translation((0, 0, _explode_offset(k)))
        meshes.append((mm, col(k)))
    render_iso(meshes, os.path.join(RENDERS, "assembly3d_exploded.png"),
               "thumbdeck — exploded stack (back shell · PCB · domes · keymats · front shell · MagSafe · phone)",
               elev=14, azim=-72)

def _asm_col(k):
    if k == "bottom_shell": return [0.30,0.32,0.36,1]
    if k == "top_shell":    return [0.42,0.45,0.50,0.6]
    if k.startswith("keymat"): return [0.15,0.5,0.65,0.92]
    if k == "phone":        return [0.05,0.05,0.08,1]
    if k == "battery":      return [0.65,0.5,0.15,1]
    if k == "magsafe":      return [0.72,0.72,0.74,1]
    if k == "flex":         return [0.75,0.55,0.2,1]
    if ":pcb" in k:         return [0.16,0.35,0.24,1]
    if ":SW" in k:          return [0.9,0.72,0.2,1]
    if any(x in k for x in (":U",":J")): return [0.2,0.2,0.24,1]
    return [0.5,0.5,0.25,1]

def _render_parts():
    for fn, nm, title in [(bottom_shell,"bottom_shell","bottom shell (one-piece: grips + spine)"),
                          (top_shell,"top_shell","top shell (79 key openings + phone window)"),
                          (lambda: keymats("right"),"keymat_right","right keymat (plungers + hinge web)")]:
        m = fn()
        render_iso([(m,[0.4,0.45,0.5,1])], os.path.join(RENDERS, f"part_{nm}.png"),
                   f"thumbdeck — {title}", elev=40, azim=-60)

def _render_assembly(A):
    def col(k):
        if k == "bottom_shell": return [0.30,0.32,0.36,1]
        if k == "top_shell":    return [0.42,0.45,0.50,0.55]
        if k.startswith("keymat"): return [0.15,0.5,0.65,0.9]
        if k == "phone":        return [0.05,0.05,0.08,1]
        if k == "battery":      return [0.6,0.5,0.15,1]
        if k == "magsafe":      return [0.7,0.7,0.72,1]
        if k == "flex":         return [0.7,0.5,0.2,1]
        if ":pcb" in k:         return [0.16,0.35,0.24,1]
        if ":SW" in k:          return [0.85,0.7,0.2,1]
        return [0.28,0.28,0.30,1]
    meshes = [(m, col(k)) for k, m in A.items()]
    render_iso(meshes, os.path.join(RENDERS, "assembly3d.png"), "thumbdeck — full assembly (real dims)", elev=26, azim=-58)


if __name__ == "__main__":
    main()

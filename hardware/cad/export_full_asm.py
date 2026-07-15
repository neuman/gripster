#!/usr/bin/env python3
"""export_full_asm.py — one full-build assembly GLB with SEPARATE NESTED OBJECTS.

Produces models/thumbdeck_full_asm.glb: a named node hierarchy (opens as an
object tree in Blender / any glTF viewer):

    thumbdeck_v018
    ├── shells/            back_left, back_right (pink) · grip_lid_* (cyan)
    │                      center_panel (pink)          — concept-sketch colors
    ├── keymats/           keymat_left, keymat_right (purple)
    ├── pcb_right/         board/ (KiCad-generated: real Edge.Cuts body, copper
    │   │                  tracks+pads, soldermask, silkscreen — exported by
    │   │                  kicad-cli from the routed .kicad_pcb, consolidated
    │   │                  by material)
    │   └── components/    every placed part (E73, USB-C, FFC, JST, switches,
    │                      diodes, passives) as its real-dimension fit body,
    │                      plus the 37 snap domes
    ├── pcb_left/          same (42 domes + FFC)
    ├── screws/            the 10 M2x10 pan-head shell screws (top-in, at the
    │                      deck.build mount bosses — 5 per grip)
    ├── battery            403040 pouch in the left grip (sketch tan)
    ├── flex               FFC jumper in the floor channel (ribbon amber)
    ├── magsafe_ring       N52 ring in the well recess
    └── phone              cased S25 Ultra, screen flush at z 14.3

Run under the CAD venv (needs trimesh); the two board GLBs must exist first:

  kicad-cli pcb export glb --force --include-tracks --include-pads \
      --include-zones --include-silkscreen --include-soldermask \
      --no-components -o build/pcb_<side>_kicad.glb \
      ../kicad/generated/thumbdeck_<side>.kicad_pcb

(this script re-exports them automatically when missing/stale).

KiCad GLB frame (verified empirically against the dome-pad grid): metres,
glTF Y-up — x = board x, y = board thickness (+y = front), z = KiCad y
(y-DOWN board frame). Product-frame mapping is rotX(+90) . scale(1000), then
translate by (grip origin, +board_h, PCB_Z).

ALL transforms are BAKED into the mesh vertices — every node in the exported
tree carries an identity transform. Deliberate: minimal glTF viewers honour only
TRS properties and silently ignore `matrix` node transforms (the first cut of
this file put group transforms in node matrices, and such a viewer rendered the
boards as a raw plate at the origin and the components hovering outside the
back shell). With baked vertices the hierarchy is pure named grouping and no
viewer can misplace anything.
"""
import os, subprocess, sys
import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import deck3d  # noqa: E402  (brings in deck + the z-stack constants)
import deck    # noqa: E402

BUILD = os.path.join(HERE, "build")
MODELS = os.path.join(HERE, "models")
GEN = os.path.join(HERE, "..", "kicad", "generated")
OUT = os.path.join(MODELS, "thumbdeck_full_asm.glb")

# ---- colors: concept sketches (sketches/side.png, All.png) where possible ----
COL = {
    "back":   [209, 92, 128, 255],   # pink back halves + center panel
    "panel":  [242, 122, 158, 217],
    "lid":    [64, 191, 204, 210],   # cyan grip lids
    "keymat": [140, 115, 217, 235],  # purple keymats
    "battery": [199, 184, 148, 255], # tan pouch (sketch battery)
    "flex":   [230, 140, 51, 255],   # amber ribbon (sketch wiring)
    "ring":   [184, 184, 189, 255],
    "phone":  [18, 18, 24, 255],
    "dome":   [212, 175, 55, 255],   # gold snap domes on ENIG
    "comp":   [56, 56, 62, 255],     # component bodies
    "conn":   [88, 88, 96, 255],     # connectors (J1/J2/J3)
    "screw":  [186, 189, 195, 255],  # M2 pan-head shell screws (steel)
}

def _kicad_glb(side):
    """Board GLB from kicad-cli (regenerate if missing or older than the PCB)."""
    glb = os.path.join(BUILD, f"pcb_{side}_kicad.glb")
    pcb = os.path.join(GEN, f"thumbdeck_{side}.kicad_pcb")
    if not os.path.exists(glb) or os.path.getmtime(glb) < os.path.getmtime(pcb):
        subprocess.run(["kicad-cli", "pcb", "export", "glb", "--force",
                        "--include-tracks", "--include-pads", "--include-zones",
                        "--include-silkscreen", "--include-soldermask",
                        "--no-components", "-o", glb, pcb], check=True,
                       capture_output=True)
    return glb

def _mat_label(rgba):
    """Human label for a KiCad material color (best-effort)."""
    r, g, b = rgba[:3]
    if g > r and g > b:
        return "soldermask"
    if r > 200 and g > 200 and b > 200:
        return "silkscreen"
    if r > 150 and g > 110 and b < 90:
        return "copper"
    return "board_body"

def _board_merged(side):
    """Load the KiCad board GLB and consolidate its ~14k geometries into a few
    meshes bucketed by material color (mm scale, still in the GLB frame)."""
    sc = trimesh.load(_kicad_glb(side))
    buckets = {}
    for node in sc.graph.nodes_geometry:
        T, gname = sc.graph[node]
        g = sc.geometry[gname]
        try:
            c = g.visual.material.baseColorFactor
            key = tuple(int(v) for v in np.array(c[:4]))
        except Exception:
            key = (128, 128, 128, 255)
        m = g.copy()
        m.apply_transform(T)
        buckets.setdefault(key, []).append(m)
    out = []
    for key, meshes in sorted(buckets.items(), key=lambda kv: -len(kv[1])):
        m = trimesh.util.concatenate(meshes)
        m.apply_scale(1000.0)                    # m -> mm
        m.visual = trimesh.visual.ColorVisuals(m, face_colors=list(key))
        out.append((_mat_label(key), m))
    # disambiguate duplicate labels
    seen = {}
    named = []
    for lbl, m in out:
        n = seen.get(lbl, 0)
        seen[lbl] = n + 1
        named.append((f"{lbl}_{n}" if n else lbl, m))
    return named

def _frame_T(side, prod):
    """GLB(mm, after scale) -> product frame: rotX(+90deg) then translate."""
    ox, oy = prod[f"{side}_origin"]
    H = prod[side]["board_h"]
    T = np.eye(4)
    T[:3, :3] = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float)  # rotX(+90)
    T[:3, 3] = [ox, oy + H, deck3d.PCB_Z]
    return T

def _grip_T(side, prod):
    ox, oy = prod[f"{side}_origin"]
    T = np.eye(4)
    T[:3, 3] = [ox, oy, deck3d.PCB_Z]
    return T

def _stl(name):
    return trimesh.load(os.path.join(BUILD, f"{name}.stl"))

def _add(scene, mesh, name, parent, color=None, transform=None):
    """Add one mesh under `parent`, BAKING any transform into the vertices so
    the node itself stays identity (viewer-proof; see module docstring)."""
    m = mesh.copy()
    if transform is not None:
        m.apply_transform(transform)
    if color is not None:
        m.visual = trimesh.visual.ColorVisuals(m, face_colors=color)
    scene.add_geometry(m, node_name=name, geom_name=name,
                       parent_node_name=parent)

def main():
    prod = deck._last_prod = deck.product(deck.Config())
    scene = trimesh.Scene()
    root = "thumbdeck_v018"
    scene.graph.update(frame_to=root, matrix=np.eye(4))
    for grp in ("shells", "keymats", "pcb_right", "pcb_left"):
        scene.graph.update(frame_to=grp, frame_from=root, matrix=np.eye(4))

    # shells + keymats (printed parts, sketch colors)
    for n, col in (("back_left", COL["back"]), ("back_right", COL["back"]),
                   ("center_panel", COL["panel"]),
                   ("grip_lid_left", COL["lid"]), ("grip_lid_right", COL["lid"])):
        _add(scene, _stl(n), n, "shells", col)
    for n in ("keymat_left", "keymat_right"):
        _add(scene, _stl(n), n, "keymats", COL["keymat"])

    # boards: KiCad-generated body/copper/mask/silk + deck3d component bodies
    for side in ("right", "left"):
        grp = f"pcb_{side}"
        boardT = _frame_T(side, prod)
        gripT = _grip_T(side, prod)
        scene.graph.update(frame_to=f"{grp}/board", frame_from=grp, matrix=np.eye(4))
        for lbl, m in _board_merged(side):
            _add(scene, m, f"{grp}/board/{lbl}", f"{grp}/board", transform=boardT)
        scene.graph.update(frame_to=f"{grp}/components", frame_from=grp, matrix=np.eye(4))
        parts, _geo = deck3d.pcb_assembly(side)
        for ref, m in parts.items():
            if ref.startswith("pcb_"):
                continue                          # board solid replaced by KiCad's
            if ref.startswith("SW") and not ref.endswith(("_pwr", "_rst")):
                col = COL["dome"]
            elif ref.startswith("J"):
                col = COL["conn"]
            else:
                col = COL["comp"]
            _add(scene, m, f"{grp}/components/{ref}", f"{grp}/components", col,
                 transform=gripT)

    # the 10 shell screws (already in product frame, z-placed by screw_bodies)
    scene.graph.update(frame_to="screws", frame_from=root, matrix=np.eye(4))
    for n, m in deck3d.screw_bodies().items():
        _add(scene, m, f"screws/{n}", "screws", COL["screw"])

    # loose bodies
    bt = deck3d.battery_body(); bt.apply_translation((0, 0, deck3d.BATT_Z))
    _add(scene, bt, "battery", root, COL["battery"])
    fx = deck3d.flex_body(); fx.apply_translation((0, 0, deck3d.FLEX_Z))
    _add(scene, fx, "flex", root, COL["flex"])
    ms = deck3d.magsafe_ring(); ms.apply_translation((0, 0, deck3d.MAGSAFE_Z))
    _add(scene, ms, "magsafe_ring", root, COL["ring"])
    ph = deck3d.phone_body(); ph.apply_translation((0, 0, deck3d.PHONE_Z))
    _add(scene, ph, "phone", root, COL["phone"])

    os.makedirs(MODELS, exist_ok=True)
    scene.export(OUT)
    b = scene.bounds
    print(f"wrote {OUT}")
    print(f"  nodes: {len(scene.graph.nodes)}  geoms: {len(scene.geometry)}")
    print(f"  bounds mm: {np.round(b[0],2)} .. {np.round(b[1],2)}  extents {np.round(b[1]-b[0],2)}")
    return scene

if __name__ == "__main__":
    main()

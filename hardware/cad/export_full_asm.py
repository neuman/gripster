#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Eric Neuman
"""export_full_asm.py — one full-build assembly GLB with SEPARATE NESTED OBJECTS.

Produces models/thumbdeck_full_asm.glb: a named node hierarchy (opens as an
object tree in Blender / any glTF viewer):

    thumbdeck_v019
    ├── shells/            back_left, back_right, grip_lid_*, bridge (v0.24 tray) —
    │                      translucent GBC "Atomic Purple" PBR material
    ├── keymats/           keymat_left, keymat_right + gripper_* (GBC dark, TPU)
    ├── pcb_right/         board/ (KiCad-generated: real Edge.Cuts body, copper
    │   │                  tracks+pads, soldermask, silkscreen — exported by
    │   │                  kicad-cli from the routed .kicad_pcb, consolidated
    │   │                  by material)
    │   └── components/    every placed part (E73, USB-C, FFC, JST, switches,
    │                      diodes, passives) as its real-dimension fit body,
    │                      plus the 37 snap domes
    ├── pcb_left/          same (42 domes + FFC)
    ├── screws/            the M3x10 flush-countersunk shell screws (top-in:
    │                      5 per grip lid) + 2 short M3 bridge-to-grip bolts
    ├── battery            403040 pouch in the left grip (sketch tan)
    ├── flex               FFC jumper in the enclosed tray channel (ribbon amber)
    └── phone/             real Samsung S25 Ultra model (assets/s25_ultra.glb,
                           own materials incl. screen texture) — screen faces OUT
                           (+z), camera bump flush with the panel's well floor

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

# ---- colors: v0.19 Game Boy Color "Atomic Purple" (feedback item 5) ----------
# Shells are TRANSLUCENT purple via a real glTF PBR material (baseColorFactor is
# LINEAR-space RGBA; [0.198,0.102,0.381] = sRGB #7B5AA6, alpha 0.55, alphaMode
# BLEND + doubleSided so the guts show through in Blender/three.js). Keymats are
# the GBC's dark-gray buttons, opaque. Everything else keeps vertex colors.
SHELL_MAT = trimesh.visual.material.PBRMaterial(
    name="atomic_purple", baseColorFactor=[0.198, 0.102, 0.381, 0.55],
    metallicFactor=0.0, roughnessFactor=0.35, alphaMode="BLEND", doubleSided=True)
KEYMAT_MAT = trimesh.visual.material.PBRMaterial(
    name="gbc_button_gray", baseColorFactor=[0.042, 0.042, 0.048, 1.0],
    metallicFactor=0.0, roughnessFactor=0.65)
# v0.22: the nub cap is a classic ThinkPad soft-dome replica — signature red
NUBCAP_MAT = trimesh.visual.material.PBRMaterial(
    name="trackpoint_red", baseColorFactor=[0.55, 0.008, 0.012, 1.0],
    metallicFactor=0.0, roughnessFactor=0.8)
COL = {
    "battery": [199, 184, 148, 255], # tan pouch (sketch battery)
    "flex":   [230, 140, 51, 255],   # amber ribbon (sketch wiring)
    "ring":   [184, 184, 189, 255],
    "phone":  [18, 18, 24, 255],
    "dome":   [212, 175, 55, 255],   # gold snap domes on ENIG
    "comp":   [56, 56, 62, 255],     # component bodies
    "conn":   [88, 88, 96, 255],     # connectors (J1/J2/J3)
    "screw":  [186, 189, 195, 255],  # M3 flush-countersunk shell screws (steel)
    "magnet": [176, 180, 188, 255],  # NiCuNi-plated NdFeB nub magnet (bright nickel)
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

def _add(scene, mesh, name, parent, color=None, transform=None, material=None):
    """Add one mesh under `parent`, BAKING any transform into the vertices so
    the node itself stays identity (viewer-proof; see module docstring).
    `material` (a PBRMaterial) wins over `color` — used for the translucent
    Atomic-Purple shells and the GBC-gray keymats."""
    m = mesh.copy()
    if transform is not None:
        m.apply_transform(transform)
    if material is not None:
        m.visual = trimesh.visual.TextureVisuals(material=material)
    elif color is not None:
        m.visual = trimesh.visual.ColorVisuals(m, face_colors=color)
    scene.add_geometry(m, node_name=name, geom_name=name,
                       parent_node_name=parent)

PHONE_GLB = os.path.join(HERE, "assets", "s25_ultra.glb")

def _add_phone(scene, root, prod):
    """Insert the real Samsung S25 Ultra model (assets/s25_ultra.glb) in place of
    the old black slab, KEEPING its own materials (screen texture, glass, cameras).
    The source model's axes: X = thickness (+X = screen face, -X = camera bump),
    Y = length, Z = width. Placement: screen faces OUT (+z, out the keyboard face).

    v0.24e — the DATUM changed, and it matters. This used to seat the camera-bump tip
    on the recess floor, a leftover from the v0.18 rigid well (which had a bump pocket).
    Under the v0.24 clamp the phone is CASED and rests on its case back, and every
    retention dimension is referenced to `deck3d.PHONE_FACE_Z` — the front face of a
    nominal cased phone. Seating by the bump put this model's screen 0.82mm above that
    plane, so the capture lip rendered buried in the phone even when it was correctly
    placed against the fit model. The screen is now pinned to PHONE_FACE_Z, so the GLB
    and the fit model agree and the lip reads as it is built.

    Consequence, deliberately left visible: this is a BARE S25U whose camera bump stands
    ~2.0mm proud of its back, while a 1.2mm case back only covers 1.2mm of that — so the
    bump now shows ~0.8mm INTO the flat tray. That is a real interference, not a render
    artifact: a flat full-width tray cannot accept a phone whose bump exceeds its case
    thickness. See docs/design-decisions.md (v0.24e, "camera bump vs the flat tray").
    All transforms baked into the vertices (viewer-proof; see module docstring)."""
    psc = trimesh.load(PHONE_GLB)
    nodes = list(psc.graph.nodes_geometry)
    full = trimesh.util.concatenate(
        [psc.geometry[psc.graph[n][1]].copy().apply_transform(psc.graph[n][0]) for n in nodes])
    ext = full.extents
    s = deck.Config().phone_h / ext[1]              # scale model Y (length) -> 162.8mm
    # rotate: model X(thick,+screen) -> product +Z(up/out); Y(len) -> +X; Z(width) -> +Y
    R = np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0], [0, 0, 0, 1]], float)
    S = np.diag([s, s, s, 1.0])
    M = R @ S
    probe = full.copy(); probe.apply_transform(M); bb = probe.bounds
    ctr = (bb[0] + bb[1]) / 2
    tx, ty = -ctr[0], (prod["phone"]["y"] + prod["phone"]["h"]/2) - ctr[1]  # x=0, y = phone centre
    tz = deck3d.PHONE_FACE_Z - bb[1][2]               # SCREEN (max z) -> the cased-phone front face
    T = np.eye(4); T[:3, 3] = [tx, ty, tz]
    Mfull = T @ M
    scene.graph.update(frame_to="phone", frame_from=root, matrix=np.eye(4))
    for n in nodes:
        Tn, gn = psc.graph[n]
        g = psc.geometry[gn].copy()
        g.apply_transform(Mfull @ Tn)                 # bake full transform into vertices
        scene.add_geometry(g, node_name=f"phone/{gn}", geom_name=f"phone_{gn}",
                           parent_node_name="phone")
    fb = full.copy(); fb.apply_transform(Mfull)
    print(f"  phone: S25U {fb.extents[0]:.1f}x{fb.extents[1]:.1f}x{fb.extents[2]:.1f}mm, "
          f"screen z={fb.bounds[1][2]:.2f} (PHONE_FACE_Z {deck3d.PHONE_FACE_Z:.2f}, lip underside), "
          f"bump tip z={fb.bounds[0][2]:.2f} (recess floor {deck3d.RECESS_TOP:.2f} "
          f"-> {deck3d.RECESS_TOP - fb.bounds[0][2]:+.2f} interference)")

def main():
    prod = deck._last_prod = deck.product(deck.Config())
    scene = trimesh.Scene()
    root = "thumbdeck_v019"
    scene.graph.update(frame_to=root, matrix=np.eye(4))
    for grp in ("shells", "keymats", "pcb_right", "pcb_left"):
        scene.graph.update(frame_to=grp, frame_from=root, matrix=np.eye(4))

    # shells + keymats (printed parts, GBC Atomic-Purple / button-gray materials)
    for n in ("back_left", "back_right",
              "grip_lid_left", "grip_lid_right", "nub_spring"):
        _add(scene, _stl(n), n, "shells", material=SHELL_MAT)
    _add(scene, _stl("nub_cap"), "nub_cap", "shells", material=NUBCAP_MAT)
    for n in ("keymat_left", "keymat_right", "gripper_left", "gripper_right"):
        _add(scene, _stl(n), n, "keymats", material=KEYMAT_MAT)   # TPU parts

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

    # the 14 shell screws (already in product frame, z-placed by screw_bodies)
    scene.graph.update(frame_to="screws", frame_from=root, matrix=np.eye(4))
    for n, m in deck3d.screw_bodies().items():
        _add(scene, m, f"screws/{n}", "screws", COL["screw"])

    # loose bodies
    bt = deck3d.battery_body(); bt.apply_translation((0, 0, deck3d.BATT_Z))
    _add(scene, bt, "battery", root, COL["battery"])
    # v0.26: the nub magnet is a BOUGHT part, not a printed one, so it comes from
    # deck3d directly rather than from an STL — but it is a real body in the product
    # and belongs in the tree (it was previously represented only by the hole cut for
    # it in nub_spring, i.e. not at all).
    _add(scene, deck3d.nub_magnet(), "nub_magnet", root, COL["magnet"])
    _add(scene, deck3d.flex_body(), "flex", root, COL["flex"])          # FFC (enclosed)
    _add(scene, deck3d.power_body(), "power", root, [217, 51, 40, 255]) # battery power cable (enclosed)
    for i, sp in enumerate(deck3d.spring_bodies()):   # v0.24 clamp extension springs (enclosed)
        _add(scene, sp, f"spring_{i}", root, COL["ring"])
    _add_phone(scene, root, prod)

    os.makedirs(MODELS, exist_ok=True)
    scene.export(OUT)
    b = scene.bounds
    print(f"wrote {OUT}")
    print(f"  nodes: {len(scene.graph.nodes)}  geoms: {len(scene.geometry)}")
    print(f"  bounds mm: {np.round(b[0],2)} .. {np.round(b[1],2)}  extents {np.round(b[1]-b[0],2)}")
    return scene

if __name__ == "__main__":
    main()

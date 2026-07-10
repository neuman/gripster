# 3D CAD process (shells, keymats, PCB assembly) — reusable

How the printable 3D parts and the fit-check assembly are generated. The guiding
principle: **one parametric source of truth.** The PCB is generated from
[`hardware/scripts/deck.py`](../hardware/scripts/deck.py); the 3D parts are generated
from the *same* `deck.py` geometry, so key openings land on dome pads, bosses land on
mount holes, and the USB cut-out lands on the connector — by construction, not by
hand-measuring.

## Toolchain

| Role | Tool | Why |
|---|---|---|
| **Generate** parts | **CadQuery** (OpenCASCADE, Python) | Parametric B-rep solids, true mm, fillets/pockets/bosses; imports `deck.py` directly; exports **STEP** (engineering/verify/share) + **STL/3MF** (print). |
| **Verify** (fast loop) | **trimesh** + **manifold3d** | Watertight/manifold, min wall thickness, and **collision detection** (pairwise mesh interference) across the whole assembly. |
| **Render** | matplotlib (headless) | 6-view part sheets + assembly / exploded views (no GPU needed). |
| **Final audit / organic finish** (optional) | **Blender** 3D-Print-Toolbox | Wall-thickness heatmap, overhang/bridge, non-manifold; comfort fillets. Run headless: `blender --background --python <script>`. |
| Slice | Bambu Studio / PrusaSlicer | Consume the exported **3MF** at true mm. |

Environment (reproducible): `hardware/cad/requirements.txt` → a venv at
`hardware/cad/.venv` (git-ignored). Everything runs headless.

## Pipeline (per iteration)

```
deck.py geometry ─▶ deck3d.py (CadQuery) ─▶ STEP + STL/3MF per part
                                         └▶ trimesh/manifold3d checks:
                                              • watertight / manifold
                                              • min wall thickness
                                              • ASSEMBLY COLLISIONS (no impossible overlap)
                                              • alignment asserts vs the KiCad board
                                         └▶ matplotlib renders (parts + assembly)
   ▲                                                   │
   └──────────── tweak shells/keymats, re-run ◀────────┘   (change the PCB only if unavoidable)
```

## Parts, all from `deck.py`

- **PCB assembly (fit model)** — board extruded from the outline (1.6 mm) with every
  placed component as a solid at its real datasheet dimensions (heights in the
  `COMPONENTS` spec table in `deck3d.py`), plus snap-domes, the LiPo cell, and the
  bridge flex. Used for collision-checking the shells against real hardware.
- **Bottom shell** — one-piece tray (both grips + central spine): walls, PCB
  standoffs + **M2 heat-set bosses** at the mount coords, USB-C wall cut-out at the
  `usb_c` keepout, **MagSafe N52 ring + LiPo pockets** in the spine.
- **Top shell** — face plate: **79 key openings at the exact dome centres**, phone
  window, screw holes aligned to the bottom bosses, MagSafe seat.
- **Keymats** (per grip, TPU 95A) — keycap plungers over the dome centres joined by
  **living-hinge webs**; each plunger nub actuates its dome. Print a 3×3 coupon to
  tune travel + hinge fatigue before the full mat.

## Fit rules the collision check enforces

Two solids may **touch** (mating faces, a plunger resting on a dome) but must not
**interpenetrate** by more than a small tolerance. The check reports any pair whose
mesh-intersection volume exceeds the tolerance, classified as *contact* (OK) vs
*clash* (fix). Intended stack (bottom→top): back shell → PCB on standoffs → domes on
pads → retention sheet → keymat plungers → front shell openings; phone on the MagSafe
ring over the spine; LiPo + magnets in the spine; bridge flex behind the phone.

## Run

```bash
hardware/cad/.venv/bin/python hardware/cad/deck3d.py --all      # build every part + assembly
hardware/cad/.venv/bin/python hardware/cad/deck3d.py --check    # collision + printability report
hardware/cad/.venv/bin/python hardware/cad/deck3d.py --render   # PNG part sheets + assembly views
```

Outputs land in `hardware/cad/build/` (STEP/STL/3MF, git-ignored) and `renders/`.

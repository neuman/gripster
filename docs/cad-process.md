# 3D CAD process (shells, keymats, PCB assembly) — rev-A / v0.16

**v0.16 shell split.** The shells are now **five printed parts** instead of two,
so every part prints flat on a **Creality Ender 3 V2 (220 × 220 mm)** — the old
one-piece shells were 306 × 120 mm and did not fit that bed at any rotation. The
split follows the concept sketches (`sketches/All.png`, `side.png`): **cyan grip
lids** left + right, a **pink back** (two halves joined at x=0), and a **pink
center front panel** — "the front of the back" — carrying the phone pocket and
MagSafe recess. Staggered splices keep every cross-section continuous: the
screwed-on panel bridges the back seam at x=0, and the back halves bridge the
front reveal seams at the grip edges. The build enforces this: `--all` asserts
every part's bbox ≤ 204 mm (220 minus 2 × 8 mm brim).

How the printable 3D parts and the fit-check assembly are generated. The guiding
principle: **one parametric source of truth.** The PCB is generated from
[`hardware/scripts/deck.py`](../hardware/scripts/deck.py); the 3D parts
([`hardware/cad/deck3d.py`](../hardware/cad/deck3d.py)) are generated from the
*same* `deck.py` geometry **plus the real KiCad placement**, so key openings land
on dome pads, bosses land on mount holes, and the USB-C / switch / pinhole / LED
openings land on the actual connectors — by construction, not by hand-measuring.

## Toolchain

| Role | Tool | Why |
|---|---|---|
| **Generate** parts | **CadQuery** (OpenCASCADE, Python) | Parametric B-rep solids, true mm, fillets/pockets/bosses; imports `deck.py` directly; exports **STEP** (engineering/verify/share) + **STL** (print). |
| **Verify** (fast loop) | **trimesh** + **manifold3d** | Watertight/manifold, min wall thickness, and **collision detection** (pairwise mesh interference) across the whole assembly. |
| **Render** | matplotlib (headless) | 6-view part sheets + assembly / exploded views (no GPU needed). |
| **Final audit / organic finish** (optional) | **Blender** 3D-Print-Toolbox | Wall-thickness heatmap, overhang/bridge, non-manifold; comfort fillets. Run headless: `blender --background --python <script>`. |
| Slice | Bambu Studio / PrusaSlicer | Consume the exported **STL** at true mm. |

Environment (reproducible): `hardware/cad/requirements.txt` → a venv at
`hardware/cad/.venv` (git-ignored). Everything runs headless.

## Pipeline (per iteration)

```
deck.py geometry ─▶ deck3d.py (CadQuery) ─▶ STEP + STL per part
                                         └▶ trimesh/manifold3d checks:
                                              • watertight / manifold
                                              • min wall thickness
                                              • ASSEMBLY COLLISIONS (no impossible overlap)
                                              • alignment asserts vs the KiCad board
                                         └▶ matplotlib renders (parts + assembly)
   ▲                                                   │
   └──────────── tweak shells/keymats, re-run ◀────────┘   (change the PCB only if unavoidable)
```

## The height stack (rev-A, verified)

Bottom → top per grip: **floor 1.6 | back cavity 6.3 | PCB 1.6 | domes 0.5 |
keymat | front plate**. The 6.3 mm PCB standoff is sized by the tallest back-side
part — the **mated JST-PH battery connector** (6.0 mm) + 0.24 mm margin. Grip body
comes out **14.3 mm** thick, the spine **16.9 mm** (panel plate 2.6 mm — thickened
in v0.16 so the MagSafe recess leaves a 0.8 mm printed web instead of one 0.2 mm
layer), **22.9 mm** including the mounted phone.

## Parts, all from `deck.py` + the placed board

- **PCB assembly (fit model)** — board extruded from the outline (1.6 mm) with
  every placed component as a solid at its real datasheet height (the
  `SPECS` table in `deck3d.py`), plus snap-domes (0.5 mm), a realistic
  ~500 mAh pouch cell, and the FFC jumper. Used for collision-checking the shells
  against real hardware — `--check` reports **0 collisions**. Caveat: the bridge
  ribbon is modeled ~2 mm below its physical run in the fit-check (clearances in
  that region are ≥4 mm, so it was not re-modeled).
- **Back halves (`back_left` / `back_right`)** — the tray split at **x=0**
  (mid-spine), each half = one grip bay + half the spine (~161 × 120 mm max):
  walls, 6.3 mm PCB standoffs + **M2 heat-set bosses (3.2 mm bores, 5/grip)** at
  the mount coords, and **3 support posts per grip under the key field** so the
  PCB no longer flexes between perimeter bosses under thumb load.
  Through-features cut from the **real part placement**: a **13.5 × 7.0 mm USB-C
  wall opening** centred on the connector with a stepped outer relief for the
  plug overmold, an **8 × 2.8 mm slide-switch slot** in the bottom wall, a
  **1.6 mm reset pinhole** and a **1.5 mm charge-LED light hole** in the floor
  (both located from the placed SW91/D80), and a **0.6 mm antenna wall relief**
  at the E73 edge. The LiPo sits on the spine floor spanning the seam (adhere it
  to ONE half only). **Seam joinery is printed and screwless**: two
  full-floor-thickness tabs (right) into cleared notches (left) register the
  halves in-plane, each perimeter wall gets an **8 mm vertical shiplap**
  (vertical faces — print clean flat; 0.25 mm clearance), and a 0.4 mm 45° V
  along the outer seam doubles as elephant-foot relief + shadow line. New in
  v0.16: a **transverse spine wall at each grip boundary** (with FFC and
  battery-lead pass-throughs) closes each half's torsion box, seats the panel
  edge, and carries a **Ø8 boss at MagSafe-ring height**.
- **Grip lids (`grip_lid_left` / `grip_lid_right`)** — per-grip face plates
  (~79 × 120 mm), cyan in the concept: **key openings at the exact dome
  centres** and a **rim that clamps the keymat web with ~0.1 mm preload** so the
  mat can't float or rattle; the **5 screw positions per grip are unchanged**
  from rev-A. The inner edge is cut straight at the grip boundary with a 0.8 mm
  top chamfer (its half of the reveal V). Print cosmetic-face-down.
- **Center panel (`center_panel`)** — the pink "front of the back"
  (~147 × 120 mm, 2.6 mm plate + 2.0 mm plateau): phone in a **2.0 mm-deep
  pocket in the raised plateau**, open at the x-ends — the grips abut the
  phone's short ends, the pocket rim captures its long edges. Inside the pocket
  floor: a **Ø57 × 1.8 mm recess** for the Ø56 N52 MagSafe ring — the 2.0 mm
  ring sits 0.2 mm proud, the phone rests on ring + pocket floor, and a
  **0.8 mm printed web** (4 layers) remains under the recess. A deliberate
  **0.3 mm reveal gap** separates panel from lids (no overlap → no screw-head
  clash, no mid-air mating faces; prints back-face-down, support-free). It is
  the **bolted splice for the x=0 back seam and the spine service hatch**:
  4 M2 screws into floor bosses straddling the seam + 2 M2 screws at
  **ring height** into the transverse-wall bosses (heads sink 1.4 mm below the
  pocket floor, under the phone). Remove 6 screws → battery + FFC exposed,
  grips untouched.
- **Keymats** (per grip, TPU 95A) — keycap plungers over the dome centres joined
  by **living-hinge webs**; each plunger nub actuates its dome; the web edge is
  what the grip lid's rim clamps. Print a 3×3 coupon to tune travel + hinge
  fatigue before the full mat.

## Fit rules the collision check enforces

Two solids may **touch** (mating faces, a plunger resting on a dome) but must not
**interpenetrate** by more than a small tolerance. The check reports any pair whose
mesh-intersection volume exceeds the tolerance, classified as *contact* (OK) vs
*clash* (fix). Intended stack (bottom→top): back halves (tabs + wall shiplaps at
x=0) → PCB on standoffs + posts → domes on pads → retention tape → keymat
plungers → grip lids (rim on the web) → center panel (on the transverse walls +
bosses, bridging the back seam); phone in the panel pocket on the MagSafe ring;
LiPo on the spine floor; FFC jumper across the spine (through the transverse-wall
windows) behind the phone. The back-half pair and the lid↔keymat rims are the
whitelisted contacts; the back-seam interpenetration is additionally asserted ~0.

## Run

```bash
hardware/cad/.venv/bin/python hardware/cad/deck3d.py --all          # build all 7 parts + Ender 3 V2 bed-fit gate
hardware/cad/.venv/bin/python hardware/cad/deck3d.py --check        # collision + printability report
hardware/cad/.venv/bin/python hardware/cad/deck3d.py --render       # PNG part sheets + assembly views
hardware/cad/.venv/bin/python hardware/cad/deck3d.py --sync-models  # copy printable STLs to tracked models/
```

Outputs land in `hardware/cad/build/` (STEP/STL, git-ignored) and `renders/`;
`--sync-models` refreshes the git-tracked STL snapshots in `hardware/cad/models/`
(the printable deliverables for a fresh clone).

## Printing (Ender 3 V2, PLA or PETG, 0.4 nozzle / 0.2 layers)

| Part | Orientation | Notes |
|---|---|---|
| `back_left`, `back_right` | floor down | 6 mm brim (long parts warp at the seam corners); no supports |
| `grip_lid_left/right` | **cosmetic face down** | rim downstands face up; no supports |
| `center_panel` | **back face down** | pocket + recess face up; no supports |
| `keymat_left/right` | web down (TPU 95A) | as before |

Slicer: ~0.12 mm elephant-foot compensation keeps the printed seam faces true;
the modeled 0.25–0.3 mm joint clearances assume roughly that. Solid infill on the
panel (it is only 2.6–4.6 mm thick) stiffens the MagSafe pocket floor.

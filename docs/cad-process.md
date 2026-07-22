# 3D CAD process (shells, keymats, PCB assembly) — rev-A / v0.19

**v0.18 flush-screen well + battery relocation (2026-07-14).** The center panel is
now a **sunken tray**: its border flange tops out flush with the grip lids
(z 14.7) and the phone — a real **S25 Ultra in a 1.2 mm thin case** (dims in
`deck.Config`) — drops into a well whose floor puts the **screen surface exactly
in the lids' keyboard-face plane**. Same MagSafe recess construction as before,
translated 10.2 mm down. Consequences handled in the same pass: the **LiPo moved
to the left grip cavity** (403040 under the passive PCB — only 0.5 mm remained
under the well), the **FFC bridge crosses in a 0.5 mm floor channel** under the
well slab, the transverse walls are cut to sills over the well span, the
ring-height panel anchors are gone (4 border screws + slab stiffness take the
MagSafe detach pull; 4 floor nubs take down-press), and an R9 thumb scallop in
the top border tips the phone out (v0.19: a closed curved finger dish — no
opening into the interior). Device: 15.7 mm max thickness (was 22.9 before
v0.18), one continuous 14.7 mm front plane. v0.19 also closes the well's
x-ends with 1.6 mm end walls and countersinks all 14 face screws (M3, flush).

**v0.17 regeneration (2026-07-14).** All parts regenerated for the re-proportioned
97 mm Rii-height grips: keymat plungers / lid openings are now the **rectangular
8.5 × 7 mm keycaps** (18.5 mm 2u space; cluster keys stay round Ø6.2/Ø7.8), the
USB-C opening + power-switch slot + antenna wall relief moved to the **top** wall,
the slide-knob direction is derived from the placed footprint rotation, panel seam
screws are derived from the phone-pocket span, and every cluster key now gets a
**3 mm living-hinge strip** tying it into the keymat web (nearest grid key +
nearest other feature, as the 2D concept always drew — previously the cluster
plungers were silently disconnected islands; the web now asserts single-piece
connectivity). `--all --check`: all 7 parts watertight + bed-fit, assembly incl. the 14 M3 CSK screws,
**0 collisions**.

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

## The height stack (rev-A / v0.19, verified)

Per grip, bottom → top: **floor 1.6 | back cavity 6.3 | PCB 1.6 | domes 0.5 |
keymat | lid** → keyboard face at **z 14.7**, keycaps 1.0 proud (15.7). The 6.3 mm
PCB standoff is sized by the tallest back-side part — the **mated JST-PH battery
connector** (6.0 mm) + 0.24 mm margin. In the spine (v0.19): FFC duct 1.1..1.6 |
well slab 2.5..5.1 (2.6 mm thick; ring recess floor 3.3, 0.8 mm web) | N52 ring
3.3..5.3 (0.2 proud of the 5.1 well floor) | **cased phone 5.3..14.7 — screen
flush with the lids** (5.3 + 9.4 mm cased phone = 14.7). The whole
device is **15.7 mm** thick (keycap tops); there is no plateau above the front
plane any more.

## Parts, all from `deck.py` + the placed board

- **PCB assembly (fit model)** — board extruded from the outline (1.6 mm) with
  every placed component as a solid at its real datasheet height (the
  `SPECS` table in `deck3d.py`), plus snap-domes (0.5 mm), a realistic
  ~500 mAh pouch cell, and the FFC jumper. Used for collision-checking the shells
  against real-dimension component models — datasheet heights, not a physical
  build — `--check` reports **0 collisions**. Caveat: the bridge
  ribbon is modeled ~2 mm below its physical run in the fit-check (clearances in
  that region are ≥4 mm, so it was not re-modeled).
- **Back halves (`back_left` / `back_right`)** — the tray split at **x=0**
  (mid-spine), each half = one grip bay + half the spine (170.5/162.8 × 103.8 mm):
  walls, 6.3 mm PCB standoffs + **M3 heat-set bosses (Ø7.5, 4.0 mm bores, 5/grip)** at
  the mount coords, and **3 support posts per grip under the key field** so the
  PCB no longer flexes between perimeter bosses under thumb load.
  Through-features cut from the **real part placement**: a **13.5 × 7.0 mm USB-C
  wall opening** centred on the connector with a stepped outer relief for the
  plug overmold (both in the TOP wall since v0.17), an **8 × 2.8 mm slide-switch
  slot** in the top wall, a
  **1.6 mm reset pinhole** and a **1.5 mm charge-LED light hole** in the floor
  (both located from the placed SW91/D80), and a **0.6 mm antenna wall relief**
  at the E73 edge (top wall — closed, 1.9 mm remains), plus the v0.18 **FFC floor
  channel** (0.5 mm recess, 19 mm lane at the J2 band) and **battery-lead windows**
  in both transverse walls. The **403040 LiPo sits on the LEFT grip's floor**
  under the passive PCB (v0.18 — the sunken well displaced it from the spine).
  **Seam joinery is printed and screwless**: two
  full-floor-thickness tabs (right) into cleared notches (left) register the
  halves in-plane, each perimeter wall gets an **8 mm vertical shiplap**
  (vertical faces — print clean flat; 0.25 mm clearance), and a 0.4 mm 45° V
  along the outer seam doubles as elephant-foot relief + shadow line. New in
  v0.16: a **transverse spine wall at each grip boundary** (with FFC and
  battery-lead pass-throughs) closes each half's torsion box, seats the panel
  edge, and carries a **Ø8 boss at MagSafe-ring height**.
- **Grip lids (`grip_lid_left` / `grip_lid_right`)** — per-grip face plates
  (77.9 × 103.8 mm), Atomic-Purple: **rounded-rect key openings at the exact
  dome centres** (cap + 0.2 mm/side; round for the cluster keys) and a **rim that clamps the keymat web with ~0.1 mm preload** so the
  mat can't float or rattle; the **5 screw positions per grip are unchanged**
  from rev-A. The inner edge is cut straight at the grip boundary with a 0.8 mm
  top chamfer (its half of the reveal V). Print cosmetic-face-down.
- **Center panel (`center_panel`)** — the pink "front of the back", v0.18 a
  **sunken tray** (~169 × 102.8 mm): border flange 12.3..14.7 flush with
  the lids, then a deep well whose floor slab (2.1..4.7) puts the **cased
  phone's screen exactly in the keyboard-face plane (14.7)**. v0.19: closed at the
  x-ends — the grips' PCB/lid inner edges stop the phone (0.3 mm/side); the
  2.0 mm well wall band captures its long edges; an R9 thumb scallop in the top
  border tips it out. In the well floor: the **Ø57 × 1.8 mm recess** for the
  Ø56 N52 MagSafe ring — the 2.0 mm ring sits 0.2 mm proud, the phone rests on
  it, and a **0.8 mm printed web** (4 layers) remains under the recess; 4 floor
  nubs below the slab carry down-press into the back floor. A deliberate
  **0.3 mm reveal gap** separates panel from lids (no overlap → no screw-head
  clash, no mid-air mating faces; prints back-face-down, support-free). It is
  the **bolted splice for the x=0 back seam and the spine service hatch**:
  4 M3 countersunk screws into Ø8 floor bosses straddling the seam + (until v0.18) 2 more at
  **ring height** into the transverse-wall bosses (heads sink 1.4 mm below the
  pocket floor, under the phone). Remove the 4 panel screws → FFC exposed, grips
  untouched; since v0.18 the battery lives in the **left grip** and is serviced
  there, not behind this panel.
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
plungers → grip lids (rim on the web) → center panel (border on the walls +
bosses, bridging the back seam; slab on its floor nubs); phone sunk in the well
on the MagSafe ring, screen flush at 14.7; LiPo on the LEFT grip floor under the
passive PCB; FFC jumper across the spine in the 0.5 mm floor channel under the
well slab. The back-half pair and the lid↔keymat rims are the
whitelisted contacts; the back-seam interpenetration is additionally asserted ~0.

## The full nested assembly (`models/thumbdeck_full_asm.glb`)

`export_full_asm.py` (CAD venv) emits the whole build as ONE glTF/GLB with a
**named node hierarchy** — shells/keymats/pcb_right/pcb_left/battery/flex/ring/
phone as separate nested objects, openable as an object tree in Blender or any
glTF viewer. The two boards are **KiCad-generated** (`kicad-cli pcb export glb`
per routed `.kicad_pcb`: real board body, copper tracks + pads, soldermask,
silkscreen — consolidated by material into board_body/copper/soldermask/
silkscreen sub-objects); every placed component + snap dome rides on top as its
real-dimension fit body under `pcb_<side>/components/<REF>`. Printed parts use
translucent Atomic-Purple shells + dark-gray keymats (glTF PBR materials), the
battery is the sketch-tan 403040, the flex the amber ribbon in its floor
channel. Frame note: KiCad's GLB is metres, glTF Y-up with z = board-y-DOWN —
the script maps it with rotX(+90°)·scale(1000) + the grip origin (verified
against the dome-pad grid).

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

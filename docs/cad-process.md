# 3D CAD process (shells, keymats, PCB assembly) — rev-A / v0.24

**v0.24 expanding clamp back — 2-PART TRAY + MagSafe + TPU grippers (2026-07-27, branch
feature/expanding-clamp).** The rigid center — the bolted **center panel** and its
**sunken flush-screen well** — is replaced by a **2-part telescoping tray** (Abxylute
S9 / 8BitDo style) that clasps different-size phones (cased long edge **130–170 mm**).
*Why the tray, not the geared 3-stage:* the 3-stage rack-and-pinion (built and kept in
git, `fbf79a9`) earns its keep only over **large** travel; our range is ~40 mm (1.3:1),
where a single lap keeps huge overlap throughout — so the gear solved a problem we don't
have. The tray is simpler, sturdier-in-practice (the clamped phone stiffens it), far
easier to print/tune, and its **continuous flat top** both hosts the MagSafe ring and
leaves clean back-space for maker alt-shells (solar / battery / LoRa). Mechanism: the
`bridge` is the fixed tray (bolted to the right grip); the left grip's plate laps inside
it, so the two overlap at every span and **enclose** the springs + FFC + power cable.
**Retention is MECHANICAL, never the magnets** — the phone is trapped between the tray
(behind) and **deep soft lips** (front) so it can't fall when used screen-down over your
face (Switch/Steam-Deck style). A soft **TPU gripper** on each grip's inner edge
(`gripper_left/right`, GameSir-style) combines the compliant edge-grip + the capture lip
in one part. **MagSafe is back** as a **secondary** back-hold/snap only: a strong N52
ring seats in a recess at the tray centre (`magsafe_ring`); because it's not load-
bearing, its alignment drift across phones/cases is a non-issue, and makers can
reposition/float it. `deck.product(clamp_pos)` is parametric on the span; `deck3d
--check` validates at **min / nominal / max** — all parts watertight + bed-fit,
**0 collisions across the whole travel**, tray lap ≥17 mm. The 403040 battery stays in
the (sliding) left grip. Fit-model notes: lip depth + clamp force are coupon-tuned for
face-down capture; non-nominal phone thicknesses sit slightly proud/low.

**v0.23 faceted ergonomic back crown (2026-07-26, branch feature/back-ergonomics).**
The dead-flat back is replaced by a **faceted palm crown** — a hard-industrial 90s
read (Sega/Nokia cut-block facets, crisp shadow-line grip grooves) delivering
Rii-8+ grip-swell ergonomics: two cut-corner **grip plateaus** (apex biased to the
outer edge where the thenar heel and curled fingers bear, three scored grip
grooves each) rise **5.5 mm** below the z=0 back plane, linked by a lower faceted
**spine panel** so the whole back reads as one milled block; a thin land survives
at the perimeter (tapered edge). The crown is **purely additive below z=0**, so the
electronics cavity, the 221-body collision result and the bed-fit are unchanged by
construction — the crown never meets a component. Generated with CadQuery **ruled
lofts** of cut-corner sections (planar-facet B-rep; scipy/scikit-image available
for future SDF/organic passes). **Consequence: the back halves now print
CAVITY-DOWN** (was floor-down) so the crown prints apex-up as a strictly-narrowing
peak = a self-supporting cosmetic face; the internal PCB bosses/posts become the
only downward faces and take supports whose scars sit hidden inside the shell.
Device max thickness at the grips ~**20 mm** back / **24.8 mm** incl. keycaps; the
edges and the 14.7 mm flush front plane are unchanged. `--all --check`: all 9 parts
watertight + bed-fit, **0 collisions**.

**v0.21 right-grip pointing nub (2026-07-23, branch feature/right-joystick).**
Bean-style hall nub at the left-D-pad mirror: the right lid gains a plain
**Ø10 through-aperture** with an **underside Ø15.2 × 1.2 counterbore**, and
prints **8 and 9** join the set — the **`nub_spring`** (Ø14.8 flange + 3 spiral
flexure arms + Ø7 magnet hub; 3 underside legs bear on the PCB front face and
the counterbore ceiling clamps the flange onto them with 0.05 mm preload — no
axial float; arm thickness `NUB_ARM_T` = 0.8 is the compliance coupon-tune)
and the **`nub_cap`** — since v0.22 a **classic ThinkPad soft-dome replica in
red TPU** (Ø7.8 mushroom, dot grid, 5.25 tall incl. the 0.35 dot studs) on a
**4.4 mm-square × 2.5 TrackPoint-standard platform** (hub top at z 14.0, 0.7
below the face), so genuine classic caps interchange with the print. The cap
skirt nestles into the Ø10 aperture; the dome top sits 4.2 mm (dot tips
4.55 mm) proud of the face, ThinkPad-flat vs the ALPS gimbal's ~12 mm
(that variant was implemented and reverted; see design-decisions.md). The
TMAG5273 sensor is back-side SMT under the aperture: nothing electronic
penetrates the face. Both nub parts are in the fit-check and bed-gate.

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
device is **15.7 mm** thick at the edges (keycap tops); there is no plateau above
the front plane any more. **v0.23** adds the faceted back crown BELOW z=0: the
grip plateaus reach **z −5.5** (grips ~20 mm back-to-face, ~24.8 mm incl. keycaps),
the spine panel −2.2, tapering to the unchanged thin z=0 edge — all additive, the
cavity stack above is untouched.

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
  PCB no longer flexes between perimeter bosses under thumb load. **v0.23: a
  faceted ergonomic crown is fused onto the outside below z=0** — two cut-corner
  **grip plateaus** (−5.5 mm, apex biased to the outer edge, three scored grip
  grooves each) rising from a lower faceted **spine panel** (−2.2 mm), tapering to
  a thin land at the perimeter. Built with CadQuery ruled lofts of cut-corner
  sections (planar B-rep). The reset pinhole + charge-LED holes are lengthened to
  pierce the crown to daylight. Purely additive: the cavity, bosses, joinery and
  the collision result are unchanged.
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
  top chamfer (its half of the reveal V). Print cosmetic-face-down. v0.21: the
  RIGHT lid additionally carries the **nub aperture** (Ø10 through) with an
  underside **Ø15.2 × 1.2 counterbore** that seats and clamps the `nub_spring`
  flange — prints clean face-down (the counterbore is a top-layers void).
- **Telescoping tray (`bridge`)** — v0.24 replaces the old bolted center panel
  with a **2-part telescoping tray** (Abxylute-S9 / 8BitDo style). The `bridge` is
  the **fixed OUTER shroud**: it bolts to the right grip (the ground member) with 2
  short M3s and cantilevers left as a closed box (open on its left end) that
  **encloses the two clamp springs, the FFC service loop, and the battery power
  cable** at every extension. Its top is the **phone rest** (RECESS_TOP = 5.1, so
  the nominal cased screen lands ≈ flush at the 14.7 face plane); the tray centre
  carries a **Ø57 × 1.8 mm recess for the Ø56 N52 MagSafe ring** (a *secondary*
  snap — see below). The **left grip is the moving jaw**: it grows an INNER shroud
  that laps inside the `bridge` (staying overlapped 57→17 mm across the 130–170 mm
  travel, so nothing ever un-encloses), pulled closed by the springs.
- **TPU grippers (`gripper_left`, `gripper_right`)** — the phone's **mechanical**
  retention (GameSir-style). Each is a soft TPU 95A part on a grip's inner edge that
  protrudes **into the well**: a compliant **edge-grip pad** (1.6 mm, the phone
  compresses it) plus a **deep capture lip** (CRADLE_LIP = 2.8 mm) overhanging the
  screen edge. Lip + clamp are what hold the phone — so it's safe used **screen-down
  over your face** (Switch/Steam-Deck style), never relying on the magnets. Print in
  TPU with the keymats.
- **MagSafe ring (`magsafe_ring`)** — Ø56 N52 ring in the tray-centre recess, a
  **SECONDARY** back-hold + snap only. Because the clamp + lips retain the phone, the
  ring isn't load-bearing, so its slight mis-alignment across phone/case sizes is a
  non-issue. The strong magnet is on **our** side (the phone/case magnet is the weak
  one — a steel plate alone wouldn't hold face-down).
- **Keymats** (per grip, TPU 95A) — keycap plungers over the dome centres joined
  by **living-hinge webs**; each plunger nub actuates its dome; the web edge is
  what the grip lid's rim clamps. Print a 3×3 coupon to tune travel + hinge
  fatigue before the full mat.

## Fit rules the collision check enforces

Two solids may **touch** (mating faces, a plunger resting on a dome) but must not
**interpenetrate** by more than a small tolerance. The check reports any pair whose
mesh-intersection volume exceeds the tolerance, classified as *contact* (OK) vs
*clash* (fix). Intended stack (bottom→top): back halves → PCB on standoffs + posts
→ domes on pads → retention tape → keymat plungers → grip lids (rim on the web);
the **`bridge` tray** bolts to the right grip and the **left grip's inner shroud**
laps inside it (overlap asserted ≥12 mm across travel); the phone rests on the tray
top, clamped by the spring-driven jaw against the **TPU grippers** (soft pads +
capture lips, which the phone compresses), screen ≈ flush at 14.7, with the N52
**MagSafe ring** in the tray-centre recess as a secondary snap. LiPo on the LEFT
grip floor under the passive PCB; the FFC jumper + battery power cable run **enclosed
inside the tray** on separate y-lanes with a rolling service loop. The back-half
pair, the lid↔keymat rims, the tray lap, and the gripper/magsafe↔phone contacts are
the whitelisted mating contacts; everything else that interpenetrates is a clash.

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
hardware/cad/.venv/bin/python hardware/cad/deck3d.py --all          # build all 9 printed parts + Ender 3 V2 bed-fit gate
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
| `back_left`, `back_right` | **cavity opening down (faceted crown up)** | v0.23: crown prints apex-up = self-supporting cosmetic face; the internal PCB bosses/posts are the only downward faces → **tree supports inside the cavity** (scars hidden); 6 mm brim. v0.24: `back_left` is the sliding jaw (slider groove); `back_right` is ground (cradle + bridge bosses) |
| `bridge` (fixed tray, v0.24) | open side down | closed tray open on its left end (the left grip's plate laps in); light supports for the cavity roof or split tray+lid; MagSafe recess in the top |
| `gripper_left/right` (v0.24) | **TPU, lip up** | soft edge-grip + capture lip; print in TPU 95A with the keymats; lip depth is the face-down-capture tune |
| `grip_lid_left/right` | **cosmetic face down** | rim downstands face up; no supports |
| `keymat_left/right` | web down (TPU 95A) | as before |
| `magsafe_ring` | *(not printed)* | Ø56 N52 ring, press-seated in the tray-centre recess (secondary hold) |
| `nub_spring` | flange down (PETG) | legs + hub up; brim; NO supports (arms self-support); `NUB_ARM_T` is the stiffness coupon |
| `nub_cap` | skirt down (**red** TPU 95A) | dot-grid top up; print with the keymats; genuine classic TrackPoint caps are a no-print alternative |

Slicer: ~0.12 mm elephant-foot compensation keeps the printed seam faces true;
the modeled 0.25–0.3 mm joint clearances assume roughly that (the tray lap fit and
the gripper seat are the coupon-tuned clearances). Dense infill on the `bridge` tray
top stiffens the MagSafe pocket floor and the cantilever.

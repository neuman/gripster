# 3D CAD process (shells, keymats, PCB assembly) — rev-A

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
comes out **14.3 mm** thick, the spine **16.3 mm**, **22.3 mm** including the
mounted phone.

## Parts, all from `deck.py` + the placed board

- **PCB assembly (fit model)** — board extruded from the outline (1.6 mm) with
  every placed component as a solid at its real datasheet height (the
  `COMPONENTS` spec table in `deck3d.py`), plus snap-domes (0.5 mm), a realistic
  ~500 mAh pouch cell, and the FFC jumper. Used for collision-checking the shells
  against real hardware — `--check` reports **0 collisions**. Caveat: the bridge
  ribbon is modeled ~2 mm below its physical run in the fit-check (clearances in
  that region are ≥4 mm, so it was not re-modeled).
- **Bottom shell** — one-piece tray (both grips + spine): walls, 6.3 mm PCB
  standoffs + **M2 heat-set bosses (3.2 mm bores, 5/grip)** at the mount coords,
  and **3 support posts per grip under the key field** so the PCB no longer
  flexes between perimeter bosses under thumb load. Through-features cut from
  the **real part placement**: a **13.5 × 7.0 mm USB-C wall opening** centred on
  the connector with a stepped outer relief for the plug overmold, an
  **8 × 2.8 mm slide-switch slot** in the bottom wall, a **1.6 mm reset pinhole**
  and a **1.5 mm charge-LED light hole** in the floor (both located from the
  placed SW91/D80), and a **0.6 mm antenna wall relief** at the E73 edge. LiPo
  pocket in the spine.
- **Top shell** — face plate: **79 key openings at the exact dome centres**, and
  a **rim that clamps the keymat web with ~0.1 mm preload** so the mat can't
  float or rattle. The phone sits in a **2.0 mm-deep pocket in a raised spine
  plateau**, open at the x-ends — the grips abut the phone's short ends, the
  pocket rim captures its long edges. Inside the pocket floor: a **Ø57 × 1.8 mm
  recess** for the Ø56 N52 MagSafe ring — the 2.0 mm ring sits 0.2 mm proud, the
  phone rests on ring + pocket floor, and a **0.2 mm membrane** remains under the
  recess (prints fine as a single solid layer; the ring holds the phone
  laterally — that is its job, the pocket takes the mechanical load).
- **Keymats** (per grip, TPU 95A) — keycap plungers over the dome centres joined
  by **living-hinge webs**; each plunger nub actuates its dome; the web edge is
  what the top-shell rim clamps. Print a 3×3 coupon to tune travel + hinge
  fatigue before the full mat.

## Fit rules the collision check enforces

Two solids may **touch** (mating faces, a plunger resting on a dome) but must not
**interpenetrate** by more than a small tolerance. The check reports any pair whose
mesh-intersection volume exceeds the tolerance, classified as *contact* (OK) vs
*clash* (fix). Intended stack (bottom→top): back shell → PCB on standoffs + posts →
domes on pads → retention tape → keymat plungers → front shell (rim on the web);
phone in the spine pocket on the MagSafe ring; LiPo in the spine; FFC jumper across
the spine behind the phone.

## Run

```bash
hardware/cad/.venv/bin/python hardware/cad/deck3d.py --all      # build every part + assembly
hardware/cad/.venv/bin/python hardware/cad/deck3d.py --check    # collision + printability report
hardware/cad/.venv/bin/python hardware/cad/deck3d.py --render   # PNG part sheets + assembly views
```

Outputs land in `hardware/cad/build/` (STEP/STL, git-ignored) and `renders/`.

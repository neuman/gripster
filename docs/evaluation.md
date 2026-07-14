# thumbdeck — fab-readiness evaluation (rev-A, v0.16, 2026-07-13)

Authoritative status of the design's readiness to be produced. Supersedes the
v0.14 evaluation and all older review notes. Where any other doc disagrees with
this file or the code, **this file and the code win.**

Method: the v0.14 6-lens audit (matrix, power/USB, module pinout, footprints,
firmware, mechanical/RF) followed by the rev-A **8-dimension audit** (120
findings, 14 blockers — see [design-review.md](design-review.md)), cross-checked
against official datasheets (Ebyte E73 User Manual, ST USBLC6-2, Microchip
MCP73831, Snaptron), an exhaustive matrix-ghosting simulation, and the headless
KiCad-9 + Freerouting pipeline with a DRC gate.

---

## Verdict

**rev-A is fab-ready: routed, DRC-clean, fab package exported, firmware fixed,
mechanicals fit-checked. It is unverified in physical hardware.** Order a
first-article run of 5 and run the bring-up checkpoints in
[assembly.md](assembly.md) before any larger spend.

## What is PROVEN (machine-verified this pass)

| Item | Evidence |
|---|---|
| **Routing + DRC** | Both boards **0 violations, 0 unconnected** (kicad-cli 9.0.9, error severity, 2026-07-11) — `hardware/kicad/generated/drc_{right,left}.json`. |
| **Fab package** | `gen_fab.py` (hard-gated on clean DRC) exported 4-layer gerbers + JLC BOM/CPL for both boards to `hardware/kicad/generated/fab/`. |
| **E73 module pinout** (the silent killer) | `E73_PINMAP` matches the official Ebyte pin table 1:1; footprint pad N = datasheet pin N. VDDH=cell, VDD=REG0 output, USB D±=29/31, SWD=37/39, RESET=26, VBUS=27, VBAT_SENSE=AIN0, **COL9 on P0.04 (XTAL pins free)**. |
| **Power architecture** | High-voltage mode: cell → charger(cell side) → SW90 → VBAT → VDDH(23); VDD(19) = internal REG0 3.3 V output, never driven; module has no DCDC inductors → LDO mode, matching the firmware config. |
| **Matrix / NKRO** | `sim_matrix.py` (final pass): **79 unique (row,col) keys, 0 cross-grip collisions, 0 ghost/miss failures** over ~68,500 scenarios; the no-diode control ghosts ~35 k× (sim detects ghosting). |
| **USB** | CC1/CC2 5.1 k pulldowns; USBLC6-2SC6 **inline**, D+=pins 1&6 / D−=pins 3&4 per ST datasheet; interleaved data pads joined by deterministic generated copper. |
| **Charger** | MCP73831-2ACI, PROG 5.1 k → ~196 mA (~0.5 C @ 400 mAh); 4.7 µF 0805 25 V at both supply and cell nodes, at the chip. |
| **Bridge correctness** | Left-grip FFC nets assigned by ribbon geometry; verified net-at-same-height matches 1:1 → a straight type-A jumper is correct by construction. |
| **Footprints** | Production `snaptron_7mm_contact` (ring + 67.5° escape gap, pour/via keepouts); E73 43-pad land pattern with embedded antenna keepout; **no hand-soldered parts** — the USB-C shell's plated stakes and the FFC/slide-switch locating pegs are the only through-board features, all placed in the same single-pass JLC assembly. |
| **Board outline / mounts** | Closed, non-self-intersecting, **76.5 × 114.5 mm**; **5× M2** per grip clear of keep-outs. |
| **Mechanical fit** | `deck3d.py --check`: **0 collisions** across the 5-part shell set (back halves, grip lids, center panel) + PCB (real part heights) + domes + keymat + LiPo + ring + phone; 6.3 mm back cavity clears the mated JST-PH by 0.24 mm; every printed part gated to fit an Ender 3 V2 bed (`--all`). |
| **Firmware buildability** | 5 build-breakers fixed (v0.3.0 pin, pointing.h include, DCDC removed, LF-RC clock, exact Adafruit/nice!nano-v2 flash partition layout); board definition at `config/boards/arm/thumbdeck`; CI = a **self-contained ZMK v0.3.0 build** (`west init -l config` inside `firmware/zmk-config`, `west build -b thumbdeck`, uploads `thumbdeck-zmk.uf2`) — ZMK's reusable workflow cannot handle a nested config dir. **No green run yet — see below.** |

## What is NOT yet verified (needs the physical prototype)

1. **RF range** with the phone mounted and hands on the grips (antenna is
   edge-mounted with keepout + shell relief, but only a range test proves it).
2. **Dome feel** through the printed keymat, hinge fatigue life, retention-tape
   behaviour over thousands of cycles.
3. **Real charge curve + idle/sleep current** on the assembled board.
4. **JLC's actual part rotations** (LED/SOT-23/E73) — controlled by the DFM
   preview checklist, confirmed only at delivery.
5. **A green run of the GitHub-Actions build** — the CI workflow is a
   self-contained ZMK v0.3.0 build, but no green run exists yet: **REQUIRE one
   green Actions run producing `thumbdeck-zmk.uf2` before ordering boards.**

## Standing constraints

- **E73 C356849:** Extended + X-ray + **volatile stock** (observed from ~1000 down
  to ~20 units within days) — check jlcpcb.com/parts and reserve/backorder the
  modules before anything else (the Holyiot 18010 backup requires a footprint
  change, rev-B); forces Standard assembly for the right board.
- **ENIG mandatory** (dome contacts) — never accept a HASL default.
- **Two separate JLC orders** — do not panelize the two designs.
- The E73 ships blank: first flash is **SWD via TP1–5** (Adafruit bootloader,
  nice_nano build), then UF2 forever.

## Reproduce

```bash
cd hardware/scripts
python3 gen_board.py                  # placement + netlist + fixed USB copper + GND escape vias
./route.sh right && ./route.sh left   # Freerouting -> stitch -> DRC gate -> renders
python3 gen_fab.py                    # fab package (refuses unless DRC 0/0)
python3 sim_matrix.py                 # 79-key ghosting/NKRO proof
python3 gen_firmware.py               # regenerate the ZMK board files from the model
cd ../.. && hardware/cad/.venv/bin/python hardware/cad/deck3d.py --all --check
```

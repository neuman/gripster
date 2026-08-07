# Gripster — fab-readiness evaluation (rev-A, v0.27, 2026-08-07)

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
| **Routing + DRC** | Both boards **0 violations, 0 unconnected** (kicad-cli 9.0.9, error severity) — `hardware/kicad/generated/drc_{right,left}.json`. **Re-routed from scratch 2026-08-07 for v0.27**'s 20-way bridge: right 75 nets / 114 footprints / 30 GND escape vias, left 60 nets (was 58 — VBAT_CELL and VCELL_RAW are new there). Two v0.27 notes worth carrying: (a) `route.sh` now injects a real `power` netclass into the DSN, so `VBAT_CELL`/`VBAT` route at **0.4 mm** instead of signal width — `gen_board.py`'s `PWR` constant had never been applied to anything and `VBAT_CELL` had been shipping at 0.2 mm (~336 mΩ, a third of the charge loop); (b) 0.5 mm was tried and **does not converge** (Freerouting leaves `VBAT_CELL` open through the inner corridor), and the 20-way connector needs **100 passes** where the 16-way closed in 30. |
| **Fab package** | `gen_fab.py` (hard-gated on clean DRC) exported 4-layer gerbers + JLC BOM/CPL for both boards to `hardware/kicad/generated/fab/`. |
| **E73 module pinout** (the silent killer) | `E73_PINMAP` matches the official Ebyte pin table 1:1; footprint pad N = datasheet pin N. VDDH=cell, VDD=REG0 output, USB D±=29/31, SWD=37/39, RESET=26, VBUS=27, VBAT_SENSE=AIN0, **COL9 on P0.04 (XTAL pins free)**. |
| **Power architecture** | High-voltage mode: cell → charger(cell side) → SW90 → VBAT → VDDH(23); VDD(19) = internal REG0 3.3 V output, never driven; module has no DCDC inductors → LDO mode, matching the firmware config. **v0.27:** topology unchanged, but the cell now terminates in its own grip — **J4** (JST-PH) on the LEFT board, through **F1** (Bourns MF-MSMF075-2 PPTC, C84140, 0.75 A hold) — and reaches the charger over the ribbon. **J3 is deleted from the right board.** F1 and a **protected** pouch are both required and cover different fault bands: the pouch's PCM trips at 2.0–2.5 A, an FFC conductor cooks its own PET at ~2.8 A·√s, and the 0.43–2.0 A gap between them is what F1 exists for. Charge-termination cost of the added series R is ITERM × Rloop ≈ 10–16 mV — negligible against the MCP73831's own ±32 mV VREG tolerance; the real cost is charge *time*. |
| **Matrix / NKRO** | `sim_matrix.py` (final pass, re-run 2026-07-24 on the v0.22 boards): **78 unique (row,col) keys (right 36 + left 42), 0 cross-grip collisions, 0 ghost/miss failures** over ~68,500 scenarios; the no-diode control ghosts ~35 k× (sim detects ghosting). The v0.21 nub is I²C — it adds no matrix key. |
| **USB** | CC1/CC2 5.1 k pulldowns; USBLC6-2SC6 **inline**, D+=pins 1&6 / D−=pins 3&4 per ST datasheet; interleaved data pads joined by deterministic generated copper. |
| **Charger** | MCP73831-2ACI, PROG 5.1 k → ~196 mA (~0.43 C @ the 403040 cell's ~450–500 mAh); 4.7 µF 0805 25 V at both supply and cell nodes, at the chip. |
| **Bridge correctness** | Left-grip FFC nets assigned by ribbon geometry; verified net-at-same-height matches 1:1 → a straight type-A jumper is correct by construction. **v0.27:** the bridge is **20-way** (AFA07-S20FCC-00 / C262352) and carries the cell as well as the matrix — 2 × GND, 14 matrix, 2 × VBAT_CELL, 2 unwired NC guards. The 14 matrix signals are byte-identical to v0.22, so firmware is untouched. Conductor order is a safety interlock: GND sits **15 positions** from VBAT_CELL, so even the 4-position mis-seat that a legacy 17 mm 16-way ribbon permits in a 21 mm housing lands VBAT on a column (one dead MCU pin), not on GND (a cell short). |
| **Footprints** | Production `snaptron_7mm_contact` (ring + 67.5° escape gap, pour/via keepouts); E73 43-pad land pattern with embedded antenna keepout; v0.21 adds only a stock SOT-23-6 (TMAG5273 hall sensor) — **everything is single-pass SMT, zero hand-soldered parts**. |
| **Board outline / mounts** | Closed, non-self-intersecting, **75.0 × 97.0 mm** (v0.19 GBC-boxy: straight outer edge, r8/r11 corners, 1.0 mm bottom crown); **5× M3** per grip clear of keep-outs (bbox-gate ≥4.0). |
| **Mechanical fit** | `deck3d.py --check` **re-run on v0.27 geometry (2026-08-07)**: **221 bodies, 0 clashes** (345 AABB-overlapping pairs) at **all four clamp spans** (min 130 / nominal / max phone 170 / open 179 mm), with the cable run reported **SEALED** at every one. Nub gap re-verified at **3.33 mm** (band 3.05–3.65) and retention at a 3.0 mm lip overhang. **v0.27 added the FFC duct that never existed**: the ZIF slot sits at z ≈ 6.95 and the enclosure lane at z = 0.2, and until now the ribbon had 1.20 mm of x in which to lose 6.74 mm of z — i.e. no physical route, in any version. J2 was rotated to face **inboard** and a low **stepped** duct cut at **z −0.8 .. 2.6** on the grip side and .. 1.95 through the moving shroud (a straight 2.6 cut left that shroud's roof 0.55 mm thick; stepping it restores **1.42 mm**), which passes *under* the whole phone-retention structure (cradle backstop wall, rest ledge and bottom shelf all sit at z ≥ 3.9) rather than through it. The descent is dimensioned with a **1.6 mm bend-radius** allowance and asserted to clear the innermost matrix diode by **0.98 / 1.03 mm**. `flex_route_report()` sweeps the ribbon's **full 21 mm section** (not its centre line — v0.24e's recorded lesson) against the built shell solids and **gates**: `--check-lanes` exits non-zero, `--check` asserts. `--check-lanes` (~15 s, since it builds both back halves to sample against) also asserts `FLEX_Y` equals J2's *placed* y and that ribbon width matches pin count via the exact AFA07 land = N+6.85 / ribbon = N+1 identity — the 2.0 mm skew those two had silently carried since v0.24d is what motivated the assert. Every part still bed-gated. |
| **Firmware buildability** | 5 build-breakers fixed (v0.3.0 pin, pointing.h include, DCDC removed, LF-RC clock, exact Adafruit/nice!nano-v2 flash partition layout); board definition at `config/boards/arm/thumbdeck`; CI = a **self-contained ZMK v0.3.0 build** (`west init -l config` inside `firmware/zmk-config`, `west build -b thumbdeck`, uploads `thumbdeck-zmk.uf2`) — ZMK's reusable workflow cannot handle a nested config dir. **CI is STALE for v0.21**: the last green run (29443394494, 2026-07-15, commit `d1ef751`) predates the nub — v0.21 adds the `tmag5273_nub` module, the `&i2c0` node and the `-DZEPHYR_EXTRA_MODULES` build flag, none of which that run compiled. **Re-run the workflow and get green before ordering boards.** It has never been flashed — no hardware exists. |

## What is NOT yet verified (needs the physical prototype)

1. **RF range** with the phone mounted and hands on the grips (antenna is
   edge-mounted with keepout + shell relief — the relieved top wall is in the regenerated v0.19 shells (closed, 1.9 mm over the antenna span); only a range test proves it).
2. **Dome feel** through the printed keymat, hinge fatigue life, retention-tape
   behaviour over thousands of cycles.
3. **Real charge curve + idle/sleep current** on the assembled board.
4. **JLC's actual part rotations** (LED/SOT-23/E73) — controlled by the DFM
   preview checklist, confirmed only at delivery.
5. **The firmware on real silicon — and, for v0.21, the compiler itself.** The
   last green CI run (29443394494, 2026-07-15) predates the nub module; the
   v0.21 firmware (tmag5273_nub, i2c0, PM hooks) has NOT yet been CI-built —
   push the branch and re-run the workflow first. Beyond that, everything past
   the compiler is unverified: the image has never been flashed,
   the matrix has never been scanned, and the pin map, kscan timing and power
   config have only ever been checked by eye against the datasheet. **A clean
   build is not a working keyboard.** Re-run the workflow before ordering so the
   artifact you flash matches the tree you built from.

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
python3 sim_matrix.py                 # 78-key ghosting/NKRO proof
python3 gen_firmware.py               # regenerate the ZMK board files from the model
cd ../.. && hardware/cad/.venv/bin/python hardware/cad/deck3d.py --all --check
```

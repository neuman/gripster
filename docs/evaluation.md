# thumbdeck — fab-readiness evaluation (v0.14)

Authoritative status of the board's readiness to be produced. This supersedes the
older, version-drifted notes in `design-review.md` (v0.4), `connectivity-and-power.md`
(v0.3) and the top half of `matrix-and-diodes.md` (v0.3). Where those disagree with
this file or the code, **this file and the code win.**

Method: a 6-lens adversarial audit (matrix, power/USB, module pinout, footprints,
firmware, mechanical/RF) cross-checked against the **official datasheets** (Ebyte
E73 User Manual, ST USBLC6-2, Microchip MCP73831, Azoteq IQS7211E) and reference
designs (joric/nrfmicro, marbastlib, Rii i8+); an exhaustive **matrix-ghosting
simulation**; and headless KiCad-9 DRC + Freerouting.

---

## Verdict

**The electrical design is correct and verified. The board is NOT yet fab-ready:**
the copper routing is the remaining gate, and a first-article prototype spin is
mandatory before volume. Confidence that *the schematic/netlist is right* is high;
confidence that *a physical board will work first try* requires the prototype.

## What is PROVEN correct (verified this pass)

| Item | Evidence |
|---|---|
| **E73 module pinout** (the silent killer) | `E73_PINMAP` matches the official Ebyte pin table 1:1; marbastlib footprint pad N = datasheet pin N. VDDH=cell, VDD=REG0 output, USB D±=29/31, SWD=37/39, RESET=26, VBUS=27, VBAT_SENSE=AIN0. |
| **Power architecture** | High-voltage mode: raw LiPo → VDDH(23); VDD(19) left as the internal REG0 3.3 V output (never driven). On-module REG1 DC/DC inductor is fitted. Correct per Nordic + Ebyte. |
| **Matrix / NKRO** | `sim_matrix.py`: all **79 keys are unique (row,col) intersections**, 0 cross-grip collisions; **0 ghost/miss failures over ~68,500 finger-press scenarios** (exhaustive singles/pairs/triples + rectangle stress + random 2–12-finger presses). Diode `col2row` orientation correct. The no-diode control ghosts ~35 k× (proves the sim detects ghosting). |
| **USB-C wiring** | VBUS=A4/B4/A9/B9, CC1=A5, CC2=B5 (each 5.1 k to GND), D+=A6/B6, D−=A7/B7, shields=GND. Correct. |
| **Charger** | MCP73831 pins 2=GND,3=VBAT,4=VBUS,5=PROG; STAT NC OK. |
| **Footprints** | E73 land pattern (43 pads, 1.27 mm, antenna keepout embedded) correct; diode SOD-323 pad1=cathode; USB-C is SMD; M2 NPTH mount holes OK. |
| **Board outline / mounts** | Closed, non-self-intersecting, 74.5 × 109.5 mm; 5× M2 clear of keep-outs. |

## Defects FIXED this pass

| Sev | Defect | Fix |
|---|---|---|
| **BLOCKER** | **USBLC6-2SC6 ESD shorted USB D+ to D−** (pin 6 was netted D− but is internally the same node as pin 1 = D+). | Rewired: D+ = pins 1&6, D− = pins 3&4 (per ST datasheet). |
| **BLOCKER** | ZMK firmware was a **stale 50-key 5×10 nice!nano/pro_micro** image — wrong matrix, wrong pins, built the wrong keyboard. | Replaced with a **generated** E73 board (`gen_firmware.py`): 9×10, 79 keys, real nRF P0/P1 pins from `E73_PINMAP`, sparse matrix-transform + keymap derived from the PCB model so they can't drift. |
| MAJOR | Charger `R24 = 2 kΩ` set **~505 mA** (>1C for the 400–500 mAh cell). | `R24 = 5.1 kΩ` → ~196 mA (~0.5C of a 400 mAh cell). |
| MAJOR | Left-grip bridge header **J2 hardcoded x=3.2** → landed on the *outer* edge (harness can't reach). | `J2` now mirrors to `board_w−3.2` on the left grip (inner edge). |
| MAJOR | **5 reflow parts on F.Cu** (C1,C2,R22,R23,J1) broke single-sided back-only SMT. | All reflow parts moved to **B.Cu**. |
| MAJOR | Bridge columns **COL6–9 on the module's 0.8 mm inner pads** (unroutable on 2 layers). | Reassigned to castellated **edge pads** (3,9,10,11). |
| MAJOR | **USB-C 44 mm from the module** (long, unroutable D+/D−). | Moved to the bottom edge beside the module (~15–20 mm), ESD inline. |
| MINOR | No bulk cap on VBAT/VDDH. | Added **C4 = 4.7 µF (0805)** on VBAT. |

## Decisions taken (v0.14)

- **4-layer stackup** — `gen_board.py` now emits **F.Cu(sig) / In1.Cu(GND plane) /
  In2.Cu(sig) / B.Cu(sig)**. This gives the antenna a real ground reference, lowers
  matrix crosstalk, and (via the empty In2 layer) makes the dense E73 fan-in routable.
- **Trackpad dropped for v1** — SDA/SCL/TP_DR removed from `E73_PINMAP` (those module
  pads are now spare). v1 ships as a keyboard; the D-pad + L/R mouse-button keys give
  pointer control. Trackpad is a documented future option.

## OPEN gates before a fab order

1. **Finish the copper route (on 4 layers).** The board ships **placed + netlisted with
   the 4-layer stackup and a solid In1 GND plane**. The final copper must be routed by a
   real router — **KiCad 9 interactive push-shove** (honours the antenna/mount keep-outs)
   or a production autorouter. Headless Freerouting and the in-repo A* finisher were
   evaluated and are **not sufficient for the final DRC-clean route** (Freerouting ignores
   keep-outs; the A* finisher is fine for closing a handful of nets but not the whole
   dense connector cluster). With In2 free, the fan-in is now straightforward for a GUI
   route. Then fill zones, pass DRC + ERC, plot gerbers.
2. **Antenna placement in 3D.** Keep the E73 ceramic-antenna edge ≥15 mm from the
   MagSafe N52 ring + steel plate and the LiPo; expect phone+hand detuning. This is a
   mechanical/shell decision, not just a 2D one.
3. **Snap-dome fab footprint.** The board routes on `snaptron_7mm_simple` (a 2-pad
   proxy). Swap to the real annular-contact footprint (`snaptron_7mm_contact_pad`,
   move it into `thumbdeck.pretty/`) before plotting gerbers, and specify **ENIG**
   (gold) on the dome pads.
4. **Meter the dome pinout** on a physical dome before committing 79 parts.
5. **ZMK CI green.** Push `firmware/zmk-config` and confirm the GitHub-Actions build
   produces a `thumbdeck` UF2 (the board scaffolding is best-effort; CI is the check).
6. **First-article prototype.** Order 5, hand-verify bring-up (BAT+/GND open, current-
   limited first power, USB-C actually charges via CC, RF range with the phone
   mounted, dome feel + keymat fatigue) **before** any larger run.

## Reproduce

```bash
cd hardware/scripts
python3 gen_board.py         # placed + netlisted boards (real footprints, matrix nets)
python3 sim_matrix.py        # ghosting/NKRO proof (both grips + combined 79-key)
python3 gen_firmware.py      # regenerate the ZMK transform/keymap/gpio from the model
# routing: finish in the KiCad 9 GUI (see gate #1), then DRC/ERC + plot gerbers
```

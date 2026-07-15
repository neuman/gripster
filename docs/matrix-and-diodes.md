# Matrix, diodes & the single-controller scan — rev-A (v0.15)

thumbdeck is **one 9-row × 10-column matrix, 78 keys** (78 of the 90 positions
used), scanned by the single
E73 (nRF52840) module on the right grip — a ZMK **unibody** board, *not* a split.
Do **not** set `CONFIG_ZMK_SPLIT` or `col-offset`; there is no BLE bond between
halves — the left grip's switches are simply columns 5–9 of the one matrix.

Like the Rii i8+, the right grip's H-row (4th from the top) ends in a
**double-wide 2u Enter**: the row is `H J K L + 2u ENT` — 5 caps spanning the
6-unit row width, one dome under the wide cap (same construction as the 2u
space bars). The apostrophe has no physical key: **`'` is `&kp SQT` on FN+`;`**
in the ZMK keymap.

## Scanning & ghosting

One **1N4148WS** (SOD-323) diode per key on the back of the board, uniform
orientation, **`col2row`**: columns are driven, rows are read, **cathode band
toward the row net**. The per-key diode blocks reverse current so any combination
of simultaneous presses stays unambiguous (NKRO best-effort; BLE HID boot protocol
is 6KRO regardless).

- Logical **columns 0–4 = RIGHT grip** (wired locally to the module).
- Logical **columns 5–9 = LEFT grip** (reached over the 16-way FFC ribbon).
- **Rows 0–8** are shared across both grips (they cross the ribbon too).

**Proof, not vibes:** `hardware/scripts/sim_matrix.py` is the final pass — all
**78 keys are unique (row,col) intersections, 0 cross-grip collisions, 0
ghost/miss failures** over ~68,500 exhaustive + random multi-finger scenarios (the
no-diode control ghosts ~35 k×, which proves the simulator detects ghosting).

## Pins (E73 / nRF52840, as routed)

The full pad → net table lives in [routing-status.md](routing-status.md). Summary:
matrix signals use E73 pads verified pin-by-pin against the Ebyte manual; the
five bridge columns (COL5–9) sit on castellated edge pads, and the rest use
whatever pads route cleanly on 4 layers; **COL9 is on pad 18
(P0.04/AIN2)**, keeping the XTAL pins P0.00/P0.01 free; battery sense on
P0.02/AIN0. Firmware maps them in the board's devicetree
(`firmware/zmk-config/config/boards/arm/thumbdeck/`), generated from the same
model by `gen_firmware.py` so board and firmware can't drift.

## Hardening that is actually on the board

| Measure | On board? | Detail |
|---|---|---|
| **9× 4.7 kΩ row pull-downs** (R1–R9) | **yes** | External, at the module — the nRF's internal ~13 kΩ pull is too weak over the ribbon capacitance (stale-high phantom presses). |
| **8 ms debounce** | yes (firmware) | `debounce-press-ms` / `debounce-release-ms` in the kscan. |
| **Solid In1 GND plane** | yes | 4-layer stackup; rows/cols reference a real plane → low crosstalk. |
| GND stitching + escape vias | yes | Machine-placed by the pipeline (see routing-status.md). |
| Column series resistors | **no — dropped** | Justified for the old long telescoping cable; the rev-A bridge is a short (≤200 mm) fixed internal ribbon. Rev-B option if ringing ever shows. |
| Dome-field TVS | **no — dropped** | Never on any real board. The dome field sits behind the keymat + shell; USB ESD is handled by the USBLC6-2. Rev-B option if field ESD appears. |

## The bridge is part of the matrix

ROW0–8 + COL5–9 (14 signals) + GND cross the **16-way FFC** to the left grip.
The left connector's pin→net assignment is generated **from ribbon geometry** so a
straight type-A jumper is correct by construction (verified: net-at-same-height
matches 1:1). Debug rule of thumb: a dead left-grip **column** → reseat the ribbon;
a dead **row** shows on **both** grips.

## Diode direction sanity

`diode-direction = "col2row"` matches the physical boards: every diode's cathode
band points to its row net, same orientation on both grips. The fab places them —
this matters only if you ever rework one.

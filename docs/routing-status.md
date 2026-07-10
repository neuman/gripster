# Routing status & finish-in-KiCad checklist

**State: route-complete matrix, not yet fab-signed-off.** `hardware/scripts/gen_board.py`
produces both grip boards with real footprints, the full netlist, and the **79-key
matrix fully routed** (verified: **0 unrouted ratsnest** — every switch, diode, per-key
via, column bus and row bus is connected in copper). The module / power / USB nets are
**placed and netlisted**; the last routing + sign-off is a one-time KiCad-GUI step.

## Why the finish must happen in the KiCad GUI (headless limits here)
This environment runs KiCad **7** headless, which **cannot**:
- run **DRC / ERC** (`kicad-cli` gained DRC only in v8) — so clearances/connectivity
  aren't machine-verified here;
- **fill copper zones** from Python (`ZONE_FILLER` segfaults) — GND zones are added
  **unfilled**; KiCad fills them on open / before plot in the GUI.

So the gerbers this repo can export headless are **missing the GND pour and are not
DRC-clean**. Do not fab from them — export final gerbers from the GUI after the steps
below.

## What is real vs. what to verify
| Item | Status |
|---|---|
| Board outline, mount holes, 79 dome + diode footprints | real, placed |
| Matrix routing (cols F.Cu / rows B.Cu / per-key vias) | **routed, 0 ratsnest** |
| Full netlist (ROW/COL, GND/3V3/VBAT/VBUS, USB, I2C, SWD) | defined |
| E73 module / IQS7211E / JST-GH footprints | **built here — VERIFY pad geometry vs datasheet** |
| E73 **pinout** (which pad → which GPIO/USB/power) | **VERIFY vs datasheet before trusting** |
| Module/USB/power routing | left as netlisted ratsnest for the GUI route |
| GND pours | zones defined, **unfilled** |

## Finish-in-KiCad checklist (once, in the GUI — KiCad 8 recommended)
1. **Open** `hardware/kicad/generated/thumbdeck_right.kicad_pcb` (and `_left`).
2. **Verify the E73 footprint + pinout** against the Ebyte datasheet — this is the one
   thing that will silently kill the board if wrong. Confirm each module pad's net.
3. **Verify USB-C**: CC1/CC2 each via a 5.1 kΩ to GND; D+/D− to the module USB pins;
   VBUS → USBLC6-2 → charger. Keep D+/D− short and roughly matched.
4. **Route** the remaining ratsnest (module GPIO ↔ rows/cols, power rails, USB, I2C).
   Use the push-shove router; rows/cols already have their buses, so it's mostly the
   module fan-in.
5. **Fill zones** (`B`), then **run DRC** and **ERC**; fix violations.
6. **Export gerbers + drill + BOM + CPL** from the GUI → upload to JLCPCB for the real
   assembled quote.

## E73 module footprint
Use the community-standard **`nRF52840_E73-2G4M08S1C`** footprint (marbastlib), staged at
[`hardware/footprints/thumbdeck.pretty/`](../hardware/footprints/thumbdeck.pretty/) — it's
**13 × 18 mm, 43 pads** (28 castellated + 15 inner SMD, 1.27 mm pitch), ceramic antenna on one
13 mm edge (keep all copper/GND clear under that edge, place it at the board edge). These are
KiCad-8 footprints — they load in the GUI; that's why the board is finished there.

## Full netlist — module pin → net (Ebyte E73-2G4M08S1C, from the datasheet)
Rows/cols are a *suggested* assignment (any GPIO works — ZMK maps them in the `.overlay`).
The **fixed** pins are power / USB / SWD.

| Module pin | nRF signal | Net | | Module pin | nRF signal | Net |
|--:|---|---|---|--:|---|---|
| 1 | P1.11 | ROW0 | | 28 | P0.15 | COL0 |
| 2 | P1.10 | ROW1 | | 30 | P0.17 | COL1 |
| 6 | P1.13 | ROW2 | | 32 | P0.20 | COL2 |
| 12 | P0.26 | ROW3 | | 33 | P0.13 | COL3 |
| 14 | P0.06 | ROW4 | | 34 | P0.22 | COL4 |
| 16 | P0.08 | ROW5 | | 35 | P0.24 | COL5 |
| 17 | P1.09 | ROW6 | | 36 | P1.00 | COL6 |
| 20 | P0.12 | ROW7 | | 38 | P1.02 | COL7 |
| 22 | P0.07 | ROW8 | | 40 | P1.04 | COL8 |
| 15 | P0.05/AIN3 | **SDA** | | 42 | P1.06 | COL9 |
| 4 | P0.28/AIN4 | **SCL** | | 7 | P0.02/AIN0 | **VBAT_SENSE** (÷2 divider) |
| 8 | P0.29/AIN5 | **TP_DR** (Cirque data-ready IRQ) | | — | — | — |

**Fixed pins:** VDD=19, VDDH=23, GND=5/21/24 (+ inner pads), VBUS=27, USB **D−=29 / D+=31**,
SWDIO=37, SWDCLK=39, RESET=26. Spare GPIO: 3,9,10,18,41,43 (41/43 boot as NFC — set
`UICR.NFCPINS=Disabled`), XL1=11/XL2=13 (free unless you add a 32.768 kHz crystal).

## Power / USB / bootloader wiring
- **LiPo-direct (REG0 / nice!nano style):** cell 3.0–4.2 V → **VDDH (23)** only; leave **VDD (19)**
  as a regulated output (decoupling only, don't drive it); set `UICR.REGOUT0` (→3.3 V) once over SWD.
- **Charger:** USB VBUS → **USBLC6-2SC6** ESD → **MCP73831** → VBAT (cell) → VDDH. VBUS also → module pin 27.
- **USB-C:** D+→31, D−→29 (keep short/matched); **CC1 & CC2 each via 5.1 kΩ to GND**.
- **Decoupling:** module has its own supply caps; add 1 µF + 100 nF near VDD/VDDH. GND pins + inner
  pads → the GND pour (kept clear under the antenna edge).
- **Bootloader gotcha:** the E73 ships **blank and CANNOT be pre-flashed** — first flash needs **SWD**
  (often an APPROTECT `recover` first). Expose SWDIO/SWDCLK/RST/GND/3V3 on pads. After flashing the
  Adafruit nRF52 UF2 bootloader (`pca10056`), it's drag-drop UF2 forever after.
- **Bridge:** ROW0–8 + COL5–9 (left-grip columns) + interleaved GND cross the JST-GH harness to the
  left grip; COL0–4 are local to the right grip.
- **Trackpad:** IQS7211E on SDA/SCL + TP_DR; the sense pad is front copper (needs the community
  Azoteq ZMK input driver).

# Bill of materials — rev-A (v0.15)

Authoritative electrical BOM is machine-exported per board to
[`hardware/kicad/generated/fab/right/bom.csv`](../hardware/kicad/generated/fab/right/bom.csv)
and [`fab/left/bom.csv`](../hardware/kicad/generated/fab/left/bom.csv) (JLC format,
exported only when DRC is clean). The tables below mirror those files and add the
mechanical / hand-installed items. Older 50-key and Raytac/Cirque BOMs are history —
see git history and [design-decisions.md](design-decisions.md).

## Right grip board (`thumbdeck_right`) — 68 SMT placements, all bottom side

| Comment | Designators | Package / footprint | LCSC | Role |
|---|---|---|---|---|
| E73-2G4M08S1C | U1 | nRF52840_E73-2G4M08S1C | **C356849** | nRF52840 module, antenna-down at the bottom edge. Extended, X-ray, **low stock — reserve early**. |
| MCP73831 | U2 | SOT-23-5 | C424093 | LiPo charger (-2ACI, 4.2 V). PROG = R24 → ~196 mA. |
| USBLC6-2SC6 | U3 | SOT-23-6 | C7519 | USB ESD, **inline** between USB-C and module. |
| USB-C | J1 | HRO TYPE-C-31-M-12, full SMD 16P | C165948 | Charge + flash. Extended part. |
| FFC16 | J2 | ffc_afa07_s16fcc (AFA07-S16FCC-00) | C13744 | 16-pin 1.0 mm bottom-contact ZIF, bridge to the left grip. |
| JST-PH-2 | J3 | S2B-PH-SM4-TB side-entry SMT | C295747 | Battery connector (polarized — but **meter the pigtail**, see assembly). |
| MSK12C02 | SW90 | msk12c02_slide | C431540 | Power slide switch, cell+ → VBAT; charger stays on the cell side. |
| TS-1187A | SW91 | SW_Push_1P1T (top-actuated) | C318884 | Reset tact, pressed via a 1.6 mm shell-floor pinhole (UF2 double-tap). |
| LED_RED | D80 | 0603 | C2286 | Charge LED on MCP73831 STAT (through R25). **Check polarity in the DFM preview.** |
| 1N4148WS | D1–D37 (37×) | SOD-323 | C2128 | Matrix diodes, cathode → row. Basic part. |
| 4k7 | R1–R9 (9×) | 0402 | C25900 | Row pull-downs. |
| 5k1 | R20, R21, R24 | 0402 | C25905 | CC1/CC2 pulldowns (R20/R21) + charger PROG (R24). |
| 1M | R22, R23 | 0402 | C26083 | Battery ÷2 divider on VBAT_SENSE (P0.02/AIN0). |
| 1k | R25 | 0402 | C11702 | Charge-LED series resistor. |
| 4u7/0805 25 V | C3, C4, C5 | 0805 | C1779 | Charger stability caps **at the chip** (C3 = VDD/VBUS, C5 = VBAT_CELL) + VBAT bulk (C4). 25 V rating — no derating collapse at 5 V. |
| 1uF | C1, C7 | 0402 | C52923 | 3V3 (C1) and VBUS (C7) decoupling. |
| 100nF | C2, C6 | 0402 | C1525 | VBAT decoupling (C2) + SAADC filter on VBAT_SENSE (C6). |

Plus non-BOM copper features: silk-labelled test pads **TP1–5** (SWDIO, SWDCLK,
RESET, 3V3, GND) and **TP6–8** (spare I²C: SDA, SCL, INT — rev-B trackpad/expansion).

## Left grip board (`thumbdeck_left`) — 43 SMT placements, all bottom side

| Comment | Designators | Package | LCSC | Role |
|---|---|---|---|---|
| 1N4148WS | D1–D42 (42×) | SOD-323 | C2128 | Matrix diodes. |
| FFC16 | J2 | ffc_afa07_s16fcc | C13744 | Bridge ZIF, inner edge. |

The left board is otherwise bare copper — no MCU, no power. It's cheap; Economic
assembly is fine.

## Mechanical / hand-installed

| Item | Spec | Qty | Notes |
|---|---|---|---|
| Snap domes | **Snaptron 7 mm 4-leg** (SnapForce) | 79 + spares (37 right / 42 left) | Pressed, not soldered, onto the ENIG contact pads. |
| Dome retention | Snaptron taped polyimide array (Peel-N-Place) or 0.2–0.3 mm laser-cut polyimide spacer | 2 | **Required** — laterally retains each dome; the tape channels also vent them. |
| FFC jumper | **16-way, 1.0 mm pitch, type-A** (same-side contacts), **length ≥160 mm** — 200 mm is the common stock length (e.g. "FFC-1.0-16P-200mm" type A) | 1 | Straight ribbon; contacts face the boards at both ends. Type-A is load-bearing — the left connector's nets are assigned by ribbon geometry. **Not 150 mm:** the J2 contact rows are 151.2 mm apart and each ZIF drawer needs ~4 mm of insertion — a 150 mm ribbon cannot mate. |
| LiPo | 1S 400–700 mAh pouch, JST-PH pigtail | 1 | Sits in the spine behind the MagSafe ring. **Meter polarity against the "+"/"−" silk at J3 first** (pin 1 = "+", nearer the bottom board edge). |
| MagSafe ring | Ø56 N52 ring, 2.0 mm | 1 | Seats in the front shell's Ø57 × 1.8 recess (sits 0.2 mm proud). |
| Shells | back + front, 3D-printed (PETG) | 1 set | From `hardware/cad/build/` (STL/STEP). |
| Keymats | per-grip, **TPU 95A** | 2 | Living-hinge web; coupon-test >10 k cycles first. |
| M2 hardware | screws + heat-set inserts (3.2 mm bores) | 10 | 5 mount holes per grip. |
| Bootloader flash rig | SWD probe (J-Link/CMSIS-DAP/pi) + 5 jumper wires | 1 | One-time Adafruit-bootloader flash on TP1–5. |

## Deliberately absent (vs earlier drafts)

- **Trackpad (IQS7211E / Cirque):** dropped from v1 — pointer duty is ZMK mouse keys
  on the FN layer + the D-pad. TP6–8 keep a rev-B trackpad possible.
- **JST-GH bridge / 2×08 pin header:** replaced by the FFC ZIF pair + type-A jumper
  (the THT header could not physically fit the shell cavity).
- **Column series resistors + dome-field TVS:** never made it onto any real board;
  the bridge is a short fixed internal ribbon. Rev-B option if field ESD appears.

# Bill of materials — rev-A (v0.19)

Authoritative electrical BOM is machine-exported per board to
`hardware/kicad/generated/fab/right/bom.csv`
and `fab/left/bom.csv` (JLC format, exported only when DRC is clean —
regenerate with `python3 hardware/scripts/gen_fab.py`; the fab package is a build
artifact and is not committed). The tables below mirror those files and add the
mechanical / hand-installed items. Older 50-key and Raytac/Cirque BOMs are history —
see git history and [design-decisions.md](design-decisions.md).

## Right grip board (`thumbdeck_right`) — 67 SMT placements, all bottom side

| Comment | Designators | Package / footprint | LCSC | Role |
|---|---|---|---|---|
| E73-2G4M08S1C | U1 | nRF52840_E73-2G4M08S1C | **C356849** | nRF52840 module, antenna-up off the top edge (centre-top). Extended, X-ray, **low stock — reserve early**. |
| MCP73831 | U2 | SOT-23-5 | C424093 | LiPo charger (-2ACI, 4.2 V). PROG = R24 → ~196 mA. |
| USBLC6-2SC6 | U3 | SOT-23-6 | C7519 | USB ESD, **inline** between USB-C and module. |
| USB-C | J1 | HRO TYPE-C-31-M-12, full SMD 16P | C165948 | Charge + flash. Extended part. |
| FFC16 | J2 | ffc_afa07_s16fcc (AFA07-S16FCC-00) | C13744 | 16-pin 1.0 mm bottom-contact ZIF, bridge to the left grip. |
| JST-PH-2 | J3 | S2B-PH-SM4-TB side-entry SMT | C295747 | Battery connector (polarized — but **meter the pigtail**, see assembly). |
| MSK12C02 | SW90 | msk12c02_slide | C431540 | Power slide switch, cell+ → VBAT; charger stays on the cell side. |
| TS-1187A | SW91 | SW_Push_1P1T (top-actuated) | C318884 | Reset tact, pressed via a 1.6 mm shell-floor pinhole (UF2 double-tap). |
| LED_RED | D80 | 0603 | C2286 | Charge LED on MCP73831 STAT (through R25). **Check polarity in the DFM preview.** |
| 1N4148WS | D1–D36 (36×) | SOD-323 | C2128 | Matrix diodes, cathode → row. Basic part. |
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
| Snap domes | **Snaptron 7 mm 4-leg** (SnapForce) | 78 + spares (36 right / 42 left) | Pressed, not soldered, onto the ENIG contact pads. |
| Dome retention | Snaptron taped polyimide array (Peel-N-Place) or 0.2–0.3 mm laser-cut polyimide spacer | 2 | **Required** — laterally retains each dome; the tape channels also vent them. |
| FFC jumper | **16-way, 1.0 mm pitch, type-A** (same-side contacts), **length ≥194 mm** — 200 mm is the common stock length (e.g. "FFC-1.0-16P-200mm" type A) | 1 | Straight ribbon; contacts face the boards at both ends. Type-A is load-bearing — the left connector's nets are assigned by ribbon geometry. **Not shorter:** the J2 contact rows are 173.3 mm apart (v0.19's well end-walls widened the spine), each ZIF drawer needs ~4 mm of insertion, and the ribbon S-bends down into the 0.5 mm floor channel under the well — anything under 194 mm cannot mate. A 200 mm ribbon leaves ~6 mm of slack. |
| LiPo | 1S **403040** pouch (4.0 × 30 × 40 mm, ~450–500 mAh), JST-PH pigtail | 1 | Foam-taped (0.3 mm) to the **left grip's floor** under the passive PCB — the sunken well leaves no room in the spine. Leads run through the bottom-border lane and lead windows to J3 on the right board; replacement means opening the left grip (5 screws, lid, keymat, board). **Meter polarity against the "+"/"−" silk at J3 first** (pin 1 = "+", nearer the bottom board edge). |
| MagSafe ring | Ø56 N52 ring, 2.0 mm | 1 | Epoxied into the center panel's Ø57 × 1.8 recess (sits 0.2 mm proud). |
| Shells | 5 parts, 3D-printed (PETG): `back_left`, `back_right`, `grip_lid_left`, `grip_lid_right`, `center_panel` | 1 set | STLs tracked in `hardware/cad/models/` (regenerate: `deck3d.py --all --sync-models`). Every part fits an Ender 3 V2 (220 × 220) flat. **Regenerated + fit-checked for v0.19** (2026-07-17, 0 collisions): lids 77.9 × 103.8, backs 170.5/162.8 × 103.8, panel 169.1 × 102.8 mm. |
| Keymats | per-grip, **TPU 95A** | 2 | Living-hinge web; coupon-test >10 k cycles first. **v0.17 geometry**: rectangular 8.5 × 7 rounded-rect caps (2u caps for the space bars + the right H-row's Rii-style Enter), round cluster keys, debossed keycap legends; ~63 × 86–89 mm per mat. |
| M3 hardware | **M3×10 countersunk (DIN 965)** screws + M3 heat-set inserts (Ø4.0 bores, OD ≤4.6, ~4 mm long) | 14 + 14 | One screw SKU, heads FLUSH with the face (v0.19 — the proud M2 pan heads were uncomfortable): 5 per grip + 4 panel border screws. |
| Bootloader flash rig | SWD probe (J-Link/CMSIS-DAP/pi) + 5 jumper wires | 1 | One-time Adafruit-bootloader flash on TP1–5. |

## Deliberately absent (vs earlier drafts)

- **Trackpad (IQS7211E / Cirque):** dropped from v1 — pointer duty is ZMK mouse keys
  on the FN layer + the D-pad. TP6–8 keep a rev-B trackpad possible.
- **JST-GH bridge / 2×08 pin header:** replaced by the FFC ZIF pair + type-A jumper
  (the THT header could not physically fit the shell cavity).
- **Column series resistors + dome-field TVS:** never made it onto any real board;
  the bridge is a short fixed internal ribbon. Rev-B option if field ESD appears.

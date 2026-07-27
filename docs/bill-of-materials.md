# Bill of materials — rev-A (v0.22)

Authoritative electrical BOM is machine-exported per board to
`hardware/kicad/generated/fab/right/bom.csv`
and `fab/left/bom.csv` (JLC format, exported only when DRC is clean —
regenerate with `python3 hardware/scripts/gen_fab.py`; the fab package is a build
artifact and is not committed). The tables below mirror those files and add the
mechanical / hand-installed items. Older 50-key and Raytac/Cirque BOMs are history —
see git history and [design-decisions.md](design-decisions.md).

## Right grip board (`thumbdeck_right`) — 71 SMT placements, all bottom side

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
| TMAG5273A1 | U4 | SOT-23-6 | **C3716049** | v0.21 pointing-nub hall sensor (Bean-style): I²C 3-axis, addr 0x35, reads the nub magnet through the 1.6 mm FR4. Basic-class SMT — machine-placed, no hand assembly. |
| LED_RED | D80 | 0603 | C2286 | Charge LED on MCP73831 STAT (through R25). **Check polarity in the DFM preview.** |
| 1N4148WS | D1–D36 (36×) | SOD-323 | C2128 | Matrix diodes, cathode → row. Basic part. |
| 4k7 | R1–R9 (9×), R26, R27 | 0402 | C25900 | Row pull-downs (R1–R9) + I²C SDA/SCL pullups (R26/R27). |
| 5k1 | R20, R21, R24 | 0402 | C25905 | CC1/CC2 pulldowns (R20/R21) + charger PROG (R24). |
| 1M | R22, R23 | 0402 | C26083 | Battery ÷2 divider on VBAT_SENSE (P0.02/AIN0). |
| 1k | R25 | 0402 | C11702 | Charge-LED series resistor. |
| 4u7/0805 25 V | C3, C4, C5 | 0805 | C1779 | Charger stability caps **at the chip** (C3 = VDD/VBUS, C5 = VBAT_CELL) + VBAT bulk (C4). 25 V rating — no derating collapse at 5 V. |
| 1uF | C1, C7 | 0402 | C52923 | 3V3 (C1) and VBUS (C7) decoupling. |
| 100nF | C2, C6, C8 | 0402 | C1525 | VBAT decoupling (C2) + SAADC filter on VBAT_SENSE (C6) + TMAG5273 bypass (C8). |

Plus non-BOM copper features: silk-labelled test pads **TP1–5** (SWDIO, SWDCLK,
RESET, 3V3, GND) and **TP6–8** (v0.21: now the live **SDA / SCL / TP_INT** I²C
nets of the nub sensor — still probe-able, and still the rev-B expansion bus).

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
| FFC jumper | **16-way, 1.0 mm pitch, type-A** (same-side contacts), **length ≥240 mm** (v0.24) | 1 | Straight ribbon; contacts face the boards at both ends. Type-A is load-bearing. **v0.24:** the clamp span is now VARIABLE (the grips slide 130–170 mm), so the ribbon carries a **rolling service loop** that folds in a channel under the telescoping bridge and pays out as the jaw moves — sized to reach at max extension (~195 mm J2-to-J2) plus the fold. Coupon-tune the loop radius. |
| LiPo | 1S **403040** pouch (4.0 × 30 × 40 mm, ~450–500 mAh), JST-PH pigtail | 1 | Foam-taped (0.3 mm) to the **left grip's floor** under the passive PCB. v0.24: the left grip is the sliding clamp jaw, so the cell rides with it; the FFC is the only cross-grip link. Replacement means opening the left grip (5 screws, lid, keymat, board). **Meter polarity against the "+"/"−" silk at J3 first** (pin 1 = "+"). |
| Extension springs (v0.24) | 2× stainless extension spring, ~5–8 N, ≥40 mm working extension | 2 | The clamp force. Hook one end to the bridge's fixed anchor and the other to the left-jaw anchor; they pull the grips together. Force is the feel — coupon-tune before committing. |
| ~~MagSafe ring~~ | — | 0 | **Dropped in v0.24** — the spring clamp + TPU edge cradles do the retention; no magnet ring. |
| Nub magnet | **Ø4 × 2 mm N52 disc**, axially magnetized | 1 + spares | Press-fit into the printed `nub_spring` pocket, **N pole toward the sensor (down)** — find N with a compass first (the face that attracts the needle's SOUTH/white end is N); the driver calibrates zero at boot but not polarity. |
| Shells | 7 printed parts: 6 in PETG — `back_left`, `back_right`, `grip_lid_left`, `grip_lid_right`, `center_panel`, + v0.21 `nub_spring` (Ø14.8 flexure, magnet press-pocket, v0.22 **4.4 mm-square TrackPoint cap platform** — arm thickness is the print-tune coupon) — and the v0.22 `nub_cap` (classic ThinkPad soft-dome replica, **RED TPU 95A**, prints with the keymats). **Or skip printing the cap: any genuine classic full-size TrackPoint cap (soft dome / soft rim / classic dome, ~4.5 mm square socket) fits the platform directly.** | 1 set | STLs tracked in `hardware/cad/models/` (regenerate: `deck3d.py --all --sync-models`). Every part fits an Ender 3 V2 (220 × 220) flat. **Regenerated + fit-checked for v0.22** (2026-07-24, 221 bodies, 0 collisions): lids 77.9 × 103.8, backs 170.5/162.8 × 103.8, panel 169.1 × 102.8 mm. |
| Keymats | per-grip, **TPU 95A** | 2 | Living-hinge web; coupon-test >10 k cycles first. **v0.17 geometry**: rectangular 8.5 × 7 rounded-rect caps (2u caps for the space bars + the right H-row's Rii-style Enter), round cluster keys, debossed keycap legends; ~63 × 86–89 mm per mat. |
| M3 hardware | **M3×10 countersunk (DIN 965)** screws + M3 heat-set inserts (Ø4.0 bores, OD ≤4.6, ~4 mm long) | 10 + 10 | Heads FLUSH with the face: 5 per grip lid. v0.24: the 4 panel border screws are gone (no center panel); the bridge bolts to the right grip with 2 short M3s into its cradle bosses. |
| Bootloader flash rig | SWD probe (J-Link/CMSIS-DAP/pi) + 5 jumper wires | 1 | One-time Adafruit-bootloader flash on TP1–5. |

## Deliberately absent (vs earlier drafts)

- **Trackpad (IQS7211E / Cirque):** dropped from v1; v0.21 gives pointer duty to the
  right-grip hall nub (FN-layer mouse keys + D-pad remain as fallback).
- **ALPS RKJXV analog stick:** implemented then reverted inside v0.21 — the THT
  gimbal module can't sit flush (11.2 mm body vs 5.2 mm cavity) and needed JLC
  hand-solder. The hall nub replaces it outright; see design-decisions.md.
- **JST-GH bridge / 2×08 pin header:** replaced by the FFC ZIF pair + type-A jumper
  (the THT header could not physically fit the shell cavity).
- **Column series resistors + dome-field TVS:** never made it onto any real board;
  the bridge is a short fixed internal ribbon. Rev-B option if field ESD appears.

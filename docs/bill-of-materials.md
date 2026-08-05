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
| Dome retention | Snaptron taped polyimide array (Peel-N-Place) or 0.2–0.3 mm laser-cut polyimide spacer | 2 | **Required** — laterally retains each dome; the tape channels also vent them. **v0.25:** this layer is *not modelled in the CAD*, so no collision check knows it exists — but it is the surface the left keymat's nav-pad back rib actually meets. `DOME_RETAIN_T` = 0.3 (the spec'd max) is subtracted before the rib's 0.2 mm clearance, so the rib clears the layer at any thickness in range rather than being preloaded into it. |
| FFC jumper | **16-way, 1.0 mm pitch, type-A** (same-side contacts), **length ≥240 mm** (v0.24) | 1 | Straight ribbon; contacts face the boards at both ends. Type-A is load-bearing. **v0.24:** the clamp span is now VARIABLE (the grips slide 130–170 mm), so the ribbon carries a **rolling service loop** that folds in a channel under the telescoping bridge and pays out as the jaw moves — sized to reach at max extension (~195 mm J2-to-J2) plus the fold. Coupon-tune the loop radius. **v0.24d:** the ribbon runs in its **own walled channel on J2's y centre** (24.5) — dead straight into the ZIF, with a divider rib between it and each spring lane, so the loop can crumple at short spans without finding a coil to snag on. |
| LiPo | 1S **403040** pouch (4.0 × 30 × 40 mm, ~450–500 mAh), JST-PH pigtail | 1 | Foam-taped (0.3 mm) to the **left grip's floor** under the passive PCB. v0.24: the left grip is the sliding clamp jaw, so the cell rides with it; the FFC is the only cross-grip link. Replacement means opening the left grip (5 screws, lid, keymat, board). **Meter polarity against the "+"/"−" silk at J3 first** (pin 1 = "+"). |
| TPU grippers (v0.24) | 2× soft **polyether TPU 95A**, **100 % infill** — edge-grip + **teeth** + lip **facing** (`gripper_left/right`), print with the keymats | 2 | Specify **polyether**, not polyester, TPU (any TDS stating polyether; NinjaTek and similar): polyester TPU hydrolyses in warm humid service, which is exactly a phone grip. 100 % infill is mandatory — a sparse pad's stiffness is infill-dependent, not material-dependent. Compliant grip on the cased short edge, plus half-round **teeth** (3.4 mm pitch, 0.8 mm proud, ribs along the phone's thickness) that bite it so the phone can't creep or rotate in y. **v0.24e — this part still retains the phone, and the lip stays TPU on purpose:** it has to flex for phone+case thickness variance, and hard plastic on cover glass is a scratch source. A rigid hook over the phone was tried and rejected (a hook at a fixed z can only capture a phone at or below the nominal cased thickness). The shell now carries a **retainer that caps the lip's root only** — it stops 0.4 mm outboard of the clamped phone edge, so nothing rigid is over the screen — which stops the gripper peeling off without stiffening the part that needs to give. Slide each gripper in from the **y end, under the retainer** — teeth facing the phone. |
| Clamp springs (v0.24) | 2×, in the tray's outboard y lanes (13.5 / 83.5), ~40 mm working travel | 2 | The clamp force. **v0.24e moved the anchor to x = 76**, so the installed length runs 61.85 → 105.85 mm — a **1.71:1** length ratio instead of the 6.1:1 (510 % extension) the x = 22 anchor demanded. **⚠ Do not buy hooked extension springs yet.** The math doesn't close: a Ø4 / 0.5 mm music-wire spring at C = 7 caps initial tension at ~1.85 N/spring (τ_i would need ~259 MPa vs a ~160 MPa limit), so min-span clamp lands ~5.8 N total, and τ ≈ 870–930 MPa against an ~843 MPa cyclic allowable means it is **fatigue-limited on a part that cycles every insertion — and a hook's failure mode is total release.** Backbone / Kishi / GameSir / Abxylute all use **compression springs captive in the bridge** or a **constant-force spiral** instead. Pick one before ordering. |
| Battery power cable (v0.24) | 2-wire, ~2 mm OD, ≥240 mm, JST-PH to the 403040 pigtail | 1 | Carries the left-grip battery to J3 on the right board — runs ENCLOSED through the tray in its **own walled channel** beside the FFC (v0.24d lane plan: `spring \| FFC \| power \| spring`, all on one z, nothing stacked), with its own service loop. |
| Nub magnet (v0.26) | **Ø4 × 2 mm, NdFeB **N45**, Ni‑Cu‑Ni plated, **AXIALLY magnetized** (poles on the flat faces).<br>**Primary: supermagnete `S-04-02-N`** — Br 1.32–1.37 T, ≤ 80 °C, 0.19 g, ~€0.26 ea in 20‑packs, mass stock.<br>**US: totalElement `D4X2MMN52-250PK`** (N52, Br 1.48 T — see temperature note).<br>**Hot‑climate option — NOT a drop‑in: Radial Magnet 9039 = Digi‑Key `469-1072-ND`** — Ø4 × **2.5** mm N35SH, 150 °C, 100 % sorted to ≤ 3° magnetization‑angle deviation. | 1 + spares | **Order by SKU, not by description.** A Ø4 × 2 mm *diametrically* magnetized disc is also a cataloged product and is the wrong part — it would give the sensor a large static transverse field and a pointer that drifts with cap rotation. Every SKU above is axial. <br>**Grade:** N45, not N52. N52 has the **lowest** service temperature of the common grades (**≤ 65 °C** vs ≤ 80 °C for N45/N42) and this device clamps a phone, sits in sunlight and rides in cars. Past that limit the loss is **irreversible**, and the driver's boot‑zero *cannot* recover it — it silently re‑zeros a weaker magnet and pointing goes permanently sluggish. The 8 % lower Br costs nothing that matters (see `deck3d.py --nub`). Use the N35SH part if the build will see a hot car dash. <br>**Fit:** the pocket is **Ø4.20** (v0.26, was Ø4.10). Stock Ø4 discs are ±0.10, so a +tolerance magnet *is* Ø4.10 — and FDM prints holes undersize, which makes a hand press‑fit into the hub's 1.45 mm wall a split‑hub risk. Bond it with a drop of cyanoacrylate instead; a press fit in a printed part relaxes anyway. <br>**Polarity: N pole DOWN, toward the sensor.** Find N with a compass first — the magnet face that attracts the needle's **SOUTH/white** end is N. The driver calibrates zero at boot but **not** polarity, so a flipped magnet gives a correctly-scaled, permanently **inverted** pointer. <br>**Handling:** keep it away from the assembled boards until it goes in — it will happily jump onto a steel tool and chip (NdFeB is brittle and the Ni plating is the corrosion barrier). <br>**⚠ The Ø4 × 2.5 mm N35SH part is a CAD change, not a substitution.** Because the magnet is bonded against the pocket **ceiling**, an extra 0.5 mm of thickness grows **downward**: the magnet‑to‑die gap falls 3.33 → 2.83 mm (outside the asserted 3.05–3.65 band, so `deck3d.py --report` will fail), and the air gap under the magnet falls 0.95 → 0.45 mm — below the 0.5 mm assert and leaving only 0.10 mm beneath the plunge stop. To use it, raise `NUB_POCKET_TOP` 12.45 → 12.95, which thins the hub crown 1.55 → 1.05 mm. Only worth it for a build that will live on a hot car dashboard. |
| Shells | **v0.25: 6 printed parts** (was 7 — the `bridge` tray is now part of `back_right`): 5 in PETG — `back_left` (moving jaw), **`back_right` (ground — grip + fixed tray as ONE part)**, `grip_lid_left`, `grip_lid_right`, + v0.21 `nub_spring` (Ø14.8 flexure, magnet press-pocket, v0.22 **4.4 mm-square TrackPoint cap platform** — arm thickness is the print-tune coupon) — and the v0.22 `nub_cap` (classic ThinkPad soft-dome replica, **RED TPU 95A**, prints with the keymats). **Or skip printing the cap: any genuine classic full-size TrackPoint cap (soft dome / soft rim / classic dome, ~4.5 mm square socket) fits the platform directly.** | 1 set | STLs tracked in `hardware/cad/models/` (regenerate: `deck3d.py --all --sync-models`). Every part fits an Ender 3 V2 (220 × 220) flat. **v0.24: `center_panel` retired → `bridge` tray; `gripper_left/right` (TPU) added. v0.25: `bridge` merged into `back_right` (joint deleted, not fixed); the faceted back crown deleted and both grips' backs dropped to the tray plane, so the whole back is one flat plane with a 1.2 mm quarter-round edge.** Fit-checked 0 collisions across the 130–170 mm clamp travel (min/nominal/max). |
| Keymats | per-grip, **TPU 95A** | 2 | Living-hinge web; coupon-test >10 k cycles first. **v0.17 geometry**: rectangular 8.5 × 7 rounded-rect caps (2u caps for the space bars + the right H-row's Rii-style Enter), round cluster keys, debossed keycap legends; ~63 × 86–89 mm per mat. **v0.25**: the left mat's nav cluster is one **Ø24 integrated D-pad** (four arm sectors + Ø9 centre OK, 2.0 mm moats over a web thinned to 0.4 mm) with an annular **back rib** at r 13.0–14.5 that meets the grip lid's clamp ring — print it **100 % infill** like the grippers, or the rib's stiffness is infill-dependent and the presses stop being discrete. Print cap-side **down**: the legends deboss cleanly off the bed and the rib/nubs become upstands, so no support. |
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

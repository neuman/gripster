# Design review (professional EE pass) — thumbdeck v0.4

Adversarial review of the whole design + plan, and the mitigations now folded in.
Grading covers geometry + config **structure only** — passing the loop is
necessary, **not** sufficient. The human-verified gates below still gate a fab
order.

## Verdict

Concept and layout are sound; the electrical design is only partly done. The two
issues that would make it fail outright — **antenna keep-out** and **bridge
signal integrity** — are now addressed in the layout, firmware and BOM, and are
enforced by the grader (`F-antenna`, `F-si-debounce`, `F-si-passives`, `F-esd-tvs`).

## Findings & mitigations

### 🔴 1. RF antenna keep-out — *fixed in layout*
nRF52840 antenna needs an all-layer no-copper keep-out under the RF path. The
nice!nano is now mounted **vertically at the top with the antenna end overhanging
the top board edge**; the LiPo is at the bottom (max separation); USB-C is via a
shell notch. Enforced by `F-antenna` (overhang + ≥10 mm from LiPo + clear of keys).
Residual risk: phone + hand still detune the antenna → expect reduced range.

### 🔴 2. Bridge signal integrity — *mitigated in firmware + BOM*
Scanned matrix over a long, flexing cable. Mitigations: external **4.7 kΩ row
pull-downs**, **100–330 Ω column series** resistors, **8 ms debounce**, **shielded
flex-rated cable** + strain relief, **TVS** on the conductors. The 4-wire I²C
expander alternative is **worse** over a flexing cable (use 74HC165/UART instead).
Residual risk: flex-cycle fatigue — spec a cable rated for it and strain-relieve.

### 🟠 3. Charge current vs. small cell — *documented*
~100 mA (1C into 100 mAh) is aggressive. Use a protected cell rated for 1C, a
≥200 mAh cell, or change the PROG resistor. (`F-charge`)

### 🟠 4. Switch pin-pairing assumed — *gated (human)*
The "4-leg → 2-terminal SPST" claim must be **metered** before committing 50
parts. (`F-switch-verify`; footprints README.)

### 🟠 5. Firmware unbuilt / pin collisions — *gated (CI)*
Config is unverified until the ZMK GitHub Actions build is green; confirm chosen
`pro_micro` pins don't collide with the nice!nano's battery ADC / LED / reset.

### 🟡 Watch items
ESD (TVS added), mechanical flex cracking joints (clamp shell load-bearing,
undesigned), grip thickness driven by LiPo, SMD tact feel/lifecycle, keycaps
unsolved, small-battery runtime, BLE latency (fine for typing, poor for gaming),
right-hand weight bias. Thermal: not a concern.

## FMEA — most likely failure modes

| # | Failure | Cause | Mitigation | Residual |
|---|---|---|---|---|
| 1 | Won't pair / poor BLE | antenna under copper; phone+hand | edge overhang keep-out | Med |
| 2 | Phantom keys / chatter | weak pulls, cable C, crosstalk | ext pull-downs, series R, debounce | Low-Med |
| 3 | Dead row/col over time | bridge flex fatigue | flex-rated shielded cable, strain relief | Med |
| 4 | Swollen/unsafe cell | 1C charge on small LiPo | protected 1C cell / bigger cell / PROG R | Low |
| 5 | Wrong matrix / rework | switch pinout assumed | meter before commit | Low |
| 6 | Firmware won't scan | unbuilt config / pin collision | run CI, check pin map | Low-Med |
| 7 | Cracked joints | board flex under thumb load | stiffen shell, support under module/LiPo | Med |
| 8 | GPIO ESD damage | exposed bridge cable | TVS on conductors | Low |

## Human-verified gates before a fab order (not automatable)

1. **Meter** the switch pin pairing; build + verify the footprint.
2. Draw the **schematic**; generate netlist; **route**; pass **DRC + ERC**.
3. **ZMK CI build green**; confirm no `pro_micro` pin collisions.
4. Confirm charge current vs. the actual cell.
5. Prototype **bring-up** with the current-draw checkpoints (assembly.md).

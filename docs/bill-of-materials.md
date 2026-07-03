# Bill of materials

Per the 25/half default (50 keys total). Quantities include the two halves.

| Item | Part | Qty | Notes |
|---|---|---|---|
| Tact switch | Xiaoyztan 5×5×1.5 mm 4-terminal SMD | 50 (+spares) | Owned (300 pcs). 4 legs, internally 2-terminal SPST. Footprint = `TODO(user)`. |
| Diode | 1N4148W SOD-123 | 50 | One per key, `col2row`, uniform orientation. |
| Controller | XIAO nRF52840 (or nice!nano v2) | 2 | BLE + USB-C + onboard LiPo charging. One per half. |
| LiPo cell | protected, ~100–150 mAh | 2 | One per half. Confirm capacity vs. shell space. |
| Power switch | slide SPST (optional) | 2 | Optional per-half power cut. |
| M2 hardware | M2 screws + heat-set inserts / standoffs | ~6 | For the 3 mount holes per half → clamp shell. |
| PCB | thumbdeck_left + thumbdeck_right, 1.6 mm HASL | 5 each | JLCPCB. Gerbers after routing + footprint verify. |
| Keycaps / tops | TBD | 50 | `TODO(user)` — required over bare plungers. |
| Inter-half cable | — | 0 | None. Halves link over BLE. |

## Sourcing notes

- **Controller default = XIAO nRF52840** for a slim grip (uses 10 of its 11
  exposed GPIO). Switch to **nice!nano v2** if you want breathing room (~18 GPIO)
  or add an I²C touchpad later.
- **LiPo:** 100–150 mAh runs a BLE keyboard for weeks idle; heavier use drains
  faster. Use a **protected** cell that physically fits the LiPo keep-out
  (26 × 13 mm zone on the board).
- **PCB finish:** HASL is fine (SMD switches, no exposed carbon pads).

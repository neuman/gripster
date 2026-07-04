# Bill of materials (v0.3 — single controller)

50 keys total (25/grip). One controller, one battery.

| Item | Part | Qty | Notes |
|---|---|---|---|
| Tact switch | Xiaoyztan 5×5×1.5 mm 4-terminal SMD | 50 (+spares) | Owned. Internally 2-terminal SPST. Footprint = `TODO(user)`. |
| Diode | 1N4148W SOD-123 | 50 | One per key, `col2row`, uniform orientation. |
| **Controller** | **nice!nano v2** (nRF52840) | **1** | ~18 usable GPIO; BLE + USB-C + onboard LiPo charging. In the right grip. |
| **LiPo cell** | protected, ~100–150 mAh | **1** | One only. In the right grip. Confirm vs. shell. |
| **Bridge connector** | 10-pin FPC/JST (2×) + ribbon/flex | 1 set | Right↔left grip, through the telescoping bridge. |
| Power switch | slide SPST (optional) | 1 | Right grip. |
| M2 hardware | screws + heat-set inserts / standoffs | ~6 | 3 mount holes per grip → clamp shell. |
| PCB | thumbdeck_right (MCU) + thumbdeck_left (passive), 1.6 mm HASL | 5 each | JLCPCB. Two distinct boards. |
| Keycaps / tops | TBD | 50 | `TODO(user)` — required over bare plungers. |

### Optional variant

| Item | Part | Qty | Notes |
|---|---|---|---|
| Bridge I/O expander | MCP23017 (I²C) | 1 | In the left grip → bridge shrinks to **4 wires** (SDA/SCL/V+/GND) instead of 10. |

## Notes vs. v0.2

- **Halved:** one controller (was 2), one LiPo (was 2), one USB-C charge (was 2).
- The two PCBs are **no longer identical** — the right is the MCU board
  (controller + LiPo + USB-C + bridge), the left is a passive matrix + bridge.
- **Controller default changed** XIAO nRF52840 → **nice!nano v2** for the GPIO to
  scan all 50 keys on one MCU (15 pins).
- HASL finish is fine (SMD switches, no exposed carbon pads).

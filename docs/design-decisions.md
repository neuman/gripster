# Design decisions

## v0.3 — the architecture pivot (single controller)

**Decision:** one nRF52840 in the right grip; the left grip is a passive matrix
wired over the bridge. This *replaces* v0.2's two-controller ZMK BLE split.

**Why:** the halves are joined by a telescoping bridge, so a cable through it is
simpler than a wireless link between them — which is exactly how real Backbone-
style controllers are built (single MCU + battery + radio; the other grip wired
across). The two-controller split was borrowed from desk split-keyboards, where
the halves are physically separate; it doesn't fit a bridged phone controller.

**What it buys:** one battery, one USB-C, **one charge session**, ~half the BOM,
lower latency, no inter-half pairing, and *simpler* firmware (a plain 50-key
keyboard, no split/`col-offset`/battery-proxy).

**What it costs:** GPIO — one MCU must scan 50 keys (15 pins). Resolved by moving
the default board **XIAO nRF52840 → nice!nano v2** (~18 usable GPIO). Optional
MCP23017 I²C expander in the left grip reduces the bridge to 4 wires. The one
property given up — halves that fully detach with zero electrical link — isn't a
real requirement for something that clamps a phone.

## Locked decisions (updated for v0.3)

| Area | Decision |
|---|---|
| Form factor | Two grips, Backbone-clamp style, flanking a phone. 3D shell = user's later work; PCB exposes mount + bridge features. |
| Reference look | i8+-inspired QWERTY, split L/R. Keys-only (touchpad = `TODO(user)`). |
| Switches | Xiaoyztan 5×5×1.5 mm 4-terminal SMD tact (owned). Treated as 2-terminal SPST. |
| **Controller** | **One nRF52840 (nice!nano v2)** in the right grip. |
| **Left grip** | **Passive** 5×5 matrix (switches + diodes), wired over the bridge. |
| **Connectivity** | BLE **or** USB-C wired HID, from the single controller. |
| **Power** | **One LiPo**, one USB-C charge, nice!nano onboard charger. |
| **Matrix** | Single 5×10 (no split). Cols 0–4 right grip, 5–9 left grip. `col2row`, 1N4148W. |
| Firmware | ZMK, single non-split shield `thumbdeck` on `nice_nano_v2`. |
| Fabrication | JLCPCB, 1.6 mm, HASL, gerbers from KiCad. |

## Decisions carried from the layout loop

- **Real pins.** rows `pro_micro 4,5,6,7,8`; cols `9,10,14,15,16` (right) +
  `18,19,20,21,1` (left, over bridge). All in the nice!nano `pro_micro` set;
  15 of ~18, leaving `0,2,3` (2/3 = I²C for the expander option).
- **Left-half legends pre-reversed** so the mirrored render reads naturally
  ("1 2 3 4 5", "Q W E R T"). `matrix_map.py` asserts legends == keymap.
- **Board geometry.** 63 × 108 mm per grip, symmetric D-shape (flat inner mating
  edge + bowed outer). Both grips same outline (symmetric phone clamp); keep-outs
  differ by role. Bridge connector at the inner-bottom corner of each grip.
- **Render path.** matplotlib PNG (no KiCad in this env); board file is
  hand-authored KiCad S-expression.
- **License:** MIT.

## History: v0.2 (superseded)

v0.2 was a ZMK **BLE split** — two XIAO nRF52840s (right=central, left=peripheral),
a 50-key combined transform with a peripheral `col-offset`, and a LiPo + USB-C per
half. It graded PASS but was more complex than this form factor needs. See the git
history and `renders/iter_03.png`.

## Open `TODO(user)`

- Datasheet-verified switch footprint (before gerbers).
- Copper routing in KiCad (before gerbers), incl. the bridge connector pinout.
- Bridge cable + connector choice (10-pin FPC/JST, or MCP23017 → 4-wire).
- LiPo capacity vs. shell space (~100–150 mAh assumed).
- Keycap/top solution; touchpad (would use the nice!nano's spare GPIO / I²C).
- 3D clamp + bridge shell geometry (out of scope here).
- Confirm key count/reach against a real i8+ and your thumb span.

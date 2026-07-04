# Assembly, flash, charge, pair & test (v0.3 — single controller)

## 0. Before boards exist (two gates)

1. Verify the switch footprint vs. the real Xiaoyztan datasheet
   (`hardware/footprints/README.md`).
2. Route both boards in KiCad and export gerbers (`hardware/kicad/README.md`),
   including the bridge connector pinout.

## 1. Solder

**Both grips:** reflow/hand-solder the **25 switches** and **25 diodes** (SOD-123).
Keep every diode's cathode band toward the row net (`col2row`), same orientation
on both grips.

**Right grip only (the MCU board):**
- Solder the **nice!nano v2** to its castellated pads (top keep-out).
- Wire the **LiPo** to `BAT+/BAT-`. **Observe polarity.**
- (Optional) slide power switch in line with the cell.

**Bridge:** solder the 10-pin bridge connector at the inner-bottom corner of each
grip; run the flex/ribbon (5 shared rows + 5 left-grip columns) through the
telescoping bridge. *(Or, for the expander variant: MCP23017 in the left grip +
a 4-wire cable.)*

## 2. Flash ZMK — one image

- Push this repo; **GitHub Actions** (`.github/workflows/build.yml`) builds a
  single `thumbdeck` firmware for `nice_nano_v2`.
- Double-tap reset on the nice!nano → it mounts as a USB drive → drag the
  `thumbdeck-*.uf2` on. **One flash — there's no second controller.**

## 3. Charge (LiPo safety — read this)

- Charge over the **single USB-C** on the right grip, via the nice!nano's
  **onboard charger**. One cable, one session.
- Use a **protected** cell. **Never charge unattended.** Keep it in its keep-out,
  clear of switch travel and soldering heat.

## 4. Pair

- Power the keyboard. Pair the host to the advertised **"thumbdeck"** device.
- No inter-half pairing — the left grip is wired, not a BLE peer.
- Wired option: plug the right grip into the host over USB-C for wired HID.
- Re-pair / clear bonds: **Fn + `BT_CLR`**, then `BT_SEL 0/1/2` for a profile.

## 5. Test

- Type across both grips — all 50 keys should register and match the legends
  (`matrix_map.py` is the label ↔ keycode source of truth). If a whole *column*
  of the **left** grip is dead, suspect a bridge-cable conductor; a dead **row**
  affects both grips (rows are shared).
- Check the single **battery level** reports on the host.
- Confirm the **fn layer** (`Fn` = left outer thumb) + `BT_*`.
- Hold several keys at once to confirm the diodes kill ghosting.

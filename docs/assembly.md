# Assembly, flash, charge, pair & test

Order of operations once you have fabricated boards.

## 0. Before boards exist (two gates)

1. Verify the switch footprint against the real Xiaoyztan datasheet
   (`hardware/footprints/README.md`).
2. Route the board in KiCad and export gerbers (`hardware/kicad/README.md`).

## 1. Solder (per half)

- Reflow/hand-solder the **25 switches** and **25 diodes** (SOD-123). Keep every
  diode's cathode band oriented the **same** way, toward the row net (`col2row`).
- Solder the **XIAO nRF52840** to its castellated pads (top keep-out).
- Wire the **LiPo** to the board's `BAT+/BAT-` pads. **Observe polarity.**
- (Optional) slide power switch in line with the cell.

## 2. Flash ZMK

- Easiest: push this repo to GitHub, let **Actions** build (see
  `.github/workflows/build.yml`), download `thumbdeck_left-*.uf2` and
  `thumbdeck_right-*.uf2`.
- Put each half into bootloader (double-tap reset on the XIAO) → it mounts as a
  USB drive → drag the matching `.uf2` on. Flash **left → thumbdeck_left**,
  **right → thumbdeck_right**.

## 3. Charge (LiPo safety — read this)

- Charge each half over its **own USB-C**, using the board's **onboard charger**.
- Use a **protected** cell. **Never charge unattended.** Keep the cell in its
  keep-out, clear of switch travel and away from any soldering heat.
- First charge: watch the charge LED; stop if the cell warms noticeably.

## 4. Pair

- Power both halves. The **right (central)** auto-links to the **left
  (peripheral)** over BLE (they bond on first co-power).
- On the host, pair to the advertised **"thumbdeck"** device (the central).
- Wired option: plug the central into the host over USB-C for wired HID; the left
  half still links to the central over BLE.
- Re-pair / clear bonds: **Fn + `BT_CLR`** (top-left on the fn layer), then
  `BT_SEL 0/1/2` to pick a host profile.

## 5. Test

- Type across both halves — confirm all 50 keys register and match the legends
  (`matrix_map.py` is the source of truth for label ↔ keycode).
- Check per-half **battery level** reports on the host.
- Confirm the **fn layer**: `Fn` (left, outer thumb) + `BT_*`.
- Hold multiple keys at once to confirm the diodes kill ghosting.

# Connectivity & power

## Two independent wireless halves (standard ZMK split)

- **Central half (default: right)** — pairs with the host (phone/PC) over BLE and
  presents the whole keyboard. Also the half you plug into the host over **USB-C**
  for wired HID.
- **Peripheral half (default: left)** — links to the central over BLE and relays
  its keypresses.

```
        wireless:                         wired:
  host  ⇄BLE⇄  RIGHT(central) ⇄BLE⇄ LEFT   host ⇄USB-C⇄ RIGHT(central) ⇄BLE⇄ LEFT
```

## Connectivity modes

- **Wireless:** host ⇄ central (BLE) ⇄ peripheral (BLE).
- **Wired:** central ⇄ host over USB-C (ZMK USB output). The peripheral **still
  links to the central over BLE** in this mode.

> **Decision point (`TODO(user)`).** A single wired USB device composed of *both*
> halves is **not** how a ZMK split works — that needs a physical bridge and a
> different single-controller design. Default accepted here:
> **central-USB + peripheral-BLE**. If fully-wired-both-halves is a hard
> requirement, respec around a bridged single controller.

## Power / charging

- One LiPo per half. Each board's **onboard charger** recharges its own cell over
  that half's USB-C (XIAO nRF52840 default charge current ≈ 50 mA — a safe
  ~0.3–0.5C for a 100–150 mAh cell; raise via the board's charge-set resistor if
  you fit a larger cell).
- ZMK reports each half's battery level over BLE; the central proxies the
  peripheral's level (`CONFIG_ZMK_SPLIT_BLE_CENTRAL_BATTERY_LEVEL_PROXY`).
- Optional slide power switch per half.

## Safety (see also assembly.md)

Use a **protected** LiPo cell of appropriate capacity. Rely on the controller
board's onboard charging circuit. **Never charge unattended.** Keep the cell
inside its keep-out, away from soldering heat and switch travel.

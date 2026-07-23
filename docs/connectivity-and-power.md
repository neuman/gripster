# Connectivity & power — rev-A (v0.19)

One controller, one battery, one USB-C. The **right grip** carries the E73
(nRF52840) module and the entire power front-end; the **left grip** is a passive
matrix over a fixed internal FFC ribbon. This supersedes all earlier versions of
this file (nice!nano/BQ24075, JST-GH harness, telescoping-cable era).

```
   LEFT grip (passive)                      RIGHT grip (MCU)
   42 domes + diodes  ── 16-way FFC ──      E73 nRF52840 + charger + USB-C  ⇄ host (BLE HID)
   (no chip; hosts cell)  straight type-A   scans all 78 keys + I2C hall nub (pointer)
```

## The power tree

```
403040 LiPo cell, left grip (leads cross the spine → JST-PH, J3)
   ├── MCP73831 charger (U2) ← USBLC6-2 ← USB-C VBUS      # charger on the CELL side
   └── MSK12C02 slide switch (SW90)
          └── VBAT rail ── E73 VDDH (pad 23)               # high-voltage / REG0 mode
                              └── internal REG0 → 3V3 (pad 19, output only)
```

- **Charger on the cell side of the switch** — the battery charges while the
  device is switched **off**. The switch only gates the load.
- **LiPo-direct (high-voltage) mode:** raw cell 3.0–4.2 V into **VDDH** only.
  **VDD (pad 19) is the internal REG0 3.3 V output** — decoupled (C1), never
  driven. The Adafruit bootloader sets `UICR.REGOUT0 = 3.3 V` at first flash. The
  E73 module has **no DCDC inductors**, so the regulator runs in LDO mode —
  correct, and why `CONFIG_BOARD_ENABLE_DCDC` is absent from the firmware.
- **Charging:** USB-C VBUS → **USBLC6-2SC6 inline** → MCP73831 (**-2ACI**, 4.2 V).
  PROG = 5.1 kΩ (R24) → **~196 mA**, ~0.43 C of the 403040 cell (~450–500 mAh) —
  comfortably safe. 4.7 µF 0805 25 V stability caps sit **at the chip** on
  both supply pins (C3) and the cell node (C5), per datasheet; C4 is VBAT bulk.
- **Charge LED (D80):** VBUS → 1 kΩ (R25) → LED → MCP73831 STAT. Lights while
  charging, off when full; visible through a 1.5 mm hole in the shell floor.
- **Battery gauge:** 1 MΩ/1 MΩ divider (R22/R23) + **100 nF SAADC filter (C6)** on
  VBAT_SENSE → P0.02/AIN0. The 100 nF is what makes the reading stable — the
  SAADC's sampling cap on a 500 kΩ source impedance needs a reservoir.

> **v0.18:** the cell left the spine — the sunken phone well leaves only 0.5 mm
> under its floor slab, so no standard pouch fits there any more. The battery is
> now a **403040** pouch (4.0 × 30 × 40 mm, ~450–500 mAh) foam-taped (0.3 mm) to
> the **left** grip's floor under the passive PCB (0.84 mm clearance below the
> diodes at nominal); its leads run along the bottom-border lane outside the
> well, across the spine through lead windows in both transverse walls, to
> **J3** on the right board. It installs in the left grip **before** that
> grip's board goes in; replacing it means opening the **left** grip (5 screws
> → lid → keymat → board). The FFC stays serviceable via the panel.

## USB

- **USB-C (J1, full-SMD 16P):** CC1/CC2 each pull down via 5.1 kΩ (R20/R21) —
  without them a Type-C charger never turns on VBUS. VBUS → module pad 27 (USB
  detect) and the charger.
- **Data pair:** the receptacle's pin pairs (A6/B6, A7/B7) are interleaved on this
  connector, so `gen_board.py` draws **deterministic copper** — a D− bar plus a
  D+ In2 hop and fixed In2 runs to module pads 29/31. Autorouters can't solve that
  pattern; it rides through routing as fixed wires.
- USB is for **charging and UF2 flashing**. (ZMK can also do wired HID over it.)

## Radio

- BLE HID to the host as **"thumbdeck"** — one device, no inter-half pairing.
- The E73's ceramic antenna points **up, off the top board edge** (centre-top,
  farthest from the phone and LiPo), with an all-layer copper keep-out crossing
  the edge and a 0.6 mm relief in the shell wall (present in the regenerated
  v0.18 shells). This replaced an earlier placement that aimed the antenna mid-board at the
  USB shell over ground pour (detuned).
- **No 32.768 kHz crystal on the module** — firmware runs the LF clock from the
  internal RC (`CONFIG_CLOCK_CONTROL_NRF_K32SRC_RC` + 500 PPM). Without that
  setting BLE never starts; it's already in `thumbdeck_defconfig`.
- Residual reality: the phone and your hands flank the antenna — expect reduced
  range vs an open board. Fine for a device used at arm's length.

## Controls through the shell

| Control | Part | Access |
|---|---|---|
| Power | MSK12C02 slide (SW90) | knob through an 8 × 2.8 mm slot in the **top** shell wall (v0.17 relocation, see note below) |
| Reset / UF2 | TS-1187A tact (SW91), top-actuated | paperclip through a 1.6 mm pinhole in the shell floor (double-tap = bootloader) |
| Charge state | red LED (D80) | 1.5 mm light hole in the shell floor |

> **v0.17:** the E73 and the whole power front-end moved to the **top** zone —
> the USB-C opening and the power-switch slot are now in the **top shell wall**;
> the reset pinhole and charge light-hole stay in the floor at the relocated
> positions. Shells regenerated + fit-checked 2026-07-14 (`deck3d.py --check`
> = 0 collisions).

## Safety

- Use a **protected** 1S pouch cell. **Never charge unattended.**
- **Polarity:** the JST-PH connector is polarized, but vendors wire PH pigtails
  **both ways** — meter the pigtail against the **"+"/"−" silk beside J3** (pin 1
  = "+", nearer the bottom board edge) before first plug-in.
- ~196 mA charge current is ~0.43 C for the 403040 cell (~450–500 mAh); no PROG
  change needed.

> ⚠️ **SUPERSEDED / VERSION-DRIFTED.** This file describes an earlier design (50-key nice!nano BQ24075 split). The current board is a **79-key 9×10 Ebyte E73 (nRF52840)** with an external **MCP73831** charger. See [`docs/evaluation.md`](evaluation.md) and the code for the authoritative design.

# Connectivity & power (v0.3 — single controller)

## One controller, a wired bridge — how real telescoping controllers work

thumbdeck v0.3 uses **one** nRF52840 (nice!nano v2), in the **right** grip. The
**left** grip is a passive 5×5 switch matrix wired to the right grip through the
telescoping bridge. This mirrors how real Backbone-style controllers are built
(single MCU + battery + radio in one grip; the other grip's inputs run across the
bridge) — not two boards doing a wireless handshake.

```
   LEFT grip (passive)                 RIGHT grip (MCU)
   25 switches + diodes  ── bridge ──  nRF52840 + LiPo + USB-C  ⇄ host (BLE or USB-C)
   (no chip, no battery)   cable       scans all 50 keys
```

### Why not two controllers over BLE?

The v2 design put an nRF52840 in *each* grip and linked them over a BLE split
(the mechanical-keyboard convention). For a device whose halves are joined by a
bridge, that's over-engineered: it doubles the controllers, batteries, chargers
and USB ports, needs two separate charge sessions, and adds a wireless hop
between the halves. Since the bridge already spans the gap, a cable through it is
simpler in every dimension. See [design-decisions.md](design-decisions.md).

## The bridge cable

10 conductors run from the right grip's bridge connector to the left grip's:

- **5 shared row lines** (`pro_micro 4,5,6,7,8`) — the scan rows reach both grips.
- **5 left-grip column lines** (`pro_micro 18,19,20,21,1`) — driven from the MCU,
  out to the left grip's columns.

The right grip's own 5 columns (`pro_micro 9,10,14,15,16`) stay local. The left
grip needs **no power** — it's a passive matrix of switches + diodes.

> **Alternative (`TODO(user)`):** put an **MCP23017** I²C GPIO expander in the
> left grip and cross only **4 wires** (SDA `pro_micro 2`, SCL `pro_micro 3`,
> V+, GND). Trades a chip for a thinner cable. The default direct-wire approach
> needs no chip.

## Connectivity modes

- **Wireless:** the MCU pairs to the host over BLE and presents the whole keyboard.
- **Wired:** plug the right grip into the host over USB-C for wired HID
  (`CONFIG_ZMK_USB`). Either way it's one USB/BLE device — no inter-half pairing.

## Power / charging

- **One LiPo**, in the right grip, on the nice!nano's **onboard charger** (BQ24075).
- **One USB-C**, one charge session (the pain point of v2's two-battery design is
  gone).
- ZMK reports the single battery level over BLE.
- Optional slide power switch in the right grip.

### Charge current vs. cell C-rating (EE review)

The nice!nano's default **charge current is ~100 mA** (set by a 10 kΩ PROG
resistor). Into a 100 mAh cell that is **1C** — aggressive; many small pouch cells
spec **0.5C** charge. Therefore: use a **protected** cell **rated for 1C charge**,
*or* fit a **≥200 mAh** cell, *or* change the PROG resistor to lower the current.
Never charge unattended.

## Antenna / RF placement (EE review #1)

The nRF52840's 2.4 GHz antenna needs a **no-copper keep-out** on every layer under
the RF path. The nice!nano is therefore mounted **vertically at the top of the
grip with its antenna end overhanging the top board edge** (nothing under it), the
**LiPo kept far away** (≥ board length — metal detunes it), and the module's USB-C
accessed via a shell notch below it. Even so, the antenna is flanked by the phone
and the user's hand — expect reduced range vs. an open board; keep the bridge
cable and its shield away from the antenna end.

## Safety (see also assembly.md)

Use a **protected** LiPo of appropriate capacity. Rely on the nice!nano's onboard
charging circuit. **Never charge unattended.** Keep the cell in its keep-out, away
from soldering heat and switch travel.

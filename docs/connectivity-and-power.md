# Connectivity & power — rev-A (v0.27)

One controller, one battery, one USB-C, **one cable between the grips**. The
**right grip** carries the E73 (nRF52840) module, the charger and the USB-C; the
**left grip** is a passive matrix that also hosts the cell, its connector (J4)
and its fuse (F1). A single fixed internal **20-way FFC ribbon** carries the
whole matrix *and* the battery across the spine. This supersedes all earlier
versions of this file (nice!nano/BQ24075, JST-GH harness, telescoping-cable era).

```
   LEFT grip (passive matrix)                 RIGHT grip (MCU)
   42 domes + diodes     ── 20-way FFC ──     E73 nRF52840 + charger + USB-C  ⇄ host (BLE HID)
   403040 cell + J4 + F1   straight type-A    scans all 78 keys + I2C hall nub (pointer)
                           14 matrix + VBAT
```

## The power tree

```
403040 LiPo cell, LEFT grip (protected pouch — PCM on the cell, see Safety)
   └── J4  JST-PH-2, LEFT board @ deck (60.0, 5.5)   # ~8 mm of pigtail, same grip
          └── F1  PPTC 0.75 A hold / 1.5 A trip      # in series with the cell "+"
                 └── J2 ── 20-way FFC ribbon ── J2   # 2× VBAT_CELL + 2× GND
                        └── VBAT_CELL node, RIGHT board
                              ├── MCP73831 charger (U2) ← USBLC6-2 ← USB-C VBUS
                              │                            # charger on the CELL side
                              └── MSK12C02 slide switch (SW90)
                                     └── VBAT rail ── E73 VDDH (pad 23)   # REG0 mode
                                            └── internal REG0 → 3V3 (pad 19, out only)
```

- **Charger on the cell side of the switch** — the battery charges while the
  device is switched **off**. The switch only gates the load.
- **One cable, not two.** VBAT_CELL crosses the bridge on **two** of the 20
  conductors, with two GND returns at the far end of the ribbon and two unwired
  **NC guard** positions between the battery group and the matrix. Conductor
  order, index 0 = highest deck y: `GND, GND, ROW0–8, COL5–9, NC, VBAT_CELL,
  VBAT_CELL, NC`. The **14 matrix signals are unchanged**, so firmware is
  completely unaffected (ROW0–8 / COL0–9 identical).
- **F1 (PPTC) is part of the power tree, not a nicety** — Bourns
  **MF-MSMF075-2** (1812, LCSC **C84140**), 0.75 A hold / 1.5 A trip, 13.2 V,
  Imax 100 A, ≤0.45 Ω initial. It sits on the **cell** side of the ribbon
  (between J4 and J2) or it protects nothing at all. See Safety.
- **J4 is what de-energizes the ribbon.** SW90 lives on the *right* board and
  gates only the load, so VBAT_CELL — and therefore the ribbon — is live
  whenever the cell is attached. Unplug J4 before touching the bridge; at
  assembly the ribbon goes in **before** J4.
- **LiPo-direct (high-voltage) mode:** raw cell 3.0–4.2 V into **VDDH** only.
  **VDD (pad 19) is the internal REG0 3.3 V output** — decoupled (C1), never
  driven. The Adafruit bootloader sets `UICR.REGOUT0 = 3.3 V` at first flash. The
  E73 module has **no DCDC inductors**, so the regulator runs in LDO mode —
  correct, and why `CONFIG_BOARD_ENABLE_DCDC` is absent from the firmware.
- **Charging:** USB-C VBUS → **USBLC6-2SC6 inline** → MCP73831 (**-2ACI**, 4.2 V).
  PROG = 5.1 kΩ (R24) → **~196 mA**, ~0.43 C of the 403040 cell (~450–500 mAh) —
  comfortably safe. 4.7 µF 0805 25 V stability caps sit **at the chip** on
  both supply pins (C3) and the cell node (C5), per datasheet; C4 is VBAT bulk.
- **The charge loop is now a loop through the ribbon**, so VBAT_CELL/VBAT route
  at **0.4 mm** on a real power netclass rather than signal width. (0.5 mm was
  tried first; Freerouting could not close VBAT_CELL through the inner corridor
  with it, and 0.4 costs only ~34 mΩ more — the PPTC dominates the loop.) What the loop
  resistance (F1's ≤0.45 Ω plus the ribbon) actually costs is **charge time**,
  not capacity: CC→CV handover happens at a lower cell voltage, so the taper is
  longer. The undercharge at termination is ITERM × Rloop — **~10–16 mV**,
  negligible against the MCP73831's own ±32 mV VREG tolerance.
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

> **v0.27:** the **separate battery cable is deleted**. The bridge went
> **16-way → 20-way** (JUSHUO **AFA07-S20FCC-00**, LCSC **C262352** — 1.0 mm
> pitch, bottom contact, slide lock, side entry, 2.5 mm height, still JLC
> *Extended*, so no assembly-class change). Of the **four** new conductors, two
> carry **VBAT_CELL** and two are unwired **NC guards**; the 2 × GND were already
> there on the 16-way. The cell's leads no longer cross the spine at all:
> **J3 is deleted from the right board** and a new **J4** (JST-PH-2,
> S2B-PH-SM4-TB, **C295747**) sits in the **left** grip's chin at deck
> (60.0, 5.5), mouth facing +y, ~8 mm from the pouch it serves — instead of a
> ~265 mm bare pigtail running the width of the device. **F1** (PPTC) goes at
> deck (50.0, 5.5) in series with the cell positive between J4 and J2. The
> clamp's lane plan drops from `spring | FFC | power | spring` to
> `spring | FFC | spring` (FLEX_Y 26.5 → **28.5**, FLEX_W 17.0 → **21.0**,
> POWER_* deleted), freeing y 40.0–82.5 inside the clamp cavity; J2 moved from
> deck y 24.5 to **28.5** on both boards to match, and deck.py's inner-mid M3
> mount hole moved from 40.74 to a frozen **46.0** — its Ø8 boss disc was the
> only thing capping the connector's pin count. Both boards re-routed to **DRC
> 0 violations / 0 unconnected** (right: 75 nets, 114 footprints, 30 GND escape
> vias; left: 60 nets). The jumper you buy is now **20-way, 1.0 mm pitch,
> TYPE-A** (contacts on the **same side at both ends**), **≥240 mm** — never a
> 16-way, see Safety. The 16-way footprint file stays in the library because the
> committed rev-A boards reference it.

> **v0.27 also built the FFC duct that had never existed.** The ZIF slot sits at
> z ≈ 6.95 and the ribbon lane at z = 0.2; with the slot facing the spine there was
> only **1.20 mm** of x in which to lose **6.74 mm** of z, so there was no route —
> in any version, for either cable. J2 now faces **inboard**, the ribbon folds in
> the grip's back cavity and leaves through a low stepped duct (z −0.8 .. 2.6 grip side,
> .. 1.95 through the shroud) that passes
> under the phone-retention structure instead of cutting through it.
> `flex_route_report()` sweeps the ribbon's full 21 mm section along that path and
> gates on it; `deck3d.py --check-lanes` is the fast check.

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

Since v0.27 the ribbon carries the raw cell, so two of these are hard
requirements rather than good practice. They cover **different** current bands;
neither alone is sufficient.

- **The cell must be a protected 1S pouch** — integrated PCM, overcurrent
  **2.0–2.5 A / 8–16 ms**, overcharge **4.275 V**, overdischarge **2.75 V**.
  Requirement, not advice. **Never charge unattended.**
- **F1 (PPTC, MF-MSMF075-2 / C84140) must be fitted**, on the **cell** side of
  the ribbon. A 1.0 mm-pitch FFC conductor is 0.70 × 0.035 mm = **0.0245 mm²**:
  it reaches its 105 °C insulation limit at about **2.8 A·√s** and melts its own
  PET in ~0.2 s at a real short, while the pouch's PCM does not trip until
  2.0–2.5 A. The band in between — roughly **0.43–2.0 A**, the signature of a
  partially abraded conductor in a mechanism that flexes on every phone
  insertion — is covered by **nothing else**.
- **Never buy or fit a 16-way ribbon.** A 16-way is **17.0 mm** wide and drops
  straight into the 20-way housing's **21.0 mm** slot with **4.0 mm** of
  independent slop at each end — up to a **4-position** shift. The conductor
  order is chosen so that even a 4-position shift lands VBAT on a **column**
  (one dead MCU pin) rather than on **GND** (a dead cell short), but that is a
  backstop, not a licence. Buy **20-way, 1.0 mm pitch, TYPE-A only** (contacts
  on the same side at both ends), **≥240 mm**; the silk beside J2 reads
  `J2 FFC20 1.0mm TYPE-A <- pin1` for exactly this reason.
- **Polarity:** the JST-PH connector is polarized, but vendors wire PH pigtails
  **both ways** — meter the pigtail against the **"+"/"−" silk beside J4, on the
  LEFT board** (pin 1 = "+"), before first plug-in.
- ~196 mA charge current is ~0.43 C for the 403040 cell (~450–500 mAh); no PROG
  change needed.

# Design review record — rev-A (v0.15, 2026-07-11)

The rev-A audit: an **8-dimension adversarial review** (snap-dome contact
mechanics, module/RF placement, bridge, battery/power, USB, pin budget, firmware
buildability, mechanical/DFM) of the v0.14 design against datasheets, real part
geometry and the fab houses' constraints. It produced **120 findings, 14 of them
blockers**. Every blocker is fixed in the boards, firmware and CAD now in the
repo; both boards subsequently routed to **0 DRC violations / 0 unconnected**. The
CI workflow is a **self-contained ZMK v0.3.0 build** — **require one green Actions
run producing `thumbdeck-zmk.uf2` before ordering boards** (no green run exists
yet). Earlier review records (the v0.4 nice!nano-era EE pass,
the v0.14 fab-readiness audit) are superseded by this file plus
[evaluation.md](evaluation.md).

## What changed and why

1. **Snap-dome footprint → production `snaptron_7mm_contact`.** Centre pad
   2.86 mm + a continuous leg ring (4.4–6.9 mm dia, drawn as 13 overlapping
   circles spanning 292°) with a **67.5° escape gap** through which the column
   trace reaches the centre pad. Worst-case dome rotation keeps 3 of 4 legs on
   the ring. Full mask apertures; F.Cu pour keepout r 3.8; all-layer via keepout
   r 3.6. No vent hole — venting comes from the Snaptron retention-tape channels.
   *Why:* the old "simple" 2-pad footprint gave **dead keys at 45° dome rotation**.
2. **E73 rotated antenna-DOWN at the bottom board edge.** Its all-layer keep-out
   covers the antenna area and crosses the board edge (~3 mm on-board strip + the
   off-board extension); the on-board region is verified copper-free on all 4
   layers (plus a 0.6 mm shell-wall relief). *Was:* antenna
   pointing mid-board at the USB shell over ground pour — detuned.
3. **Bridge → 16-pin 1.0 mm FFC ZIF** (JUSHUO AFA07-S16FCC-00, C13744,
   bottom-contact, 2.5 mm tall) on each grip's inner edge + a **16-way 1.0 mm
   type-A (same-side contacts) FFC jumper, length ≥160 mm** — 200 mm is the common
   stock length (e.g. "FFC-1.0-16P-200mm" type A; the J2 contact rows are
   151.2 mm apart + ~4 mm ZIF insertion per end, so a 150 mm ribbon cannot mate).
   Left-grip connector nets are assigned **by
   ribbon geometry**, so a straight jumper is correct by construction (verified:
   net-at-same-height matches 1:1). *Was:* a 2×08 THT pin header that (a)
   physically could not fit the shell — 8.5 mm part vs a 5.7 mm cavity, (b)
   overhung the right board edge, and (c) landed under dome SW25 on the left.
4. **Battery connector → JST-PH 2.0 mm side-entry SMT** (S2B-PH-SM4-TB, C295747) —
   polarized, the hobby-LiPo standard. *Was:* an unpolarized 2.54 mm pin header.
   Build-guide note: vendors wire PH pigtails **both ways** — meter against the
   "+"/"−" silk beside J3 (pin 1 = "+", nearer the bottom board edge) before
   first plug-in.
5. **NEW power switch:** MSK12C02 slide (C431540, SW90) between cell+ and the
   VBAT rail; the charger stays on the **cell side**, so it charges while
   switched off. Knob through a slot in the bottom shell wall.
6. **NEW reset button:** TS-1187A tact (C318884, SW91, top-actuated), pressed
   through a 1.6 mm pinhole in the shell floor — UF2 double-tap entry without
   opening the shell.
7. **NEW charge LED:** 0603 red (C2286, D80) + 1 kΩ (R25): VBUS → R25 → LED →
   MCP73831 STAT; lights while charging, viewed through a 1.5 mm floor hole.
   *Watch:* LED polarity is the classic JLC 180° error — check the DFM preview.
8. **Charger caps fixed:** 4.7 µF **0805 25 V** (C1779) at **both** MCP73831
   supply (C3) and VBAT_CELL (C5), per datasheet. *Was:* a single cap 48 mm away,
   and a 0402 4µ7 that derates to ~1 µF at 5 V bias. PROG 5.1 kΩ → ~196 mA
   (~0.5 C of a 400 mAh cell).
9. **Battery divider hardened:** 1 MΩ/1 MΩ (R22/R23) + **new 100 nF SAADC filter
   cap (C6)** on VBAT_SENSE (P0.02/AIN0).
10. **USB ESD moved INLINE:** the USBLC6-2SC6 now sits between the USB-C and the
    module (*was:* a stub on the wrong side). The USB data pair uses interleaved
    same-net pads (B6 A7 A6 B7) joined by **deterministic generated copper** (D−
    bar + D+ In2 hop) plus fixed In2 runs to the module — autorouters cannot
    solve this pattern, so it's drawn, not routed.
11. **COL9 moved off P0.00/XL1** (pad 11) to **pad 18 (P0.04/AIN2)** — the XTAL
    pins stay free. Spare I²C broken out: pads 15/4/8 (P0.05 SDA / P0.28 SCL /
    P0.29 INT) to labelled test pads **TP6–8** for a rev-B trackpad/expansion.
    SWD on **TP1–5** (SWDIO/SWDCLK/RESET/3V3/GND), all silk-labelled.
12. **Trackpad DROPPED from v1** (was IQS7211E): the community ZMK Azoteq driver
    is single-maintainer and needs per-build ATI tuning; pointer duty = ZMK mouse
    keys on the FN layer + the D-pad. The I²C breakout keeps a rev-B trackpad
    possible.
13. **Matrix hardening right-sized:** the 9× 4.7 kΩ row pull-downs (R1–R9) stay;
    column series resistors + dome-field TVS are **dropped from the BOM** (they
    were never on any real board — artifacts of the telescoping-cable era). Noted
    as a rev-B option if field ESD issues appear.
14. **Routability engineered in:** every small-part GND pad gets a generated
    **escape via** to the In1 plane before routing (26 on the right board);
    combined with the obstacle-aware GND stitcher, this is what makes the
    headless route loop converge to 0/0 (see
    [routing-status.md](routing-status.md)).

Board-envelope consequence of 3–7: each grip grew **74.5 × 109.5 → 76.5 ×
114.5 mm** (inner margin 6 → 8 mm for the FFC bridge; bottom strip 14 → 19 mm for
the module-at-edge + passive lane), and the back-cavity height 5.7 → 6.3 mm for
the mated JST-PH.

## Firmware findings (5 build-breakers, all fixed)

| # | Breaker | Fix |
|---|---|---|
| 1 | ZMK `main` dropped HWMv1 boards — config didn't build | `west.yml` + CI pinned to **ZMK v0.3.0** |
| 2 | Missing `#include <dt-bindings/zmk/pointing.h>` | added to the keymap |
| 3 | `CONFIG_BOARD_ENABLE_DCDC` — symbol undefined for this board, and the module has **no DCDC inductors** | removed; LDO mode is correct |
| 4 | **No 32.768 kHz crystal on the E73** — BLE never started | `CONFIG_CLOCK_CONTROL_NRF_K32SRC_RC=y` + 500 PPM |
| 5 | Flash partitions didn't match the bootloader | now exactly the nice!nano-v2/Adafruit layout: sd 0x0/0x26000, code 0x26000/0xc6000, storage 0xec000/0x8000, boot 0xf4000 |

The board definition moved to `firmware/zmk-config/config/boards/arm/thumbdeck`
(ZMK discovers it via `ZMK_CONFIG`). CI (`.github/workflows/build.yml`) is a
**self-contained build** — `west init -l config` inside `firmware/zmk-config`,
`west build -b thumbdeck`, uploads `thumbdeck-zmk.uf2` — because ZMK's reusable
workflow cannot handle a nested config dir. **Require one green Actions run
producing `thumbdeck-zmk.uf2` before ordering boards.** The FN layer gained
MINUS/EQUAL, HOME/END, PSCRN, BT_CLR/BT_SEL 0–3, bootloader/sys_reset.

## Residual risks (rev-A is unbuilt)

| # | Risk | Standing mitigation |
|---|---|---|
| 1 | RF range with phone + hands flanking the antenna | edge-mounted antenna + keepout + shell relief; measure on the first article |
| 2 | Dome feel / keymat hinge fatigue | coupon-test before full mats; retention tape mandatory |
| 3 | JLC part rotation (LED, SOT-23, E73) | DFM preview checklist in fabrication-sourcing.md |
| 4 | Battery pigtail polarity | polarized JST-PH + meter-against-silk step in assembly.md |
| 5 | E73 stock is volatile (observed ~1000 → ~20 units within days; Extended, X-ray) | check jlcpcb.com/parts for C356849 and reserve/backorder before anything else; Holyiot 18010 backup needs a footprint change (rev-B) |

**Gate that remains:** a **first-article run of 5** with the bring-up checkpoints
in [assembly.md](assembly.md) before any larger spend.

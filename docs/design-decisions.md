# Design decisions

Decision log, newest first. Older entries are **history** — they record why calls
were made at the time and may name parts since replaced (Raytac → E73, Cirque /
IQS7211E trackpad → dropped, JST-GH → FFC ZIF, nice!nano → bare E73 board). The
current design is rev-A / v0.15 (first entry).

## v0.15 / rev-A — the production audit pass (2026-07-11)

An 8-dimension adversarial audit (120 findings, 14 blockers) followed by fixes,
a fully autonomous route (both boards **DRC-clean, 0/0**), fab export, firmware
repair and a mechanical re-verify. Full record in
[design-review.md](design-review.md); status in [evaluation.md](evaluation.md).

- **Snap-dome footprint → production `snaptron_7mm_contact`** (centre pad +
  continuous leg ring with a 67.5° routing escape gap, pour/via keepouts, tape-
  channel venting). The simple 2-pad proxy would have given dead keys at 45° dome
  rotation.
- **E73 antenna-down at the bottom board edge**, keep-out crossing the edge +
  0.6 mm shell relief (was aimed mid-board at the USB shell — detuned).
- **Bridge → 2× 16-pin 1.0 mm FFC ZIF (AFA07-S16FCC-00, C13744) + a 16-way
  1.0 mm type-A (same-side contacts) jumper, length ≥160 mm** (200 mm is the
  common stock length, e.g. "FFC-1.0-16P-200mm" type A — the J2 contact rows are
  151.2 mm apart + ~4 mm ZIF insertion per end, so 150 mm cannot mate); left-grip
  nets assigned by ribbon geometry (straight
  jumper correct by construction). Replaces the 2×08 THT header that couldn't fit
  the shell cavity (8.5 vs 5.7 mm), overhung the right edge and landed under a
  left-grip dome. **No hand-soldered parts remain** — the USB-C shell's plated
  stakes and the FFC/slide-switch locating pegs are the only through-board
  features, all placed in the same single-pass JLC assembly → 100 % turnkey.
- **Battery: JST-PH SMT (C295747)**, polarized (was an unpolarized 2.54 header);
  **NEW** MSK12C02 power switch (charger on the cell side — charges while off),
  TS-1187A reset tact behind a floor pinhole, charge LED behind a floor light
  hole.
- **Charger corrected per datasheet:** 4.7 µF 0805 25 V at both supply and cell
  nodes, at the chip; PROG 5.1 k → ~196 mA. 100 nF SAADC filter added to the
  battery divider.
- **USB ESD inline; deterministic USB copper** for the interleaved data pads
  (autorouters can't solve it). **COL9 off P0.00/XL1 → P0.04**; spare I²C to
  TP6–8; SWD on TP1–5.
- **Trackpad dropped from v1** (single-maintainer ZMK Azoteq driver + ATI tuning
  burden); D-pad + FN-layer mouse keys cover pointer duty; TP6–8 keep rev-B open.
  Column series R + dome-field TVS dropped from the BOM (telescoping-cable-era
  artifacts; rev-B option).
- **Boards 76.5 × 114.5 mm** (inner margin 6→8 for the FFC, bottom strip 14→19
  for module-at-edge + passive lane), 4-layer with solid In1 GND; **GND escape
  vias + obstacle-aware stitcher** make the headless route loop converge to 0/0.
- **Fabrication: two separate JLC orders** (panelizing two designs costs more);
  right = Standard (E73 X-ray), left = Economic-eligible.
- **Firmware:** ZMK **pinned to v0.3.0** (main dropped HWMv1 boards); LF clock
  from internal RC (**the E73 has no 32 kHz crystal** — without this BLE never
  starts); DCDC config removed (module has no inductors; LDO correct); flash
  partitions = exact Adafruit/nice!nano-v2 bootloader layout; board moved to
  `config/boards/arm/thumbdeck`; FN layer gained MINUS/EQUAL, HOME/END, PSCRN,
  BT controls, bootloader/sys_reset.
- **Mechanical:** back cavity 5.7→6.3 mm (mated JST-PH + 0.24 margin); 3 support
  posts per grip under the key field; top-shell rim clamps the keymat web
  (0.1 mm preload); phone pocket in a raised spine plateau with a Ø57×1.8
  MagSafe-ring recess; USB-C/switch/pinhole/LED openings cut from real part
  placement. `deck3d.py --check` = 0 collisions.

## v0.13 — printable spacing, 2u space bar, cluster fixes

- **Pitch 8.5/8.8 → 9.5 mm (#5).** At 8.5 mm the inter-key wall was only ~0.5 mm —
  **not printable in PETG-FDM** (needs ≥1.2–1.6 mm = 3–4 perimeters at a 0.4 mm nozzle).
  9.5 mm gives a ~1.5 mm wall, and matches the i8+ pitch. Grips grow to 74.5 × 109.5 mm.
  (To go tighter you'd print the keymat/shell in resin/SLA or use a 0.25 mm nozzle.)
- **Double-wide 2u space bar (#4).** The MENU key is dropped and the bottom row shifts
  over one, so the inner key is a **2u space** on each side (`SPC AGR [ ] \` right,
  `SPC ALT WIN FN CTL` left). The dome stays single under the wide keycap. Keys now
  carry a `w` (width in units); `_key_centers` lays each row out by cumulative units.
- **D-pad no longer overlaps the F-row (#2).** The upper zone is sized to fully clear
  the plus-cluster and the clusters are centred in it (previously an offset pushed
  NAV_D down into the grid).
- **Screw no longer passes through the bridge (#1).** The bottom-inner mount hole moved
  below the vertical JST-GH connector.
- **Every cluster keycap ties into the keymat web (#3).** The one-piece keymat now
  draws living-hinge strips from each D-pad / mouse / page key to its nearest grid key
  and nearest neighbour, so nothing floats.
- Verified programmatically: no keycap overlaps, nothing off-board, no screw inside any
  keep-out, both grips.

## v0.12 — outline-clamped placement, layer-correct traces, PCB antenna

- **Nothing hangs off the board.** All right-grip electronics (module, charger,
  USB-C, antenna) and the two outer mount holes are now **clamped inside the actual
  rounded/bowed outline** via `_right_edge_x()`, instead of being referenced to
  `outer_base` (which sits outside the corner). Electronics moved into the **bottom
  zone**; the trackpad has the upper zone to itself (clean capacitance).
- **Layer-correct matrix (Rii i8+ topology).** Front copper = **vertical columns**
  (over the keys) + inner-margin **row feeders**; back copper = **horizontal rows** +
  diodes + chips. The two layers connect **only through vias** (drawn at every key and
  at each row's inner end), so nothing shorts — the earlier diagonal "airwire" fan
  that crossed the row buses is gone. Power traces are short and local to the bottom
  cluster.
- **PCB meander antenna** (fat squiggle on the front, with a **ground cut-out** on the
  back) drawn in the outer-bottom corner, far from the centre magnets. **OPEN
  DECISION:** a board antenna means going **chip-down** (a module carries its own
  antenna) — chip-down is cheaper and gives the free squiggle, but re-adds RF
  match/tuning + crystals + DC-DC + bootloader, and (only if ever *sold*) FCC/IC/RED
  radiated cert. For a personal, non-marketed build the cert isn't required, so the
  real cost is RF tuning + assembly complexity. Keep the certified E73 module (its own
  antenna) unless you want to take that on.

## v0.11 — trackpad-on-PCB, battery-behind-ring, straight bridge, cleanup

- **Trackpad → PCB-integrated capacitive pad** (~34×26 mm copper on the front, driven
  by an **Azoteq IQS7211E** controller on the back), replacing the 43×40 mm TPS43
  module. It now **fits the grip** (no overhang) *and* is **turnkey-friendly** — the
  pad is free copper and the controller reflows with everything else, so the trackpad
  no longer has to be dropped for assembly. Trade: needs the community Azoteq ZMK input
  driver (vs the in-tree Cirque one).
- **Battery stack-up fixed:** the LiPo sits **inside the spine, directly behind the
  MagSafe ring** (sandwiched between back and front shells). The **N52 ring is applied
  to the outside of the front shell** (top of the stack); the phone mates to it.
- **Bridge connectors rotated vertical** at each grip's inner edge so the flex exits
  toward the spine and runs **straight across** to the mirror connector, clearing the
  spine battery above it.
- **Chip-interconnect traces** are now drawn (indicatively) on the PCB layers: module →
  rows / USB-C / charger / ESD / IQS7211E / bridge; passive grip rows → bridge.
- **Repo cleanup:** old 50-key design-loop scripts moved to `hardware/scripts/legacy/`;
  grading artifacts + the superseded front/back render archived to `renders/history/`.

## v0.10 — proportions, spine battery, rectangular trackpad, layer set

- **LiPo → central spine** (behind the phone / MagSafe ring), out of the grips. Short
  wire to the right-grip charger; it does **not** cross the left bridge, so the
  battery-across-flex risk still doesn't apply. This lets the grips shrink from
  **118 → 102 mm** so the ~72 mm (landscape) phone is no longer dwarfed (~15 mm
  overhang/side, matching the i8+).
- **Trackpad → Azoteq TPS43** (43×40 mm **rectangular** I²C module, 40 µA active, sold
  maker-ready). Still optional; sits as a **shoulder-bump** over the upper-right grip
  (its 40 mm height overhangs the top rather than forcing the whole grip taller).
- **Stackable layer renders** (`render_layers.py`): back_shell · pcb_back · pcb_front ·
  keymats · front_shell, all on one 2400×1050 canvas for overlay/animation.

## v0.9 — landscape, turnkey sourcing, and shell-readiness

- **Phone orientation → LANDSCAPE.** The phone's long side spans horizontally
  between the grips (Steam-Deck posture); device is now ~287 mm wide. `deck.product()`
  handles orientation.
- **MCU module → Ebyte E73-2G4M08S1C** (JLC C356849), replacing the Raytac MDBT50Q,
  because the Raytac was out of stock / not reliably JLC-placeable. The E73 is in the
  JLC library, is the community-standard ZMK nRF52840 module, and machine-places.
- **Trackpad dropped from the turnkey build** (kept as an optional, dashed, hand-fit
  I²C header). The host is a phone with its own touchscreen; the Cirque isn't LCSC-
  stocked (hand-assembled anyway), and enabling ZMK pointing forces a HID re-pair on
  every host. This resolves the crowded upper-right zone too.
- **Turnkey assembly = JLCPCB, single-sided (all reflow parts on the BACK), L+R
  panelized.** ~$150–230 for 5 sets vs ~$300–600 at PCBWay. Domes + retention sheet +
  LiPo + shell are hand steps at either house (snap domes can't be reflowed). Full
  costing, LCSC part numbers and open decisions in [fabrication-sourcing.md](fabrication-sourcing.md).
- **Shell-readiness (emulate i8+):** 5× M2 screws per grip clamp the keymat perimeter
  evenly (consistent dome feel), placed in the inner column + top/bottom strips, clear
  of the key field; every key/cluster is ≥6.5 mm from the board edge (shell wall +
  keycap skirt); USB-C on the outer-bottom edge; module + all SMD on the back. This
  preps the board for the next step — the 3D shell + keymat models.

## v0.8 — phone target, MagSafe, module, and a 5-lens EE/PD review

Big shifts from v0.3–0.7: target is a **phone** (MagSafe centre-mount), telescoping
is **deferred** for a **fixed one-piece shell**, switches are **Snaptron 7 mm snap
domes** on a one-piece 3D-printed keymat (adopted from PocketMage), the grid grew to
**6×6/half + clusters** (~81 keys) validated against the Rii i8+ the user thumb-types,
and a trackpad + D-pad + mouse buttons returned. A background workflow ran a
**5-lens review** (digital EE, RF/power EE, product/ergonomics, DFM, firmware). Its
decision record, adopted:

| Topic | Decision | Why (short) |
|---|---|---|
| **MCU** | **Raytac MDBT50Q-1MV2 module**, *not* chip-down bare nRF52840 | Chip-down triggers FCC/IC/RED radiated cert + RF match + crystals/DC-DC + USB bootloader + Zephyr port. Module gives certified radio + ~48 GPIO (need ~23) + UF2. |
| **GPIO** | Budget ~23: 19 matrix + 2 I²C + 1 Cirque DR-IRQ + 1 batt ADC | Confirms the pin-starved nice!nano was the real problem, solved by a full-pinout module — not by chip-down. |
| **Battery** | LiPo + charger + USB-C + MCU **all in the right grip**; ballast the left | Cell across the bridge = chafe-to-short fire + charge IR-drop undercharge + ground coupling into the SAADC/scan. Only logic crosses the bridge. |
| **Power front-end** | Add MCP73831 charger + PROG R, USB-C **2× 5.1 kΩ CC**, USBLC6-2 ESD, ÷2 batt divider, VDDH wiring, SWD pads | A module hides crystals/DC-DC/antenna but **not** the charger, CC resistors, ESD or divider. Their absence = won't charge / over-VDD / unflashable. |
| **Matrix** | Single 9×10, passive left, per-key **SOD-323** `col2row`, NKRO best-effort | Unibody single kscan over a cable (NOT a ZMK split). Diodes de-ghost modifiers even though BLE boot is 6KRO. Standardise SOD-323 (drop SOD-123). |
| **Bridge** | Static internal harness, **JST-GH ≥15 pos**, signals only, ~22–24 conductors w/ ground interleave | Fixed shell ⇒ assembled-once harness (no flex-fatigue). One GND can't shield 9 sense lines; power stays with the MCU. |
| **Trackpad** | **Cirque TM023023 (23 mm)**, I²C 0x2A, **DR-IRQ wake** (not polled), flat ≤2 mm non-conductive overlay | 30 mm isn't a catalog size. Polling collapses runtime to ~28 h; conductive/variable FDM overlay kills sensing. |
| **PCB finish** | **ENIG** (hard gold on dome pads for production), not HASL | Snap domes shorting bare pads need gold; HASL oxidises → rising contact resistance in weeks. |
| **Dome retention** | Add taped-polyimide dome array / laser-cut spacer | Keymat alone doesn't laterally retain a dome on its single ~1.4 mm arc; ~0.5 mm walk = dead key. |
| **Keymat** | TPU 95A / tough resin; fatigue-test a hinge coupon >10 k cycles | Non-TPU living hinges at ~0.5 mm webs crack early; boss preload must be shimmed. |
| **MagSafe** | Alignment only + **mechanical edge-capture** on 2+ edges | Magnets alone shed peel/torque on a waved handheld. |

### Open questions (need a human call — see README §Open questions)

- **Pitch/feel:** keep 8.5 mm flat ortho, or go ≥9.5 mm canted/fanned arc (i8+-like) via a switch daughter-PCB / standoff-canted mat? The review says the flat rigid plane can't both type well and feel like a controller.
- **Phone-fit:** fixed shell = ~145–160 mm band (≈ one phone family); accept, or bring back telescoping for multi-phone?
- **NKRO vs simplicity:** if 6KRO is fine, dropping diodes enables a TCA8418 local scanner + a 4-wire bridge.
- **Shoulder/bumper buttons** for index fingers? Changes the matrix + conductor count.
- **Cell size:** sleep-managed runtime is weeks → a 400–500 mAh cell may pack better than 700 mAh.

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
history and `renders/history/iter_03.png`.

## Open `TODO(user)` — historical (v0.3 era), all resolved by rev-A

Kept for the record only; every item below was closed by the rev-A design (see
the v0.15 entry at the top): production dome footprint, fully routed/DRC-clean
boards, FFC ZIF bridge with a defined pinout, spine LiPo, printed keymats, 3D
shells, and a layout validated against the i8+.

- Datasheet-verified switch footprint (before gerbers).
- Copper routing in KiCad (before gerbers), incl. the bridge connector pinout.
- Bridge cable + connector choice (10-pin FPC/JST, or MCP23017 → 4-wire).
- LiPo capacity vs. shell space (~100–150 mAh assumed).
- Keycap/top solution; touchpad (would use the nice!nano's spare GPIO / I²C).
- 3D clamp + bridge shell geometry (out of scope here).
- Confirm key count/reach against a real i8+ and your thumb span.

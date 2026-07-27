# Design decisions

Decision log, newest first. Older entries are **history** — they record why calls
were made at the time and may name parts since replaced (Raytac → E73, Cirque /
IQS7211E trackpad → dropped, JST-GH → FFC ZIF, nice!nano → bare E73 board). The
current design is rev-A / v0.24 (first entry).

## v0.24 — expanding spring-clamp back (2026-07-26, branch feature/expanding-clamp)

User request: make the back **expand and collapse like a Razer Kishi 2 / Backbone** so
it clasps different-size phones with a spring — a drastic rework of the rigid center.
Chosen after four decisions: **printed dual-rail slide** (no metal rods), **2 extension
springs**, **preserve near-flush at the nominal phone**, phone long-edge range
**130–170 mm**.

- **The rigid center is gone.** Deleted the bolted `center_panel`, the sunken
  flush-screen well, the MagSafe ring, the x=0 back seam + tabs/shiplap, the panel
  screws, and the central spine slab. The two grips are now separate bodies. This was
  a deliberate reversal of the v0.8 "fixed shell vs telescoping" call and the v0.18
  flush-well — logged there as trade-offs, now revisited because the user wants
  multi-phone fit over a single-phone flush mount.
- **THREE-STAGE GEARED brace (feedback: match the Kishi's geared telescope; make it
  sturdy for print/mould).** `deck.product()` is parametric on `clamp_pos`; the right
  grip is the frame reference and the left is the moving jaw. The brace is a 3-section
  slide: a **centre stage** (`bridge`) telescoping inside a **channel on each grip**,
  with a **pinion** (`pinion`) meshing a **fixed rack** (right grip) and a **moving
  rack** (left grip). This enforces a **2:1** — `_center_x()` places the centre at the
  midpoint = the phone centreline at every span. *Why geared, not free-sliding:* a
  telescope's stiffness is its overlap; free stages hand off (one runs to its stop,
  then the other), leaving the worst-case one-joint-does-all at intermediate spans. The
  2:1 keeps **both joints half-engaged everywhere**, maximising rigidity, killing
  racking, halving per-joint travel/wear, and keeping the pad behind the phone. Three
  stages (not two) also buy the collapsed→extended range without a bigger closed unit.
  It evolved from a 2-stage nested shroud (this same iteration) once the geared
  reference was specified.
- **Sturdy section (per the brief).** Every stage is a solid bar with a **flat
  phone-side top + a rounded-bevel back** (`_rbar`) — a deep, stress-concentration-free
  section for bending/torsion, comfortable in hand, and consonant with the v0.23 crown.
  The clamp **springs**, the **FFC**, and the **power cable** run enclosed in the nested
  stages' cavity on y-lanes clear of the gear/racks.
- **The missing power cable, added + enclosed.** The battery leads (left-grip 403040 →
  J3 on the right board) were never modeled; they're now a `power_body` routed enclosed
  through the shrouds in its own y/z lane beside the FFC, each with a rolling service
  loop. Collision shows both cables as intended contacts with the shrouds (threaded
  through, inside the cavity), not clashes.
- **Packing conflicts solved during collision bring-up** (validated at min/nominal/max):
  the left grip's mount screws had to be shifted with the moving jaw (they were pinned
  at nominal); the recess floor was shortened to x −60 so it clears the **collapsed
  grip's battery** (the phone is edge-clamped, so it only needs central + cradle-edge
  support, not full-back support); the cradle walls were pulled 0.9 mm shy of J2's
  courtyard; and the bolt column was moved off J2's y-band. `--check` asserts the
  shrouds stay overlapped (≥12 mm) so the enclosure can't open at full extension.
- **Retention & near-flush trade-offs (accepted).** X = spring clamp on the short
  edges via TPU-padded cradles; Z = screen-edge lips + the recess; Y = bridge walls.
  Near-flush holds exactly only at the nominal cased thickness (9.4 mm) — thinner
  phones sit slightly low, thicker slightly proud — and the smallest phones are
  right-justified (right edge pinned) rather than centred.
- **Electrical / battery.** Both cross-grip cables — the 16-way FFC (matrix) and the
  battery power leads — now need a **rolling service loop** (fold inside the shroud;
  FFC grows to ≈240 mm) because the span is variable. The 403040 battery stays in the
  left grip and rides the moving jaw. No PCB changes — this is shell-only; the boards
  remain v0.22 rev-A.

## v0.23 — faceted ergonomic back crown (2026-07-26, branch feature/back-ergonomics)

User feedback: "the design is great but flat — use more sophisticated geometry for
better ergonomics, especially the back contours; take inspiration from the Rii 8+
back and 90s electronics." The back was a dead-flat extruded tray (outer face a
single z=0 plane), so the device pressed a flat slab into the palm.

- **A faceted palm crown, added BELOW z=0.** Two cut-corner **grip plateaus** rise
  **5.5 mm** below the back plane (apex biased to the outer edge where the thenar
  heel and curled fingers bear), each scored with three **shadow-line grip
  grooves**; a lower faceted **spine panel** (−2.2 mm) laps into both so the whole
  back reads as one milled 90s-industrial block (Sega/Nokia cut-block facets, crisp
  panel lines), tapering to a thin land at the perimeter. Generated with CadQuery
  **ruled lofts** of cut-corner octagon sections — planar-facet B-rep, exact and
  STEP-clean, the right tool for the *faceted* (not smooth-organic) look the user
  chose. scipy thin-plate-RBF + scikit-image marching-cubes were installed for a
  future SDF/organic pass but are unused here by design.
- **Why additive-below-z=0 is the whole trick.** The crown never enters the
  electronics cavity (everything at z ≥ FLOOR), so the validated PCB fit, the
  221-body collision result (still **0 clashes**), the joinery and the bed-fit are
  unchanged by construction — the change is provably local to the cosmetic back.
  The reset pinhole + charge-LED holes are the only cavity features it touches, and
  they are just lengthened to pierce the crown to daylight.
- **Print orientation flips floor-down → CAVITY-DOWN** (the one real cost). A
  convex crown can't print floor-down (a convex-down face droops near its apex), so
  the halves now print cavity-opening-down: the crown prints **apex-up as a
  strictly-narrowing faceted peak** — self-supporting at any facet angle, clean
  cosmetic face. The internal PCB bosses/posts become the only downward faces and
  take **tree supports inside the cavity**, where the scars are hidden (the user
  explicitly chose "cavity-down with supports so the support scars are internal"
  over a bolt-on cover or an outer-face-down print with visible palm-side scars).
- **Thickness.** Device stays 14.7 mm at the flush front plane and ~15.7 mm at the
  thin edges; the grips swell to ~20 mm back-to-face (~24.8 mm incl. keycaps) —
  the Rii-8+ hand-filling target. The PCB is unchanged from v0.22 rev-A (the crown
  is shell-only; boards were not re-fabbed, so their silkscreen still reads v0.22).

## v0.22 — true-mirror page keys + genuine-TrackPoint-cap mount (2026-07-24, branch feature/right-joystick)

Two user-feedback items on the v0.21 print/renders.

- **PgUp/PgDn move to the TRUE mouse-button mirror x = 57.25** (the F10|DEL
  gap, mirroring the left pair's ESC|F1 gap; y unchanged at cy_lo ± 5.5). The
  user caught them sitting "above F9" (x 45.7). v0.21 had dodged 57.25 with
  the note "the true mirror is ON the E73 body" — which conflated the two
  board FACES: domes are front-side copper, the module is a back-side part,
  and they coexist at the same x/y. What actually needed care: (1) BOTH
  feature diodes — PGUP's default spot (deck 57.25, 87.5) is under the module
  belly and PGDN's (57.25, 76.5) is on the TP1-5 SWD row (y 75.7), so they
  drop to deck (52.5, 73.2) and (57.25, 73.2), just under the TP row; (2)
  SW91 moved (53.5, 71.5) → (46.0, 80.5) — the vacated old-PGUP zone; its
  first two candidates hit TP6/TP7 and the R-row (the reset's 7.6×5.7
  courtyard fits no gap in the crowded y 66–77 band); (3) the
  module's south-castellation escape vias must clear the PGUP dome's r3.6
  all-layer via keep-out — the autorouter re-fans them (tracks stay legal
  through the keep-out; only vias are banned). The dome courtyard clears the
  antenna keep-out band (module-top 5.5 mm) by ~4 mm.
- **The nub mount becomes GENUINE-TrackPoint-cap compatible.** v0.21's Ø5
  round spigot + smooth-top printed dish cap (TPU, but no dot texture — a
  slick surface that wears with no replacement path but a reprint); the user
  asked for the classic cap look ("people who love the nub
  will respond to it visually"). The spring's post is now the **standard
  classic TrackPoint square platform: 4.4 mm sq × 2.5** (genuine classic
  full-size caps — soft dome / soft rim / classic dome, the ones sold in
  10-packs everywhere — have a ~4.5 mm square socket ~2.5 deep; dimension
  cross-checked against the navcaps project's cap-mount sources, which print
  against genuine caps: mount side 4.5, height 2.5, classic cap adds ~5 mm
  height, and 6 mm-tall variants "tend to come off" as thumbsticks). The
  printed cap is now a **classic soft-dome replica in ThinkPad-red TPU**:
  mushroom profile (Ø7.8 flared skirt, Ø6.8 waist, Ø7.8 dotted dome, 5.25
  tall), the same 4.6 sq × 2.6 socket (corners r0.6, waist Ø6.8 — the r0.6 corner
  reaches r3.00, so a Ø6.2 waist left a 0.10 mm unprintable corner wall,
  caught in STL review; Ø6.8 leaves 0.40 mm ≈ one extrusion width), so
  printed and genuine caps interchange on the same post.
  Hub top drops 16.4 → **14.0** (0.7 below the face): the cap skirt nestles
  INTO the Ø10 aperture exactly like a TrackPoint between keycaps; dome top
  z 18.9 (+0.35 dot grid) ≈ 4.2 mm proud of the face. First tilt-stop is now the rubber skirt
  against the aperture wall (1.2 mm) instead of plastic-on-plastic — gentler
  on the flexure (peak arm strain drops below ~3.5%). Sensor gap, magnet,
  arms, legs and clamp are untouched; the GLB paints the cap
  `trackpoint_red`.

## v0.21 — right-grip pointing nub: Bean-style TMAG5273 hall sensor (2026-07-23, branch feature/right-joystick)

The right top zone becomes a mirror of the left cluster, with a real pointing
device where the D-pad mirror lands. Final architecture: a **ThinkPad-style
rate-control nub** built the way the
[Ploopy Bean pointing stick](https://github.com/ploopyco/bean-pointing-stick/)
does it (hardware CERN-OHL-S v2 — credit where due; our sensor placement,
flexure, and driver are original implementations of the same architecture):
a **TI TMAG5273A1 I²C 3-axis hall sensor** (SOT-23-6, LCSC **C3716049**,
~$0.60, basic SMT — machine-placed like everything else) under the board, a
**Ø4×2 mm N52 disc magnet** press-fit into a **3D-printed flexure spring**
above the lid, and a printed friction cap. Deflecting the nub tilts/shifts the
magnet; the sensor reads the X/Y field **through the 1.6 mm FR4**; firmware
maps deflection to cursor **velocity** (quadratic curve + deadzone + remainder
accumulation) — steeper tilt = faster cursor, exactly the trackpoint behavior
the user asked for, with zero moving parts on the PCB.

- **The ALPS detour, recorded honestly**: the first implementation used an
  ALPS RKJXV1224005 analog gimbal stick (THT, JLC hand-solder). It worked
  electrically (routed 0/0) but the 11.2 mm module body stood proud of the
  face with a housing built around it — the user expected "the stick pokes
  out, not the module," and a Switch-style flush face is geometrically
  impossible with any COTS gimbal in a 5.2 mm under-lid cavity: the module
  that fits doesn't exist at JLC, and the module JLC has doesn't fit. The
  hall-nub architecture inverts the problem: the tall part (spring + cap) is
  a printed part *outside* the shell; the electronic part is a 1 mm SMT chip
  *inside* it. It also restores the all-SMT, no-hand-solder fab story and
  drops the moving-part count on the board to zero.
- **Placement**: sensor U4 at (32.3, 79.0) right-grip-local — the **exact**
  left-D-pad mirror (32.3 mm from the inner edge on both grips, same y — the
  ALPS variant's 2 mm terminal-row offset died with the ALPS). Back
  side, under the lid's Ø10 nub aperture. PgUp/PgDn are the mouse-button
  pair's mirror: same y-heights (cy_lo ± 5.5), same 11 mm spacing, at
  x = 45.7 — the true MB mirror x (57.25) is ON the E73 body; the right
  outer-top has belonged to the antenna since v0.17, so the pair sits between
  nub and radio.
- **Electrical**: the rev-B "trackpad breakout" pads finally do their job —
  **SDA = TP6 (P0.05), SCL = TP7 (P0.28), INT = TP8 (P0.29)**, TWIM0 at
  400 kHz, addr 0x35. Adds only R26/R27 (4k7 pullups) and C8 (100 nF bypass).
  No new MCU pins, no analog domain, no SAADC conflict with the battery
  divider (the ALPS plan's open risk), and deep-sleep drain is the sensor's
  sleep current instead of 660 µA of pot bias.
- **Board knock-ons**: TP6-8 relocate to deck y 67.5 (PgDn's diode landed on
  the old row); C7 beside the USB-C; SW91 reset to deck (53.5, 71.5); the
  deterministic In2 USB lanes get a reworked D+ elbow (rev-A 24.0 → 33.0) and
  a dedicated D− resurface column — the v0.17 columns are inside the new
  PGUP dome ring. Board is back to **all-SMT, 36 right keys, 78 total**; the
  ALPS footprint file is deleted.
- **Firmware**: new in-tree Zephyr module **`firmware/zmk-modules/tmag5273_nub`**
  (Apache-2.0, register map from the upstream Zephyr tmag5273 sensor driver +
  TI datasheet — NOT derived from the Bean's GPLv3 QMK firmware): polls X/Y at
  100 Hz, boot-averages the magnetic zero (which also swallows the MagSafe
  ring's static field), then quadratic rate-control → `input_report_rel`
  into a `zmk,input-listener`. Deadzone/gain/max-speed/axis-flips are DT
  properties — first-article tuning without touching C. A `pm_device` hook +
  `CONFIG_PM_DEVICE` puts the sensor into its ~nA sleep mode when ZMK deep
  sleep fires (continuous mode free-runs at ~2.3 mA on the always-up REG0
  rail — enough to kill the cell in a week of "sleep"; caught in review) and
  re-zeros on resume. Matrix stays 78 keys; west.yml carries no third-party
  modules.
- **Shell/CAD**: right lid gets a plain **Ø10 aperture** (no collar, no pod —
  the face stays flat like a ThinkPad keyboard) with an underside counterbore
  over a printed **nub_spring** (Ø14.8 flange + 3 spiral flexure arms + Ø7 hub;
  the magnet pocket is a press-fit, N-up). The spring is **clamped, not
  floating**: 3 legs on the flange underside bear on the PCB front face and
  the counterbore ceiling presses the flange onto them with 0.05 mm preload
  when the lid screws go home (the adversarial fit review caught the first cut
  leaving the flange 0.9 mm free to drop). A **nub_cap** (Ø8.5 TPU friction
  dome, 4.25 mm proud of the face) press-fits 0.95 mm onto the hub's Ø5
  spigot — cap and spring are prints 8 and 9. Spring compliance is a
  print-tune parameter (arm thickness 0.8); both parts verified watertight.

## v0.20 — mirrored modifiers: Ctrl/Shift/Alt on both grips (2026-07-22)

The 147 mm phone gap means a thumb can never reach the opposite grip, so any
modifier+same-side-key chord needs that modifier on BOTH grips — with left-only
Ctrl, the entire core shortcut cluster (Ctrl+Z/X/C/V/A/S — all left-grip
letters) was physically impossible. The Rii i8+ itself half-acknowledges this:
it duplicates Shift at both ends of the Z-row and carries a right-side AltGr,
and its layout demotes Del to Fn+Backspace. We extend its own logic to the
split geometry. Reviewed by a 3-critic panel (thumb ergonomics, ZMK
feasibility, Rii fidelity) before landing.

- **Two right-grip caps relabel, nothing else moves**: bottom-row `AGR` → `Alt`
  (the keycode was already RALT; AltGr ≡ right Alt on US layouts) and the
  outer-corner `\` → `Ctrl`. Both grips now end in the identical mirrored
  stack — **Ctrl at the bottom-outside corner, Shift directly above it, Alt
  beside Space** (the Rii's own Alt|Space|AltGr grammar). Left grip, brackets,
  FN and WIN are untouched. Zero PCB/matrix change: `thumbdeck.dtsi`
  regenerated **byte-identical**; all 78 domes keep their positions; the JLC
  fab package stays valid.
- **Backslash demotes to the FN layer as DIRECT bindings — FN+`]` = `\`,
  FN+`[` = `|`** (same pattern as `'` on FN+`;`). Pipe deliberately does NOT go
  through Shift: Shift+FN+] would be a three-key chord no thumb-pair can hold.
  Bracket caps get debossed Rii-blue sublegends (`|` and `\`).
- **Side-aware HID codes** in `gen_firmware.py` (`KC_RIGHT`): the right grip
  emits RCTRL/RSHFT/RALT so left/right modifiers stay distinguishable and AltGr
  keeps working under intl layouts. Previously `kc()` was side-agnostic.
- **No sticky/one-shot behaviors — deliberate.** All chords are plain holds;
  the modifier is held by the thumb opposite the target key. Same-side triples
  (Ctrl+Shift+letter) use the vertical corner Ctrl+Shift one-thumb bridge or an
  occasional cross-hand reach. Known residual gaps, accepted: Win+left-side
  combos (Win+E/D, Super+1–5) and left-grip FN-layer targets (BT select) need
  the cross-hand reach — BT is setup-time, Win combos are rare on this device.
- Stale-count cleanup: `gen_firmware.py` docstring and `sim_matrix.py` banner
  said 79 keys; the matrix has been 78 since the v0.17 2u-Enter change.
  `sim_matrix.py` re-run fresh: **78 keys (right 36 + left 42), 0 cross-grip
  collisions, 0 ghost/miss failures — PASS**.

## v0.19 — Game-Boy-Color rework: boxy outline, flush M3 screws, closed well (2026-07-17)

Driven by the user's print-test feedback (5 items) with a Game Boy Color as the
design-language reference (boxy rounded silhouette, Atomic-Purple translucent
shell, dark button-gray keys).

- **Outline (item 4):** the outer **parabolic cheek bow is deleted** — printed
  testing showed the widest part of the cheek blocks thumb reach to the
  edge-adjacent keys and top corners. The outer edge is now **straight** at a
  constant `grip_margin` (7.0 → 8.5: +1 for the fatter M3 boss column, +0.5 routing
  relief — at 8.0 Freerouting left 1-3 nets open every attempt), so
  boards go **79.493 → 75.0 mm** wide; corners: r_in 4.0 / **r_out_top 8.0**
  (antenna-pinned — the E73 keep-out forbids anything rounder) / **r_out_bot
  11.0**, plus a **1.0 mm parabolic bottom crown** (the GBC's convex bottom).
  Face cheek is now a constant ~11.4 mm (was 9.9–15.9 bowed). Device face
  width 330.6 → **325.5 mm** despite the wider spine (below).
- **Mount holes → M3 (item 1):** all 14 face screws are **M3×10 DIN 965
  countersunk, heads flush** with the face (proud M2 pan heads were
  uncomfortable). PCB holes Ø2.2 → **3.4** (boards unordered — free change),
  bosses Ø6/7 → **Ø7.5/8.0** with **Ø4.0 bores** for M3 heat-set inserts;
  lid plate **TOP_T 2.0 → 2.4** so the Ø6.2 countersink cone keeps ≥1.0 mm of
  land (face plane 14.3 → **14.7**; keymat plungers +0.4 to keep caps 1.0
  proud). Hole positions re-tuned for the fatter bosses (inner column x 3.2 →
  4.2, H3 y 77.6 → 72.0, outer column at edge−4.2, H5 y 67.9 → 68.0) against a
  **raised boss gate (r 3.0 → 4.0)** in gen_board/verify_alignment — at the old
  r 3.0 a real dome-courtyard clash would have shipped. The top electronics
  cluster's placement anchor is now a **frozen absolute** (AX 72.493), not
  board_w-derived — the narrower board slid a W-anchored cluster 5 mm inboard
  onto the PGUP/PGDN dome courtyards (caught by the C5 GND-escape assert).
- **Closed phone well (item 2):** the well's x-ends were open slots into the
  grip cavities (the v0.18 gap put the phone ends exactly AT the panel edges).
  The spine gap grows `2 × (0.35 well clearance + 1.6 end wall + 0.3 reveal)`
  = span_x + 4.5 (gap 165.8 → **169.7**), and the panel's well is a full
  **picture-frame** (explicit frame rect replaces the y-only buffer band).
  FFC jumper spec ≥190 → **≥194 mm** (J2 rows now 173.3 mm apart).
- **Thumb scallop → finger dish (item 3):** the R9 scallop cut used to punch
  through into the interior. Now a **curved backer** (R10.6 half-annulus wall +
  solid floor to z 6.0, clipped to the spine cavity −0.25) is unioned before
  the R9 re-cut: watertight, support-free in the panel's slab-down print, case
  edge still exposed ~17 mm for tip-out. Scallop centre moved 2.3 mm into the
  well; the top border screws moved to |x|=13 to clear the dish + Ø8 bosses.
- **Colors (item 5):** GLB shells switch from per-face concept colors to a real
  **glTF PBR material** — "atomic_purple", baseColorFactor linear [0.198,
  0.102, 0.381, 0.55], alphaMode BLEND, doubleSided (translucent purple with
  the guts visible); keymats **dark button gray**. The matplotlib renders
  mirror both (render_iso no longer forces alpha=1).
- **Boards re-routed from scratch** (outline + all 10 hole centers moved =
  Edge.Cuts change): gen_board → route.sh both sides → DRC 0/0 gate → fab
  re-export; sim_matrix / verify_alignment / verify_geometry re-run
  (verify_geometry's hole-to-key gate raised 3.0 → 7.9 c-c to encode the M3
  boss + dome-courtyard rule).

## Rii-follow: 2u Enter at the end of the right H-row (2026-07-15)

Following the Rii i8+'s wide Enter: the right grip's H-row (4th from the top) is
now **H J K L + a double-wide 2u ENT** — 5 caps spanning the 6-unit row width,
one dome under the wide cap (same construction as the 2u space bars). The
apostrophe gave up its physical spot: **`'` is now `&kp SQT` on FN+`;`** (the FN
layer already carried -, =, Home/End, PrtSc and the mouse moves).

- Key count **79 → 78** (right grip 37 → 36: 34 grid keys + PgUp/PgDn; left
  unchanged at 42); diodes likewise 78 (right board 36, refs D1–D36).
- **PCB, keymat and shells regenerated**; the right board **rerouted — still
  0 DRC violations / 0 unconnected** (left board untouched, 0/0); fab package
  re-exported (right BOM now 67 placements). Board dims unchanged (79.5 × 97.0).
- Firmware regenerated: 78 `RC()` transform entries, keymap carries `&kp SQT`
  on FN+`;`.
- Also in this pass: the keymat model carries **debossed Rii-style keycap
  legends** (primary legend + small shifted-symbol secondaries + FN-layer
  legends on 0/9/PgUp/PgDn/Del/;), and the assembled 3D model now includes the
  **M2 shell screws**.

## v0.18 — flush-screen phone well + battery to the left grip (2026-07-14)

Goal: an **S25 Ultra in a typical thin case** sits with its **screen surface flush
with the grip lids' keyboard face** — one continuous 14.3 mm-high front plane
(lids · panel border · screen), thumbs sweeping from glass onto keys with no step.
No change to the boards (no reroute); grips untouched.

- **The math.** Keyboard face (lid top) = z 14.3. Cased S25U = 8.2 + 1.2 case back
  = **9.4 mm** back-of-case → screen. So the phone must rest at z 4.9 — a
  **10.2 mm drop** from v0.17's 15.1. The center panel becomes a **sunken tray**:
  border flange 12.3..14.3 (flush with the lids), well floor at 4.7 with the same
  Ø57×1.8 MagSafe recess / 0.8 mm web / 0.2 mm-proud ring construction as before,
  translated down. Device thickness **22.9 → 15.3 mm** (keycap tops; the flat
  face is 14.3, the case lip sits ~0.4 proud of flush glass).
- **Phone dims got real.** The model carried placeholder iPhone dims (71.6 ×
  147.6); the flush stack forced the real **S25 Ultra (162.8 × 77.6 × 8.2) +
  case_t 1.2** into `deck.Config`. Consequence: the spine gap is sized to the
  cased length (165.2 + 0.6 clearance), so the device is **324.8 mm wide
  (+18.2)** — that is the phone's own size, not packaging growth; y-footprint
  (102.8) and grips unchanged.
- **Battery relocation: REQUIRED, not optional.** Under the sunken well's floor
  slab only **0.5 mm** remains above the back floor — no standard Li-Po exists
  that thin. Survey of the cavities: right grip has 0.24 mm spare (mated JST-PH),
  the **left grip (passive board: diodes 1.16 mm + the FFC ZIF) has 5.14 mm
  free**. The cell is now a **standard 403040 pouch (4.0 × 30 × 40 mm,
  ~450–500 mAh)** foam-taped (0.3 mm) to the left floor under the key field —
  0.84 mm below the diodes at nominal, ~0.4 mm at +10 % swell. 450–500 mAh is the
  capacity the README's own cell-size note preferred, and PROG (196 mA ≈ 0.43 C)
  needs no change. Support posts auto-route around the cell (it's an obstacle box
  in `support_post_locations`). Leads run left cavity → bottom-border lane (y≈5,
  outside the well) across the spine → J3 on the right board. Trade-off logged:
  battery replacement now means opening the left grip (5 screws + lid + keymat +
  board) instead of the panel hatch; the FFC stays panel-serviceable.
- **FFC drops into a floor channel.** The ribbon crossed at z≈5.4 — inside the
  well now. A **0.5 mm recess in the back floor (19 mm lane at the J2 band)**
  gives it a 1.1..1.6 duct under the panel slab (0.5 mm headroom), S-bending down
  from each ZIF inside the grip cavities. The lower seam floor-tab moved
  30–38 → 36–44 so the channel doesn't thin it.
- **Transverse walls cut down to sills** (z 1.95) over the well span — the phone
  and the slab pass over them; full height outside the span still seats the
  border. The old ring-height Ø8 anchors are gone (their bores sit 8 mm above the
  new floor): MagSafe detach is held by the **4 border screws** + slab stiffness
  (~0.25 mm flex at 8 N), down-press by **4 floor nubs** under the slab. Panel
  screw count 6 → 4; **total M2×10: 16 → 14**.
- **Removal scallop.** With the phone sunk 9.4 mm, you can't pinch it — an R9
  thumb scallop in the top border exposes ~18 mm of case edge to tip it out
  against the ring.
- Phone x-retention is the grips' PCB/lid inner edges (0.3 mm clearance per
  side); y-retention the well's 2.0 mm wall band; alignment the MagSafe ring.

## v0.17 — Rii-height grips: chin cut + electronics to the top (2026-07-14)

Ergonomic feedback after printing the right grip lid: the grip (114.5 mm) was
significantly taller than the phone (~80 mm short-side) and than the Rii i8+ the
user thumb-types daily (~97 mm), the excess concentrated in a tall "chin" below the
bottom key row, and the 6-row field (55.5 mm) read taller than the i8+'s (~45 mm),
so the keys sat less within thumb reach. Goal: mimic the i8+'s proportions within
FDM + our-board limits — and since the **trackpad was dropped for v1**, the top zone
it would have occupied is free to reclaim.

- **Grip 114.5 → 97.0 mm** (the i8+ is ~97 mm); width 76.5 → 79.5 mm. Three levers:
  1. **Chin cut, `bottom_strip` 19 → 7 mm.** The 19 mm strip existed only to hold
     the E73 (18 mm) antenna-down at the bottom edge. With the module relocated
     (below), the chin under the space row drops ~23 → ~9 mm — the bulk of the excess.
  2. **Rectangular keys, `key` 8×8 → 8.5×7, `pitch` 9.5 → 10 (X) / 9 (Y).** The i8+
     keeps a short field with wider-than-tall chiclets; ours follow. The 7 mm domes
     (contact courtyard r3.9) still clear at 9 mm Y-pitch (1.2 mm courtyard gap);
     gutters stay ≥1.5 mm (X) / 2.0 mm (Y) for PETG-FDM. Field 55.5 → 52 mm.
  3. **Electronics to the top zone.** The E73 + the whole power front-end (USB-C,
     charger, ESD, reset/power switches, JST, passives, SWD/I²C pads) move from the
     old bottom strip up into the vacated trackpad space, implemented as a rigid
     180° rotation of the DRC-verified rev-A cluster about the board centre
     (`gen_board`'s `P()`/`xf()` involution), so the hand-routed USB fan-in copper
     carries along unchanged rather than being re-derived.
- **Antenna-up at the top edge.** The rotation lands the E73 antenna at the
  CENTRE-top edge — farthest from the centred phone/LiPo, and off the edge the palm
  (which cradles the bottom) doesn't cover. RF is a judgment call vs the old
  antenna-down: hand-detune should improve, phone/battery proximity is similar —
  **re-check range on the first article.** A small inward shift (`DX = 7`) keeps the
  13 mm module off the rounded corner; the JST is placed separately in the chin (its
  rotated pose hit the inner-top page keys); PgUp/PgDn move to the inner-top corner.
- **Top-outer corner sharpened, r_out 14 → 10** (bottom stays 14 for the palm) so
  the top cluster clears the corner — and squarer "shoulders" read more like the i8+.
- **Both boards re-routed 0/0** (KiCad 9, error-severity DRC + 0 unconnected); the
  fab package, firmware (byte-identical — the matrix/pin-map is unchanged) and all 2D
  renders are regenerated. Routing is tighter than rev-A (module-top / bridge-bottom
  puts the 14 bridge nets across the board); `route.sh` is a route-until-clean loop
  and hit 0/0 within a few passes.
- **Switch re-evaluated and KEPT: Snaptron 7 mm 4-leg dome** (2026-07-14 review,
  triggered by the rectangular-cap change). It verifiably fits the new geometry —
  courtyard Ø7.8 vs 9.0 mm Y-pitch = 1.2 mm gap (0.7 mm at the 8.5 mm cluster
  pitch), Ø2.8 nub presses every dome dead-centre (cap centre = dome centre for all
  79 keys incl. the 2u space), and both boards are routed 0/0 around this exact
  footprint. Alternatives lose: 8.4 mm domes physically don't fit the pitch; 5–6 mm
  domes give up travel/centre-hit tolerance under an 8.5 mm cap; LCSC SMD tacts
  (TS-1088 etc.) add 1.0–2.6 mm of z-stack (dome is 0.5 mm), 79 fab-soldered parts,
  and a full reroute. The fab's role is unchanged either way: ENIG gold pads only —
  domes press on at assembly. **Actionable:** sample LIGHT-force (~160–180 gf trip)
  4-leg domes, not the 400+ gf GX class, to approximate the i8+'s light feel.
- **3D regenerated for v0.17** (same session, after review): `deck3d.py` updated —
  keymat plungers/lid openings are now the real **rounded-rect 8.5 × 7 caps** (18.5
  for the 2u space; cluster keys stay round), the USB-C opening / power-switch slot /
  antenna wall relief moved to the TOP wall, the slide-switch knob direction is
  derived from the placed rotation, and the 4 panel seam screws are derived from the
  phone-pocket span (the old hardcoded y=105 was off the 97 mm shell entirely, and
  y=10 clipped the new pocket rim). The antenna wall stays CLOSED — 1.9 mm of PETG
  remains over the relieved span; the antenna radiates through plastic, not a hole.
  Also fixed a **latent v0.16 keymat bug the regen render exposed**: the cluster
  plungers (PgUp/PgDn, D-pad, mouse pair) sat outside the web buffer's reach — the
  "one-piece" keymat was really 3+ floating pieces. The web now grows the **3 mm
  living-hinge strips** the 2D concept always drew (each feature → nearest grid key
  + nearest other feature) and asserts single-polygon connectivity at build time.
  Also fixed: `deck.product()` origin rounding 2 → 3 decimals (a 79.493 mm board_w
  put the left grip 0.003 mm off the seam and tripped deck3d's frame assert).
- **Adversarial alignment audit (machine-verified, 2026-07-14):** all 79 domes sit
  at model key centres with 0.0 µm deviation on both boards; diodes at +3.0 mm; min
  dome courtyard spacing 9.0/8.5 mm vs the 7.8 floor; every non-dome footprint is
  back-mounted. Two margins worth knowing: (1) the cap Y-dimension (7.0) exactly
  equals the dome diameter — zero cover margin, so keymat registration (screw bosses
  + clamp rim) is what keeps the dome edge hidden; (2) the USB-C shield stakes and
  the J1/SW90 locating pegs protrude through to the PCB FRONT in the top zone —
  they clear the keymat web by ~8.4 mm and sit below the lid plate, but any rev-B
  front-side feature near x 31–40, y 90–95 must account for them.

## v0.16 — 5-part shell split for a 220 mm bed (2026-07-13)

Concept change from the sketches (`sketches/All.png`, `top_shell.png`, `side.png`):
the front is **two cyan grip lids** and a **pink center panel** that is visually
"the front of the back"; the back stays pink. Driver: the one-piece shells were
306 × 120 mm — they don't fit a Creality **Ender 3 V2 (220 × 220)** at any
rotation (min enclosing square ~302 mm); the target printer is now first-class.

- **Part set: 5 shells** — `back_left` + `back_right` (tray split at x=0 mid-
  spine, ~161/153 × 120 mm), `grip_lid_left/right` (~79 × 120), `center_panel`
  (~147 × 120). `deck3d.py --all` gates every part on **bbox ≤ 204 mm** (220 −
  2×8 brim). Keymats unchanged.
- **Staggered splices** — the bolted-on panel bridges the back seam at x=0; the
  continuous back halves bridge the front seams at the grip edges: every
  cross-section keeps one uncut structural member.
- **Back seam is screwless printed joinery** (adversarial design review killed
  the lap-screw variant: M2 inserts don't fit a 0.8 mm floor flap, and a
  horizontal lap is a 120 mm unprintable one-sided cantilever): floor butt +
  two full-thickness tabs into cleared notches, an 8 mm **vertical shiplap** in
  each perimeter wall (vertical faces print clean; 0.25 mm clearances), and a
  0.4 mm 45° outer V-groove = elephant-foot relief + intentional shadow line.
- **Panel/lid joint is a 0.3 mm open reveal, no overlap** — a shiplap/rebate
  here either lands on the inner lid screw heads (3.2 mm from the grip edge,
  fab-locked) or creates more mid-air mating faces; the reveal needs neither.
  Both edges get 0.8 mm 45° chamfers, so the seam reads as a design line.
- **Transverse spine wall at each grip boundary** (new, in each back half):
  closes each half's torsion box where the front plate is now cut, seats the
  panel edge, and carries a **Ø8 boss at MagSafe-ring height** — phone-detach
  pull anchors in line with the ring instead of peeling the panel. FFC and
  battery-lead windows are cut from the placed J2/J3 positions.
- **Panel plate 2.0 → 2.6 mm**: the Ø57 ring recess now leaves a **0.8 mm
  (4-layer) web** instead of one 0.2 mm layer; ring still sits 0.2 mm proud;
  spine grows 16.3 → 16.9 mm. Panel = spine **service hatch**: 6 screws expose
  battery + FFC without touching the grips.
- **Fasteners: 10 → 16 M2 (one SKU, M2×10 button-head)** — grips keep their 5
  per side untouched; the panel adds 4 floor bosses straddling the back seam +
  the 2 ring-height wall bosses.
- **Fixed en route:** `battery_body()` modeled the 503450 pouch rotated 90°
  (34 × 50 overflowed the 52 × 36 reserved rect y-span); `--sync-models` now
  refreshes the tracked `hardware/cad/models/` STLs (they had gone stale/orphan).
- `deck3d.py --check` = **0 collisions** (203 bodies); back-seam interpenetration
  asserted 0.000 mm³; both cosmetic faces verified flat for their print
  orientation.

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
- **License:** Apache License 2.0. Chosen over MIT for the explicit **patent
  grant** (§3) and the explicit **inbound contribution terms** (§5) — both matter
  for a hardware-adjacent project that ships fabricable board files and invites
  outside build reports. It also states attribution/NOTICE handling explicitly,
  which is what carries the vendored third-party footprint attribution
  (marbastlib, CERN-OHL-2.0-P) cleanly alongside the original work.

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

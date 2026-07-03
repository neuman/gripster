# Design decisions

Locked decisions from PROJECT_SPEC §2, plus decisions taken during the loop.

## Locked (from spec)

| Area | Decision |
|---|---|
| Form factor | Two grips, Backbone-clamp style, flanking a phone. 3D shell = user's later work; PCB exposes mount features. |
| Reference look | i8+-inspired QWERTY, split L/R. Keys-only (touchpad = `TODO(user)`). |
| Switches | Xiaoyztan 5×5×1.5 mm 4-terminal SMD tact (owned). Treated as 2-terminal SPST (§ footprints). |
| Controller | nRF52840, one per half. Default **XIAO nRF52840**; nice!nano v2 alt. |
| Connectivity | BLE split + USB-C wired HID on the central. |
| Power | LiPo per half, USB-C charging via the board's onboard charger. |
| Split model | ZMK central + peripheral over BLE. No inter-half cable. |
| Diodes | One per key, 1N4148W SOD-123, uniform orientation, `col2row`. |
| Firmware | ZMK (wireless-native). |
| Fabrication | JLCPCB, 1.6 mm, HASL, gerbers from KiCad. |

## Decisions taken during the loop (with rationale)

- **Default GPIO pins corrected.** The spec's provisional column pins
  `P0.06–P0.09` are **not broken out** on the XIAO nRF52840. Real exposed pins
  used instead: rows `P0.02,03,28,29,04` (D0–D4), cols `P0.05,P1.11,P1.12,P1.13,P1.14`
  (D5–D9), leaving `P1.15` (D10) spare. Verified against the Seeed pinout.

- **Combined 50-key transform, not "25/half".** The spec says "matrix transform
  sized to 25 keys/half", but a ZMK split joins both halves into **one** logical
  keymap. Implemented as a 50-position transform (columns=10, rows=5): central
  (right) → logical cols 0–4, peripheral (left) → cols 5–9 via `col-offset = 5`.
  A literal per-half 25-key transform would not build. See
  [matrix-and-diodes.md](matrix-and-diodes.md).

- **Left-half legends pre-reversed.** The left half is a geometric mirror of the
  right, which reverses on-screen column order. Legends are stored inner→outer
  so the mirrored render reads naturally ("1 2 3 4 5", "Q W E R T").
  `matrix_map.py` asserts render legends == keymap bindings.

- **Board geometry.** 63 × 108 mm per half. Vertical stack: bottom strip
  (USB-C + LiPo) / 5×5 key field fanned into a thumb arc / top strip (controller).
  D-shaped silhouette: flat inner edge (clamp mating reference), bowed + rounded
  outer edge. 3 mount holes (2 on the inner edge for the clamp).

- **Render path.** KiCad `pcbnew` headless (the spec's "primary") is unavailable
  in this environment, so rendering uses matplotlib PNG (viewable by the loop for
  visual grading). The board file is hand-authored KiCad S-expression — no KiCad
  install needed to produce it.

- **License:** MIT (spec default). **Central/peripheral:** right/left (flippable
  by swapping which shield is flashed to which half).

## Open `TODO(user)`

- Datasheet-verified switch footprint (before gerbers).
- Copper routing in KiCad (before gerbers).
- LiPo capacity vs. shell space (~100–150 mAh assumed).
- Keycap/top solution over bare plungers.
- Touchpad (omitted; would need an I²C module + the nice!nano's spare GPIO).
- 3D clamp shell geometry (out of scope here).
- Confirm key count/reach against a real i8+ and your thumb span.

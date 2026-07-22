# Contributing to Gripster

Thanks for looking. Gripster (the repo and board id are `thumbdeck` internally) is a
one-person open hardware project, and contributions are genuinely welcome — but this
repo works differently from most, so please read the golden rule before you open an
editor.

**Before anything else, the honest bit: this device has never been physically built.**
No board has been fabricated, no shell printed, no dome pressed, nothing flashed onto
real hardware. Everything in this repo is a design, a generated artifact, or a render.
That makes some contributions unusually valuable — see
[The most useful thing you can do](#the-most-useful-thing-you-can-do-right-now).

---

## The golden rule: this design is generated

Almost nothing in this repo is hand-drawn. A single parametric Python model,
[`hardware/scripts/deck.py`](hardware/scripts/deck.py), defines the key grid, board
outline, component placement, legends and dimensions. Every other artifact — the KiCad
boards, the printable shells, the ZMK keymap, the renders — is emitted from it by a
generator script.

**So: change the model, then regenerate. Never hand-edit a generated file.** The next
generator run overwrites it silently, your change disappears, and the boards and the
firmware drift out of agreement with each other. A hand-edited `.kicad_pcb` is the one
kind of PR that cannot be merged.

### Generated — do not hand-edit

| Path | Produced by |
|---|---|
| `hardware/kicad/generated/thumbdeck_{left,right}.kicad_pcb` (and `.kicad_pro`, `.kicad_dru`, `*_placement.csv`) | `gen_board.py` → `route.sh` → `stitch.py` |
| `hardware/kicad/generated/fab/**`, `*.dsn`, `*.ses`, `drc_*.json` | `route.sh`, `gen_fab.py` — git-ignored local build artifacts |
| `firmware/zmk-config/config/boards/arm/thumbdeck/thumbdeck.dtsi` | `gen_firmware.py` (kscan + matrix transform) |
| `firmware/zmk-config/config/boards/arm/thumbdeck/thumbdeck.keymap` | `gen_firmware.py` (one binding per real key) |
| `hardware/cad/models/*.stl`, `hardware/cad/models/thumbdeck_full_asm.glb` | `deck3d.py --all`, `export_full_asm.py` |
| `renders/*.png` | `render_product.py`, `render_layers.py`, `render_fab.py`, `deck3d.py --render` |
| `renders/history/**` | archive of the superseded v0.4 design loop — history, not current state |

Both generated firmware files carry a `GENERATED … DO NOT hand-edit` banner at the top.
If you find yourself deleting that banner, stop and go edit the generator.

### Authored — edit these

- `hardware/scripts/deck.py` — **the source of truth.** Dimensions, the key grid, the
  `LEGENDS` tables. Most design changes are a change here and nowhere else.
- `hardware/scripts/` generators and gates: `gen_board.py`, `route.sh`, `stitch.py`,
  `gen_fab.py`, `gen_firmware.py`, `sim_matrix.py`, `verify_alignment.py`,
  `verify_geometry.py`, `render_*.py`.
- `hardware/cad/deck3d.py`, `export_full_asm.py`, `export_placement.py` — the CadQuery
  shells, keymats and assembly export.
- `hardware/footprints/thumbdeck.pretty/*.kicad_mod` — hand-authored footprints,
  including the snap-dome contact pad. Do **not** modify `marbastlib-LICENSE`; it is a
  vendored third-party license that must stay byte-identical.
- `firmware/zmk-config/` **except** the two generated files above — so `thumbdeck.dts`,
  `thumbdeck.dtsi`'s consumer, `Kconfig.board`, `Kconfig.defconfig`, `board.cmake`,
  `thumbdeck_defconfig`, `thumbdeck.zmk.yml`, `config/thumbdeck.conf`, `config/west.yml`,
  `build.yaml`.
- `docs/`, `README.md`, `.github/`.

`hardware/layout/keymat.json` is the original sketch digitization — historical only. The
live layout is the `LEGENDS` tables in `deck.py`. Likewise the old 50-key / nice!nano
scripts under `hardware/scripts/legacy/` are kept for history and are not part of the
pipeline.

Commit the regenerated output alongside the model change, in the same PR, so the tracked
artifacts always match the model that produced them.

---

## Toolchain

You do not need all of this. Match the tools to the part you are touching.

| Contributing to | You need |
|---|---|
| Docs only | nothing |
| 2D layout / renders / matrix sim | Python 3 + `matplotlib` |
| PCB / routing / fab output | the above, plus **KiCad 9** (the `pcbnew` Python module *and* `kicad-cli`), plus a **Freerouting** jar and a JRE |
| 3D shells and keymats | the CadQuery venv at `hardware/cad/.venv` |
| Firmware | nothing locally — CI builds it; a local `west` + ZMK v0.3.0 setup is optional |

Create the CAD venv once:

```bash
python3 -m venv hardware/cad/.venv
hardware/cad/.venv/bin/pip install -r hardware/cad/requirements.txt
```

`route.sh` currently points at a JRE and a Freerouting jar under `$HOME/tools/`
(see the variables at the top of the file). If yours live elsewhere, adjust those two
lines locally — but please do not commit machine-specific paths.

---

## Regenerating

The full pipeline, in order (this is the same sequence as the README's *Reproduce the
design* section):

```bash
cd hardware/scripts
python3 gen_board.py                  # placement + netlist + deterministic USB copper + GND escape vias
./route.sh right && ./route.sh left   # Freerouting autoroute -> GND stitch + zone fill -> DRC gate
python3 gen_fab.py                    # gerbers/BOM/CPL per side (refuses to export unless DRC-clean)
python3 verify_alignment.py           # top-to-bottom 2D stack audit: domes/diodes vs model, cap gutters, boss clearances
python3 sim_matrix.py                 # ghosting/NKRO proof — FINAL PASS
python3 gen_firmware.py               # ZMK transform/keymap/gpio, generated from the model
python3 render_layers.py              # 5 stackable 2D layers -> renders/layer_*.png

# --- 3D (CadQuery; see docs/cad-process.md) ---
cd ../..
hardware/cad/.venv/bin/python hardware/cad/deck3d.py --all --check --render
hardware/cad/.venv/bin/python hardware/cad/export_full_asm.py   # nested full-assembly GLB
```

You only need to run the stages your change actually affects — but if you touched
`deck.py`, assume it affects everything downstream of it.

---

## The acceptance gate

These are the checks the project holds itself to. A PR that changes the corresponding
subsystem should report the real output of the relevant ones, pasted into the PR body.
Most of them are self-enforcing: they exit non-zero or refuse to run.

**PCB / routing change**

- `kicad-cli pcb drc --severity-error` must report **0 violations, 0 unconnected items**
  on both `thumbdeck_right` and `thumbdeck_left`.
- `python3 gen_fab.py` must complete. It runs the DRC itself and hard-exits with
  `"<side>: DRC NOT CLEAN (N violations, M unconnected) — not exporting fab data"` if the
  board is not clean, so a successful fab export *is* the proof. Success prints
  `<side>: DRC clean` per side.
- Note for reviewers and authors alike: 0 DRC violations means *no design rule was
  broken*. It does not mean the circuit is correct. Say what you actually verified.

**Geometry / 3D / layout change**

- `python3 verify_alignment.py` must end in `ALL CHECKS PASS` (it exits 1 and lists the
  failing check names otherwise).
- `python3 verify_geometry.py` must exit 0.
- `hardware/cad/.venv/bin/python hardware/cad/deck3d.py --all --check` must report
  **0 impossible overlaps** (`✅ no impossible overlaps`), and every part must still fit
  the 220 × 220 mm Ender 3 V2 bed — `--all` gates on that.

**Matrix / key-grid change**

- `python3 sim_matrix.py` must end in `FINAL: PASS`. It proves the diode matrix is
  ghost-free *and* proves the simulation can detect ghosting (the no-diode control case
  must fail). Both halves matter — a sim that never fails proves nothing.
- If you added, removed or moved keys, the key count changes in several places at once.
  Re-run `gen_firmware.py` so the transform and keymap follow, and grep the docs for the
  old count.

**Firmware change**

- The GitHub Actions workflow (`.github/workflows/build.yml`) must build. It is a
  self-contained ZMK v0.3.0 build against the real board definition
  (`-b thumbdeck` with `ZMK_CONFIG` pointed at `firmware/zmk-config/config`) and it
  produces `thumbdeck-zmk.uf2`. `thumbdeck` here is the internal board id and the
  artifact name — please leave those literal strings alone.
- Nobody has ever flashed the result to hardware, because no hardware exists. Do not
  describe a firmware change as "tested" unless you tested it on something.

**Docs change**

- No gate, but check that relative links resolve. A fair amount of the fab output
  (`hardware/kicad/generated/fab/`, `*.dsn`, `*.ses`, `drc_*.json`) is git-ignored, so
  do not link to it as if a fresh clone contains it.

---

## Issues and pull requests

**Open an issue when** you have found something wrong, you are stuck on a build, or you
want to propose a design change. There are forms for all three — bug report, build help,
and design proposal — and the design-proposal form asks the questions a maintainer would
ask anyway (which subsystem, does it need a board respin, what does it do to the gate).

**Start large changes as an issue, not a PR.** Anything that moves keys, changes the
board outline, alters the matrix, or would require re-routing both boards is worth a
conversation first. Routing is slow, the boards are tightly packed at 75 × 97 mm, and it
is disheartening to sink a weekend into a PR that was architecturally off the table.

**Good PRs** are small, regenerate rather than hand-edit, include the output of the
relevant gate checks, and say plainly what was verified and what was not. Typo fixes and
doc corrections need no ceremony — send them.

**Not useful:** hand-edited generated files, mass reformatting, or PRs that regenerate
everything as a side effect of an unrelated one-line change.

---

## The most useful thing you can do right now

Ranked, honestly:

1. **Build one and tell us what is wrong.** Nobody has. A first-article report — even a
   failed one, *especially* a failed one — is worth more than every other contribution
   combined. Photos of a bad print, a board that arrived wrong, a dome that will not
   seat: all of it is signal. Use the *Build help / first-article report* issue form.
2. **Print a part and report the result.** You do not need the boards. Shell fit, keymat
   living-hinge behaviour in TPU 95A, and boss/screw tolerances have only ever been
   checked in CAD.
3. **Ergonomic critique**, if you have built or used a thumb-typed device. Key pitch,
   grip shape and thumb reach are genuinely unresolved.
4. **A KiCad or RF review.** The boards are autorouted and DRC-clean, which is not the
   same as good. Antenna keep-out, ground stitching and the power front-end all deserve
   a second pair of eyes.
5. **A ZMK review** of the board definition at
   `firmware/zmk-config/config/boards/arm/thumbdeck/`.

---

## Licensing

Gripster is licensed under the **Apache License 2.0**. Contributions are accepted
inbound=outbound: by submitting a PR you agree your contribution is licensed under
Apache 2.0. There is **no CLA** to sign.

Please add the SPDX header to any new source file you create:

```python
# SPDX-License-Identifier: Apache-2.0
```

(`// SPDX-License-Identifier: Apache-2.0` for C/DTS, `# ...` for Python, shell and YAML.)

Some third-party material in this repo is under other licenses and must be left alone —
notably `hardware/footprints/thumbdeck.pretty/marbastlib-LICENSE`. See
[NOTICE](NOTICE) for the full attribution list, and add to it if you vendor anything new.

---

## Conduct

Be decent to people. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md); reports go to
eric@trydotted.com.

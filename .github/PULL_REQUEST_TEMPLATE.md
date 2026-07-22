<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 Eric Neuman -->

## What does this change?

<!-- One or two sentences. Link the issue if there is one: Fixes #123 -->

## Why?

<!-- The problem it solves. For a design change, this should already have been discussed
     in an issue — link it. -->

## Subsystems touched

<!-- Delete the ones that do not apply. -->

- [ ] Key layout / legends (`LEGENDS` in `deck.py`)
- [ ] Matrix / diodes
- [ ] PCB placement & routing
- [ ] 3D shells & keymats
- [ ] Firmware / ZMK
- [ ] Generator scripts & pipeline
- [ ] Docs

---

## The golden rule

- [ ] **I changed the model/generators and regenerated. I did not hand-edit any generated
      file** — nothing under `hardware/kicad/generated/`, `hardware/cad/models/`,
      `renders/`, or the generated `thumbdeck.dtsi` / `thumbdeck.keymap`.
- [ ] Regenerated artifacts are committed in this PR, so the tracked output matches the
      model that produced it.

## Acceptance gate

Tick only what you actually ran, and paste the real output below. **Leave a box unticked
rather than guessing** — an honest "not run" is fine; a wrong tick is not.

**If this changes the PCB or routing**

- [ ] `python3 gen_fab.py` completes — it runs DRC itself and refuses to export unless
      clean. Prints `<side>: DRC clean` per side.
- [ ] **0 violations, 0 unconnected items** (error severity) on both `thumbdeck_right`
      and `thumbdeck_left`.

**If this changes geometry, layout or 3D**

- [ ] `python3 verify_alignment.py` → `ALL CHECKS PASS`
- [ ] `python3 verify_geometry.py` → exit 0
- [ ] `deck3d.py --all --check` → **0 impossible overlaps**, all parts still fit the
      220 × 220 mm Ender 3 V2 bed

**If this changes the matrix or key grid**

- [ ] `python3 sim_matrix.py` → `FINAL: PASS` (ghost-free with diodes, *and* the no-diode
      control case still fails, proving the sim detects ghosting)
- [ ] Re-ran `gen_firmware.py` so the transform and keymap follow; grepped the docs for a
      stale key count

**If this changes firmware**

- [ ] The GitHub Actions ZMK build passes and produces `thumbdeck-zmk.uf2`

### Output

<details>
<summary>Paste the real output of the checks you ran</summary>

```
```

</details>

---

## Housekeeping

- [ ] Docs updated if behaviour, dimensions, part numbers or commands changed
- [ ] New source files carry `SPDX-License-Identifier: Apache-2.0`
- [ ] No machine-specific paths committed (e.g. the `JAVA` / `FR` variables in `route.sh`)
- [ ] Internal names left literal where they must be — the board id `thumbdeck`, the
      artifact `thumbdeck-zmk.uf2`, `boards/arm/thumbdeck/`, `thumbdeck_*.kicad_pcb`

## What did you *not* verify?

<!-- Please be specific. Nobody has ever built this device, so "tested" means something
     narrower here than usual — say what you actually observed. DRC-clean means no rule
     was broken, not that the circuit is correct. -->

<!-- By submitting this PR you agree your contribution is licensed under the Apache
     License 2.0 (inbound=outbound). There is no CLA. -->

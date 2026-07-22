# legacy scripts (v0.4 design loop — superseded)

These drove the old 50-key / nice!nano / auto-grader loop and reference geometry
that no longer matches the design. Kept for history. The active pipeline is:
`deck.py` · `gen_board.py` · `route.sh` · `stitch.py` · `gen_fab.py` ·
`gen_firmware.py` · `sim_matrix.py` · `verify_alignment.py` · `verify_geometry.py`
(2D renders: `render_product.py` · `render_fab.py` · `render_layers.py`).

Note that `gen_kicad_pcbnew.py` — previously listed here as active — is itself a
legacy script and lives in this directory; the current board generator is
`gen_board.py`.

# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Eric Neuman

# thumbdeck — nRF52840, flashed once over SWD then drag-drop UF2.
board_runner_args(nrfjprog "--nrf-family=NRF52")
board_runner_args(jlink "--device=nRF52840_xxAA" "--speed=4000")
include(${ZEPHYR_BASE}/boards/common/nrfjprog.board.cmake)
include(${ZEPHYR_BASE}/boards/common/jlink.board.cmake)

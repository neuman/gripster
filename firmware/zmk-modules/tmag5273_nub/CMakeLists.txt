# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Eric Neuman
if(CONFIG_INPUT_TMAG5273_NUB)
  zephyr_library()
  zephyr_library_sources(src/tmag5273_nub.c)
endif()

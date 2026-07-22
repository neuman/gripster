#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Eric Neuman
"""count_stragglers.py <placed_board> <ses> <out_board>
Import a Freerouting SES onto a pristine placed board, save it, and print how many
non-GND ratsnest connections remain (sum of components-1 over signal/power nets).
Used to pick the best of several stochastic Freerouting runs."""
import sys, os, importlib.util, pcbnew

_spec = importlib.util.spec_from_file_location(
    "rn", os.path.join(os.path.dirname(__file__), "route_nets.py"))
rn = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(rn)


def main():
    b = pcbnew.LoadBoard(sys.argv[1])
    pcbnew.ImportSpecctraSES(b, sys.argv[2])
    pcbnew.SaveBoard(sys.argv[3], b)
    gnd = b.FindNet("GND").GetNetCode()
    total = 0
    for code in range(1, b.GetNetInfo().GetNetCount()):
        if code == gnd:
            continue
        total += max(0, len(rn.components(b, code)) - 1)
    print(total)


if __name__ == "__main__":
    main()

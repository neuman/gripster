#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Eric Neuman
"""
final_grade.py — combined pass/fail for one iteration.

Fuses the objective functional grade (grade.py: geometry + firmware) with the
visual rubric (renders/visual_scores.json, scored by the loop operator viewing
the PNG). Overall PASS requires: no functional hard-fails, functional score
>= 90, and every visual checklist item pass.

Usage: python3 final_grade.py --iter 3
"""
import argparse, json, os
import grade

HERE = os.path.dirname(__file__)
RENDERS = os.path.abspath(os.path.join(HERE, "..", "..", "renders"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iter", type=int, required=True)
    a = ap.parse_args()

    geo = json.load(open(os.path.join(RENDERS, f"iter_{a.iter:02d}.geo.json")))
    checks = grade.geometric_checks(geo) + grade.firmware_checks() + grade.doc_checks()
    pct, hard_fail, passed, total = grade.score(checks)
    func_pass = not hard_fail and pct >= 90.0

    vs = json.load(open(os.path.join(RENDERS, "visual_scores.json")))
    vitems = vs["checklist"]
    vpass = all(i["pass"] for i in vitems)
    vpassed = sum(1 for i in vitems if i["pass"])

    overall = func_pass and vpass

    print("============================================================")
    print(f"  thumbdeck — COMBINED GRADE (iter {a.iter:02d})")
    print("============================================================")
    print(f"  FUNCTIONAL : {pct:5.1f}%  ({passed}/{total})  "
          f"hard-fails: {hard_fail or 'none'}   -> {'PASS' if func_pass else 'FAIL'}")
    print(f"  VISUAL     : {vpassed}/{len(vitems)} checklist items          "
          f"    -> {'PASS' if vpass else 'FAIL'}")
    print("------------------------------------------------------------")
    print(f"  OVERALL    : {'*** PASS ***' if overall else 'FAIL'}")
    print("============================================================")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())

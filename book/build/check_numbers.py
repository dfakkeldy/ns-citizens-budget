"""Headline numbers: the front pages and chapters must print what the model prints.

Reads model/proposals/plan-b-final-output.txt (written by model/plan_b_final.py),
rounds the headline figures the way the text does, and checks that front/front.html
and the Plan B chapter carry them. Also fails on figures from superseded runs.
Run from the book folder: .venv/bin/python build/check_numbers.py
"""
import re
import sys
from pathlib import Path

BOOK = Path(__file__).resolve().parents[1]
OUT = (BOOK.parent / "model" / "proposals" / "plan-b-final-output.txt").read_text()
FRONT = (BOOK / "front" / "front.html").read_text()
CH2 = (BOOK / "src" / "chapters" / "02-plan-a.md").read_text()
CH3 = (BOOK / "src" / "chapters" / "03-plan-b.md").read_text()


def row(label):
    m = re.search(rf"^{re.escape(label)}\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s*$", OUT, re.M)
    return [float(v.replace(",", "")) for v in m.groups()]


plan_a = row("Plan A (path.py, reviewed measures)")
plan_b = row("Plan B")
no_b5 = row("  Without B5 (no room left under a combined 5%)")
risk = [float(v.replace(",", "")) for v in
        re.search(r"plan ([\d,.]+); with Plan A ([\d,.]+); with Plan B ([\d,.]+)", OUT).groups()]
r = lambda x: f"{round(x):,}"

need = {
    "front": [f"${r(plan_b[2])}M", r(plan_b[0]), r(plan_b[1]), r(plan_b[2]), f"${r(no_b5[2])} million",
              r(risk[1]), r(risk[2]), r(risk[0])],
    "chapter 3": [f"**{r(plan_b[0])}**", f"**{r(plan_b[1])}**", f"**{r(plan_b[2])}**",
                  f"${r(plan_b[2])} million", f"${r(no_b5[2])} million", r(no_b5[0]), r(no_b5[1])],
    "chapter 2": [f"{plan_a[0]:,.1f}", f"{plan_a[2]:,.1f}", f"{risk[0]:,.1f} / {risk[1]:,.1f}"],
}
text = {"front": FRONT, "chapter 3": CH3, "chapter 2": CH2}
stale = ["$510", "1,053", "821", "1,259", "$549", "$420 million", "59%", "$65 million", "$70M"]
bad = []
for where, items in need.items():
    bad += [f"{where}: missing {x!r}" for x in items if x not in text[where]]
for where in ("front", "chapter 3"):
    bad += [f"{where}: stale {x!r}" for x in stale if x in text[where]]
print(f"numbers: Plan B {' / '.join(r(v) for v in plan_b)}; without B5 {r(no_b5[2])}; "
      f"2027-28 overrun case {' / '.join(r(v) for v in risk)}")
if bad:
    print("FAIL:\n  " + "\n  ".join(bad))
    sys.exit(1)
print("PASS: front pages and chapters carry the model's headline numbers; no superseded figures.")

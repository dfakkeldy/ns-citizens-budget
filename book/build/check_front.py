"""Front pages: no text may run into the bottom margin.

The designed front pages (front/front.html) sit outside the engine's overflow check.
Each .page has 48px (36pt) of bottom padding on a 792pt Letter page, so the lowest
text on every front page must end by about 756pt; 760pt allows for text metrics.
Run from the book folder: .venv/bin/python build/check_front.py out/front.pdf
Given the merged book, it checks only the first three pages (the front pages);
body pages have their own layout and the engine's overflow check.
"""
import re
import subprocess
import sys

LIMIT = 760.0
FRONT_PAGES = 3
pdf = sys.argv[1] if len(sys.argv) > 1 else "out/front.pdf"
html = subprocess.run(["pdftotext", "-bbox", "-f", "1", "-l", str(FRONT_PAGES), pdf, "-"], capture_output=True, text=True, check=True).stdout
bad = []
for n, page in enumerate(re.findall(r"<page [^>]*>(.*?)</page>", html, re.S), 1):
    ys = [float(y) for y in re.findall(r'<word [^>]*yMax="([\d.]+)"', page)]
    low = max(ys) if ys else 0.0
    print(f"front p.{n}: lowest text ends at {low:.1f}pt (limit {LIMIT:.0f})")
    if low > LIMIT:
        bad.append(n)
if bad:
    print(f"FAIL: text runs into the bottom margin on front page(s) {bad}")
    sys.exit(1)
print("PASS: every front page keeps its bottom margin.")

"""Citations: every [n] in the text has a numbered source, and every source is cited.

Reads src/chapters/*.md and src/cards.yaml; the numbered list in the sources chapter
(the file whose entries start "1. ", "2. ", ...) is the bibliography.
Run from the book folder: .venv/bin/python build/check_citations.py
"""
import glob
import re
import sys

text, bib_file = "", None
for f in sorted(glob.glob("src/chapters/*.md")) + ["src/cards.yaml"]:
    t = open(f).read()
    if re.search(r"^1\. ", t, re.M) and re.search(r"^2\. ", t, re.M) and "sources" in f.lower():
        bib_file = f
        body = t.split("::: full", 1)[0]          # the intro before the list may cite nothing
        text += body
        listed = set(int(n) for n in re.findall(r"^(\d+)\. ", t, re.M))
        continue
    text += t
if not bib_file:
    sys.exit("FAIL: no sources chapter found")
cited = set(int(n) for n in re.findall(r"\[(\d+)\](?!\()", text))
for a, b in re.findall(r"\[(\d+)\]-\[(\d+)\]", text):
    cited.update(range(int(a), int(b) + 1))
missing, unused = sorted(cited - listed), sorted(listed - cited)
print(f"citations: {len(cited)} cited, {len(listed)} listed in {bib_file}")
if missing or unused:
    if missing: print(f"FAIL: cited but not listed: {missing}")
    if unused: print(f"FAIL: listed but never cited: {unused}")
    sys.exit(1)
print("PASS: every citation resolves and every source is cited.")

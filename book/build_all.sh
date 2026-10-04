#!/bin/bash
# Build the whole submission: the checked body (engine), the designed front pages,
# and the merged PDF. Run from this folder: ./build_all.sh
set -euo pipefail
cd "$(dirname "$0")"
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
OUT=own-costs-first-budget-2027-28.pdf

echo "== model outputs current"
../model/check_outputs.sh

echo "== citations"
.venv/bin/python build/check_citations.py

echo "== body (engine) and checks"
.venv/bin/python build/build.py
build/check_all.sh

echo "== front pages"
# Chrome sometimes exits non-zero on teardown after writing the file, so delete the old
# file first and judge success by a fresh three-page PDF rather than by Chrome's exit code.
rm -f out/front.pdf
"$CHROME" --headless=new --disable-gpu --no-pdf-header-footer --allow-file-access-from-files \
  --print-to-pdf="$PWD/out/front.pdf" "file://$PWD/front/front.html" 2>/dev/null || true
test -s out/front.pdf
test "$(pdfinfo out/front.pdf | awk '/^Pages:/{print $2}')" = 3
.venv/bin/python build/check_front.py out/front.pdf

echo "== merge"
.venv/bin/python - "$OUT" <<'EOF'
import sys
from pypdf import PdfReader, PdfWriter
out = sys.argv[1]
w = PdfWriter()
w.append(PdfReader("out/front.pdf"), import_outline=False)
body = PdfReader("own-costs-first-budget-2027-28-body.pdf")
# Chrome drops the space where text-wrap:balance breaks a heading ("thegovernment's");
# restore each bookmark title from the source headings.
import glob, re
from pypdf.generic import NameObject, TextStringObject
heads = [m.group(1).strip() for f in sorted(glob.glob("src/chapters/*.md"))
         for m in re.finditer(r"^#{1,3} (.+)$", open(f).read(), re.M)]
norm = lambda x: x.replace(" ", "").replace("\u2019", "'")
def fix(node):
    while node is not None:
        node = node.get_object()
        t = str(node["/Title"])
        for h in heads:
            if norm(h) == norm(t) and h.replace("'", "\u2019") != t:
                node[NameObject("/Title")] = TextStringObject(h.replace("'", "\u2019"))
        if "/First" in node:
            fix(node["/First"])
        node = node.get("/Next")
fix(body.trailer["/Root"]["/Outlines"].get("/First"))
w.add_outline_item("Own costs first (cover)", 0)
w.add_outline_item("At a glance", 1)
w.add_outline_item("Where things stand (charts)", 2)
w.append(body, import_outline=True)
# page labels: front pages i-iii, then the body's printed folios from 1
w.set_page_label(0, 2, style="/r")
w.set_page_label(3, len(w.pages) - 1, style="/D", start=1)
w.add_metadata({"/Title": "Own costs first: a 2027-28 budget submission for Nova Scotia",
                "/Author": "Dan Fakkeldy", "/Subject": "Building Our Budget Together submission"})
w.write(out)
print(f"wrote {out}: {len(w.pages)} pages")
EOF

echo "== headline numbers"
.venv/bin/python build/check_numbers.py

echo "== fonts (TrueType only)"
if pdffonts "$OUT" | awk 'NR>2{print $2,$3}' | grep -v -E "TrueType" | grep -q .; then
  pdffonts "$OUT"; echo "FAIL: non-TrueType font found"; exit 1
fi
echo "PASS: all fonts TrueType"

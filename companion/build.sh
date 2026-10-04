#!/bin/bash
# Build the companion paper PDF from planning-for-ai-2027-28.md.
# Uses pandoc and Google Chrome, with the main book's fonts (../book/fonts/static).
# Run from anywhere: companion/build.sh
set -euo pipefail
cd "$(dirname "$0")"
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
SRC=planning-for-ai-2027-28.md
OUT=planning-for-ai-2027-28.pdf

pandoc "$SRC" -f markdown -t html5 -s --css companion.css \
  --metadata pagetitle="Planning for AI" -o planning-for-ai-2027-28.html

rm -f "$OUT"
"$CHROME" --headless=new --disable-gpu --no-pdf-header-footer --allow-file-access-from-files \
  --print-to-pdf="$PWD/$OUT" "file://$PWD/planning-for-ai-2027-28.html" 2>/dev/null || true
test -s "$OUT"

# Checks: page count, every [n] citation resolves, nothing private leaks into the PDF.
pdfinfo "$OUT" | awk '/^Pages:/{print "pages:", $2}'
python3 - "$SRC" <<'EOF'
import re, sys
t = open(sys.argv[1]).read()
body, src = t.split('\n## Sources', 1)
cited = set(int(m) for m in re.findall(r'\[(\d+)\](?!\()', body))
for a, b in re.findall(r'\[(\d+)\]-\[(\d+)\]', body):
    cited.update(range(int(a), int(b) + 1))
listed = set(int(x) for x in re.findall(r'^(\d+)\. ', src, flags=re.M))
bad = (cited - listed) | (listed - cited)
print("citations:", "PASS" if not bad else f"FAIL {sorted(bad)}")
EOF
if pdftotext "$OUT" - | grep -i -E "/Users/|dfakkeldy|99-other/|codex|foipop request|not sent" >/dev/null || pdftotext "$OUT" - | grep -F "[PENDING]" >/dev/null; then
  echo "leak check: FAIL"; exit 1
else
  echo "leak check: PASS"
fi

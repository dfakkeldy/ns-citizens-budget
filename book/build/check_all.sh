#!/bin/bash
# Run every check on every edition (or the ones named). Exit non-zero if any fails.
#   build/check_all.sh [edition ...]
cd "$(dirname "$0")/.." || exit 2
PY=.venv/bin/python
[ -x "$PY" ] || PY=python3
if [ $# -gt 0 ]; then eds=("$@"); else
  mapfile_eds=$($PY -c 'import sys; sys.path.insert(0, "build"); from common import editions; print(" ".join(editions()))')
  read -r -a eds <<< "$mapfile_eds"
fi
rc=0
for ed in "${eds[@]}"; do
  echo "== $ed"
  $PY build/check_footers.py "$ed" || rc=1
  $PY build/check_integrity.py "$ed" || rc=1
  $PY build/check_source.py "$ed" || rc=1
  $PY build/check_breaks.py "$ed" || rc=1
  $PY build/check_leaks.py "$ed" || rc=1
done
[ $rc -eq 0 ] && echo "ALL CHECKS PASSED" || echo "SOME CHECKS FAILED"
exit $rc

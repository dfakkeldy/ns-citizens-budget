#!/bin/bash
# The committed model outputs must match a fresh run, so numbers in the text can't drift from
# the model. If this fails, rerun the commands below and commit the new outputs.
#   model/check_outputs.sh            (from anywhere)
set -u
cd "$(dirname "$0")" || exit 2
PY="${PY:-python3}"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
rc=0
check() {  # check <committed output> <command...>
  local out="$1"; shift
  if "$@" > "$T/new" 2>&1 && diff -q "$T/new" "$out" >/dev/null; then echo "PASS: $out"
  else echo "FAIL: $out is out of date (rerun: $*)"; diff "$out" "$T/new" | head -20; rc=1; fi
}
check proposals/final-path-output.txt        "$PY" -B path.py proposals/final-measures.json
check proposals/final-debt-check-output.txt  "$PY" -B proposals/final-debt-check.py proposals/final-measures.json
check proposals/plan-b-final-output.txt      "$PY" -B plan_b_final.py
check ../research/plan-b/plan_b.out.txt      bash -c "cd ../research/plan-b && $PY -B plan_b.py"
[ $rc -eq 0 ] && echo "MODEL OUTPUTS CURRENT" || echo "MODEL OUTPUTS OUT OF DATE"
exit $rc

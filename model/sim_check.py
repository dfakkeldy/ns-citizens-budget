"""Check a set of simulator entries against yourbudget.novascotia.ca's own rules.

Reads the simulator's reference data (saved 3 Oct 2026) and a plan file, then
reports each department's dollar change, the simulator deficit, and any rule the
entries would break. All amounts in the reference data are $ thousands.

Rules taken from the simulator's code and text (step 5 and step 6):
- each adjustable department moves at most +/-5% (Health: increase only);
- debt servicing, refundable tax credits and the pension adjustment are locked;
- total department spending must stay at or below the current total;
- within a department, each program's share moves at most +/-5 percentage
  points from its starting share, locked programs keep their share, and the
  shares must add to 100%.

Usage: python3 sim_check.py plan.json
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REF = HERE.parent / "simulator-data-2026-10-03" / "reference.json"


def load(path):
    with open(path) as f:
        return json.load(f)


def money(thousands):
    sign = "-" if thousands < 0 else ""
    return f"{sign}${abs(thousands) / 1000:,.1f}M"


def check(plan, ref):
    problems = []
    depts = {d["deptId"]: d for d in ref["departments"]}
    totals = ref["totals"]
    changes = plan.get("departments", {})

    rows = []
    total_delta = 0.0
    for dept_id, d in sorted(depts.items(), key=lambda kv: -kv[1]["budget"]):
        pct = changes.get(dept_id, 0)
        if d["type"] == "locked":
            if pct:
                problems.append(f"{dept_id} is locked but plan changes it by {pct}%")
            pct = 0
        else:
            lo = -100 * (d["maxCutPct"] or 0)
            hi = 100 * (d["maxIncreasePct"] or 0)
            if not lo - 1e-9 <= pct <= hi + 1e-9:
                problems.append(f"{dept_id}: {pct}% is outside {lo:g}% to +{hi:g}%")
            if pct != int(pct):
                problems.append(f"{dept_id}: {pct}% is not a whole step (the +/- buttons move 1 point)")
        delta = d["budget"] * pct / 100
        total_delta += delta
        rows.append((d["name"], d["budget"], pct, delta))

    for dept_id in changes:
        if dept_id not in depts:
            problems.append(f"unknown department {dept_id}")

    if total_delta > 500:  # the simulator blocks "over" by more than $0.5M
        problems.append(f"department total is {money(total_delta)} above the current budget; the simulator blocks this")

    # Programs: shares within each department.
    progs_by_dept = {}
    for p in ref["programs"]:
        progs_by_dept.setdefault(p["deptId"], []).append(p)
    for dept_id, shares in plan.get("programs", {}).items():
        progs = {p["programId"].split(":", 1)[1]: p for p in progs_by_dept.get(dept_id, [])}
        base_total = sum(p["budget"] for p in progs.values())
        new_total = 0.0
        for key, p in progs.items():
            orig = 100 * p["budget"] / base_total
            new = shares.get(key, orig)
            new_total += new
            if p["locked"] and abs(new - orig) > 1e-6:
                problems.append(f"{dept_id}:{key} is locked")
            if new < max(0.0, orig - 5) - 1e-6 or new > min(100.0, orig + 5) + 1e-6:
                problems.append(f"{dept_id}:{key} share {new:.2f}% is outside {orig - 5:.2f}-{orig + 5:.2f}%")
        for key in shares:
            if key not in progs:
                problems.append(f"unknown program {dept_id}:{key}")
        if abs(new_total - 100) > 0.01:
            problems.append(f"{dept_id} program shares add to {new_total:.2f}%, not 100%")

    deficit = totals["deficitAfterContingency"] - total_delta
    return rows, total_delta, deficit, problems


def main():
    plan = load(sys.argv[1])
    ref = load(REF)
    rows, total_delta, deficit, problems = check(plan, ref)
    print(f"{'Department':58} {'Current':>12} {'Change':>7} {'$ change':>11}")
    for name, budget, pct, delta in rows:
        if pct:
            print(f"{name:58} {money(budget):>12} {pct:>+6g}% {money(delta):>11}")
    print(f"\nTotal department change: {money(total_delta)}")
    print(f"Simulator deficit: {money(ref['totals']['deficitAfterContingency'])} -> {money(deficit)}")
    print("\nRule check: " + ("passes" if not problems else "FAILS"))
    for p in problems:
        print("  - " + p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

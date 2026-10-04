"""Plan B on the reviewed Plan A: the deficit path, the risk case, the debt ratio and the
sensitivities the submission prints.

Plan A comes from path.py on proposals/final-measures.json (after the review).
The Plan B levers come from research/plan-b/plan_b.py (scenario 1, the "Plan B
package"), imported so the two cannot drift apart. Interest on the extra
reductions uses path.py's convention (4.2%, half rate in the first year).

Usage: python3 plan_b_final.py
"""

import importlib.util
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("path", HERE / "path.py")
path = importlib.util.module_from_spec(spec)
spec.loader.exec_module(path)
spec_b = importlib.util.spec_from_file_location("plan_b", HERE.parent / "research" / "plan-b" / "plan_b.py")
plan_b_mod = importlib.util.module_from_spec(spec_b)
spec_b.loader.exec_module(plan_b_mod)

YEARS = path.YEARS
PKG = dict(wage_pts=1.0, phys_pts=1.5, drug_pts=1.0, home_pts=1.0)
NAMES = {
    "Wages: open settlements": "B1 Wage settlements 1 point below plan on open increases (negotiated)",
    "Physician services": "B2 Physician services growth 1.5 points slower (April 2027 agreement)",
    "Drug programs": "B3 Drug programs growth 1 point slower",
    "Home care": "B4 Home care growth 1 point slower",
    "Departments to 5% (ex Municipal Affairs)": "B5 Departments to 5%, learning and trades lines held whole",
}
B5 = "Departments to 5% (ex Municipal Affairs)"


def lever_table(retro=False, phys_share=1.0, with_b5=True, wage_pts=PKG["wage_pts"]):
    lm = plan_b_mod.levers(wage_pts, PKG["phys_pts"], PKG["drug_pts"], PKG["home_pts"], retro)
    lm["Physician services"] = {y: v * phys_share for y, v in lm["Physician services"].items()}
    if not with_b5:
        lm.pop(B5)
    return {NAMES[k]: [v[y] for y in YEARS] for k, v in lm.items()}


LEVERS = lever_table()
RISK_PRESSURES = 235.4  # gross recurring pressures used in the risk case (path.py docstring)


def deficits(levers, plan_a):
    """Plan B deficits, extra interest and net-debt ratios for a lever table."""
    totals = [sum(v[i] for v in levers.values()) for i in range(3)]
    extra_interest, cumulative = [], 0.0
    for i in range(3):
        interest = cumulative * path.INTEREST_RATE + totals[i] * path.INTEREST_RATE / 2
        extra_interest.append(interest)
        cumulative += totals[i] + interest
    plan_b, cum_b, ratios = [], 0.0, []
    for i, y in enumerate(YEARS):
        plan_b.append(plan_a[i]["deficit"] - totals[i] - extra_interest[i])
        cum_b += totals[i] + extra_interest[i]
        ratios.append((plan_a[i]["net_debt"] - cum_b) / path.PLAN[y]["gdp"])
    return totals, extra_interest, plan_b, ratios


def main():
    spec_file = json.loads((HERE / "proposals" / "final-measures.json").read_text())
    plan_a = path.run(spec_file)
    totals, extra_interest, plan_b, ratios = deficits(LEVERS, plan_a)

    def row(label, vals, fmt="{:>10,.1f}"):
        print(f"{label:84}" + "".join(fmt.format(v) for v in vals))

    print(f"{'$ millions, after contingency':84}" + "".join(f"{y:>10}" for y in YEARS))
    row("Government plan (Addendum Table 3.2)", [path.PLAN[y]["deficit"] for y in YEARS])
    row("Plan A (path.py, reviewed measures)", [r["deficit"] for r in plan_a])
    for name, vals in LEVERS.items():
        row("  less " + name, vals)
    row("  less extra interest saved", extra_interest)
    row("Plan B", plan_b)
    row("Plan B net debt-to-GDP (excl. capital pacing)", ratios, "{:>10.1%}")
    # 2027-28 stress: September's gross recurring pressures come back. Protect and additional
    # measures (and Plan B's levers) reduce it; interest at half rate in the first year.
    a0 = plan_a[0]
    cut_a = a0["protect"] + a0["additional"]
    risk_plan = path.PLAN["2027-28"]["deficit"] + RISK_PRESSURES
    risk_a = risk_plan - cut_a - cut_a * path.INTEREST_RATE / 2
    risk_b = risk_a - totals[0] - extra_interest[0]
    print(f"\n2027-28 if this year's overruns recur: plan {risk_plan:,.1f}; with Plan A {risk_a:,.1f}; with Plan B {risk_b:,.1f}")
    print(f"\nPlan B below the government's plan in 2029-30: {path.PLAN['2029-30']['deficit'] - plan_b[-1]:,.1f}"
          f" ({plan_b[-1] / path.PLAN['2029-30']['deficit']:.0%} of the plan's deficit remains)")

    print(f"\n{'Sensitivities (Plan B deficit, $M)':84}" + "".join(f"{y:>10}" for y in YEARS))
    cases = [
        ("Without B5 (no room left under a combined 5%)", lever_table(with_b5=False)),
        ("Physicians share half of B2 back (Alberta 2022 style)", lever_table(phys_share=0.5)),
        ("Open steps from Nov 2025, Aug 2026, Nov 2026 also settle 1 point lower", lever_table(retro=True)),
    ]
    b1 = NAMES["Wages: open settlements"]
    smaller = lever_table()
    smaller[b1] = [v - c for v, c in zip(smaller[b1], (0.0, 0.0, 11.0))]
    cases.append(("B1 base cut for the workforce steps (verifier: up to 11 less in 2029-30)", smaller))
    for label, lv in cases:
        row("  " + label, deficits(lv, plan_a)[2])
    lo, hi = 0.0, 15.0
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if deficits(lever_table(wage_pts=mid), plan_a)[2][-1] > 0 else (lo, mid)
    print(f"  Wage points a year below plan needed for zero in 2029-30 (other levers fixed): {hi:.2f}")

if __name__ == "__main__":
    main()

"""Final plan: net debt, guardrail, balance-year and scale arithmetic that path.py does not cover.

Adapted from p3-debt-check.py with the judges' corrections:
  - capital pacing is about $75M a year (A4), not $200M;
  - deferred projects return after 2029-30 (added back in 2030-31 in the long-run illustration);
  - the balance year uses the plan's own 2028-29 to 2029-30 slope only (no extrapolation of measure growth).

Usage: python3 final-debt-check.py final-measures.json
"""

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("path", HERE.parent / "path.py")
path = importlib.util.module_from_spec(spec)
spec.loader.exec_module(path)
REF = HERE.parent.parent / "simulator-data-2026-10-03" / "reference.json"

YEARS = path.YEARS
CAPITAL_DEFERRED = {"2027-28": 75.0, "2028-29": 75.0, "2029-30": 75.0}  # A4, $M a year
# Addendum Chart 3.4, before contingency: 'With Change' vs 'No Change' (LTC accounting adjustment)
WITH_CHANGE = {"2027-28": 0.427, "2028-29": 0.448, "2029-30": 0.457}
NO_CHANGE = {"2027-28": 0.388, "2028-29": 0.409, "2029-30": 0.419}
NET_TCA_2029_30 = 1204.7  # Budget 2026-27 Table 7.4, increase in net book value of TCA
GDP_GROWTH = path.PLAN["2029-30"]["gdp"] / path.PLAN["2028-29"]["gdp"] - 1  # plan's own 2029-30 nominal growth


def main():
    spec_file = json.loads(Path(sys.argv[1]).read_text())
    rows = path.run(spec_file)
    out, cum = {}, 0.0
    for r in rows:
        y = r["year"]
        gdp = path.PLAN[y]["gdp"]
        cum += CAPITAL_DEFERRED[y]
        nd = r["net_debt"] - cum
        ltc = (WITH_CHANGE[y] - NO_CHANGE[y]) * gdp
        out[y] = dict(plan=r["plan_ratio"], path=r["ratio"], cum=cum, nd=nd, ratio=nd / gdp,
                      gap=nd - 0.40 * gdp, plan_gap=path.PLAN[y]["net_debt"] - 0.40 * gdp,
                      noltc_plan=(path.PLAN[y]["net_debt"] - ltc) / gdp, noltc_this=(nd - ltc) / gdp,
                      deficit=r["deficit"], below=r["plan_deficit"] - r["deficit"])

    def line(label, key, fmt="{:>11.1%}"):
        print(f"{label:46}" + "".join(fmt.format(out[y][key]) for y in YEARS))

    print(f"{'':46}" + "".join(f"{y:>11}" for y in YEARS))
    line("Proposed deficit (path.py)", "deficit", "{:>11,.1f}")
    line("  below plan, incl. interest", "below", "{:>11,.1f}")
    line("Plan net debt-to-GDP (after contingency)", "plan")
    line("With this plan's deficit path (path.py)", "path")
    line("  capital deferred or lapsed (A4), cum. $M", "cum", "{:>11,.0f}")
    line("  net debt with A4, $M", "nd", "{:>11,.0f}")
    line("  net debt-to-GDP with A4", "ratio")
    line("Gap to the 40% guardrail, plan, $M", "plan_gap", "{:>11,.0f}")
    line("Gap to the 40% guardrail, this plan, $M", "gap", "{:>11,.0f}")
    line("Plan, no LTC change, after contingency", "noltc_plan")
    line("This plan + A4, no LTC change", "noltc_this")

    # Balance year on the plan's own slope only
    slope = path.PLAN["2029-30"]["deficit"] - path.PLAN["2028-29"]["deficit"]
    d = out["2029-30"]["deficit"]
    year, start = d, 2029
    print(f"\nPlan's own slope 2028-29 to 2029-30: {slope:,.1f} a year (illustrative straight line, not a forecast).")
    while d > 0:
        start += 1
        d += slope
        print(f"  {start}-{str(start + 1)[2:]}: {d:,.1f}")
    print(f"First year at or below balance on that line: {start}-{str(start + 1)[2:]}.")
    d_plan, s2 = path.PLAN["2029-30"]["deficit"], 2029
    while d_plan > 0:
        s2 += 1
        d_plan += slope
    print(f"On the plan alone, same line: {s2}-{str(s2 + 1)[2:]}.")

    # Long-run guardrail illustration
    print(f"\nGuardrail illustration: nominal GDP +{GDP_GROWTH:.1%} a year (plan's 2029-30 rate); deficit falls "
          f"{-slope:,.1f} a year to zero, then zero; deferred capital (${out['2029-30']['cum']:,.0f}M) returns in 2030-31.")
    for cap in (NET_TCA_2029_30, 600.0):
        nd, gdp, dd, y0 = out["2029-30"]["nd"], path.PLAN["2029-30"]["gdp"], out["2029-30"]["deficit"], 2029
        while True:
            y0 += 1
            dd = max(0.0, dd + slope)
            gdp *= 1 + GDP_GROWTH
            nd += dd + cap + (out["2029-30"]["cum"] if y0 == 2030 else 0)
            if nd / gdp < 0.40 or y0 > 2060:
                break
        print(f"  net capital ${cap:,.1f}M a year: under 40% first in {y0}-{str(y0 + 1)[2:]} ({nd / gdp:.1%})")

    # Scale of balance in 2027-28 against the simulator's non-protected departments
    ref = json.loads(REF.read_text())
    nonprot = [d_ for d_ in ref["departments"] if d_["type"] not in ("protected", "locked")]
    tot = sum(d_["budget"] for d_ in nonprot) / 1000
    maxcut = sum(d_["budget"] * (d_["maxCutPct"] or 0) for d_ in ref["departments"] if d_["type"] != "locked") / 1000
    d27 = out["2027-28"]["deficit"]
    print(f"\nBalancing 2027-28 needs ${d27:,.1f}M more: {d27 / tot:.0%} of the ${tot:,.1f}M in the {len(nonprot)} "
          f"simulator departments not labelled protected or locked; {d27 / maxcut:.1f}x the simulator's maximum cut (${maxcut:,.1f}M).")
    d30 = out["2029-30"]["deficit"]
    print(f"Balancing 2029-30 needs ${d30:,.1f}M more = {d30 / 18634.9:.1%} of 2029-30 departmental expenses ($18,634.9M).")


if __name__ == "__main__":
    main()

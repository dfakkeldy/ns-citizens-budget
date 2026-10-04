"""Deficit path for the proposed budget, compared with the government's plan.

Baseline: the four-year fiscal plan as passed (Budget 2026-27 Addendum,
Table 3.2, after contingency). The plan already counts on unallocated
"Fiscal Stability Plan" reductions (Addendum Table 3.1), so measures are
scored in four columns:

  booked      names savings the plan already counts on; no change to the
              published deficit, but less risk that it slips
  protect     stops overruns above the plan (e.g. the September 2026
              forecast pressures); scored against the risk case, not the plan
  additional  lowers the deficit below the published plan
  growth      revenue from faster growth, net of the equalization offset

Interest: every dollar of deficit avoided is a dollar not borrowed. Saved
interest is applied at INTEREST_RATE on the cumulative reduction, at half
rate in the year the reduction first occurs (mid-year borrowing).

Usage: python3 path.py measures.json
"""

import json
import sys

YEARS = ["2027-28", "2028-29", "2029-30"]

# Budget 2026-27 Addendum, Table 3.2 ($ millions). Deficits are after contingency.
PLAN = {
    "2026-27": {"deficit": 1294.5, "net_debt": 28048, "gdp": 70945},
    "2027-28": {"deficit": 1148.8, "net_debt": 31511, "gdp": 73603},
    "2028-29": {"deficit": 1052.1, "net_debt": 34255, "gdp": 76129},
    "2029-30": {"deficit": 861.7, "net_debt": 36321, "gdp": 79018},
}
FSP_TARGET = {"2027-28": 590.0, "2028-29": 724.5, "2029-30": 882.0}  # Addendum Table 3.1
SEPT_FORECAST_2026_27 = 1490.3  # Forecast Update Sept 2026, after contingency
GUARDRAIL = 0.40  # Budget 2026-27, p. 9: "Net Debt-to-GDP less than 40 percent"

INTEREST_RATE = 0.042  # central; research range 3.9-4.6% on new borrowing


def load(path):
    with open(path) as f:
        return json.load(f)


def column_totals(measures, column):
    return {y: sum(m.get(y, 0) for m in measures if m["column"] == column) for y in YEARS}


def run(spec):
    measures = spec["measures"]
    risk = spec.get("risk_pressures", {})  # extra cost above plan if nothing is done
    booked = column_totals(measures, "booked")
    protect = column_totals(measures, "protect")
    additional = column_totals(measures, "additional")
    growth = column_totals(measures, "growth")

    rows = []
    cumulative = 0.0  # borrowing avoided up to the end of the previous year
    for y in YEARS:
        reduction = additional[y] + growth[y]
        # Full-year interest on debt avoided in earlier years, half-year on this year's.
        interest = cumulative * INTEREST_RATE + reduction * INTEREST_RATE / 2
        deficit = PLAN[y]["deficit"] - reduction - interest
        cumulative += reduction + interest
        net_debt = PLAN[y]["net_debt"] - cumulative
        rows.append({
            "year": y,
            "plan_deficit": PLAN[y]["deficit"],
            "risk_deficit": PLAN[y]["deficit"] + risk.get(y, 0),
            "booked": booked[y],
            "fsp_target": FSP_TARGET[y],
            "protect": protect[y],
            "additional": additional[y],
            "growth": growth[y],
            "interest_saved": interest,
            "reduction": reduction,
            "deficit": deficit,
            "net_debt": net_debt,
            "ratio": net_debt / PLAN[y]["gdp"],
            "plan_ratio": PLAN[y]["net_debt"] / PLAN[y]["gdp"],
        })
    return rows


def main():
    spec = load(sys.argv[1])
    rows = run(spec)
    print(f"Interest rate on avoided borrowing: {INTEREST_RATE:.1%} (half rate in first year)\n")
    head = f"{'':34}" + "".join(f"{r['year']:>11}" for r in rows)
    print(head)

    def line(label, key, fmt="{:>11,.1f}"):
        print(f"{label:34}" + "".join(fmt.format(r[key]) for r in rows))

    line("Plan deficit (Addendum)", "plan_deficit")
    line("Risk case if overruns persist", "risk_deficit")
    line("FSP target already in plan", "fsp_target")
    line("  named by this plan (booked)", "booked")
    line("Overruns prevented (protect)", "protect")
    line("Additional savings", "additional")
    line("Growth revenue (net)", "growth")
    line("Interest saved", "interest_saved")
    line("Proposed deficit", "deficit")
    line("Plan net debt-to-GDP", "plan_ratio", "{:>11.1%}")
    line("Proposed net debt-to-GDP", "ratio", "{:>11.1%}")
    print(f"\nGuardrail: under {GUARDRAIL:.0%}. Sept 2026 forecast for 2026-27: ${SEPT_FORECAST_2026_27:,.1f}M.")


if __name__ == "__main__":
    main()

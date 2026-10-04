"""Plan B: the least painful path toward balance by 2029-30 without raising taxes.

Plan B is built on top of Plan A (the submission's main proposal). It adds
three levers the user accepted, with the user's guardrails:

  1. Wages: public-sector settlements below the plan's (unpublished) wage
     assumption, NEGOTIATED, never legislated (Bill 148 was struck down on
     27 Feb 2026). Only increases that are still open count. The civil
     service's 2.0% on 1 April 2027 is fixed by its agreement (Art. 38.01,
     term to 31 Mar 2028) and is not touched.
  2. Health "rules": slower growth in physician services, drug programs and
     home care through payment, formulary and assessment rules. NOT service
     cuts, NOT premium or co-pay increases. Health-authority (NSH, IWK) staff
     pay is in lever 1 only, so lever 2 covers non-compensation lines only.
     Health-authority operations are left out because Plan A's health
     measures (P1-P5) already work there.
  3. Departments: up to 5% on the consultation tool's non-protected
     departments, EXCLUDING Municipal Affairs, with Plan A's protections and a
     few more held whole (listed in PROTECTED below). No line is cut by more
     than 5%. Only the part beyond what Plan A already takes is counted.

No tax or fee increases. Front-line services protected.

Method
- Plan A deficits come from model/path.py run on Plan A's measures file,
  model/proposals/final-measures.json (after the review moved three items to
  $0): 1,150.2 / 1,050.4 / 855.7. The first draft's file
  (final-measures-pre-codex.json, 1,129.3 / 1,019.9 / 815.7) is printed for
  reference only.
- Plan B levers are added to Plan A's measures as "additional" items and
  the combined spec is run through path.run(), so interest saved follows
  path.py exactly (4.2%, half rate in the first year, on cumulative
  reductions). path.py is imported, never modified; bytecode writing is
  switched off so nothing is written into model/.
- Every lever is measured against the plan's own assumptions. "1 point"
  means one percentage point a year below whatever the plan assumes.
  The plan publishes no wage assumption and no department-level health
  growth, so these are levers on an unknown baseline (see caveats).
- Bases grow with the plan's own departmental spending before Fiscal
  Stability Plan reductions (Addendum Tables 3.1 + 3.2):
  18,096.6 (2026-27), 18,405.0, 18,962.4, 18,634.9 + 882.0 = 19,516.9.
  2025-26 audited payroll bases are treated as 2026-27 levels (conservative).

Sources (local copies; URLs in the submission text):
  The local text copies named below are not published in this repository, for copyright
  reasons. Every document is in the bibliography, book/src/chapters/99-sources.md, with its
  URL and page. Line numbers refer to `pdftotext -layout` output of each document.
  Addendum Tables 3.1, 3.2 ......... sources/budget-addendum-2026-27.txt lines 153-159, 247-273
  Estimates 2026-27 ................. sources/budget-estimates-2026-27-en.txt lines 4104-4106 (physicians
                                      1,446,431; pharma 452,494), 8187 (home care 443,270), 5758 (Fleet and
                                      Forest Protection 21,146), 5761 (Enforcement 7,037), 8722 (rebates),
                                      2112 (Cyber Security and Enterprise Risk 17,375)
  Forecast Update Sept 2026 ......... sources/forecast-update-september-2026.txt lines 678-681, 750-752
  Public Accounts 2025-26 Vol 1 ..... sources/r5-public-accounts-2025-26-vol1-financial-statements.txt line 5240
  NSH 2025-26 statements ............ sources/r3-pa-2025-26-nova-scotia-health-authority-fs.txt lines 1458, 1535
  IWK 2025-26 statements ............ sources/r3-pa-2025-26-iwk-fs.txt lines 1376, 1599
  Teachers' Pension Plan 2025 AR .... research/plan-b/design-sources/tpp-2025-annual-report.pdf printed p.4
  Teachers' Provincial Agreement .... research/plan-b/sources/nstu-tpa-2023-2026.txt line 3666 (art. 73.01)
  Civil Service Agreement ........... sources/r5-nsgeu-civil-service-agreement-2024-2028.txt lines 4352-4389
  Physician Agreement 2023-27 ....... research/codex-review-2026-10-03/cx-ns-physician-agreement.txt lines 168-182
  Simulator reference data .......... simulator-data-2026-10-03/reference.json

Usage: python3 plan_b.py
"""

import copy
import json
import sys
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True  # never write model/__pycache__

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]  # .../05-budget-2027-28
MODEL = ROOT / "model"
sys.path.insert(0, str(MODEL))
import path as pathmod  # noqa: E402  (model/path.py, read-only)

YEARS = pathmod.YEARS  # ["2027-28", "2028-29", "2029-30"]
FY_START = {"2027-28": date(2027, 4, 1), "2028-29": date(2028, 4, 1), "2029-30": date(2029, 4, 1)}

PLAN_A_PRE_REVIEW = MODEL / "proposals" / "final-measures-pre-codex.json"  # the first text draft
PLAN_A_REVIEWED = MODEL / "proposals" / "final-measures.json"             # after the review
PLAN_A_FILE = PLAN_A_REVIEWED                                               # what the submission uses
REFERENCE = ROOT / "simulator-data-2026-10-03" / "reference.json"

# ---------------------------------------------------------------- growth index
# Addendum Table 3.2 departmental expenses + Table 3.1 FSP target = spending before FSP.
DEPT_BEFORE_FSP = {
    "2026-27": 17824.0 + 272.6,
    "2027-28": 17815.0 + 590.0,
    "2028-29": 18237.9 + 724.5,
    "2029-30": 18634.9 + 882.0,
}
IDX = {y: DEPT_BEFORE_FSP[y] / DEPT_BEFORE_FSP["2026-27"] for y in YEARS}

# ---------------------------------------------------------------- lever 1: wages
# Payroll whose increases are still open, with the dates increases take effect.
NSH_IWK = 2917.0 + 357.3        # NSH "Compensation" + IWK "Compensation and benefits", 2025-26
TEACHERS = 14283 * 90010 / 1e6  # TPP active members x average pensionable earnings, 31 Dec 2025
CIVIL_SERVICE = 1292.7          # sum of departmental "Salary and Employee Benefits", 2026-27 est.

WAGE_GROUPS = [
    # name, base $M, step dates (one negotiated increase a year), first date already open
    ("NSH and IWK staff (agreements expired 31 Oct 2025)", NSH_IWK,
     [date(2025, 11, 1), date(2026, 11, 1), date(2027, 11, 1), date(2028, 11, 1), date(2029, 11, 1)]),
    ("Teachers (agreement expired 31 Aug 2026)", TEACHERS,
     [date(2026, 8, 1), date(2027, 8, 1), date(2028, 8, 1), date(2029, 8, 1)]),
    ("Civil service (2.0% on 1 Apr 2027 fixed; open from 1 Apr 2028)", CIVIL_SERVICE,
     [date(2028, 4, 1), date(2029, 4, 1)]),
]


def step_weight(step, year):
    """Share of fiscal year `year` that an increase effective on `step` is in force."""
    start = FY_START[year]
    end = date(start.year + 1, 4, 1)
    if step <= start:
        return 1.0
    if step >= end:
        return 0.0
    months = (end.year - step.year) * 12 + (end.month - step.month)
    return months / 12


def wage_saving(points, include_retro=False):
    """$M saved each year if every open increase settles `points` below the plan's assumption.

    Default counts only increases effective on or after 1 April 2027 (Plan B is a
    2027-28 proposal; earlier steps belong to 2026-27 provisions). include_retro
    also counts the already-open Nov 2025, Aug 2026 and Nov 2026 steps (their
    2026-27 retroactive saving is still not counted).
    """
    cutoff = date(2025, 1, 1) if include_retro else date(2027, 4, 1)
    out = {}
    for y in YEARS:
        total = 0.0
        for _, base, steps in WAGE_GROUPS:
            w = sum(step_weight(s, y) for s in steps if s >= cutoff)
            total += base * IDX[y] * points / 100 * w
        out[y] = total
    return out


# ---------------------------------------------------------------- lever 2: health rules
# Sept 2026 forecast basis = 2026-27 estimate + forecast variance.
PHYSICIANS = 1446.4 + 46.7   # Physician Services est. + APP/AFP utilization (Forecast Update)
DRUGS = 452.5 + 30.8         # Pharmaceutical Services and Extended Benefits + Seniors' Pharmacare growth
HOME_CARE = 443.3 + 51.2 + 8.8  # Home Care est. + Home Support Direct Funding + home support (assumes
                                # Direct Funding sits in Home Care; see lever-data.md (e))


def growth_saving(base, points):
    """$M saved if growth runs `points` a year below plan from 2027-28 (additive, so slightly conservative)."""
    return {y: base * IDX[y] * points / 100 * (i + 1) for i, y in enumerate(YEARS)}


# ---------------------------------------------------------------- lever 3: departments
PLAN_A_SIM = {"publicservice": -3, "finance": -2, "servicens": -2, "cyber": -3, "growthdev": -1, "energy": -5}
# Program lines held whole in Plan B ($M; None = whole simulator line).
PROTECTED = {
    "growthdev:housing": None, "growthdev:publichousing": None,             # Plan A: housing protected
    "growthdev:jobsfund": None,                                             # signed legacy contracts honoured
    "ccth:arts": None, "ccth:film": None, "ccth:libraries": None, "ccth:heritage": None,
    "ccth:artgallery": None, "ccth:acadianaffairs": None, "ccth:ansaffairs": None,
    "ccth:gaelicaffairs": None,                                             # no further arts/culture cuts
    "publicservice:auditorgeneral": None, "publicservice:elections": None, "publicservice:foipop": None,
    "publicservice:humanrights": None, "publicservice:ombudsman": None,
    "publicservice:policecomplaints": None, "publicservice:prosecution": None,  # independent officers
    "servicens:citizenservices": None,                                      # Access NS counters
    "servicens:programmodernization": None,                                 # holds seniors' property tax and
                                                                            # heating rebates (not split out)
    "advanced:studentassistance": None,                                     # need-based student aid
    "advanced:grantsuniversities": None, "labour:nscc": None,              # teaching grants: Plan A's broader-
                                                                            # sector 3% already works there (B2),
                                                                            # and no source rules out tuition rises
    "labour:apprenticeship": None, "labour:skillslearning": None,          # trades training (Plan A protects
                                                                            # the trades that finish homes)
    "labour:safety": None, "environment:compliance": None,                  # inspection and enforcement
    "naturalres:regional": 21.146 + 7.037,                                  # wildfire protection + enforcement
    "cyber:cybersecuritytech": 17.375,                                      # Cyber Security and Enterprise Risk
                                                                            # unit (Plan A leaves it untouched)
}
DEPT_PHASE = {"2027-28": 0.6, "2028-29": 1.0, "2029-30": 1.0}  # operations by attrition over two years


def department_lever():
    ref = json.loads(REFERENCE.read_text())
    progs = {p["programId"]: p["budget"] / 1000 for p in ref["programs"]}
    rows = []
    for d in ref["departments"]:
        did = d["deptId"]
        if d["type"] not in ("discretionary", "coreops") or did == "municipal":
            continue
        base = d["budget"] / 1000
        held = sum(v if v is not None else progs[k] for k, v in PROTECTED.items() if k.startswith(did + ":"))
        five = 0.05 * (base - held)
        plan_a = -PLAN_A_SIM.get(did, 0) / 100 * base
        rows.append((d["name"], base, held, five, plan_a, max(0.0, five - plan_a)))
    return rows


def sim_max_cut():
    ref = json.loads(REFERENCE.read_text())
    tot = prot = 0.0
    for d in ref["departments"]:
        if d["type"] == "locked" or d["deptId"] == "health":
            continue
        c = d["budget"] * d["maxCutPct"] / 1000
        tot += c
        prot += c if d["type"] == "protected" else 0
    return tot, prot, -ref["totals"]["deficitAfterContingency"] / 1000


# ---------------------------------------------------------------- scenarios
def levers(wage_pts, phys_pts, drug_pts, home_pts, retro=False):
    extra = sum(r[5] for r in department_lever())
    return {
        "Wages: open settlements": wage_saving(wage_pts, retro),
        "Physician services": growth_saving(PHYSICIANS, phys_pts),
        "Drug programs": growth_saving(DRUGS, drug_pts),
        "Home care": growth_saving(HOME_CARE, home_pts),
        "Departments to 5% (ex Municipal Affairs)": {y: extra * IDX[y] * DEPT_PHASE[y] for y in YEARS},
    }


def run_path(plan_a_file, lever_map):
    spec = json.loads(Path(plan_a_file).read_text())
    spec = copy.deepcopy(spec)
    for name, vals in lever_map.items():
        spec["measures"].append({"id": "PB-" + name, "column": "additional", **{y: vals[y] for y in YEARS}})
    return pathmod.run(spec)


def plan_a(plan_a_file):
    return pathmod.run(json.loads(Path(plan_a_file).read_text()))


def solve_wage_points(plan_a_file, phys, drug, home, retro=False, target=0.0):
    lo, hi = 0.0, 15.0
    for _ in range(80):
        mid = (lo + hi) / 2
        d = run_path(plan_a_file, levers(mid, phys, drug, home, retro))[-1]["deficit"]
        lo, hi = (mid, hi) if d > target else (lo, mid)
    return hi


def fmt_row(label, vals, width=50, f="{:>10,.1f}"):
    return f"{label:{width}}" + "".join(f.format(v) for v in vals)


def show_scenario(title, plan_a_file, wage, phys, drug, home, retro=False):
    base = plan_a(plan_a_file)
    lm = levers(wage, phys, drug, home, retro)
    rows = run_path(plan_a_file, lm)
    print(f"\n{title}")
    print(f"{'$ millions':50}" + "".join(f"{y:>10}" for y in YEARS))
    print(fmt_row("Government plan (Addendum Table 3.2)", [r["plan_deficit"] for r in rows]))
    print(fmt_row("Plan A deficit", [r["deficit"] for r in base]))
    for name, vals in lm.items():
        print(fmt_row("  less " + name, [vals[y] for y in YEARS]))
    lev_tot = [sum(v[y] for v in lm.values()) for y in YEARS]
    print(fmt_row("  Plan B levers, total", lev_tot))
    extra_int = [b["interest_saved"] - a["interest_saved"] for a, b in zip(base, rows)]
    print(fmt_row("  less extra interest saved (path.py method)", extra_int))
    print(fmt_row("Plan B deficit", [r["deficit"] for r in rows]))
    print(fmt_row("Plan B net debt-to-GDP", [r["ratio"] for r in rows], f="{:>10.1%}"))
    return rows, lm


def main():
    print("PLAN B: balance by 2029-30 without raising taxes (built on Plan A)")
    print(f"Interest on avoided borrowing: {pathmod.INTEREST_RATE:.1%}, half rate in the first year (model/path.py)")
    print("Growth index for lever bases (plan's departmental spending before FSP): "
          + ", ".join(f"{y} {IDX[y]:.3f}" for y in YEARS))

    # ---- bases
    print("\nLever bases ($M)")
    print(f"  NSH + IWK compensation 2025-26 ............ {NSH_IWK:8.1f}")
    print(f"  Teachers' salaries (TPP, derived) .......... {TEACHERS:8.1f}")
    print(f"  Civil service salary line 2026-27 .......... {CIVIL_SERVICE:8.1f}  (2.0% on 1 Apr 2027 = {CIVIL_SERVICE*0.02:.1f}, fixed)")
    print(f"  Physician services (Sept-forecast basis) ... {PHYSICIANS:8.1f}")
    print(f"  Drug programs (Sept-forecast basis) ........ {DRUGS:8.1f}")
    print(f"  Home care (Sept-forecast basis) ............ {HOME_CARE:8.1f}")
    w1 = wage_saving(1.0)
    w1r = wage_saving(1.0, include_retro=True)
    print("  1 point on open wage settlements, default calendar: "
          + ", ".join(f"{y} {w1[y]:.1f}" for y in YEARS))
    print("  1 point incl. already-open Nov 2025/Aug 2026/Nov 2026 steps: "
          + ", ".join(f"{y} {w1r[y]:.1f}" for y in YEARS))

    # ---- departments
    print("\nLever 3: 5% of each non-protected department's unprotected lines, less what Plan A takes ($M, 2026-27 base)")
    print(f"  {'Department':42}{'base':>8}{'held':>8}{'5% rest':>9}{'Plan A':>8}{'extra':>8}")
    rows = department_lever()
    for name, base, held, five, pa, extra in rows:
        print(f"  {name[:42]:42}{base:8.1f}{held:8.1f}{five:9.2f}{pa:8.2f}{extra:8.2f}")
    t = [sum(r[i] for r in rows) for i in range(1, 6)]
    print(f"  {'13 departments':42}{t[0]:8.1f}{t[1]:8.1f}{t[2]:9.2f}{t[3]:8.2f}{t[4]:8.2f}")
    print("  Held whole as learning and trades lines: university grants 460.9, NSCC 196.4, "
          "Apprenticeship Agency 50.0, Skills and Learning 131.3")
    mx, mxp, simdef = sim_max_cut()
    print(f"\nConsultation tool: every allowed 5% cut = {mx:.1f} ({mxp / mx:.0%} in 'protected' departments); "
          f"tool deficit {simdef:,.1f} -> {simdef - mx:,.1f}")

    # ---- Plan A
    ar = plan_a(PLAN_A_REVIEWED)
    first = ""
    if PLAN_A_PRE_REVIEW.exists():   # the first-draft measures are kept privately, not published
        a = plan_a(PLAN_A_PRE_REVIEW)
        first = "; first draft (pre-review measures, reference only) " + " / ".join(f"{r['deficit']:,.1f}" for r in a)
    print("\nPlan A deficits: reviewed model (final-measures.json, used throughout) "
          + " / ".join(f"{r['deficit']:,.1f}" for r in ar) + first)

    # ---- scenario 1: Plan B package (top of the Canadian negotiated record)
    PKG = dict(wage=1.0, phys=1.5, drug=1.0, home=1.0)
    rows_b, lm = show_scenario(
        "SCENARIO 1 - PLAN B PACKAGE (top of the Canadian negotiated record): wages 1 pt below plan on every open "
        "increase from 1 Apr 2027; physicians 1.5 pts; drugs 1 pt; home care 1 pt; departments to 5%",
        PLAN_A_FILE, PKG["wage"], PKG["phys"], PKG["drug"], PKG["home"])

    # ---- scenario 2: precedent-sized floor
    show_scenario(
        "SCENARIO 2 - PRECEDENT-SIZED FLOOR: wages 0.55 pt (BC 2014 mandate ~1.45%/yr incl. dividends vs 2%/yr); "
        "physicians 1 pt (Alberta 2022: 1%/yr); drugs 1; home care 1; departments to 5%",
        PLAN_A_FILE, 0.55, 1.0, 1.0, 1.0)

    # ---- scenario 3: what reaching zero would take
    x0 = solve_wage_points(PLAN_A_FILE, PKG["phys"], PKG["drug"], PKG["home"])
    show_scenario(
        f"SCENARIO 3 - TO ZERO IN 2029-30: Plan B package with wages solved = {x0:.2f} pts below plan every open year",
        PLAN_A_FILE, x0, PKG["phys"], PKG["drug"], PKG["home"])

    # ---- sensitivities
    print("\nSensitivities (2029-30 deficit, $M)")
    for label, f, wage, retro in [
        ("Plan B package, retro steps counted (Nov 2025, Aug 2026, Nov 2026)", PLAN_A_FILE, 1.0, True),
        ("Plan B package on the first-draft Plan A (815.7 start, reference only)", PLAN_A_PRE_REVIEW, 1.0, False),
    ]:
        if not Path(f).exists():
            continue
        d = run_path(f, levers(wage, PKG["phys"], PKG["drug"], PKG["home"], retro))[-1]["deficit"]
        print(f"  {label:78}{d:10,.1f}")
    xr = solve_wage_points(PLAN_A_FILE, PKG["phys"], PKG["drug"], PKG["home"], retro=True)
    print(f"  Wage points needed for zero, retro steps counted ............................ {xr:10.2f}")
    # health-only and departments-only cannot do it
    phys_needed = None
    lo, hi = 0.0, 40.0
    for _ in range(80):
        mid = (lo + hi) / 2
        d = run_path(PLAN_A_FILE, levers(PKG["wage"], mid, mid, mid))[-1]["deficit"]
        lo, hi = (mid, hi) if d > 0 else (lo, mid)
    phys_needed = hi
    print(f"  Health points needed for zero (all three health lines, wages at 1 pt) ......... {phys_needed:10.2f}")

    # ---- risk case and the residual
    resid = rows_b[-1]["deficit"]
    protect_a = {y: sum(m.get(y, 0) for m in json.loads(PLAN_A_FILE.read_text())["measures"]
                        if m["column"] == "protect") for y in YEARS}
    risk = json.loads(PLAN_A_FILE.read_text())["risk_pressures"]
    print("\nIf this year's overruns recur (risk case = plan + "
          f"{risk['2029-30']:.1f}/yr, less Plan A's 'protect' measures):")
    print("  Plan B package deficit in risk case: "
          + " / ".join(f"{r['deficit'] + risk[y] - protect_a[y]:,.1f}" for r, y in zip(rows_b, YEARS)))
    print("\nNot modelled: the Bill 148 remedy (Premier: 'at least $300 million', 'not in the budget'); "
          "whether any part recurs is unverified. It would add to every column above.")

    # ---- illustration: balance year on the plan's own slope
    slope = rows_b[-2]["plan_deficit"] - rows_b[-1]["plan_deficit"]
    d = resid
    year = 2029
    while d > 0 and year < 2040:
        year += 1
        d -= slope
    print(f"\nIllustration only: Plan B package residual in 2029-30 = {resid:,.1f}. If it then fell by the plan's "
          f"own 2028-29 to 2029-30 slope ({slope:,.1f}/yr) with Plan B savings held flat, the first year at or "
          f"below zero would be {year}-{str(year + 1)[2:]}.")
    print(f"Closing the 2029-30 residual instead would need about {resid:,.0f} more of cuts beyond the three "
          f"levers ({resid / DEPT_BEFORE_FSP['2029-30']:.1%} of 2029-30 departmental spending before FSP).")


if __name__ == "__main__":
    main()

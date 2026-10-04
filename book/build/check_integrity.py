#!/usr/bin/env python3
"""Check that pagination kept every word, once, in order.

Compares the words of the flow (before layout) with the words placed in the
page bodies (after layout), ignoring page chrome and filled-in page numbers.
    .venv/bin/python build/check_integrity.py <edition>
"""
import difflib, os, re, sys
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import out_path  # noqa: E402


def words(nodes):
    out = []
    for n in nodes:
        for el in n.select(".toc-n, .gl-pg, svg, script, style"):
            el.decompose()
        out.extend(re.findall(r"\S+", n.get_text(" ")))
    return out


def main(ed):
    flow = BeautifulSoup(open(out_path(ed, "flow.html")).read(), "html.parser")
    paged = BeautifulSoup(open(out_path(ed, "paged.html")).read(), "html.parser")
    fl = flow.select_one("#flow")
    for el in fl.select(".rh-set"):
        el.decompose()
    a = words([fl])
    for th in paged.select("table.cont > thead"):   # header rows repeated on continuation pages
        th.decompose()
    b = words(paged.select("section.page .pb"))
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    bad = [op for op in sm.get_opcodes() if op[0] != "equal"]
    print(f"[{ed}] words before layout: {len(a)}, after: {len(b)}")
    if not bad:
        print(f"[{ed}] PASS: every word placed exactly once, in order.")
        return 0
    print(f"[{ed}] FAIL: {len(bad)} differences")
    for tag, i1, i2, j1, j2 in bad[:20]:
        print(f"  {tag}: before «{' '.join(a[max(0, i1 - 5):i2 + 5])}» after «{' '.join(b[max(0, j1 - 5):j2 + 5])}»")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))

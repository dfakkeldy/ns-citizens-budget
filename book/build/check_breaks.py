#!/usr/bin/env python3
"""Report bad page breaks: pages that end on a heading, a card header or a
lead-in (text ending with ':'), stranded away from what it introduces;
near-empty pages; and pages where the body overflowed into the footer.
    .venv/bin/python build/check_breaks.py <edition>
Also fails pages that end in a split block yet leave too much free space above the footer
(the split was made too early): over about 1.5 lines after a paragraph split, about 4 lines
after a list or table split. Lines the paginator moved over to avoid a widow (data-held, in px)
are added to the allowance.
Stranded lead-ins, early splits and overflow fail; near-empty pages are reported only.
"""
import json, os, re, sys
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import out_path  # noqa: E402

STRANDED_CLASSES = {"chapter-head", "sec-head", "sec-h", "card-wrap", "list-lead"}
EARLY_SPLIT_PX = 90   # about four lines (15.33px at 1.47 line height): lists and tables split only
                      # between items or rows, and a short item that brings a new footer term may not fit
EARLY_TEXT_SPLIT_PX = 34   # about one and a half lines: a paragraph split between lines


def main(ed):
    s = BeautifulSoup(open(out_path(ed, "paged.html")).read(), "html.parser")
    pagemap = json.load(open(out_path(ed, "pagemap.json")))
    bad, sparse, early = [], [], []
    pages = s.select("section.page")
    for pg in pages:
        pb = pg.select_one(".pb")
        blocks = [b for b in pb.children if getattr(b, "name", None)]
        if not blocks or "fullpage" in pg.get("class", []):
            continue
        words = len(pb.get_text(" ").split())
        if words < 60 and not pg.select(".chapter-head, .sec-head, figure"):
            sparse.append((pg["data-n"], words))
        if pg is pages[-1]:
            continue
        last = blocks[-1]
        split_end = last.get("data-split") or last.select_one("[data-split]")
        text_split = last.get("data-textsplit") or last.select_one("[data-textsplit]")
        limit = EARLY_TEXT_SPLIT_PX if text_split else EARLY_SPLIT_PX
        held = last if last.get("data-held") else last.select_one("[data-held]")
        if held:
            limit += int(held["data-held"])
        if split_end and int(pg.get("data-free", "0")) > limit:
            early.append((pg["data-n"], int(pg["data-free"])))
        t = re.sub(r"\s+", " ", last.get_text(" ", strip=True))
        cls = set(last.get("class", []))
        if cls & STRANDED_CLASSES or last.name in ("h1", "h2", "h3", "h4", "h5") or t.endswith(":"):
            bad.append((pg["data-n"], t[-90:]))
    if early:
        print(f"[{ed}] pages split too early (too much free space above the footer): "
              + ", ".join(f"p.{n} ({px}px free)" for n, px in early))
    over = pagemap.get("overflow") or []
    print(f"[{ed}] pages ending on a stranded heading or lead-in: {len(bad)}; body overflowing the footer: {len(over)}")
    for n, t in bad:
        print(f"  page {n}: …{t}")
    if over:
        print(f"  overflow on pages: {', '.join(map(str, over))} (a block too tall for any page: split it or mark it smaller)")
    if sparse:
        print(f"[{ed}] note: nearly empty pages (under 60 words): " + ", ".join(f"p.{n} ({w})" for n, w in sparse))
    return 1 if bad or over or early else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))

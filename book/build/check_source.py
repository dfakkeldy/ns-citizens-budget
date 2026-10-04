#!/usr/bin/env python3
"""Check that every block of source text made it into the book.

Loads each chapter of the edition exactly as the build does, takes every
paragraph, list item, table cell and heading (and the side-head labels and
card titles that live in attributes), and confirms its text
(whitespace ignored) appears in the assembled flow. Catches text the build
silently drops (an unhandled wrapper, a skipped element), which the
pagination check can't see because the text is gone before layout starts.
    .venv/bin/python build/check_source.py <edition>
"""
import os, re, sys
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import CARDS, chapter_files, editions, load_chapter, out_path  # noqa: E402


def squash(t):
    return re.sub(r"\s+", "", t.replace(" ", " "))


def leaf_texts(soup):
    out = []
    for el in soup.find_all(["p", "li", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6", "figcaption", "dt", "dd"]):
        if el.name == "li" and el.find(["ul", "ol", "p", "div"]):
            continue          # its parts are checked separately
        t = el.get_text(" ").strip()
        if len(t) >= 3:
            out.append(t)
    return out


def attr_texts(soup, ed):
    """Text that lives in attributes: side-head labels and card titles."""
    out = []
    for d in soup.find_all(["div", "section"]):
        cls = d.get("class", [])
        label = d.get("data-label") or d.get("label")
        if label and ("rail" in cls or "source" in cls or "note" in cls or "careful" in cls):
            out.append(label)
        code = d.get("data-code") or d.get("code")
        if "card" in cls and code in CARDS:
            out.append(CARDS[code].get("title_" + ed, CARDS[code].get("title", "")))
    return [t for t in out if len(t) >= 3]


def main(ed):
    cfg = editions()[ed]
    flow = BeautifulSoup(open(out_path(ed, "flow.html")).read(), "html.parser").select_one("#flow")
    ftxt = squash(flow.get_text(""))
    blocks = []
    for path in chapter_files(cfg):
        _, soup = load_chapter(path, ed)
        blocks += [(os.path.basename(path), t) for t in leaf_texts(soup) + attr_texts(soup, ed)]
    missing = [(src, t) for src, t in blocks if squash(t) not in ftxt]
    print(f"[{ed}] source blocks: {len(blocks)}, missing from the book: {len(missing)}")
    for src, t in missing[:40]:
        print(f"  {src}: {t[:140]}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))

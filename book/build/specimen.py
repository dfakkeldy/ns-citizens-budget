#!/usr/bin/env python3
"""Specimen pages: chosen pages of a built edition as standalone HTML and PNG.

    .venv/bin/python build/specimen.py <edition> <page> [page ...] [--dpi 110]

Writes out/specimens/<edition>-pNNN.html (the real page markup and CSS, so a
specimen can't drift from the book) and out/specimens/<edition>-pNNN.png
(rendered from the PDF). Use them for design review, for a Design canvas,
or to attach to a Codex review.
"""
import argparse, os, subprocess, sys
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT, ROOT, editions, out_path  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edition")
    ap.add_argument("pages", nargs="+", type=int)
    ap.add_argument("--dpi", type=int, default=110)
    a = ap.parse_args()
    cfg = editions()[a.edition]
    paged = BeautifulSoup(open(out_path(a.edition, "paged.html")).read(), "html.parser")
    style = "".join(str(s) for s in paged.head.find_all("style"))
    dest = os.path.join(OUT, "specimens")
    os.makedirs(dest, exist_ok=True)
    pages = {int(p["data-n"]): p for p in paged.select("section.page")}
    pdf = os.path.join(ROOT, cfg["file"])
    for n in a.pages:
        if n not in pages:
            sys.exit(f"{a.edition} has no page {n} (1–{max(pages)})")
        stem = os.path.join(dest, f"{a.edition}-p{n:03d}")
        with open(stem + ".html", "w") as f:
            f.write(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><base href="../">'
                    f'<title>{a.edition} page {n}</title>{style}</head><body>{pages[n]}</body></html>')
        subprocess.run(["pdftoppm", "-r", str(a.dpi), "-f", str(n), "-l", str(n), "-png", "-singlefile", pdf, stem], check=True)
        print(stem + ".html", stem + ".png")


if __name__ == "__main__":
    main()

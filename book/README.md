# Book project

Made with the textbook-pdf template. The text is plain Markdown; the build lays it out on pages, writes a glossary footer for each page, and prints a PDF for each edition.

## Rebuild

Needs Python 3, Node, pandoc, poppler (`pdftotext`, `pdftoppm`) and Google Chrome (or set `CHROME=/path/to/chrome`).

```bash
python3 -m venv .venv && .venv/bin/pip install -r build/requirements.txt   # once
(cd build && npm install)                                                  # once
.venv/bin/python build/fonts.py        # once, and after changing fonts in book.yaml
.venv/bin/python build/build.py        # every edition; or name one: build.py public
build/check_all.sh                     # every check on every edition
```

## Where things are

- `book.yaml`: title, cover, page size, colours, fonts, labels, and the editions (which chapters each contains, what each must never contain, the private mark).
- `src/chapters/*.md`: the text, one chapter per file. Settings at the top of a file (between `---` lines): `label`, `intro`, `kicker`, `running_head`, `toc`, `break`.
- `src/glossary.yaml`: the words the page footers explain. `src/cards.yaml`: card headers and ratings (optional).
- `src/assets/`: pictures. `fonts/`: the static font files cut by `build/fonts.py`.
- `build/`: the build (`build.py`, `theme.py`, `paginate.js`, `render.js`), the checks (`check_*.py`, `check_all.sh`), `specimen.py` for review pages, and `fonts.py`.
- `out/`: intermediate files (flow, paginated HTML, page maps, specimens). Safe to delete.
- `review/`: frozen review copies. Not published in this repository; the top-level README summarizes the review history.

## Checks

- `check_footers.py`: every abbreviation on every page is spelled out in that page's footer (read from the PDF with `pdftotext`); flags capitalised words missing from the glossary.
- `check_integrity.py`: every word of the assembled text lands on a page exactly once, in order.
- `check_source.py`: every paragraph, list item, table cell and heading of the chapter files is in the book.
- `check_breaks.py`: no page ends on a heading, card or lead-in; no text runs into the footer.
- `check_leaks.py`: nothing on an edition's forbid list appears in it; a private edition carries its mark on every page and says "private" in its file name.

## Specimens

```bash
.venv/bin/python build/specimen.py public 1 3 7     # out/specimens/public-p001.html and .png, ...
```

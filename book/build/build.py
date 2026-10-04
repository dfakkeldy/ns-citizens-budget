#!/usr/bin/env python3
"""Build the book's PDFs from book.yaml, src/chapters/*.md, src/glossary.yaml
and (optionally) src/cards.yaml.

    .venv/bin/python build/build.py [edition ...] [--no-pdf]     (default: every edition)

Steps: assemble each edition as a flow of top-level blocks (HTML), wrap every
glossary word in a marker, then paginate in headless Chrome (paginate.js
computes each page's footer from the words actually on it) and print to PDF.
Intermediate files go to out/: <edition>-flow.html, -paged.html, -pagemap.json.
"""
import argparse, json, os, re, subprocess, sys
from html import escape
from bs4 import BeautifulSoup, NavigableString

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import BOOK, BUILD, CARDS, CHAPTERS, GLOSSARY, OUT, ROOT, editions, load_chapter, out_path  # noqa: E402
from theme import Theme  # noqa: E402

T = Theme(BOOK)
L = T.L
BODY = "main" if T.layout == "rail" else "full"


def frag(html):
    return BeautifulSoup(html, "html.parser")


def rel_from_out(path):
    return os.path.relpath(path, OUT)


# ====================================================================== flow
class Flow:
    """An ordered list of top-level blocks (HTML strings) plus the contents."""
    def __init__(self):
        self.blocks = []
        self.toc = []        # (level, id, title_html)
        self.n = 0
        self.after_head = False

    def add(self, html):
        self.blocks.append(html)

    def uid(self, prefix):
        self.n += 1
        return f"{prefix}-{self.n}"

    def rh(self, text):
        self.add(f'<div class="rh-set" data-rh="{escape(text, quote=True)}"></div>')

    def sec_title(self, sid, title, sub=None, toc=True):
        if toc:
            self.toc.append((1, sid, escape(title)))
        s = f'<p class="sec-sub">{escape(sub)}</p>' if sub else ""
        self.add(f'<div class="blk full sec-head" id="{sid}" data-break="before" data-keep="next">'
                 f'<h1 class="sec-title">{escape(title)}</h1>{s}</div>')


# ====================================================================== blocks
BLOCK_TAGS = {"p", "ul", "ol", "div", "section", "table", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6",
              "figure", "dl", "pre"}


def is_label_para(el):
    """A lead-in that must stay with what follows: ends with a colon, or is only a bold label."""
    if el.name != "p":
        return False
    t = el.get_text().strip()
    if t.endswith(":") and len(t) < 160:
        return True
    kids = [k for k in el.contents if not (isinstance(k, NavigableString) and not k.strip())]
    return len(kids) == 1 and getattr(kids[0], "name", None) in ("strong", "b") and len(t) < 80


def fix_table(t):
    """The paginator splits tables by tbody rows and repeats thead."""
    if t.find("tbody") is None:
        tb = frag("<tbody></tbody>").tbody
        for r in t.find_all("tr"):
            if r.find_parent("thead") is None:
                tb.append(r.extract())
        t.append(tb)
    for cg in t.find_all("colgroup"):
        cg.decompose()


def add_cls(el, *cls):
    el["class"] = list(el.get("class", [])) + list(cls)


def attr(el, name, default=""):
    """A fenced-div attribute. Pandoc writes unknown ones as data-name but keeps
    names that are valid HTML (such as label) as they are."""
    v = el.get("data-" + name)
    if v is None:
        v = el.get(name)
    return default if v is None else v


def kids(el):
    return [c for c in el.contents if not (isinstance(c, NavigableString) and not c.strip())]


class Blocks:
    """Turns one chapter's pandoc HTML into flow blocks."""

    def __init__(self, F, edition):
        self.F, self.edition = F, edition
        self.pending_break = False

    def emit(self, html):
        if self.pending_break:
            html = re.sub(r"^<(\w+)", r'<\1 data-break="before"', html, count=1)
            self.pending_break = False
        self.F.add(html)
        self.F.after_head = False

    def run(self, children, width=None):
        width = width or BODY
        for el in children:
            if isinstance(el, NavigableString):
                if el.strip():
                    self.emit(f'<p class="blk {width}">{escape(str(el))}</p>')
                continue
            self.element(el, width)

    def element(self, el, width):
        name, cls = el.name, el.get("class", [])
        if name == "h2":
            sid = self.F.uid("s")
            self.F.toc.append((2, sid, el.decode_contents()))
            first = " first" if self.F.after_head else ""
            self.emit(f'<h2 class="blk full sec-h{first}" id="{sid}" data-keep="next">{el.decode_contents()}</h2>')
            return
        if name in ("h3", "h4", "h5", "h6"):
            add_cls(el, "blk", width)
            el["data-keep"] = "next"
            self.emit(str(el))
            return
        if name in ("div", "section"):
            return self.division(el, cls, width)
        if name == "table":
            fix_table(el)
            add_cls(el, "blk", "full")
            self.emit(str(el))
            return
        if name == "figure" or (name == "p" and el.find("img") and not el.get_text().strip()):
            if name == "p":
                el.name = "figure"
            add_cls(el, "blk", "full", "atomic")
            self.emit(str(el))
            return
        if name == "hr":
            return
        add_cls(el, "blk", width)
        if is_label_para(el):
            el["data-keep"] = "next"
        if name in ("ul", "ol"):
            lis = el.find_all("li", recursive=False)
            last = lis[-1] if lis else None
            if last is not None and last.get_text().strip().endswith(":") and len(last.get_text().strip()) < 60 and not last.find(["ul", "ol"]):
                lab = last.extract()          # a list ending in a lead-in: the lead-in travels with what follows
                self.emit(str(el))
                self.emit(f'<p class="blk {width} list-lead" data-keep="next">{lab.decode_contents()}</p>')
                return
        self.emit(str(el))

    def division(self, el, cls, width):
        ch = kids(el)
        if "pagebreak" in cls:
            self.pending_break = True
        elif "rail" in cls:
            self.railed(attr(el, "label"), ch)
        elif "note" in cls or "careful" in cls:
            kind = "careful" if "careful" in cls else "note"
            label = attr(el, "label", "Careful:" if kind == "careful" else "")
            if label and ch and ch[0].name == "p":
                ch[0].insert(0, frag(f'<span class="lbl">{escape(label)}</span> '))
            inner = "".join(str(c) for c in ch)
            atomic = " atomic" if "keep" in cls else ""
            self.emit(f'<div class="blk {width} callout {kind}{atomic}">{inner}</div>')
        elif "source" in cls:
            inner = "".join(str(c) for c in ch)
            short = " atomic" if len(el.get_text()) < 700 else ""     # a short note moves whole rather than leaving two lines behind
            self.emit(f'<div class="blk rb src-wrap{short}"><div class="rail-label">{escape(attr(el, "label", L["source"]))}</div>'
                      f'<div class="src">{inner}</div></div>')
        elif "card" in cls:
            self.card(attr(el, "code"), ch)
        elif "keep" in cls:
            # lay out the contents as usual (side heads, panels...), then bind them into one unsplittable block
            saved, self.F.blocks = self.F.blocks, []
            self.run(ch, width)
            inner, self.F.blocks = "".join(self.F.blocks), saved
            self.emit(f'<div class="blk full atomic keep-group">{inner}</div>')
        elif "full" in cls:
            self.run(ch, "full")
        else:
            self.run(ch, width)             # unknown wrapper: its contents still go in

    def railed(self, label, ch):
        """A side head in the rail beside the first block; the rest follows in the main column."""
        if not ch:
            return
        first, rest = ch[0], ch[1:]
        gap = "" if self.F.after_head else " sec-gap"
        if first.name == "table":
            self.emit(f'<div class="blk rb{gap}" data-keep="next"><div class="rail-label">{escape(label)}</div></div>')
            self.element(first, "main")
        else:
            keep = ' data-keep="next"' if first.name in ("h3", "h4", "h5") or is_label_para(first) else ""
            self.emit(f'<div class="blk rb{gap}"{keep}><div class="rail-label">{escape(label)}</div>{first}</div>')
        self.run(rest, "main")

    def card(self, code, ch):
        c = CARDS.get(code)
        if c is None:
            sys.exit(f"cards.yaml has no card '{code}'")
        title = c.get("title_" + self.edition, c.get("title", ""))
        cid = f"card-{code}"
        self.F.toc.append((2, cid, f'<span class="toc-code">{escape(code)}</span>{escape(title)}'))
        first = " first" if self.F.after_head else ""
        self.emit(f'<div class="blk full card-wrap atomic{first}" id="{cid}" data-keep="next" data-need="110">'
                  f'{T.card_head(code, c, escape(title))}</div>')
        self.F.after_head = True
        self.run(ch, BODY)


# ====================================================================== chapters
def resolve_images(soup, chapter_path):
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if re.match(r"^(https?:|data:|file:)", src):
            continue
        for base in (os.path.dirname(chapter_path), ROOT, os.path.join(ROOT, "src")):
            p = os.path.normpath(os.path.join(base, src))
            if os.path.exists(p):
                img["src"] = rel_from_out(p)
                break
        else:
            print(f"warning: image not found: {src} (in {os.path.basename(chapter_path)})", file=sys.stderr)


def add_chapter(F, path, edition):
    fm, soup = load_chapter(path, edition)
    resolve_images(soup, path)
    B = Blocks(F, edition)
    pending = []
    started = False

    def flush():
        B.run(pending)
        pending.clear()

    for el in list(soup.contents):
        if getattr(el, "name", None) == "h1":
            flush()
            title = el.get_text().strip()
            meta = fm if not started else {}
            started = True
            cid = F.uid("ch")
            label = str(meta.get("label", "")).strip()
            kicker = meta.get("kicker", f'{L["chapter"]} {label}' if label else "")
            F.rh(meta.get("running_head", (f"{label} · " if label else "") + title))
            if meta.get("toc", True):
                F.toc.append((1, cid, escape((f"{label}. " if label else "") + title)))
            lab = f'<div class="ch-label">{escape(label)}</div>' if label else ""
            brk = ' data-break="before"' if meta.get("break", True) else ""
            F.add(f'<div class="blk full chapter-head{"" if label else " nolabel"}" id="{cid}"{brk} data-keep="next">{lab}'
                  f'<div><div class="ch-kicker">{escape(kicker)}</div><h1 class="ch-title">{el.decode_contents()}</h1></div></div>')
            if meta.get("intro"):
                F.add(f'<p class="blk full ch-intro">{escape(meta["intro"])}</p>')
            F.after_head = True
        else:
            pending.append(el)
    flush()


# ====================================================================== glossary
class Glossary:
    def __init__(self, entries):
        self.entries = {g["key"]: g for g in entries}
        self.pats = []
        for g in entries:
            for p in g.get("match") or [r"(?<![\w\-])" + re.escape(g["key"]) + r"(?![\w])"]:
                self.pats.append((re.compile(p), g["key"]))
        # dependencies: acronyms mentioned inside each definition must be spelled out too
        for k, g in self.entries.items():
            g.setdefault("more", "")
            g["_deps"] = sorted({key for _, _, key in self.find(g["short"] + " " + g["more"])
                                 if key != k and self.entries[key]["kind"] == "acronym"} | set(g.get("deps") or []))
            g["_deps_short"] = sorted({key for _, _, key in self.find(g["short"])
                                       if key != k and self.entries[key]["kind"] == "acronym"})

    def find(self, text):
        """Non-overlapping matches, longest first at each position."""
        cands = []
        for rx, key in self.pats:
            for m in rx.finditer(text):
                if m.end() > m.start():
                    cands.append((m.start(), -(m.end() - m.start()), m.end(), key))
        cands.sort()
        out, last = [], -1
        for st, _, en, key in cands:
            if st >= last:
                out.append((st, en, key))
                last = en
        return out

    def js(self):
        return {k: {"kind": g["kind"], "short": g["short"], "more": g["more"], "deps": g["_deps"], "depsShort": g["_deps_short"]}
                for k, g in self.entries.items()}


SKIP_TAGS = {"script", "style", "svg", "code", "pre", "title"}
# Card codes that look like codes (a capital and a digit, e.g. B1, Q12) become links wherever they're mentioned.
_CODES = sorted((c for c in CARDS if re.fullmatch(r"[A-Z]+\d+[a-z]?", str(c))), key=len, reverse=True)
CODE_RX = re.compile(r"(?<![\w\-/.#])(" + "|".join(map(re.escape, _CODES)) + r")(?![\w\-])") if _CODES else None


def wrap_li_text(soup):
    """In list items and quotes that also hold blocks, wrap each run of inline
    content in a div, so the paginator only ever splits or moves whole blocks."""
    for li in soup.find_all(["li", "blockquote"]):
        ks = list(li.children)
        if not any(getattr(k, "name", None) in BLOCK_TAGS for k in ks):
            continue
        run = []

        def flush():
            if run and any((getattr(k, "name", None) or str(k).strip()) for k in run):
                d = soup.new_tag("div")
                d["class"] = ["li-t"]
                run[0].insert_before(d)
                for k in run:
                    d.append(k.extract())
            run.clear()
        for k in ks:
            if getattr(k, "name", None) in BLOCK_TAGS:
                flush()
            else:
                run.append(k)
        flush()


URL_RX = re.compile(r"(https?://[^\s<>()\[\]]+[^\s<>()\[\].,;:!?'\"”’])|(?<![\w@/.\-])((?:[a-z0-9\-]+\.)+"
                    r"(?:com|org|net|gov|edu|int|info|io|ca|uk|au|nz|ie|eu|de|fr|nl|us)(?:/[^\s<>()\[\]]*[^\s<>()\[\].,;:!?'\"”’])?)(?![\w@])")


def linkify(soup):
    """Make printed web addresses real links, keeping the visible text."""
    for s in list(soup.find_all(string=True)):
        if any(p.name in ("a", "script", "style", "svg", "code", "pre") for p in s.parents):
            continue
        text = str(s)
        if not URL_RX.search(text):
            continue
        out, pos = [], 0
        for m in URL_RX.finditer(text):
            url = m.group(0)
            if m.group(2) and "@" in text[max(0, m.start() - 1):m.start()]:
                continue
            href = url if m.group(1) else "https://" + url
            out.append(escape(text[pos:m.start()]))
            out.append(f'<a class="ext" href="{escape(href, quote=True)}">{escape(url)}</a>')
            pos = m.end()
        if pos:
            out.append(escape(text[pos:]))
            s.replace_with(frag("".join(out)))


def enrich(soup, gloss, link_codes=True):
    """Wrap glossary words in spans; link card codes to their cards."""
    texts = []
    for s in soup.find_all(string=True):
        skip = False
        for par in s.parents:
            if par.name in SKIP_TAGS or par.name == "head" or "no-gloss" in (par.get("class") or []) \
                    or (par.name == "a" and str(par.get("href", "")).startswith("http")):
                skip = True
                break
        if not skip:
            texts.append(s)
    for s in texts:
        text = str(s)
        hits = [(st, en, "g", key) for st, en, key in gloss.find(text)]
        in_link = any(p.name == "a" or "card-head" in (p.get("class") or []) for p in s.parents)
        if link_codes and CODE_RX and not in_link:
            for m in CODE_RX.finditer(text):
                if not any(st <= m.start() < en for st, en, _, _ in hits):
                    hits.append((m.start(), m.end(), "x", m.group(1)))
        if not hits:
            continue
        hits.sort()
        pieces, pos = [], 0
        for st, en, typ, key in hits:
            if st < pos:
                continue
            pieces.append(escape(text[pos:st]))
            seg = escape(text[st:en])
            if typ == "g":
                nb = " nb" if (" " in key and gloss.entries[key]["kind"] == "acronym") else ""
                pieces.append(f'<span class="gt{nb}" data-t="{escape(key, quote=True)}">{seg}</span>')
            else:
                pieces.append(f'<a class="xref" href="#card-{key}">{seg}</a>')
            pos = en
        pieces.append(escape(text[pos:]))
        s.replace_with(frag("".join(pieces)))


def glossary_rows(used):
    """The glossary chapter: the words this edition uses, two to a row, with first-defined page numbers."""
    items = sorted([g for g in GLOSSARY if g["key"] in used], key=lambda g: re.sub(r"[^a-z0-9]", "", g["key"].lower()))

    def entry(g):
        j = ". " if re.match(r"[A-Z][a-z]", g["more"] or "") else (": " if g["more"] else "")
        return (f'<div class="gl-entry" data-entry="{escape(g["key"], quote=True)}"><div><span class="gl-term no-gloss">{escape(g["key"])}</span> '
                f'{escape(g["short"])}{j}{escape(g["more"] or "")}</div><div class="gl-pg" data-gl-pg="{escape(g["key"], quote=True)}"></div></div>')
    return "".join(f'<div class="blk full gl-row atomic" data-page-class="selfdef">{"".join(entry(g) for g in items[i:i + 2])}</div>'
                   for i in range(0, len(items), 2))


# ====================================================================== assemble
def build_flow(edition, cfg):
    F = Flow()
    for item in cfg["contents"]:
        if item == "@cover":
            img = BOOK.get("cover_image")
            src = rel_from_out(os.path.join(ROOT, img)) if img else None
            F.add(T.cover(BOOK, edition, cfg, src, BOOK.get("cover_alt", "")))
        elif item == "@toc":
            F.rh(L["contents"])
            F.add("<!--TOC-->")
        elif item == "@glossary":
            F.rh(L["glossary"])
            F.sec_title("glossary", L["glossary"], L["glossary_sub"])
            F.add('<div id="gl-placeholder"></div>')
        elif item.startswith("@"):
            sys.exit(f"unknown contents entry {item}")
        else:
            add_chapter(F, os.path.join(CHAPTERS, item), edition)
    return F


def toc_blocks(F):
    depth = BOOK.get("toc_depth", 2)
    out = [f'<div class="blk full sec-head" id="contents" data-break="before" data-keep="next"><h1 class="sec-title">{escape(L["contents"])}</h1></div>']
    for level, sid, title in F.toc:
        if level <= depth:
            out.append(f'<div class="blk full toc-row lvl{level}" data-toc-target="{sid}"><a href="#{sid}"><span class="toc-t">{title}</span>'
                       f'<span class="toc-n"></span></a></div>')
    return out


def fonts_css():
    p = os.path.join(ROOT, "fonts", "fonts.css")
    if not os.path.exists(p):
        print("warning: fonts/fonts.css missing (run build/fonts.py); using fallback fonts", file=sys.stderr)
        return ""
    return open(p).read()


def assemble(F, edition, cfg):
    gloss = Glossary(GLOSSARY)
    blocks = []
    for b in F.blocks:
        blocks.extend(toc_blocks(F) if b == "<!--TOC-->" else [b])
    soup = frag(f'<div id="flow">{chr(10).join(blocks)}</div>')
    wrap_li_text(soup)
    linkify(soup)
    enrich(soup, gloss)
    used = {sp["data-t"] for sp in soup.select("[data-t]")}
    changed = True
    while changed:                      # footers also explain the words definitions mention
        changed = False
        for k in list(used):
            for d in gloss.entries[k]["_deps"]:
                if d not in used:
                    used.add(d)
                    changed = True
    ph = soup.select_one("#gl-placeholder")
    if ph is not None:
        rows = frag(glossary_rows(used))
        linkify(rows)
        enrich(rows, gloss)
        ph.replace_with(rows)
    for rh in soup.select(".rh-set"):    # running heads carry glossary words too
        t = frag(f"<span>{escape(rh['data-rh'])}</span>")
        enrich(t, gloss, link_codes=False)
        rh["data-rh"] = str(t.span.decode_contents())
    edition_js = {"name": edition, "runningRight": cfg.get("running_head", BOOK.get("running_head", BOOK.get("title", ""))),
                  "privateMark": cfg.get("private_mark", ""), "reminders": bool((BOOK.get("footer") or {}).get("reminders", True)),
                  "labels": L}
    title = cfg.get("pdf_title", BOOK.get("title", "Book") + ("" if len(editions()) == 1 else f" ({edition} edition)"))
    paginator = open(os.path.join(BUILD, "paginate.js")).read()
    return f"""<!doctype html>
<html lang="{escape(BOOK.get('lang', 'en'))}"><head><meta charset="utf-8"><title>{escape(title)}</title>
<style>{fonts_css()}{T.css()}</style></head>
<body>
<div id="pages"></div>
{soup}
<script>window.GLOSSARY = {json.dumps(gloss.js(), ensure_ascii=False)};
window.EDITION = {json.dumps(edition_js, ensure_ascii=False)};
window.LAYOUT = {json.dumps(T.layout_js())};</script>
<script data-paginator>{paginator}</script>
</body></html>"""


def build(edition, cfg, pdf=True):
    os.makedirs(OUT, exist_ok=True)
    F = build_flow(edition, cfg)
    html = assemble(F, edition, cfg)
    flow = out_path(edition, "flow.html")
    open(flow, "w").write(html)
    print(f"[{edition}] flow: {len(F.blocks)} blocks, {len(html) // 1024} KB")
    if not pdf:
        return
    pdfp = os.path.join(ROOT, cfg["file"])
    mapp = out_path(edition, "pagemap.json")
    subprocess.run(["node", os.path.join(BUILD, "render.js"), flow, out_path(edition, "paged.html"), pdfp, mapp,
                    str(T.W), str(T.H)], check=True)
    m = json.load(open(mapp))
    print(f"[{edition}] {len(m['pages'])} pages; overflow on pages: {m['overflow'] or 'none'}")
    print(f"[{edition}] wrote {pdfp}")


if __name__ == "__main__":
    eds = editions()
    ap = argparse.ArgumentParser()
    ap.add_argument("editions", nargs="*", help=f"default: all ({', '.join(eds)})")
    ap.add_argument("--no-pdf", action="store_true")
    a = ap.parse_args()
    for ed in a.editions or list(eds):
        if ed not in eds:
            sys.exit(f"no edition '{ed}' in book.yaml (have: {', '.join(eds)})")
        build(ed, eds[ed], pdf=not a.no_pdf)

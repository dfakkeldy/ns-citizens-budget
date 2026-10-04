#!/usr/bin/env python3
"""Check every page's glossary footer against the text actually on the page.

Uses pdftotext -bbox-layout (poppler) to get each page's words with their
positions, splits the page at the footer heading (labels.footer in book.yaml), and
checks that every abbreviation on the page (running head, body and footer)
is spelled out in that page's footer as "KEY short-expansion".

    .venv/bin/python build/check_footers.py <edition> [--verbose]

Exit status 1 if any page fails. Also reports unknown abbreviations (tokens
that look like acronyms but aren't in the glossary) and footer entries that
don't belong on their page.
"""
import re, subprocess, sys, os, html

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import BOOK, CARDS, GLOSSARY as GLOSS, ROOT, editions  # noqa: E402
from theme import Theme  # noqa: E402

LB = Theme(BOOK).L
ACR = [g for g in GLOSS if g["kind"] == "acronym"]
PATS = []
for g in ACR:
    pats = list(g.get("match") or [r"\b" + re.escape(g["key"]) + r"\b"])
    if re.fullmatch(r"[A-Za-z0-9&.\- ]+", g["key"]):
        pats.append(r"(?<![\w\-])" + re.escape(g["key"]) + r"(?![\w])")   # the key itself, as printed in a footer entry
    for p in pats:
        PATS.append((re.compile(p), g["key"]))
SHORT = {g["key"]: g["short"] for g in GLOSS}
# tokens that look like acronyms but aren't (roman numerals are skipped anyway);
# add the book's own in book.yaml under checks: not_acronyms: [...]
WHITELIST = {"OK", "II", "III", "IV", "V", "XX"} | set((BOOK.get("checks") or {}).get("not_acronyms") or []) | set(map(str, CARDS))


def norm(s):
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "–").replace(" ", " ")
    return re.sub(r"\s+", " ", s)


NONTEXT = re.compile(r"\S*(?:://|@|www\.|/)\S*|\S+\.(?:pdf|md|html?|php|svg|xlsx)\b\S*", re.I)


def find_keys(text):
    """Acronym keys present in text (longest match wins at each position).
    URLs, email addresses and file paths are blanked out first."""
    text = NONTEXT.sub(lambda m: " " * len(m.group(0)), text)
    cands = []
    for rx, key in PATS:
        for m in rx.finditer(text):
            cands.append((m.start(), -(m.end() - m.start()), m.end(), key))
    cands.sort()
    out, last, spans = [], -1, []
    for st, _, en, key in cands:
        if st >= last:
            out.append(key)
            spans.append((st, en))
            last = en
    return out, spans


def unknown_acronyms(text, spans):
    covered = lambda i: any(a <= i < b for a, b in spans)
    out = set()
    for w in re.finditer(r"\S+", text):
        tok = w.group(0)
        if any(x in tok for x in ("://", "@", "www.", "/")) or re.search(r"\.(pdf|md|html?|php|svg|xlsx)\b", tok, re.I):
            continue
        for m in re.finditer(r"[A-Za-z0-9][A-Za-z0-9&.\-]*[A-Za-z0-9]", tok):
            t = m.group(0)
            t = re.sub(r"['’]s$", "", t)
            letters = [c for c in t if c.isalpha()]
            caps = [c for c in letters if c.isupper()]
            if len(caps) >= 2 and len(caps) >= 0.5 * len(letters):
                if t in WHITELIST or re.fullmatch(r"[IVX]+", t):
                    continue
                if re.fullmatch(r"(?:[A-Z]\.){1,3}[A-Z]?", t):   # initials, e.g. A.F.
                    continue
                parts = [(pm.start(), pm.group(0)) for pm in re.finditer(r"[A-Za-z0-9&]+", t)]
                bad = [pt for off, pt in parts
                       if sum(c.isupper() for c in pt) >= 2 and not covered(w.start() + m.start() + off)
                       and pt not in WHITELIST and not re.fullmatch(r"[IVX]+", pt)]
                if bad:
                    out.add(t)
    return out


def pages_words(pdf):
    xml = subprocess.run(["pdftotext", "-bbox-layout", pdf, "-"], capture_output=True, text=True, check=True).stdout
    pages = []
    for pm in re.finditer(r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>', xml, re.S):
        H = float(pm.group(2))
        lines = []
        for lm in re.finditer(r"<line[^>]*>(.*?)</line>", pm.group(3), re.S):
            ws = [(float(a), float(b), float(c), float(d), html.unescape(t))
                  for a, b, c, d, t in re.findall(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>', lm.group(1))]
            if ws:
                lines.append(ws)
        pages.append((H, lines))
    return pages


def split_page(H, lines):
    """Return (body_text, footer_text, is_glossary_page)."""
    ftop = None
    for ws in lines:
        t = " ".join(w[4] for w in ws)
        if t.startswith(LB["footer"]) or t.startswith(LB["footer_glossary"]):
            y = ws[0][1]
            if y > H * 0.3:
                ftop = y if ftop is None else max(ftop, y)
    body, foot = [], []
    folio_y = H - 40   # the folio sits below the footer
    for ws in lines:
        y = ws[0][1]
        t = " ".join(w[4] for w in ws)
        if y > folio_y and re.fullmatch(r"\d{1,3}", t.strip()):
            continue
        (foot if ftop is not None and y >= ftop - 0.5 else body).append(t)
    def join(ls):
        out = ""
        for l in ls:
            if out and not re.search(r"[-–]$", out):
                out += " "
            out += l
        return out
    btxt = norm(join(body))
    gloss_page = LB["glossary"] in btxt[:200] or any(l.startswith(LB["footer_glossary"]) for l in foot)
    return btxt, norm(join(foot)), gloss_page


def squash(s):
    return re.sub(r"\s+", "", s)


def expanded(key, text):
    return squash(norm(key + " " + SHORT[key])) in squash(text)


def main():
    pdf = os.path.join(ROOT, editions()[sys.argv[1]]["file"])
    verbose = "--verbose" in sys.argv
    pages = pages_words(pdf)
    fails, unknown, extras = [], {}, []
    n_acr_checks = 0
    for i, (H, lines) in enumerate(pages, 1):
        body, foot, gloss_page = split_page(H, lines)
        bkeys, bspans = find_keys(body)
        fkeys, fspans = find_keys(foot)
        need = set(bkeys) | set(fkeys)
        n_acr_checks += len(need)
        missing = []
        for k in sorted(need):
            if expanded(k, foot):
                continue
            if gloss_page and expanded(k, body):
                continue
            missing.append(k)
        if missing:
            fails.append((i, missing))
        u = unknown_acronyms(body, bspans) | unknown_acronyms(foot, fspans)
        for t in u:
            unknown.setdefault(t, []).append(i)
        # footer entries whose key is not on the page (and isn't a dependency) — informational
        if verbose and foot:
            listed = [k for k in SHORT if norm(k + " " + SHORT[k]) in foot and SHORT[k]]
            for k in listed:
                if k not in need and not re.search(r"\b" + re.escape(k) + r"\b", body):
                    extras.append((i, k))
    print(f"{pdf}: {len(pages)} pages, {n_acr_checks} page-level abbreviation checks")
    if fails:
        print(f"FAIL: {len(fails)} pages have abbreviations not spelled out in their footer:")
        for i, m in fails:
            print(f"  page {i}: {', '.join(m)}")
    else:
        print("PASS: every abbreviation on every page is spelled out in that page's footer.")
    if unknown:
        print("Unknown abbreviation-like tokens (not in the glossary):")
        for t, pg in sorted(unknown.items()):
            print(f"  {t}: pages {', '.join(map(str, pg[:12]))}{' …' if len(pg) > 12 else ''}")
    if verbose and extras:
        print(f"Footer terms not found in the page body (usually dependencies or reminders): {len(extras)}")
    sys.exit(1 if fails or unknown else 0)


if __name__ == "__main__":
    main()

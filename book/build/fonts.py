#!/usr/bin/env python3
"""Download the book's Google fonts and cut static TrueType instances.

    .venv/bin/python build/fonts.py

Why static: Chrome embeds variable fonts in PDFs as Type 3 fonts, which some
viewers render blurry and some text extractors (and pdftotext checks) mangle.
Static instances embed as normal TrueType.

Reads book.yaml:
    fonts:
      serif: Source Serif 4          # body text and display headings
      sans: Atkinson Hyperlegible Next   # labels, tables, footers, running heads
      serif_bold: 600                # optional; the weight used for bold serif text
      text_opsz: 12                  # optional optical sizes, used when the font has an opsz axis
      display_opsz: 48
Writes fonts/static/*.ttf and fonts/fonts.css under three fixed family names
(TB Serif, TB Serif Display, TB Sans) that theme.py uses. Latin and Latin
Extended subsets only (add more in SUBSETS if the book needs them).
"""
import io, json, os, re, sys, urllib.parse, urllib.request
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import BOOK, ROOT  # noqa: E402

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/130.0 Safari/537.36")        # Google serves woff2 with unicode-range blocks only to modern browsers
SUBSETS = ("latin", "latin-ext")
FONTS = os.path.join(ROOT, "fonts")
STATIC = os.path.join(FONTS, "static")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


_META = []


def family_meta(name):
    if not _META:
        raw = get("https://fonts.google.com/metadata/fonts").decode("utf-8")
        _META.append(json.loads(raw[raw.index("{"):])["familyMetadataList"])
    for f in _META[0]:
        if f["family"] == name:
            return f
    sys.exit(f"'{name}' is not a Google font (check the spelling on fonts.google.com)")


def css_query(name, meta):
    """css2 query for the whole family: full axis ranges if variable, else every static style."""
    axes = {a["tag"]: a for a in meta.get("axes") or []}
    styles = set(meta.get("fonts", {}))
    italic = any(s.endswith("i") for s in styles)
    fam = urllib.parse.quote_plus(name)
    if axes:
        tags = sorted(axes, key=lambda t: (t.isupper(), t))       # lowercase axes first, alphabetical
        rng = ",".join(f'{int(axes[t]["min"]) if axes[t]["min"].is_integer() else axes[t]["min"]}..'
                       f'{int(axes[t]["max"]) if axes[t]["max"].is_integer() else axes[t]["max"]}' for t in tags)
        if italic:
            spec = f"ital,{','.join(tags)}@0,{rng};1,{rng}"
        else:
            spec = f"{','.join(tags)}@{rng}"
    else:
        ws = sorted({int(s.rstrip("i")) for s in styles})
        if italic:
            spec = "ital,wght@" + ";".join([f"0,{w}" for w in ws if str(w) in styles] + [f"1,{w}" for w in ws if f"{w}i" in styles])
        else:
            spec = "wght@" + ";".join(str(w) for w in ws)
    return f"https://fonts.googleapis.com/css2?family={fam}:{spec}&display=swap"


def faces(css):
    """[(subset, style, (wmin, wmax), unicode_range, url)]"""
    out = []
    for sub, body in re.findall(r"/\* ([\w-]+) \*/\s*@font-face \{(.*?)\}", css, re.S):
        if sub not in SUBSETS:
            continue
        style = re.search(r"font-style: (\w+)", body).group(1)
        w = [int(x) for x in re.search(r"font-weight: ([\d ]+);", body).group(1).split()]
        out.append((sub, style, (w[0], w[-1]), re.search(r"unicode-range: (.*?);", body).group(1),
                    re.search(r"url\((.*?)\)", body).group(1)))
    return out


def cut(name, jobs, cache):
    """jobs: [(family_alias, out_stem, style, weight, extra_axes)] -> css lines."""
    meta = family_meta(name)
    css = get(css_query(name, meta)).decode("utf-8")
    fl = faces(css)
    if not fl:
        sys.exit(f"no latin faces returned for {name}")
    lines = []
    for alias, stem, style, weight, extra in jobs:
        for sub in SUBSETS:
            cands = [f for f in fl if f[0] == sub and f[1] == style]
            if not cands and style == "italic":
                cands = [f for f in fl if f[0] == sub and f[1] == "normal"]     # no italic: browser will slant
            if not cands:
                continue
            # the face whose weight range covers (or is nearest to) the wanted weight
            f = min(cands, key=lambda c: 0 if c[2][0] <= weight <= c[2][1] else min(abs(weight - c[2][0]), abs(weight - c[2][1])))
            url = f[4]
            if url not in cache:
                cache[url] = get(url)
            font = TTFont(io.BytesIO(cache[url]))
            if "fvar" in font:
                limits = {}
                for a in font["fvar"].axes:
                    if a.axisTag == "wght":
                        limits["wght"] = max(a.minValue, min(a.maxValue, weight))
                    elif a.axisTag in extra:
                        limits[a.axisTag] = max(a.minValue, min(a.maxValue, extra[a.axisTag]))
                    else:
                        limits[a.axisTag] = a.defaultValue
                font = instancer.instantiateVariableFont(font, limits)
            font.flavor = None
            fn = f"{stem}-{sub}.ttf"
            font.save(os.path.join(STATIC, fn))
            lines.append(f"@font-face{{font-family:'{alias}';font-style:{style};font-weight:{weight};"
                         f"src:url('../fonts/static/{fn}') format('truetype');unicode-range:{f[3]};}}")
    return lines


def main():
    cfg = BOOK.get("fonts") or {}
    serif = cfg.get("serif", "Source Serif 4")
    sans = cfg.get("sans", "Atkinson Hyperlegible Next")
    bold = int(cfg.get("serif_bold", 600))
    text_o = {"opsz": cfg.get("text_opsz", 12)}
    disp_o = {"opsz": cfg.get("display_opsz", 48)}
    os.makedirs(STATIC, exist_ok=True)
    for f in os.listdir(STATIC):
        if f.endswith(".ttf"):
            os.remove(os.path.join(STATIC, f))
    cache = {}
    lines = []
    lines += cut(serif, [
        ("TB Serif", "serif-400", "normal", 400, text_o),
        ("TB Serif", f"serif-{bold}", "normal", bold, text_o),
        ("TB Serif", "serif-400i", "italic", 400, text_o),
        ("TB Serif", f"serif-{bold}i", "italic", bold, text_o),
        ("TB Serif Display", "display-400", "normal", 400, disp_o),
        ("TB Serif Display", f"display-{bold}", "normal", bold, disp_o),
    ], cache)
    if bold != 700:      # CSS 'bold' (700) maps to the nearest available weight; also cut 700 for <b>
        lines += cut(serif, [("TB Serif", "serif-700", "normal", 700, text_o)], cache)
    lines += cut(sans, [
        ("TB Sans", "sans-400", "normal", 400, {}),
        ("TB Sans", "sans-700", "normal", 700, {}),
        ("TB Sans", "sans-400i", "italic", 400, {}),
        ("TB Sans", "sans-700i", "italic", 700, {}),
    ], cache)
    with open(os.path.join(FONTS, "fonts.css"), "w") as f:
        f.write(f"/* {serif} and {sans}, static instances cut by build/fonts.py */\n" + "\n".join(lines) + "\n")
    print(f"fonts: {serif} + {sans}: {len(lines)} faces in fonts/static, fonts/fonts.css written")
    print("Licence: check each family's licence on fonts.google.com (most are SIL Open Font License) and credit it in the book.")


if __name__ == "__main__":
    main()

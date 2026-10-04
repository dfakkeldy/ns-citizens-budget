"""The book's visual system: page geometry, colour tokens, type and CSS.

Everything visual comes from here, driven by book.yaml (page size, theme
colours, labels). build.py, the paginator (through window.LAYOUT) and the
specimen pages all use the same values, so a specimen is the book.

Fonts: fonts.py cuts static instances of the chosen Google fonts and writes
fonts/fonts.css under three fixed family names (TB Serif, TB Serif Display,
TB Sans), so this file never changes when the fonts do.
"""
from html import escape

SIZES = {"letter": (816, 1056), "a4": (794, 1123)}     # CSS px at 96 px/in

DEFAULT_COLORS = {
    "ink": "#1d1c1a",          # body text
    "ink2": "#4a4843",         # secondary text; never lighter (4.5:1 on white)
    "rule": "#cfcac0",         # hairlines
    "accent": "#1f4d3b",       # headings, codes, meter fills
    "accent_tint": "#e8efea",  # card ground, table heads, notes
    "accent_mid": "#9fb8aa",   # link underlines, quiet accents
    "caution": "#a8452a",      # warnings, private marks
    "caution_tint": "#f6e9e3",
    "paper": "#ffffff",
}

DEFAULT_LABELS = {
    "footer": "Words on this page",
    "footer_glossary": "Other abbreviations on this page",
    "also": "Also on this page:",
    "earlier": "Earlier words:",
    "contents": "Contents",
    "glossary": "Glossary and index of abbreviations",
    "glossary_sub": "Every word the footers explain, with the page where it is first defined.",
    "source": "Where this comes from",
    "chapter": "Chapter",
}

SERIF = "'TB Serif', Georgia, 'Times New Roman', serif"
SERIF_DISPLAY = "'TB Serif Display', 'TB Serif', Georgia, serif"
SANS = "'TB Sans', 'Helvetica Neue', Arial, sans-serif"


class Theme:
    def __init__(self, book):
        page = (book.get("page") or {})
        self.page_size = page.get("size", "letter").lower()
        self.W, self.H = SIZES[self.page_size]
        self.MARGIN_X = page.get("margin_x", 72 if self.page_size == "letter" else 64)
        self.CONTENT_W = self.W - 2 * self.MARGIN_X
        self.RAIL_W, self.GUTTER = 144, 24
        self.MAIN_W = self.CONTENT_W - self.RAIL_W - self.GUTTER
        self.HEAD_TOP = 36            # running head text top
        self.BODY_TOP = 92            # first body line
        self.FOLIO_BOTTOM = 34        # folio distance from page bottom
        self.FOOTER_BOTTOM = 62       # footer bottom edge distance from page bottom
        self.FOOTER_GAP = 20          # min clear space between body and footer
        self.BODY_SIZE = 15.33        # 11.5 pt
        self.layout = (book.get("layout") or {}).get("body", "rail")   # rail | full
        self.C = dict(DEFAULT_COLORS, **(book.get("theme") or {}))
        self.L = dict(DEFAULT_LABELS, **(book.get("labels") or {}))

    def layout_js(self):
        return {"pageW": self.W, "pageH": self.H, "bodyTop": self.BODY_TOP,
                "footerBottom": self.FOOTER_BOTTOM, "footerGap": self.FOOTER_GAP}

    # ------------------------------------------------------------ components
    def meter(self, level, tone="accent", uncertain=False):
        """Five segments; level 0–5, a partial segment filled in proportion. Filled vs empty, so it reads in greyscale."""
        col = {"accent": self.C["accent"], "caution": self.C["caution"], "neutral": self.C["ink2"]}.get(tone, tone)
        segs = []
        for i in range(5):
            fill = 0 if level is None else max(0.0, min(1.0, level - i))
            if uncertain or level is None:
                segs.append(f'<span class="seg" style="border:1.3px dashed {col};background:transparent"></span>')
            elif fill >= 1:
                segs.append(f'<span class="seg" style="background:{col};border:1.3px solid {col}"></span>')
            elif fill > 0:
                segs.append(f'<span class="seg" style="border:1.3px solid {col};background:linear-gradient(90deg,{col} {fill:.0%},transparent {fill:.0%})"></span>')
            else:
                segs.append(f'<span class="seg" style="border:1.3px solid {col};background:transparent"></span>')
        return f'<span class="meter" role="img" aria-label="{level if level is not None else "unknown"} of 5">{"".join(segs)}</span>'

    def card_head(self, cid, card, title_html=None):
        """The card header: code tile, kind, title, action chip, rating cells, meta and notes."""
        title = title_html or escape(card.get("title", ""))
        kind = f'<span class="card-kind">{escape(card["kind"])}</span>' if card.get("kind") else ""
        action = f'<div class="card-action"><span>{escape(self.L.get("action", "Suggested action"))}</span>{escape(card["action"])}</div>' \
            if card.get("action") else ""
        cells = []
        for r in card.get("ratings") or []:
            q = f'<div class="rq">{escape(r["qual"])}</div>' if r.get("qual") else ""
            cells.append(f'<div class="rcell"><div class="rl">{escape(r["label"])}</div><div class="rw">{escape(str(r.get("word", "")))}</div>{q}'
                         f'{self.meter(r.get("level"), r.get("tone", "accent"), r.get("uncertain", False))}</div>')
        grid = f'<div class="card-ratings" style="grid-template-columns:repeat({max(1, len(cells))},minmax(0,1fr))">{"".join(cells)}</div>' if cells else ""
        meta = "".join(f'<span><b>{escape(k)}</b> {escape(str(v))}</span>' for k, v in (card.get("meta") or {}).items())
        meta = f'<div class="card-meta">{meta}</div>' if meta else ""
        notes = "".join(f'<div class="card-note"><b>{escape(n["label"])}</b> {escape(n["text"])}</div>' for n in (card.get("notes") or []))
        return (f'<div class="card-head"><div class="card-top"><div class="card-id">'
                f'<span class="card-code">{escape(cid)}</span>{kind}</div>{action}</div>'
                f'<h2 class="card-title">{title}</h2>{grid}{meta}{notes}</div>')

    # ------------------------------------------------------------ CSS
    def css(self):
        C, L = self.C, self.L
        W, H, MX, CW, RW, G = self.W, self.H, self.MARGIN_X, self.CONTENT_W, self.RAIL_W, self.GUTTER
        main_ml = RW + G if self.layout == "rail" else 0
        return f"""
@page {{ size: {W / 96:.3f}in {H / 96:.3f}in; margin: 0; }}
html, body {{ margin:0; padding:0; background:{C['paper']}; }}
body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
#flow {{ position:absolute; left:-20000px; top:0; width:{CW}px; }}
a {{ color:inherit; text-decoration:none; }}

/* ---- page chrome ---- */
.page {{ width:{W}px; height:{H}px; position:relative; overflow:hidden; background:{C['paper']}; break-after:page; contain:layout paint size; }}
.page .rh {{ position:absolute; left:{MX}px; right:{MX}px; top:{self.HEAD_TOP}px; display:flex; justify-content:space-between; gap:24px;
  align-items:baseline; font-family:{SANS}; font-size:12px; color:{C['ink2']}; border-bottom:1px solid {C['rule']}; padding-bottom:7px; }}
.page .rh-l {{ font-weight:700; color:{C['accent']}; min-width:0; }}
.page .rh-r {{ flex:none; }}
.page .rh .pm {{ color:{C['caution']}; font-weight:700; }}
.page .pb {{ position:absolute; left:{MX}px; top:{self.BODY_TOP}px; width:{CW}px; display:flow-root; overflow-wrap:break-word; }}
.page .gf {{ position:absolute; left:{MX}px; right:{MX}px; bottom:{self.FOOTER_BOTTOM}px; border-top:1px solid {C['rule']};
  padding-top:7px; font-family:{SANS}; font-size:12.67px; line-height:1.36; color:{C['ink2']}; }}
.page .gf:empty {{ display:none; }}
.page .gf-label, .page .gf-rl {{ font-weight:700; color:{C['accent']}; }}
.page .gf-defs {{ column-count:2; column-gap:24px; margin-top:3px; }}
.page .gf-def {{ break-inside:avoid; margin:0 0 4px 0; }}
.page .gf b {{ font-weight:700; color:{C['ink']}; }}
.page .gf-rems {{ margin-top:3px; }}
.page .gf-dot {{ color:#8a857c; }}
.page .gf a.ext {{ text-decoration:underline; text-decoration-color:{C['accent_mid']}; }}
.page .folio {{ position:absolute; right:{MX}px; bottom:{self.FOLIO_BOTTOM}px; font-family:{SANS}; font-size:12px; font-weight:700;
  color:{C['ink2']}; font-variant-numeric:lining-nums; }}
.page.no-head .rh, .page.no-folio .folio {{ display:none; }}
.page.fullpage .pb {{ left:0; top:0; width:{W}px; }}

/* ---- body type ---- */
#flow, .pb {{ font-family:{SERIF}; font-size:{self.BODY_SIZE}px; line-height:1.47; color:{C['ink']};
  font-variant-numeric:oldstyle-nums proportional-nums; }}
.pb p {{ margin:0 0 9px 0; text-wrap:pretty; }}
.pb ul, .pb ol {{ margin:0 0 9px 0; padding-left:22px; }}
.pb li {{ margin:0 0 5px 0; padding-left:2px; }}
.pb li::marker {{ color:{C['accent']}; }}
.pb ol > li::marker {{ font-family:{SANS}; font-weight:700; font-size:13.5px; }}
.pb li.cont {{ list-style:none; }}
.pb .li-t {{ margin:0; }}
.pb strong, .pb b {{ font-weight:600; }}
.pb h1 {{ margin:0; }}
.pb h3 {{ font-family:{SANS}; font-size:17px; line-height:1.3; font-weight:700; color:{C['accent']}; margin:18px 0 8px 0; }}
.pb h4 {{ font-family:{SANS}; font-size:14.5px; line-height:1.3; font-weight:700; color:{C['ink']}; margin:14px 0 6px 0; }}
.pb .blk.main {{ margin-left:{main_ml}px; }}
.pb .blk.rb {{ position:relative; margin-left:{RW + G}px; }}
.pb .rail-label {{ position:absolute; left:-{RW + G}px; top:3px; width:{RW}px; font-family:{SANS}; font-size:12.5px; line-height:1.25;
  font-weight:700; color:{C['accent']}; letter-spacing:0.01em; }}
.pb .blk.cont > .rail-label {{ display:none; }}
.pb .rb.sec-gap {{ margin-top:8px; }}
.pb a.ext {{ text-decoration:underline; text-decoration-color:{C['accent_mid']}; text-underline-offset:2px; overflow-wrap:anywhere; }}
.pb a.xref {{ color:{C['accent']}; font-weight:600; }}
.pb code {{ font-family:{SANS}; font-size:0.9em; color:{C['ink2']}; }}
.gt.nb {{ white-space:nowrap; }}
.gt-first {{ text-decoration: underline dotted {C['accent']}; text-decoration-thickness:1px; text-underline-offset:3px; }}

/* ---- headings ---- */
.pb .sec-head {{ margin:0 0 14px; }}
.pb .sec-title {{ font-family:{SERIF_DISPLAY}; font-size:34px; line-height:1.1; font-weight:600; color:{C['ink']}; margin:2px 0 6px; text-wrap:balance; }}
.pb .sec-sub {{ font-size:{self.BODY_SIZE}px; line-height:1.47; color:{C['ink2']}; margin:0 0 4px; max-width:620px; }}
.pb .chapter-head {{ display:grid; grid-template-columns:auto minmax(0,1fr); column-gap:22px; align-items:end; margin:0 0 18px;
  padding-bottom:14px; border-bottom:1.5px solid {C['accent']}; }}
.pb .chapter-head.nolabel {{ grid-template-columns:minmax(0,1fr); }}
.pb .ch-label {{ font-family:{SERIF_DISPLAY}; font-size:104px; line-height:0.8; font-weight:600; color:{C['accent']}; font-variant-numeric:lining-nums; }}
.pb .ch-kicker {{ font-family:{SANS}; font-size:13px; font-weight:700; color:{C['accent']}; letter-spacing:0.02em; margin-bottom:4px; }}
.pb .ch-title {{ font-family:{SERIF_DISPLAY}; font-size:38px; line-height:1.08; font-weight:600; color:{C['ink']}; margin:0; text-wrap:balance; }}
.pb .ch-intro {{ font-size:16.5px; line-height:1.5; color:{C['ink2']}; margin:0 0 16px; max-width:{self.MAIN_W + 100}px; }}
.pb h2.sec-h {{ font-family:{SANS}; font-size:20px; line-height:1.25; font-weight:700; color:{C['accent']}; margin:22px 0 10px; }}
.pb h2.sec-h.first {{ margin-top:0; }}

/* ---- tables ---- */
.pb table {{ width:100%; border-collapse:collapse; font-family:{SANS}; font-size:14px; line-height:1.38; color:{C['ink']};
  font-variant-numeric:lining-nums tabular-nums; margin:4px 0 14px; }}
.pb th {{ text-align:left; vertical-align:bottom; font-weight:700; background:{C['accent_tint']}; padding:7px 8px;
  border-top:1.5px solid {C['accent']}; border-bottom:1px solid {C['accent']}; }}
.pb td {{ text-align:left; vertical-align:top; padding:7px 8px; border-bottom:1px solid {C['rule']}; }}
.pb th p, .pb td p {{ margin:0; }}
.pb td ul, .pb td ol {{ margin:0; padding-left:16px; }}

/* ---- callouts, quotes, sources, figures ---- */
.pb .callout {{ padding:11px 15px; border-radius:2px; font-family:{SANS}; font-size:14px; line-height:1.45; margin:4px 0 14px; }}
.pb .callout p:last-child, .pb .callout ul:last-child {{ margin-bottom:0; }}
.pb .callout.note {{ background:{C['accent_tint']}; }}
.pb .callout.careful {{ background:{C['caution_tint']}; }}
.pb .callout .lbl {{ font-weight:700; }}
.pb .callout.note .lbl {{ color:{C['accent']}; }}
.pb .callout.careful .lbl {{ color:{C['caution']}; }}
.pb blockquote {{ margin:4px 0 12px; padding:10px 14px; background:#f5f3ee; border-radius:2px; font-family:{SANS}; font-size:14px; line-height:1.45; }}
.pb blockquote p {{ margin:0 0 7px; }}
.pb blockquote p:last-child {{ margin-bottom:0; }}
.pb .src-wrap {{ margin-top:10px; padding-top:7px; border-top:1px solid {C['rule']}; }}
.pb .src-wrap .rail-label {{ top:8px; color:{C['ink2']}; font-size:12px; }}
.pb .src {{ font-family:{SANS}; font-size:12.5px; line-height:1.4; color:{C['ink2']}; }}
.pb .src p {{ margin:0 0 4px; }}
.pb figure {{ margin:6px 0 16px; }}
.pb figure img {{ display:block; max-width:100%; max-height:{H - 360}px; margin:0 auto; }}
.pb figcaption {{ font-family:{SANS}; font-size:13px; line-height:1.4; color:{C['ink2']}; margin-top:8px; }}

/* ---- cards ---- */
.pb .card-wrap {{ margin-top:22px; }}
.pb .card-wrap.first {{ margin-top:0; }}
.pb .card-head {{ background:{C['accent_tint']}; padding:14px 16px 12px; border-radius:2px; margin:0 0 14px; font-family:{SANS}; }}
.pb .card-top {{ display:flex; justify-content:space-between; align-items:flex-start; gap:16px; }}
.pb .card-id {{ display:flex; align-items:center; gap:10px; }}
.pb .card-code {{ background:{C['accent']}; color:#fff; font-weight:700; font-size:14px; padding:2px 8px; border-radius:2px;
  font-variant-numeric:lining-nums; }}
.pb .card-kind {{ font-size:13px; font-weight:700; color:{C['accent']}; }}
.pb .card-action {{ border:1.3px solid {C['accent']}; border-radius:3px; padding:4px 9px; font-size:13px; font-weight:700; color:{C['ink']};
  max-width:230px; text-align:right; }}
.pb .card-action span {{ display:block; font-size:11.5px; font-weight:400; color:{C['ink2']}; }}
.pb .card-title {{ font-family:{SERIF_DISPLAY}; font-size:25px; line-height:1.14; font-weight:600; color:{C['ink']}; margin:8px 0 10px; text-wrap:balance; }}
.pb .card-ratings {{ display:grid; column-gap:14px; border-top:1px solid {C['rule']}; padding-top:9px; }}
.pb .rcell .rl {{ font-size:12px; color:{C['ink2']}; }}
.pb .rcell .rw {{ font-size:14.5px; font-weight:700; color:{C['ink']}; line-height:1.25; }}
.pb .rcell .rq {{ font-size:12px; color:{C['ink2']}; line-height:1.25; }}
.pb .meter {{ display:flex; gap:3px; margin-top:5px; }}
.pb .meter .seg {{ display:block; width:20px; height:9px; box-sizing:border-box; }}
.pb .card-meta {{ display:flex; flex-wrap:wrap; gap:3px 18px; font-size:13px; line-height:1.38; margin-top:10px; }}
.pb .card-meta b, .pb .card-note b {{ color:{C['accent']}; font-weight:700; margin-right:3px; }}
.pb .card-note {{ font-size:13px; line-height:1.38; margin-top:5px; color:{C['ink']}; }}

/* ---- contents and glossary ---- */
.pb .toc-row a {{ display:grid; grid-template-columns:minmax(0,1fr) 44px; column-gap:12px; align-items:baseline; }}
.pb .toc-row.lvl1 {{ font-family:{SANS}; font-size:15px; font-weight:700; margin-top:10px; color:{C['ink']}; }}
.pb .toc-row.lvl2 {{ font-family:{SANS}; font-size:13.5px; margin-left:{RW + G}px; color:{C['ink']}; padding:1px 0; }}
.pb .toc-row .toc-n {{ text-align:right; font-variant-numeric:lining-nums tabular-nums; color:{C['ink2']}; font-weight:700; }}
.pb .toc-row .toc-code {{ display:inline-block; min-width:38px; color:{C['accent']}; font-weight:700; }}
.pb .gl-row {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); column-gap:{G}px; border-bottom:1px solid #ebe8e1; }}
.pb .gl-entry {{ display:grid; grid-template-columns:minmax(0,1fr) 30px; column-gap:6px; font-family:{SANS}; font-size:13px; line-height:1.38; padding:5px 0; }}
.pb .gl-term {{ font-weight:700; color:{C['accent']}; }}
.pb .gl-pg {{ text-align:right; color:{C['ink2']}; font-variant-numeric:lining-nums tabular-nums; }}

/* ---- notices ---- */
.pb .notice {{ padding:12px 16px; background:{C['caution_tint']}; border-radius:2px; font-family:{SANS}; font-size:14px; line-height:1.45; margin:0 0 14px; }}
.pb .notice b.l {{ color:{C['caution']}; }}
"""

    def cover(self, book, edition, ed_cfg, image_src=None, image_alt=""):
        """A full-page cover: optional image band, kicker, title, subtitle, blurb, edition line and credit."""
        C, W, H, MX = self.C, self.W, self.H, self.MARGIN_X
        private = ed_cfg.get("private_mark")
        kicker = ed_cfg.get("kicker", book.get("kicker", ""))
        title = ed_cfg.get("title", book.get("title", ""))
        sub = ed_cfg.get("subtitle", book.get("subtitle", ""))
        blurb = ed_cfg.get("blurb", book.get("blurb", ""))
        left = ed_cfg.get("cover_line", f"{edition.capitalize()} edition")
        credit = book.get("cover_credit", "")
        band_h = 520 if image_src else 0
        top = band_h + 46 if image_src else 300
        img = (f'<img src="{escape(image_src, quote=True)}" alt="{escape(image_alt, quote=True)}" '
               f'style="position:absolute;left:0;top:0;width:{W}px;height:{band_h}px;object-fit:cover;display:block">'
               f'<div style="position:absolute;left:0;top:{band_h}px;width:{W}px;height:6px;background:{C["accent"]}"></div>') if image_src else \
              f'<div style="position:absolute;left:{MX}px;right:{MX}px;top:{top - 40}px;height:6px;background:{C["accent"]}"></div>'
        mark = (f'<div style="position:absolute;left:{MX}px;top:24px;background:#fff;color:{C["caution"]};font-family:{SANS};font-size:14px;'
                f'font-weight:700;padding:6px 10px;border-radius:3px;border:1.3px solid {C["caution"]}">{escape(private)}</div>') if private else ""
        kcol = C["caution"] if private else C["accent"]
        return (
            f'<div class="blk full atomic no-gloss" data-page-class="fullpage no-head no-folio no-footer cover" data-break="after">'
            f'<div style="position:relative;width:{W}px;height:{H}px">{img}{mark}'
            f'<div style="position:absolute;left:{MX}px;right:{MX}px;top:{top}px;display:flex;flex-direction:column;gap:14px">'
            f'<div style="font-family:{SANS};font-size:14px;font-weight:700;color:{kcol};letter-spacing:0.04em">{escape(kicker)}</div>'
            f'<h1 style="margin:0;font-family:{SERIF_DISPLAY};font-size:62px;line-height:1.02;font-weight:600;color:{C["ink"]};'
            f'letter-spacing:-0.01em;text-wrap:balance">{escape(title)}</h1>'
            f'<div style="font-family:{SERIF_DISPLAY};font-weight:400;font-size:25px;line-height:1.25;color:{C["ink"]};max-width:600px;'
            f'text-wrap:balance">{escape(sub)}</div>'
            f'<div style="font-family:{SERIF};font-size:16px;line-height:1.5;color:{C["ink2"]};max-width:580px;margin-top:6px">{escape(blurb)}</div></div>'
            f'<div style="position:absolute;left:{MX}px;right:{MX}px;bottom:44px;display:flex;justify-content:space-between;align-items:flex-end;'
            f'gap:24px;font-family:{SANS};font-size:12px;line-height:1.4;color:{C["ink2"]};border-top:1px solid {C["rule"]};padding-top:10px">'
            f'<div><b style="color:{C["ink"]}">{escape(left)}</b><br>{escape(book.get("date", ""))}</div>'
            f'<div style="text-align:right;max-width:390px">{escape(credit)}</div></div></div></div>')

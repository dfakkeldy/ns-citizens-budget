/* Textbook paginator.
 *
 * Flows the blocks in #flow onto fixed Letter pages. For every page it
 * computes the glossary footer from the terms actually placed on that page
 * (spans with data-t), measures it, and shrinks the body to fit. Blocks that
 * don't fit are split (paragraph lines, list items, table rows) or moved.
 * Because the footer is recomputed for exactly what is on the page before a
 * block is accepted, the result is correct by construction, in one pass.
 *
 * Inputs (set by build.py):
 *   window.GLOSSARY = {key: {kind, short, more, deps, depsShort}}
 *   window.EDITION  = {name, runningRight, privateMark (text or ''), reminders, labels}
 *   window.LAYOUT   = {pageW, pageH, bodyTop, footerBottom, footerGap}
 *
 * Block attributes it understands (set by build.py on top-level blocks):
 *   class "atomic"          never split; move whole to the next page
 *   data-keep="next"        keep on the same page as the start of the next block
 *   data-need="<px>"        start a new page unless this much room is left below it
 *   data-break="before|after"  page break
 *   data-page-class="..."   classes for the page it lands on (fullpage, no-head,
 *                           no-folio, no-footer, selfdef = glossary pages)
 *   .rh-set[data-rh]        sets the running head from the next page on
 * Output: .page elements in #pages; body[data-done="1"] when finished;
 *   #pagemap (JSON) with the terms, new terms and footer keys of each page.
 */
(function () {
  const LY = window.LAYOUT, G = window.GLOSSARY, E = window.EDITION, LB = E.labels;
  const PAGE_H = LY.pageH, BODY_TOP = LY.bodyTop, FOOTER_BOTTOM = LY.footerBottom, FOOTER_GAP = LY.footerGap;
  const SAFETY = 4, SPLIT_ALLOW = 18;

  const pagesEl = document.getElementById('pages');
  const flow = document.getElementById('flow');
  const defined = new Set();          // terms fully defined on an earlier page
  const recent = [];                  // defined terms, most recent last
  const pagemap = [];
  let page = null, pb = null, gf = null, rhText = '', pendingRh = null, pageNo = 0;

  // ---------------------------------------------------------------- helpers
  // "short: more" when the definition continues the phrase; "short. More" when it starts a sentence
  // web addresses in definitions become real links
  const links = h => h.replace(/\b((?:[a-z0-9-]+\.)+(?:com|org|net|gov|edu|int|info|io|ca|uk|au|nz|ie|eu|de|fr|nl|us)(?:\/[^\s<>()]*[^\s<>().,;:])?)/g,
    (m) => `<a class="ext" href="https://${m}">${m}</a>`);
  const joiner = m => (!m ? '' : /^[A-Z][a-z]/.test(m) ? '. ' : ': ');   // no stray colon when there is no 'more'
  const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  function termsIn(el, into) {
    if (!el.querySelectorAll) return into;
    if (el.dataset && el.dataset.t) into.push(el.dataset.t);
    el.querySelectorAll('[data-t]').forEach(s => into.push(s.dataset.t));
    return into;
  }

  function pageTerms() {
    const list = [];
    termsIn(page.querySelector('.rh'), list);
    termsIn(pb, list);
    const seen = new Set(), order = [];
    for (const k of list) if (G[k] && !seen.has(k)) { seen.add(k); order.push(k); }
    return order;
  }

  // Decide the footer entries for the given ordered term list.
  function footerModel(terms) {
    const news = [], rems = [];
    const selfdef = page && page.classList.contains('selfdef');
    if (selfdef) {
      // Glossary pages: an entry spells its own word out. Only words mentioned
      // on the page without their own entry need the footer.
      const own = new Set(Array.from(pb.querySelectorAll('[data-entry]')).map(e => e.dataset.entry));
      terms = terms.filter(k => !own.has(k) && G[k].kind === 'acronym');
    }
    const inNew = new Set(), inRem = new Set();
    const addNew = k => { if (!inNew.has(k)) { inNew.add(k); news.push(k); } };
    const addRem = k => { if (!inNew.has(k) && !inRem.has(k)) { inRem.add(k); rems.push(k); } };
    for (const k of terms) {
      if (!defined.has(k)) addNew(k);
      else if (G[k].kind === 'acronym') addRem(k);
    }
    let earlier = false;
    if (news.length === 0 && !selfdef && E.reminders) {
      // No new words: use the space for reminders of earlier definitions,
      // first of words on this page, else of the most recent definitions.
      for (const k of terms) if (G[k].kind !== 'acronym') addRem(k);
      if (rems.length === 0) {
        earlier = true;
        for (let i = recent.length - 1; i >= 0 && rems.length < 3; i--) addRem(recent[i]);
      }
    }
    // Close over definitions that mention other entries (deps).
    let changed = true;
    while (changed) {
      changed = false;
      const shown = news.map(k => [k, true]).concat(rems.map(k => [k, false]));
      for (const [k, full] of shown) {
        for (const d of ((full ? G[k].deps : G[k].depsShort) || [])) {
          if (!G[d] || inNew.has(d) || inRem.has(d)) continue;
          if (!defined.has(d)) addNew(d); else addRem(d);
          changed = true;
        }
      }
    }
    return {news, rems, earlier};
  }

  function renderFooter(model) {
    const {news, rems, earlier} = model;
    if (page.classList.contains('no-footer') || (!news.length && !rems.length)) { gf.innerHTML = ''; return 0; }
    let html = `<div class="gf-label">${esc(page.classList.contains('selfdef') ? LB.footer_glossary : LB.footer)}</div>`;
    if (news.length) {
      html += '<div class="gf-defs">' + news.map(k =>
        `<div class="gf-def"><b>${esc(k)}</b> ${esc(G[k].short)}${joiner(G[k].more)}${links(esc(G[k].more))}</div>`).join('') + '</div>';
    }
    if (rems.length) {
      html += `<div class="gf-rems"><span class="gf-rl">${esc(earlier ? LB.earlier : LB.also)}</span> ` +
        rems.map(k => `<span class="gf-rem"><b>${esc(k)}</b> ${esc(G[k].short)}</span>`).join('<span class="gf-dot"> · </span>') + '</div>';
    }
    gf.innerHTML = html;
    return gf.getBoundingClientRect().height;
  }

  function limitFor(footerH) {
    // Max bottom (relative to pb top) for body content.
    const bottom = footerH > 0 ? FOOTER_BOTTOM + footerH + FOOTER_GAP : FOOTER_BOTTOM;
    return PAGE_H - BODY_TOP - bottom - SAFETY;
  }

  function contentBottom() {
    const r = pb.getBoundingClientRect();
    return r.height;
  }

  function fits() {
    const h = renderFooter(footerModel(pageTerms()));
    if (page.classList.contains('fullpage')) return true;
    return contentBottom() <= limitFor(h);
  }

  function freeSpace() {
    const h = renderFooter(footerModel(pageTerms()));
    return limitFor(h) - contentBottom();
  }

  // ---------------------------------------------------------------- pages
  function newPage() {
    if (page) finishPage();
    pageNo++;
    page = document.createElement('section');
    page.className = 'page';
    page.dataset.n = pageNo;
    if (pendingRh !== null) { rhText = pendingRh; pendingRh = null; }
    page.innerHTML =
      `<div class="rh"><span class="rh-l">${rhText}</span><span class="rh-r">${E.privateMark ? `<span class="pm">${esc(E.privateMark)}</span>` : esc(E.runningRight)}</span></div>` +
      `<div class="pb"></div><div class="gf"></div><div class="folio">${pageNo}</div>`;
    pagesEl.appendChild(page);
    pb = page.querySelector('.pb');
    gf = page.querySelector('.gf');
  }

  function isEmpty() { return !pb || pb.children.length === 0; }

  function finishPage() {
    const terms = pageTerms();
    const model = footerModel(terms);
    renderFooter(model);
    if (page.classList.contains('no-footer')) gf.innerHTML = '';
    // Mark the first appearance of newly defined words.
    for (const k of model.news) {
      const s = pb.querySelector(`[data-t="${CSS.escape(k)}"]`);
      if (s) s.classList.add('gt-first');
    }
    for (const k of model.news) { defined.add(k); recent.push(k); }
    if (page.classList.contains('selfdef')) pb.querySelectorAll('[data-entry]').forEach(e => defined.add(e.dataset.entry));
    pagemap.push({page: pageNo, terms, news: model.news, rems: model.rems, cls: page.className});
    page.dataset.terms = terms.join('|');
    page.dataset.free = String(Math.round(limitFor(gf.getBoundingClientRect().height) - contentBottom()));
  }

  // ---------------------------------------------------------------- splitting
  function lineRects(el) {
    const range = document.createRange();
    range.selectNodeContents(el);
    const rects = Array.from(range.getClientRects()).filter(r => r.width > 0.5 && r.height > 0.5);
    // group into lines by top
    const lines = [];
    for (const r of rects) {
      const l = lines.find(x => Math.abs(x.top - r.top) < 3 || (r.top >= x.top - 1 && r.bottom <= x.bottom + 1));
      if (l) { l.top = Math.min(l.top, r.top); l.bottom = Math.max(l.bottom, r.bottom); }
      else lines.push({top: r.top, bottom: r.bottom});
    }
    lines.sort((a, b) => a.top - b.top);
    return lines;
  }

  function textPositionAt(el, yTop) {
    // First (node, offset) whose glyph box top >= yTop.
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    const range = document.createRange();
    let n;
    while ((n = walker.nextNode())) {
      const len = n.data.length;
      if (!len) continue;
      range.selectNodeContents(n);
      const rr = range.getBoundingClientRect();
      if (rr.bottom <= yTop + 1) continue;
      let lo = 0, hi = len;  // find first offset whose char top >= yTop
      while (lo < hi) {
        const mid = (lo + hi) >> 1;
        range.setStart(n, mid); range.setEnd(n, Math.min(mid + 1, len));
        const rs = Array.from(range.getClientRects()).filter(r => r.width > 0.2);
        const top = rs.length ? rs[rs.length - 1].top : range.getBoundingClientRect().top;
        if (top >= yTop - 1) hi = mid; else lo = mid + 1;
      }
      if (lo < len) {
        // move back to the start of the word
        while (lo > 0 && !/\s/.test(n.data[lo - 1])) lo--;
        return {node: n, offset: lo};
      }
    }
    return null;
  }

  function splitText(el, limitAbs) {
    const lines = lineRects(el);
    const n = lines.length;
    if (n < 4) return null;
    let k = 0;
    while (k < n && lines[k].bottom <= limitAbs) k++;
    k = Math.min(k, n - 2);           // keep 2 lines for the next page (widows)
    if (k < 2) return null;           // need 2 lines here (orphans)
    const pos = textPositionAt(el, lines[k].top);
    if (!pos) return null;
    const r2 = document.createRange();
    r2.setStart(pos.node, pos.offset);
    r2.setEndAfter(el.lastChild);
    const rest = el.cloneNode(false);
    rest.appendChild(r2.extractContents());
    rest.classList.add('cont');
    el.dataset.textsplit = '1';       // split between lines, so the page should end within about a line
    // trim leading whitespace of the continuation
    const w = document.createTreeWalker(rest, NodeFilter.SHOW_TEXT);
    const t = w.nextNode(); if (t) t.data = t.data.replace(/^\s+/, '');
    return rest;
  }

  const TEXTY = new Set(['P', 'H5']);

  function isLabel(el) {
    const t = (el.textContent || '').trim();
    if (!t) return false;
    if (/:$/.test(t)) return true;          // any lead-in ending with a colon
    if (t.length > 90) return false;
    if (/^H\d$/.test(el.tagName)) return true;
    const kids = Array.from(el.childNodes).filter(n => !(n.nodeType === 3 && !n.data.trim()));
    return kids.length === 1 && /^(STRONG|B)$/.test(kids[0].nodeName || '');
  }

  function isTextBlock(el) {
    if (TEXTY.has(el.tagName)) return true;
    if (el.tagName === 'LI' || el.tagName === 'DIV') {
      // text-level only (no block children)
      return !Array.from(el.children).some(c => /^(P|UL|OL|DIV|TABLE|H\d)$/.test(c.tagName));
    }
    return false;
  }

  // Split `el` (already on the page) so its content ends above limitAbs.
  // Returns the remainder element for the next page, or null if nothing can stay.
  function split(el, limitAbs) {
    if (el.classList && (el.classList.contains('atomic') || /^H\d$/.test(el.tagName))) return null;
    if (el.tagName === 'TABLE') {
      const rows = Array.from(el.tBodies[0] ? el.tBodies[0].rows : []);
      let i = 0;
      while (i < rows.length && rows[i].getBoundingClientRect().bottom <= limitAbs) i++;
      if (i >= rows.length) return null;
      if (rows.length - i < 2) i = rows.length - 2;   // never carry a single row over
      if (i < 2) return null;                          // never leave a single row behind
      const rest = el.cloneNode(false);
      if (el.tHead) rest.appendChild(el.tHead.cloneNode(true));
      const tb = el.tBodies[0].cloneNode(false);
      rest.appendChild(tb);
      rows.slice(i).forEach(r => tb.appendChild(r));
      rest.classList.add('cont');
      return rest;
    }
    if (isTextBlock(el)) return splitText(el, limitAbs);
    // container: UL, OL, LI with blocks, DIV
    const BLOCKS = /^(P|UL|OL|LI|DIV|TABLE|H\d|BLOCKQUOTE|FIGURE|SECTION)$/;
    const kids = Array.from(el.children).filter(c => BLOCKS.test(c.tagName) && !c.classList.contains('rail-label'));
    let i = 0;
    while (i < kids.length && kids[i].getBoundingClientRect().bottom <= limitAbs) i++;
    if (i >= kids.length) return null;
    let partial = split(kids[i], limitAbs);
    // Don't leave a lead-in label ("Actions:", a bold one-liner) as the last
    // thing on the page: move it with what it introduces.
    if (!partial && i > 0 && isLabel(kids[i - 1])) i--;
    if (i === 0 && !partial) return null;
    const rest = el.cloneNode(false);
    rest.classList.add('cont');
    rest.removeAttribute('id');
    if (partial) { rest.appendChild(partial); }
    const moveFrom = partial ? i + 1 : i;
    kids.slice(moveFrom).forEach(k => rest.appendChild(k));
    if (el.tagName === 'OL') {
      const start = parseInt(el.getAttribute('start') || '1', 10);
      rest.setAttribute('start', String(start + (partial ? i : i)));
    }
    if (partial && partial.tagName === 'LI') partial.classList.add('cont');
    return rest;
  }

  // ---------------------------------------------------------------- placing
  // Try to place `el` on the current page, splitting if needed.
  // Returns: 'all' | {rest} | 'none'
  function place(el) {
    pb.appendChild(el);
    if (fits()) return 'all';
    el.remove();
    if (el.classList.contains('atomic')) return 'none';
    // Split a copy, so a failed attempt never damages the original. Retry
    // with more room if padding and margins push the kept part over.
    for (let attempt = 0; attempt < 5; attempt++) {
      const trial = el.cloneNode(true);
      pb.appendChild(trial);
      const fh = renderFooter(footerModel(pageTerms()));
      const limitAbs = pb.getBoundingClientRect().top + limitFor(fh) - SPLIT_ALLOW - attempt * 24;
      const rest = split(trial, limitAbs);
      if (!rest) { trial.remove(); break; }
      if (fits()) return refill(el, trial, rest, attempt);
      trial.remove();
    }
    renderFooter(footerModel(pageTerms()));
    return 'none';
  }

  // The split point above was chosen with the footer of the WHOLE block on the page. Terms that
  // moved to the next page no longer need footer space, so the kept part can often hold more
  // lines. Re-split a fresh copy against the smaller footer until it stops gaining.
  function refill(el, trial, rest, attempt) {
    let best = {rest, placed: trial};
    best.placed.dataset.split = '1';
    for (let pass = 0; pass < 3; pass++) {
      const before = best.placed.getBoundingClientRect().bottom;
      const fh = renderFooter(footerModel(pageTerms()));
      const limitAbs = pb.getBoundingClientRect().top + limitFor(fh) - SPLIT_ALLOW - attempt * 24;
      if (limitAbs <= before + 1) break;
      best.placed.remove();
      const t2 = el.cloneNode(true);
      pb.appendChild(t2);
      const r2 = split(t2, limitAbs);
      if (r2 && fits() && t2.getBoundingClientRect().bottom > before + 1) {
        t2.dataset.split = '1';
        best = {rest: r2, placed: t2};
        continue;
      }
      t2.remove();
      pb.appendChild(best.placed);
      break;
    }
    renderFooter(footerModel(pageTerms()));
    return best;
  }

  function run() {
    const blocks = Array.from(flow.children);
    newPage();
    for (let bi = 0; bi < blocks.length; bi++) {
      let el = blocks[bi];
      if (el.classList.contains('rh-set')) {
        const txt = el.dataset.rh;
        if (isEmpty()) { rhText = txt; page.querySelector('.rh-l').innerHTML = txt; }
        else pendingRh = txt;
        continue;
      }
      if (el.dataset.break === 'before' && !isEmpty()) newPage();
      if (el.dataset.need && !isEmpty()) {
        pb.appendChild(el);
        const h = el.getBoundingClientRect().height;
        el.remove();
        if (freeSpace() < parseFloat(el.dataset.need) + h) newPage();
      }
      if (el.dataset.pageClass) page.classList.add(...el.dataset.pageClass.split(' '));
      // keep-with-next: place this block and at least the start of the next
      if (el.dataset.keep === 'next' && bi + 1 < blocks.length) {
        const group = [el];
        let j = bi + 1;
        while (j < blocks.length && blocks[j].dataset.keep === 'next' && !blocks[j].classList.contains('rh-set')) { group.push(blocks[j]); j++; }
        const next = blocks[j];
        const tryGroup = () => {
          for (const g of group) pb.appendChild(g);
          if (!fits()) { group.forEach(g => g.remove()); return false; }
          if (!next) return true;
          const probe = next.cloneNode(true);
          const r = place(probe);
          if (r === 'none') { group.forEach(g => g.remove()); return false; }
          if (r === 'all') probe.remove(); else r.placed.remove();
          // restore any footer state
          renderFooter(footerModel(pageTerms()));
          return true;
        };
        if (!tryGroup()) {
          if (!isEmpty()) { newPage(); if (!tryGroup()) { for (const g of group) pb.appendChild(g); } }
          else { for (const g of group) pb.appendChild(g); }
        }
        bi = j - 1;
        if (el.dataset.break === 'after') newPage();
        continue;
      }
      // normal block
      let cur = el;
      let guard = 0;
      while (cur && guard++ < 200) {
        const r = place(cur);
        if (r === 'all') { cur = null; break; }
        if (r === 'none') {
          if (isEmpty()) { pb.appendChild(cur); cur = null; break; } // too big: overflow (flagged)
          newPage();
          if (el.dataset.pageClass) page.classList.add(...el.dataset.pageClass.split(' '));
          continue;
        }
        cur = r.rest;
        newPage();
        if (el.dataset.pageClass) page.classList.add(...el.dataset.pageClass.split(' '));
      }
      if (el.dataset.break === 'after') newPage();
    }
    finishPage();
    page = null;
    // drop an empty trailing page
    const last = pagesEl.lastElementChild;
    if (last && last.querySelector('.pb').children.length === 0) last.remove();
    // glossary: page where each word was first defined
    const firstNew = {};
    for (const p of pagemap) for (const k of p.news) if (!(k in firstNew)) firstNew[k] = p.page;
    for (const p of pagemap) for (const k of p.terms) if (!(k in firstNew)) firstNew[k] = p.page;
    document.querySelectorAll('[data-gl-pg]').forEach(s => { s.textContent = firstNew[s.dataset.glPg] || '—'; });
    // table of contents page numbers
    document.querySelectorAll('[data-toc-target]').forEach(a => {
      const t = document.getElementById(a.dataset.tocTarget);
      const pg = t && t.closest('.page');
      a.querySelector('.toc-n').textContent = pg ? pg.dataset.n : '?';
    });
    // overflow report
    const over = [];
    document.querySelectorAll('.page').forEach(p => {
      const pbb = p.querySelector('.pb').getBoundingClientRect();
      const gft = p.querySelector('.gf').getBoundingClientRect();
      if (p.querySelector('.gf').children.length && pbb.bottom > gft.top - 2) over.push(p.dataset.n);
    });
    flow.remove();
    const pm = document.createElement('script');
    pm.type = 'application/json'; pm.id = 'pagemap';
    pm.textContent = JSON.stringify({pages: pagemap, overflow: over});
    document.body.appendChild(pm);
    document.body.dataset.done = '1';
  }

  window.__paginate = run;
})();

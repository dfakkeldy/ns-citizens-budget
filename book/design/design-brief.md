# Design brief: Own costs first (Budget 2027-28 submission)

3 October 2026. A citizen's written submission to Nova Scotia's "Building Our Budget Together" consultation: a plan the government can adopt now (Plan A) and a priced path to balance without new taxes (Plan B), for Finance officials and the advisory committee to act on.

## The user's words

- "Make a sensible budget that would be hard for the government to ignore, and hard for the public to rail against."
- "Make the PDF look really professional and eye-catching."
- On the style: "do the hybrid": an eye-catching front from the design canvas, the body from the field-guide engine.

## Readers and editions

- Readers: Department of Finance and Treasury Board staff, the Building Our Budget Together advisory committee, MLAs, and possibly the public if the user shares it. Read on screen as an email attachment, and printed at home or in an office in black and white.
- One public edition. It must contain nothing private: no file paths, no private project notes, no email address other than budget@novascotia.ca, no FOIPOP request numbers.
- Length target: about 16-20 pages including front pages, glossary and sources.

## Direction: "Harbour ledger"

Professional and eye-catching at the front, calm and evidence-first inside. The one memorable thing: the front pages' charts (the $590M bar and the deficit path with Plan B's line) and, inside, the Plan B lever cards with honest rating meters.

- Front (fixed pages, laid out by hand, rendered separately and merged first):
  1. Cover: large "Own costs first." headline (Instrument Serif), the one-sentence pitch, a navy band with the two hook numbers, faint sea-chart contour lines, name and town, "Not affiliated with the Government of Nova Scotia". No abbreviations on the cover.
  2. At a glance: Plan A and Plan B side by side, the result of each, and the "not cut in either plan" strip.
  3. Where things stand: the $590M bar, the deficit path (plan, Plan A, Plan B, overrun risk), and why the consultation tool can't balance it.
- Body (engine, rail layout, Letter): chapters with side heads, tables that continue, Plan B lever cards, glossary footers on every page.
- Paper: white in the body (prints cleanly); the front pages may use the canvas's cool off-white #F4F6F7. Near-black ink. Everything must read in greyscale.
- No gradients, no emoji, no drop shadows, no rounded cards with a coloured left border.

## Page grid (engine defaults)

US Letter 816 × 1056 px. Margins 72 px; running head at 36 px; body from 92 px. Content 672 px: 144 px rail, 24 px gutter, 504 px main column. Tables, card headers and the footer span the full width. Footer computed per page.

## Typography

- Body (engine): Source Serif 4 for reading and display; Atkinson Hyperlegible Next for small and functional text. Engine scale unchanged.
- Front pages: Instrument Serif for the big headlines only; Atkinson Hyperlegible Next for text (the same static files as the body); IBM Plex Mono for chart numbers. All embedded as TrueType (`pdffonts` must show no Type 3).

## Colour tokens

| Token | Hex | Use |
|---|---|---|
| ink | #1d1c1a | body text |
| ink2 | #4a4843 | secondary text |
| accent | #13293D | harbour navy: headings, side heads, meters, Plan A |
| accent_tint | #E3E9EF | card ground, table heads, notes |
| accent_mid | #9AA6B1 | meter outlines, the plan line in charts |
| caution | #B9481C | buoy orange: risks, overruns, Plan B, careful panels |
| caution_tint | #F7E3D8 | caution panels |

## Components

- Plan B lever cards: code (B-W, B-H, B-D), title, kind, ratings (2029-30 saving, evidence, risk to services, who pushes back), When/Who line, one line of reasoning per rating.
- Tables for Plan A measures (2027-28 and 2029-30 columns), totals in bold.
- `::: careful` panels for the honest caveats (what the numbers assume).
- `::: source` notes for references; the full source list at the end.

## What the submission must never do

- No allegation without a document; say what the record shows.
- Date every fact ("as of 3 October 2026"); mark estimates and assumptions as such.
- Never speak for unions, Mi'kmaw communities, municipalities or other groups; say what they have said publicly, with the source.
- No tax or fee increases and no legislated wage restraint proposed anywhere.
- Plain language first; numbers and formal references in tables and source notes.

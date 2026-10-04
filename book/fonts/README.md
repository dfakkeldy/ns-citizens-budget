# Fonts

The book's text fonts, Source Serif 4 and Atkinson Hyperlegible Next, are not stored in this repository. `build/fonts.py` downloads them from Google Fonts and cuts static TrueType instances into `fonts/static/`, with a matching `fonts/fonts.css`. Run it once before the first build; the GitHub check runs it on every pull request.

Both fonts are licensed under the SIL Open Font License, Version 1.1. Their licence texts are in `licenses/`. The cut instances are renamed (TB Serif, TB Serif Display, TB Sans) as the licence requires for modified versions, and are embedded in the PDFs.

The front pages use Instrument Serif and IBM Plex Mono. They are in `../front/fonts/` unmodified, with their licence texts beside them.

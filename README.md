# Own costs first: a citizen's budget for Nova Scotia

A citizen's submission to Nova Scotia's *Building Our Budget Together* consultation on the 2027-28 budget, in two documents:

- **Own costs first** (41 pages). **Plan A** makes the government's own savings plan real: it names where $85.5 million of the $590 million can come from, government's own costs first, keeps health savings in health, and adds rules so the plan sticks. **Plan B** shows how close negotiated restraint could get to balance without raising taxes: about $560 million in 2029-30, against $862 million in the plan.
- **Planning for AI** (8 pages), a companion paper. It asks the province to plan rather than bet on AI: avoid long lock-ins, measure before scaling, and set checkpoints.

Version 1.0 was emailed to budget@novascotia.ca on October 5, 2026. **Download the PDFs from [Releases](../../releases/latest).** Facts are as of October 3, 2026.

Written by Dan Fakkeldy, Judique, Inverness County. Not affiliated with the Government of Nova Scotia.

## Help improve it

Somebody will think of something we haven't. If you can make this better, with a better idea, a correction, newer numbers or clearer wording, please:

- **Open an issue** (no coding needed): report an error, suggest a change, or propose a measure.
- **Open a pull request** if you're comfortable editing the Markdown. Every pull request rebuilds both PDFs and runs every check automatically, and you can download the result.

Dan checks every change himself before it goes in. See [CONTRIBUTING.md](CONTRIBUTING.md).

### Fixed principles

Contributions work inside these. Proposals to change a principle belong in [Discussions](../../discussions), not a pull request.

1. No tax or fee increases. The one exception is the companion paper's disclosed charge on qualifying new large power loads of 25 MW or more, which is not levied on existing loads or households.
2. No legislated wage restraint: pay restraint is negotiated, never legislated.
3. No front-line cuts to care, classrooms, seniors' care, disability or income supports, or housing.
4. Nothing pushed onto municipalities.

## How it was made

- **Research and drafting:** done with Claude (Anthropic), working from primary documents: budgets, estimates, Public Accounts, Auditor General reports, legislation, agreements and the consultation tool's data. Every figure is tied to a numbered source with its page.
- **Review:** each version was reviewed adversarially by Codex (OpenAI), round by round, until it approved. That came to eight rounds for the main submission and four for the companion. Every finding was checked against the cited source before it was fixed or rejected.
- **Automatic checks** on every build:
  - every abbreviation is explained on the page where it appears
  - every word of the source text reaches the PDF exactly once
  - every citation resolves
  - the model's outputs are current, and the headline numbers in the text match the model
  - no stranded headings or early page breaks
  - no private file paths
- **The numbers** come from small Python scripts in `model/`, which anyone can rerun.

## Repository layout

| Folder | What it holds |
|---|---|
| `book/` | The main submission: Markdown chapters (`src/chapters/`), cards and glossary, the designed front pages (`front/front.html`), and the build engine and checks (`build/`) |
| `companion/` | *Planning for AI*: Markdown source, style sheet and build script |
| `model/` | Deficit path and interest (`path.py`), Plan B (`plan_b_final.py`), debt ratio, the simulator check, and their saved outputs |
| `research/plan-b/` | Plan B's lever arithmetic (`plan_b.py`) |
| `simulator-data-2026-10-03/` | The consultation tool's public reference data, as captured on October 3, 2026 |
| `SIMULATOR-PLAYBOOK.md` | How the author entered his choices in the online tool |

The local copies of the source documents are not published, for copyright reasons. The bibliographies link to every source.

## Build it yourself

Needs Python 3, Node, pandoc, poppler (`pdftotext`, `pdfinfo`) and Google Chrome. Set `CHROME=/path/to/chrome` if Chrome isn't in the usual place.

```bash
cd book
python3 -m venv .venv && .venv/bin/pip install -r build/requirements.txt
(cd build && npm ci)
.venv/bin/python build/fonts.py      # once: downloads and cuts the fonts
./build_all.sh                       # model check, citations, build, every check, merged PDF
cd .. && companion/build.sh          # the companion paper
```

## Licences

- **Code:** MIT ([LICENSE](LICENSE)).
- **Text and PDFs:** CC BY 4.0 ([LICENSE-TEXT.md](LICENSE-TEXT.md)).
- **Fonts:** SIL Open Font License 1.1 ([book/fonts/README.md](book/fonts/README.md)).

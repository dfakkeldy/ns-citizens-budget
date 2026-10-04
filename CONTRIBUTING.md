# Contributing

Thank you. The point of publishing this is that someone will see what we missed.

## Ways to help

- **Report an error:** a wrong number, an outdated fact or a broken link. Use the "Report an error" issue form.
- **Suggest a change:** better wording, a clearer explanation or a missing caveat. Use "Suggest a change".
- **Propose a measure:** a saving, a protection, a rule or a question for the budget. Use "Propose a measure".
- **Edit directly:** open a pull request. You can edit Markdown files in GitHub's web editor, and it will offer to open the pull request for you.

To change one of the fixed principles (see the README), start a Discussion instead.

## How changes are checked

There is no required evidence standard. Dan checks every change himself, from first principles, before merging. It helps him if you say where a figure came from, but you don't have to.

Every pull request is also checked automatically. GitHub rebuilds both PDFs and runs every check, and the PDFs are attached to the run so you can see your change on the page. A pull request needs those checks to pass and Dan's approval before it is merged.

## Writing style

The documents aim to be hard to dismiss and hard to rail against. Changes fit best when they:

- **are plainly written:** plain Canadian English and short sentences, with no em dashes;
- **are dated:** facts are dated, because numbers change;
- **are labelled:** estimates say "my estimate" or "illustrative";
- **speak only for the author:** they don't speak for unions, Mi'kmaw communities, municipalities or other groups, and report only their documented positions.

## Where things are

- **Main submission text:** `book/src/chapters/*.md`. The Plan B cards are in `book/src/cards.yaml`, the glossary that feeds the page footers is in `book/src/glossary.yaml`, and the sources are in `book/src/chapters/99-sources.md`.
- **Front pages** (cover, at a glance, charts): `book/front/front.html`. The charts are drawn by hand from the model's numbers, so if a headline number changes, the chart needs updating too. Say so in your pull request and Dan will help.
- **Companion:** `companion/planning-for-ai-2027-28.md`. Its sources are at the end of the file.

## Changing a number

The numbers come from the model, not the text.

1. Edit the measure in `model/proposals/final-measures.json` (values by year and its `basis`).
2. Rerun the model and commit the outputs:

   ```bash
   cd model
   python3 -B path.py proposals/final-measures.json > proposals/final-path-output.txt
   python3 -B proposals/final-debt-check.py proposals/final-measures.json > proposals/final-debt-check-output.txt
   python3 -B plan_b_final.py > proposals/plan-b-final-output.txt
   (cd ../research/plan-b && python3 -B plan_b.py > plan_b.out.txt)
   ```
3. Update the text and tables that print the changed figures. The check `book/build/check_numbers.py` fails if the front pages or chapters 2 and 3 still show an old headline number.

## New sources

Add a new source at the end of the numbered list rather than renumbering, and cite it as `[n]` in the text. The citation check fails if a citation has no entry, or an entry is never cited. For web pages and news, an archive link (web.archive.org) helps, because pages change.

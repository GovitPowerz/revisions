# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

Static quiz site for exam revision, used by a student in Terminale générale (France) preparing the baccalauréat. Almost every task here is "write a new quiz on chapter X"; changes to the app itself are rare.

Live site: https://govitpowerz.github.io/revisions/ (GitHub Pages, legacy build, served from the root of `main`). Merging to `main` is the deployment. The repository is public: never commit photos of course notes, names, or other personal details.

## Commands

The site has no build step, no package manager, no linter and no test suite. The only build is for the printable exercise series:

```
uv run --with reportlab --with matplotlib python exercices/maths/probabilites-loi-binomiale-serie-1.py
```

Run locally (the site fetches its JSON over HTTP, so opening `index.html` from disk does not work):

```
python3 -m http.server 8000
```

Check a quiz file before committing (20 questions, 4 distinct answers each, explanation present, split by category):

```
node -e 'const q=require("./quiz/svt/atmosphere-terrestre-vie.json");console.log(q.questions.length);q.questions.forEach((x,i)=>{if(x.reponses.length!==4||new Set(x.reponses).size!==4||!x.explication)console.log("BAD",i+1)});const c={};q.questions.forEach(x=>c[x.categorie]=(c[x.categorie]||0)+1);console.log(c)'
```

Then open `#/<subject>/<topic>` in a browser and play the quiz through to the result screen.

## Architecture

- `index.html` is the only page. `assets/app.js` is one IIFE with a hash router and three views: `#/` (subjects), `#/<subject>` (topics), `#/<subject>/<topic>` (quiz).
- `quiz/catalogue.json` lists subjects (`matieres`) and their topics (`themes`); each topic points to one quiz file through `fichier`. Adding a subject or a quiz is a data-only change: no code to touch.
- JSON keys are in French (`matieres`, `themes`, `titre`, `niveau`, `fichier`, `questions`, `reponses`, `explication`, `indice`, `categorie`). The full format is documented in `README.md`, section "Ajouter un quiz".
- `exercices/<subject>/<topic>-serie-N.pdf` is a printable series of exercises with corrections, committed next to the `.py` of the same name that builds it (ReportLab for layout, matplotlib for figures and display formulas). The script holds all the text; edit it and rebuild, never the PDF. The build is reproducible (ReportLab `invariant` mode): rebuilding an unchanged script with the same library versions leaves the PDF byte-identical. The site does not link the series; GitHub Pages serves them at their path.

Invariants that are not obvious from a single file:

- The first entry of `reponses` is the correct answer. The app shuffles the display order and treats answer index 0 as "correct" everywhere (scoring, pips, review).
- `question`, `reponses`, `explication` and `indice` are inserted as raw HTML; catalogue fields and `categorie` are escaped. So quiz text can use `<sub>`/`<sup>`, but a literal `<` or `&` there must be written as an entity, and HTML in `titre`, `description` or `categorie` shows up as text.
- `questions` in the catalogue entry is a hand-written count; keep it equal to the length of the quiz file's `questions` array.
- `id` values are URLs and storage keys: the best score lives in `localStorage` under `revisions:best:<subject>/<topic>`. Renaming an id breaks shared links and orphans stored scores.
- The per-category score split only appears when a quiz has at least two distinct `categorie` values.

## Writing a quiz

- Sources, in order: the student's own course notes when provided (usually photos), then the official programme. Cover what the course actually covered; the programme fills gaps (expected skills, exact figures) and settles the scope. Say in the final report which programme items were left out.
- Official programmes: the Bulletin officiel PDFs on `cache.media.education.gouv.fr` can be downloaded and read with `pdftotext -layout`; `eduscol.education.gouv.fr` and `education.gouv.fr/bo` answer 403 to automated fetches. Terminale enseignement scientifique: `https://cache.media.education.gouv.fr/file/SPE8_MENJ_25_7_2019/84/7/spe241_annexe_1158847.pdf`. Terminale spécialité maths: `https://cache.media.education.gouv.fr/file/SPE8_MENJ_25_7_2019/90/7/spe246_annexe_1158907.pdf` (in force through 2026-2027; a new Terminale programme, BO n°14 of 2 April 2026, applies from September 2027).
- If the notes contain an error or contradict the programme, report it to the user; do not silently build questions on it.
- Format used so far: 20 questions, 4 answers, 2 to 4 categories following the structure of the course, an `explication` on every question, an `indice` on roughly one question in three.
- Distractors must be plausible and close in length to the correct answer: the order is shuffled, so a correct answer that is always the longest gives itself away. Prefer distractors that are real confusions (a date from another event of the chapter, the inverse process, a neighbouring notion).
- Explanations teach: state the rule, then name the confusion behind the wrong answers.
- All site content is in French and addresses the student as "tu". Typography: decimal comma (`4,6`), `×`, the minus sign `−` (U+2212) in exponents, `«` `»` for quotes, `<sub>`/`<sup>` for formulas (`CO<sub>2</sub>`). Maths: `−` for every minus sign, `≤`/`≥` (never a literal `<`), `ℬ(n ; p)` with a semicolon because of the decimal comma, and binomial coefficients written « k parmi n » since the app has no stacked notation.
- Enseignement scientifique chapters go under the subject of the discipline that teaches them (`svt`, `physique-chimie`), with `"niveau": "Terminale enseignement scientifique"` in the catalogue.
- When a new subject is added, also update the one-line site description in `README.md` and in the `<meta name="description">` of `index.html`.

## Writing an exercise series

- Format: 5 bac-style exercises of about 20 minutes each (calculator allowed), each starting on a new page, with a pink subtitle naming the notions and numbered questions (parts A/B when useful); then a "Corrigés" section, each correction starting on a new page. The first page states where the corrections start; the script finds that page with a first build pass.
- Start from an existing series script and replace only `TITLE`, `LEVEL` and `content()`, so every series keeps the same layout. Same sources and scope rules as quizzes.
- Statements use the impersonal bac style ("Calculer", "Montrer que"), not "tu". Corrections show the computation, then name the classic mistake, like quiz explanations.
- Compute every number with a script before writing it into the text.
- Check by rendering every page (`pdftoppm -r 70 -png`) and looking at it: no formula, table or code block cut from its lead-in line, no orphaned `?` or `:`.
- ReportLab traps: `keepWithNext` does not chain into a `KeepTogether`, so formula images, tables and code blocks are returned as bare flowables; French spaces before `? : ; » € %` and spaces inside `P(...)`, `E(...)`, `V(...)` become non-breaking in `fr()`; a combining overline is drawn on the letter, so complements are written with `bar()`. Mathtext traps: use `\dfrac` for display-size fractions and `\genfrac{(}{)}{0}{0}{n}{k}` for binomial coefficients (`\dbinom` does not exist).

## Git

Every quiz branch appends to `quiz/catalogue.json`. When several quiz branches are open at once, rebase on `origin/main` before merging and re-check that the catalogue still parses and lists every quiz.

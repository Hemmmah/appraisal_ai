---
name: appraisal-ai
description: >
  Automated appraisal report drafting pipeline. Scans project workfiles
  (PDFs, deeds, assessor cards, CoStar reports), extracts structured data,
  and generates Word narrative drafts with tracked changes and Excel
  adjustment grids from master templates. Supports land-only, improved,
  condemnation, and custom template packs.
metadata: {"clawdbot":{"emoji":"🏠","requires":{"bins":["python3"]}}}
---

# Appraisal AI — Report Drafting Pipeline

Generates **Word narrative drafts with tracked changes** and **Excel adjustment grids** from master templates and project workfile data. Every substitution is visible in Word Review mode — accept or reject each change.

## Prerequisites

This skill requires the `appraisal_ai` repo installed locally:

```
~/appraisal_ai/
├── scripts/utils.py          — core utilities
├── templates/<pack-name>/    — template packs (narrative.docx, grid.xlsx, reference-data.md)
├── .claude/agents/           — agent specs for the pipeline
├── .claude/skills/           — slash command definitions
├── CLAUDE.md                 — full rules, workflow, and lessons learned
└── requirements.txt          — Python dependencies
```

Set up the virtual environment (one time):

```bash
python3 -m venv ~/appraisal_ai/venv
~/appraisal_ai/venv/bin/pip install -r ~/appraisal_ai/requirements.txt
```

Always run scripts with `~/appraisal_ai/venv/bin/python`.

## Project Folder Structure

Each appraisal project uses this layout:

```
2026-NNN Address/
├── Subject/         — engagement letter, assessor card, deed, LOI, CoStar
├── Narrative/       — output drafts go here
├── Comparables/     — comp sheets, CoStar/MLS printouts, sale data
├── Exhibits/        — maps, photos, figures
└── Template/        — completed appraisal .docx and grid .xlsx
```

## Pipeline (5 Phases)

The full pipeline dispatches 10 agents across 5 phases.

### Phase 1 — Read (3 agents, parallel)
Subject Reader, Comp Reader, Exhibit Reader scan all project documents. PDFs are split before reading with `split_pdf()` from `scripts/utils.py` (3 pages/chunk for scanned docs, 5 for text-heavy).

### Phase 2 — Extract (2 agents, parallel → pause)
Field Extractor builds `data.md`. Comp Grid Agent builds `comp_grid.md`. **Pauses for user review** of `*** UPDATE ***` and `*** VERIFY ***` fields before continuing.

### Phase 3 — Build (3 steps)
Comp Writer generates `comp_writeups.md` from source documents → then Draft Builder + Grid Builder run in parallel. Draft uses Word XML tracked changes (`w:del` + `w:ins`). Grid writes to named Excel sheets (never `wb.active`).

### Phase 4 — Review (2 agents, parallel)
QA Reviewer checks data consistency. USPAP Reviewer checks compliance. Auto-fix loop runs up to 2 iterations — rebuild is mandatory after every fix.

### Phase 5 — Final Review (blocks delivery)
Cross-check grid vs. narrative vs. data.md. Verify tracked changes, formula cells preserved, adjustment rows untouched. **No files delivered to the user until Phase 5 passes.**

## Data Files

Project data uses structured Markdown:

- `data.md` — project fields (address, dates, values, parties, etc.)
- `comp_grid.md` — comparable sale data (price, SF, date, grantor/grantee)
- `comp_writeups.md` — narrative prose for each comparable sale
- `templates/<type>/reference-data.md` — template replacement values

Load and save with `load_md()` / `save_md()` from `scripts/utils.py`.

## Template Packs

Each pack in `templates/<name>/` contains:

- `narrative.docx` — master template (user-provided, not in git)
- `grid.xlsx` — adjustment grid template (optional, user-provided)
- `reference-data.md` — every replaceable text string extracted from the template

Custom packs follow the same structure. The user supplies their own completed appraisal as the master template.

## Key Utilities (`scripts/utils.py`)

- `extract_docx_text(path)` — extract text from .docx (never read .docx with file tools — it's binary XML)
- `extract_xlsx_text(path)` — extract text from .xlsx
- `split_pdf(path, pages_per_chunk)` — split large PDFs into readable chunks
- `load_md(path)` / `save_md(data, path)` — structured Markdown data I/O
- Tracked change builders: `tracked_replace_in_run()`, `tracked_replace_across_runs()`, `tracked_delete_paragraph()`
- Table helpers: `find_table_by_text()`, `set_cell_text()`, `add_table_row()`
- Word XML safety: `next_change_id()`, `get_date()`, `make_tracked_delete()`

## Word XML — Mandatory on Every Save

Three rules prevent Word "unreadable content" errors:

1. **Double-quote XML declaration.** `etree.tostring()` outputs single quotes — replace with double quotes after every serialize.
2. **`<w:delText>` inside `<w:del>`.** Deleted text must use `<w:delText>`, not `<w:t>`. Use `make_tracked_delete()`.
3. **Unique `w:id` + `w:date`** on every `<w:del>` and `<w:ins>`. Use `next_change_id()` and `get_date()`.

## Critical Rules

- **All Word replacements must use tracked changes** — never direct `w:t` text replacement
- **Never use `wb.active`** for Excel — always open sheets by name
- **Never overwrite adjustment rows** — those are appraiser professional judgment
- **Never overwrite grid cells with `*** UPDATE ***`** — leave template values if data is missing
- **If it's not in the workfile, it doesn't exist** — flag unsupported template artifacts for removal
- **Report truths, don't make appraiser judgments** — adjustments, comp selection, and value conclusions are the appraiser's call
- **Deed-first for grantor/grantee** — read deeds first, cross-check against CoStar, report mismatches
- **Mandatory rebuild after auto-fix** — never skip, even for one small fix

## Agent and Skill Specs

Detailed agent instructions: `.claude/agents/*.md`
Slash command definitions: `.claude/skills/*.md`
Full rules, workflow, and lessons learned: `CLAUDE.md`

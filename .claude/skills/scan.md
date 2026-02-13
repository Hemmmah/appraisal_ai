---
name: scan
description: Read project documents and extract data into data.md using Claude agents
user_invocable: true
---

# /scan — Scan Workfile

## Usage
`/scan <project-folder-path>`

Optionally: `/scan <project-folder-path> <template-type>` (defaults to `land-only`)

## What This Does
Reads all documents in a project folder using Claude agents (no external scripts), extracts structured data, and outputs a `data.md` file for user review. This runs Phases 1 and 2 of the full pipeline.

## Steps

### Phase 0 — Validate

1. Verify `<project-folder-path>` exists
2. Verify it has `Subject/` and/or `Comparables/` subfolders (support numbered-prefix variants)
3. Determine template type (default: `land-only` if not specified)
4. Create `<project-folder-path>/_workstate/` directory if it doesn't exist
5. Verify venv exists at `~/appraisal_ai/venv/bin/python`

### Phase 1 — Read (3 agents in parallel)

Launch all three agents simultaneously using the Task tool (3 Task calls in one message):

1. **Subject Reader** — reads all files in `Subject/`, writes `_workstate/subject_text.md`
   - Agent spec: `.claude/agents/subject-reader.md`
   - Use `subagent_type: "general-purpose"`
   - Prompt: `"Read all documents in <project-path>/Subject/ and write combined text to <project-path>/_workstate/subject_text.md. See .claude/agents/subject-reader.md for full instructions. Use the Read tool for PDFs and images. For .docx files use: ~/appraisal_ai/venv/bin/python -c \"import sys, os; sys.path.insert(0, os.path.expanduser('~/appraisal_ai/scripts')); from utils import extract_docx_text; print(extract_docx_text('<filepath>'))\" via Bash. For .xlsx use extract_xlsx_text() similarly. Skip files starting with ~$. Write all text to _workstate/subject_text.md with ## Filename headers."`

2. **Comp Reader** — reads all files in `Comparables/`, writes `_workstate/comp_text.md` + `_workstate/comp_data.md`
   - Agent spec: `.claude/agents/comp-reader.md`
   - Use `subagent_type: "general-purpose"`
   - Prompt: `"Read all documents in <project-path>/Comparables/ and write raw text to <project-path>/_workstate/comp_text.md and structured comp records to <project-path>/_workstate/comp_data.md. See .claude/agents/comp-reader.md for full instructions. Use the Read tool for PDFs and images. For .docx/.xlsx use extract_docx_text/extract_xlsx_text from ~/appraisal_ai/scripts/utils.py via Bash. Extract comp records with: address, sale_price, sale_date, grantor, grantee, land_sf, price_psf. Mark unknowns as *** UPDATE ***."`

3. **Exhibit Reader** — reads all files in `Exhibits/`, writes `_workstate/exhibit_descriptions.md`
   - Agent spec: `.claude/agents/exhibit-reader.md`
   - Use `subagent_type: "general-purpose"`
   - Prompt: `"Read all visual documents in <project-path>/Exhibits/ using the Read tool and write detailed descriptions to <project-path>/_workstate/exhibit_descriptions.md. See .claude/agents/exhibit-reader.md for full instructions. Describe what each image/PDF shows: document type, key information (flood zones, boundaries, dimensions), visible text. Skip files starting with ~$."`

Wait for all three to complete. Tell the user: "Phase 1 complete — all documents read."

If `Exhibits/` or `Comparables/` doesn't exist, skip that agent and continue.

### Phase 2 — Extract (2 agents in parallel)

Launch both agents simultaneously:

1. **Field Extractor** — reads Phase 1 outputs + reference-data.md, writes `data.md`
   - Agent spec: `.claude/agents/field-extractor.md`
   - Use `subagent_type: "general-purpose"`
   - Prompt: `"Extract all structured fields from <project-path>/_workstate/subject_text.md and <project-path>/_workstate/exhibit_descriptions.md using ~/appraisal_ai/templates/<template-type>/reference-data.md as the field list. Write data.md to <project-path>/data.md using save_md() from ~/appraisal_ai/scripts/utils.py. See .claude/agents/field-extractor.md for full instructions. Never guess dollar amounts or SF. Use *** UPDATE *** for unknowns and *** VERIFY *** for low confidence."`

2. **Comp Grid Agent** — reads comp data, enriches for grid
   - Agent spec: `.claude/agents/comp-grid-agent.md`
   - Use `subagent_type: "general-purpose"`
   - Prompt: `"Enrich comp data from <project-path>/_workstate/comp_data.md using <project-path>/_workstate/comp_text.md. Ensure all grid-relevant fields populated. Write to <project-path>/_workstate/comp_grid.md. See .claude/agents/comp-grid-agent.md for full instructions."`

Wait for both to complete.

### Present Results

1. Read the generated `data.md` and display a summary to the user
2. Collect ALL fields marked `*** UPDATE ***` or `*** VERIFY ***`
3. Present them clearly:

> **Scan complete.** Here's what was extracted:
>
> **Fields that need your input** (`*** UPDATE ***`):
> - `pe_value`: Not found in documents
> - `te_value`: Not found in documents
> ...
>
> **Fields to verify** (`*** VERIFY ***`):
> - `land_sf`: Extracted as "10,000" — is this correct?
> ...
>
> Review and correct the Markdown data, then run `/run` or `/draft` to build the output.

## Notes
- This uses Claude agents to read documents directly — no `scan_workfile.py`
- Claude reads PDFs (text and scanned) and images natively via the Read tool
- .docx and .xlsx files are extracted via Python utility functions
- The scan produces `data.md` + `_workstate/` intermediate files
- After scanning, the user should review data.md before building the draft
- To build the draft and grid after scanning, use `/run` (which skips re-scanning if data.md exists) or `/draft` + `/grid` individually

## Large PDF Fallback
If a PDF is over ~10 MB or the Read tool fails on it, reader agents should split it first using `split_pdf()` from `scripts/utils.py`, read each chunk separately, then clean up with `cleanup_pdf_chunks()`. See CLAUDE.md "Reading Large PDFs" for the exact commands.

---
name: run
description: Run the full appraisal pipeline — read documents, extract data, build draft and grid, review
user_invocable: true
---

# /run — Full Appraisal Pipeline

## Usage
`/run <project-folder-path> <template-type>`

Template types: `land-only`, `improved`

## What This Does
Runs the complete appraisal workflow in 5 phases using parallel Claude agents. Reads all project documents, extracts structured data, generates comp writeups, builds the narrative draft and grid with tracked changes, then reviews the output for QA and USPAP compliance.

## Phase 0 — Validate & Load Context (orchestrator, no agents)

1. **Read `.claude/CPM_SNAPSHOT.md`** — Load project context, architecture decisions, known issues, and lessons learned from previous sessions. This is your institutional memory. Review it for any rules, warnings, or known issues relevant to this project before proceeding.
2. Verify `<project-folder-path>` exists
3. Verify it has `Subject/`, `Comparables/`, and `Exhibits/` subfolders (support numbered-prefix variants like `1. Subject/`)
4. Verify `<template-type>` is valid (`land-only` or `improved`)
5. Verify template files exist at `~/appraisal_ai/templates/<template-type>/`
6. Create `<project-folder-path>/_workstate/` directory if it doesn't exist
7. Verify venv exists at `~/appraisal_ai/venv/bin/python`

If any validation fails, stop and tell the user what's wrong.

## Phase 1 — Read (3 agents in parallel)

Launch all three agents simultaneously using the Task tool (3 Task calls in one message):

1. **Subject Reader** — reads all files in `Subject/`, writes `_workstate/subject_text.md`
   - Agent spec: `.claude/agents/subject-reader.md`
   - Prompt: `"Read all documents in <project-path>/Subject/ and write combined text to <project-path>/_workstate/subject_text.md. See .claude/agents/subject-reader.md for full instructions."`

2. **Comp Reader** — reads all files in `Comparables/`, writes `_workstate/comp_text.md` + `_workstate/comp_data.md`
   - Agent spec: `.claude/agents/comp-reader.md`
   - Prompt: `"Read all documents in <project-path>/Comparables/ and write to <project-path>/_workstate/comp_text.md and <project-path>/_workstate/comp_data.md. See .claude/agents/comp-reader.md for full instructions."`

3. **Exhibit Reader** — reads all files in `Exhibits/`, writes `_workstate/exhibit_descriptions.md`
   - Agent spec: `.claude/agents/exhibit-reader.md`
   - Prompt: `"Read all documents in <project-path>/Exhibits/ and write descriptions to <project-path>/_workstate/exhibit_descriptions.md. See .claude/agents/exhibit-reader.md for full instructions."`

Wait for all three to complete. Verify `_workstate/subject_text.md` exists.

Tell the user: "Phase 1 complete — all documents read."

## Phase 2 — Extract (2 agents in parallel)

Launch both agents simultaneously:

1. **Field Extractor** — reads Phase 1 outputs + reference-data.md, writes `data.md`
   - Agent spec: `.claude/agents/field-extractor.md`
   - Prompt: `"Extract all structured fields from <project-path>/_workstate/subject_text.md and <project-path>/_workstate/exhibit_descriptions.md using ~/appraisal_ai/templates/<template-type>/reference-data.md as the field list. Write data.md to <project-path>/data.md. See .claude/agents/field-extractor.md for full instructions."`

2. **Comp Grid Agent** — reads comp data, enriches for grid
   - Agent spec: `.claude/agents/comp-grid-agent.md`
   - Prompt: `"Enrich comp data from <project-path>/_workstate/comp_data.md using <project-path>/_workstate/comp_text.md and <project-path>/data.md. Write to <project-path>/_workstate/comp_grid.md. See .claude/agents/comp-grid-agent.md for full instructions."`

Wait for both to complete.

### User Review Pause

After Phase 2, read `data.md` and collect ALL fields marked `*** UPDATE ***` or `*** VERIFY ***`. Present them to the user in a clear list:

> **Fields that need your input** (`*** UPDATE ***`):
> - `pe_value`: Not found in documents
> - `te_value`: Not found in documents
> ...
>
> **Fields to verify** (`*** VERIFY ***`):
> - `land_sf`: Extracted as "10,000" — is this correct?
> ...
>
> Please provide values for the UPDATE fields, and confirm or correct the VERIFY fields.

**Walk through each field one group at a time.** Don't just dump a list — ask the user about each group of related fields, explain what the field is, suggest values when you can infer them from documents, and help the user fill in as many as possible. Group fields logically (dates, property details, value conclusions, comp analysis). For fields the user doesn't have yet, confirm they want to leave them as `*** UPDATE ***` and move on.

Wait for the user to respond to each group. Update `data.md` with their answers before proceeding.

## Phase 3 — Build (3 steps: comp writer first, then draft + grid in parallel)

### Step 1: Comp Writer (runs first — draft builder depends on its output)

Launch the Comp Writer agent:

1. **Comp Writer** — generates structured comp writeups from source documents
   - Agent spec: `.claude/agents/comp-writer.md`
   - Prompt: `"Generate comp writeups for '<project-path>'. Read comp data from <project-path>/_workstate/comp_grid.md and source text from <project-path>/_workstate/comp_text.md. Write structured writeups to <project-path>/_workstate/comp_writeups.md. See .claude/agents/comp-writer.md for full instructions."`

Wait for completion. Verify `_workstate/comp_writeups.md` exists.

### Step 2: Draft Builder + Grid Builder (in parallel)

Launch both agents simultaneously:

1. **Draft Builder** — builds the narrative docx directly using lxml and utility functions
   - Agent spec: `.claude/agents/draft-builder.md`
   - Prompt: `"Build the narrative draft for '<project-path>' using template type '<template-type>'. Follow the instructions in .claude/skills/draft.md to copy the template, load data.md and reference-data.md, and apply tracked-change replacements directly using inline Python and utility functions from scripts/utils.py. See .claude/agents/draft-builder.md for full instructions."`

2. **Grid Builder** — fills the adjustment grid directly using openpyxl
   - Agent spec: `.claude/agents/grid-builder.md`
   - Prompt: `"Build the adjustment grid for '<project-path>' using template type '<template-type>'. Follow the instructions in .claude/skills/grid.md to copy the template, open it with openpyxl, and fill cells from data.md and _workstate/comp_grid.md. See .claude/agents/grid-builder.md for full instructions."`

Wait for both to complete. Verify output files exist in `Narrative/`.

Tell the user: "Phase 3 complete — comp writeups generated, draft and grid built."

## Phase 4 — Review (2 agents in parallel)

Launch both agents simultaneously:

1. **QA Reviewer** — cross-checks draft + grid against source docs and data.md
   - Agent spec: `.claude/agents/qa-reviewer.md`
   - Prompt: `"Review the outputs in <project-path>/Narrative/ against <project-path>/data.md and <project-path>/_workstate/subject_text.md. Write QA report to <project-path>/_workstate/qa_review.md. See .claude/agents/qa-reviewer.md for full instructions."`

2. **USPAP Reviewer** — checks narrative for USPAP compliance
   - Agent spec: `.claude/agents/uspap-reviewer.md`
   - Prompt: `"Review the narrative draft in <project-path>/Narrative/ for USPAP compliance. Write review to <project-path>/_workstate/uspap_review.md. See .claude/agents/uspap-reviewer.md for full instructions."`

Wait for both to complete.

### Phase 4.5 — Auto-Fix Loop (max 2 iterations)

After Phase 4 completes, run an automated fix-and-rebuild loop before presenting results to the user. This fixes deterministic errors (value mismatches with unambiguous corrections) without bothering the user, while still making every change visible as tracked changes in Word.

**Set `iteration = 0`.**

#### Step 1: Read review outputs
- Read `_workstate/qa_fixes.md` (load via Python/load_md)
- Read `_workstate/uspap_review.md`

#### Step 2: Apply auto-fixes (if any)
If `auto_fixes` is non-empty AND `iteration < 2`:

1. Read `data.md` (load via Python/load_md)
2. For each entry in `auto_fixes`:
   - Look up `entry.field` in the loaded data
   - **Stale-fix guard:** verify the current value in data.md matches `entry.current_value`. If it doesn't match, skip this fix and move it to `human_required` (the data changed since the review ran)
   - Set the field to `entry.correct_value`
3. Write updated `data.md` via `save_md()`
4. Log what was fixed (keep a running list across iterations for the final summary)
5. Re-run **Phase 3** (build draft + grid) — same agent calls as above
6. Re-run **Phase 4** (QA + USPAP review) — same agent calls as above
7. Increment `iteration`, go back to Step 1

#### Step 3: Present results to user
When iteration cap is reached OR `auto_fixes` is empty, present ONLY actionable items:

> **Auto-fixed (no action needed — verified in Word tracked changes):**
> - `land_sf`: corrected from "10,000" to "10,500" (source: assessor_card.pdf)
> - `price_psf`: corrected from "$2.50" to "$2.63" (math: $27,500 / 10,500 SF)
> ...
>
> **Needs your input** (`human_required`):
> - `pe_value`: Still marked *** UPDATE *** — not found in any source document
> - `land_sf`: Assessor card says 10,500 but deed says 10,000 — which is correct?
> ...
>
> **Template text to check** (`recheck_flags`):
> - Page 5, paragraph 2: "John Smith" appears to be unreplaced template appraiser name
> ...
>
> **USPAP gaps** (NEEDS ATTENTION and NOT FOUND items only):
> - Prior services disclosure — not found, needs to be added
> ...

Omit any section that has zero items. Do NOT show USPAP items that passed.

#### Step 4: User corrections
If the user provides corrections:
1. Update `data.md` with their answers via `save_md()`
2. Run one final rebuild (Phase 3 only — no further review loop)
3. Run Final Verification (see below)
4. Tell the user the updated draft is ready
5. **CPM TRIGGER:** Update `.claude/CPM_SNAPSHOT.md` — record what the user corrected, any new lessons learned, and updated project status. (See "CPM Update Triggers" below.)

## Phase 5 — Final Verification (data vs. draft deep comparison)

After all auto-fix iterations complete (or after user corrections + final rebuild), run one final extraction and comparison. This is the last gate before handing the draft to the user. Follow the "Final Verification" instructions in `.claude/skills/review.md`:

1. Extract the final draft text using `extract_docx_text()`
2. Load data.md (and comp_grid.md if it exists)
3. Compare every data.md field value against the draft text
4. Check for stale template values from reference-data.md still present
5. Verify table integrity (comp summary row count, ALLOCATION/SUMMARY dollar values, TE removal)
6. Report findings — do NOT silently rebuild again; just report what was found

This catches anything the QA agents or auto-fix loop missed: double-space artifacts, partial replacements, missed table updates, and template remnants.

## Final Output

After all phases and the auto-fix loop complete:

> Your appraisal is ready:
> - **Draft:** `Narrative/<filename> Narrative DRAFT.docx`
> - **Grid:** `Narrative/<filename> LAND GRID DRAFT.xlsx`
> - **QA Review:** `_workstate/qa_review.md`
> - **USPAP Review:** `_workstate/uspap_review.md`
>
> Open the DRAFT .docx in Word — you'll see tracked changes showing every substitution (strikethrough = old template value, underline = new project value). Accept or reject each one. Check the .xlsx grid in Excel to verify values and formatting.
>
> Every auto-fix is also visible as a tracked change — nothing was silently changed.

**CPM TRIGGER:** After delivering the final output, update `.claude/CPM_SNAPSHOT.md`. (See below.)

## CPM Update Triggers

The CPM snapshot (`.claude/CPM_SNAPSHOT.md`) is the system's persistent memory. It MUST be updated automatically at these points — do not wait for the user to ask:

### Trigger 1: After Phase 5 delivery
When you hand the final files to the user, update the snapshot with:
- Project status (which project, what was built, what issues remain)
- Pipeline results summary (replacements made, QA findings, known limitations flagged)
- Any new rules or workflow changes made during this run

### Trigger 2: After user corrections
When the user provides corrections and you rebuild, update the snapshot with:
- What the user corrected (these are learning signals — the pipeline got it wrong or couldn't find it)
- Whether the correction reveals a pattern worth adding to Lessons Learned in CLAUDE.md
- Updated project status after the rebuild

### What to update in the snapshot
- `Last updated` date
- `Known Projects` table — status of the active project
- `Current State` → `What's Working` and `What Still Needs Work`
- `Lessons Learned` summary (keep in sync with the full log in CLAUDE.md)
- Any new design decisions or architecture changes

### What NOT to put in the snapshot
- Client-specific data (addresses, dollar amounts, names) — the snapshot is in git
- Full QA reports — those live in `_workstate/`
- Entire file contents — keep it concise

## Notes
- All agents use the Task tool with `subagent_type: "general-purpose"`
- Phase 3 runs in two steps: Comp Writer first (generates comp_writeups.md), then Draft Builder + Grid Builder in parallel. The draft builder reads comp_writeups.md to replace LAND SALE NO. sections.
- Phase 1 agents need Read tool access for PDFs/images and Bash for .docx/.xlsx extraction
- Phase 3 Draft Builder agent needs Bash to run lxml/docx Python code inline; Grid Builder agent needs Bash to run openpyxl Python code inline
- Phase 4 agents need Bash for .docx/.xlsx text extraction and Read/Write for review reports
- Auto-fix loop only touches `data.md` field values — no structural changes
- Max 2 auto-fix iterations to prevent infinite cycling
- If any agent fails, report the error and ask the user how to proceed

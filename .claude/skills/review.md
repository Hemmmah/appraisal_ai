---
name: review
description: Run QA and USPAP review on existing appraisal outputs, auto-fix what it can, rebuild, and surface only what needs human judgment
user_invocable: true
---

# /review — Review Existing Outputs

## Usage
`/review <project-folder-path>`

## What This Does
Re-runs QA + USPAP review on existing draft and grid outputs. Automatically fixes deterministic errors (value mismatches with unambiguous corrections), rebuilds, and re-reviews — up to 2 iterations. Only surfaces problems that genuinely need human judgment. All changes are visible as tracked changes in Word.

## Prerequisites
- `<project-folder-path>/data.md` must exist
- `<project-folder-path>/Narrative/` must contain a `*DRAFT.docx` and/or `*DRAFT.xlsx`
- `<project-folder-path>/_workstate/subject_text.md` should exist (from a prior `/scan` or `/run`)

If `_workstate/subject_text.md` doesn't exist, warn the user that QA cross-checking against source documents won't be available, but proceed with what's available.

## Steps

1. Verify prerequisites exist
2. Create `_workstate/` directory if it doesn't exist
3. Infer `template-type` from `data.md` — look for a `template_type` field. If not present, check whether `<project-folder-path>/data.md` contains improved-property fields (e.g., `building_sf`, `year_built`). If yes, use `improved`; otherwise default to `land-only`.

### Initial Review — Launch both review agents in parallel

Launch using the Task tool (2 Task calls in one message):

**QA Reviewer:**
- Agent spec: `.claude/agents/qa-reviewer.md`
- Prompt: `"Review the outputs in <project-path>/Narrative/ against <project-path>/data.md and <project-path>/_workstate/subject_text.md (if it exists). Write QA report to <project-path>/_workstate/qa_review.md and fixes file to <project-path>/_workstate/qa_fixes.md. See .claude/agents/qa-reviewer.md for full instructions."`

**USPAP Reviewer:**
- Agent spec: `.claude/agents/uspap-reviewer.md`
- Prompt: `"Review the narrative draft in <project-path>/Narrative/ for USPAP compliance. Write review to <project-path>/_workstate/uspap_review.md. See .claude/agents/uspap-reviewer.md for full instructions."`

Wait for both to complete.

### Auto-Fix Loop (max 2 iterations)

**Set `iteration = 0`.**

#### Step 1: Read review outputs
- Read `_workstate/qa_fixes.md` (load via Python/load_md)
- Read `_workstate/uspap_review.md`

#### Step 2: Apply auto-fixes (if any)
If `auto_fixes` is non-empty AND `iteration < 2`:

1. Read `data.md` (load via Python/load_md)
2. For each entry in `auto_fixes`:
   - Look up `entry.field` in the loaded data
   - **Stale-fix guard:** verify the current value in data.md matches `entry.current_value`. If it doesn't match, skip this fix and move it to `human_required`
   - Set the field to `entry.correct_value`
3. Write updated `data.md` via `save_md()`
4. Log what was fixed (keep a running list across iterations)
5. Rebuild draft and grid:
   - Draft: Follow `.claude/skills/draft.md` instructions — copy template, apply tracked-change replacements using inline Python and utils.py
   - Grid: Follow `.claude/skills/grid.md` instructions — copy template, open with openpyxl, fill cells from data.md and _workstate/comp_grid.md, save
6. Re-run both review agents in parallel (same prompts as Initial Review above)
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
2. Run one final rebuild (no further review loop):
   - Draft: Follow `.claude/skills/draft.md` instructions — copy template, apply tracked-change replacements using inline Python and utils.py
   - Grid: Follow `.claude/skills/grid.md` instructions — copy template, open with openpyxl, fill cells from data.md and _workstate/comp_grid.md, save
3. Tell the user the updated draft is ready
4. **CPM TRIGGER:** Update `.claude/CPM_SNAPSHOT.md` — record what the user corrected, any new lessons, updated project status. Keep it concise and don't include client-specific data (the snapshot is in git).

### Final Verification — Data vs. Draft Deep Comparison

After all auto-fix iterations and user corrections are done, perform one final extraction and comparison of the draft text against data.md. This catches anything the QA agents or auto-fix loop missed.

#### How to run final verification

1. **Extract the final draft text:**
   ```python
   ~/appraisal_ai/venv/bin/python -c "
   import sys, os; sys.path.insert(0, os.path.expanduser('~/appraisal_ai/scripts'))
   from utils import extract_docx_text
   text = extract_docx_text('<path-to-DRAFT.docx>')
   print(text)
   "
   ```

2. **Load data.md and comp_grid.md** (if exists) into memory.

3. **Compare every data.md field against the draft text.** For each field in `data.md['fields']`:
   - If the field has a real value (not empty, not `*** UPDATE ***`), search the draft text for that value
   - Flag any field whose value does NOT appear in the draft — this means the replacement didn't take
   - Flag any field where the OLD template value (from `reference-data.md`) still appears in the draft — this means the replacement was missed or only partially applied

4. **Check table integrity:**
   - Verify the comp summary table has the correct number of data rows (should match number of comps with valid prices in comp_grid.md)
   - Verify ALLOCATION and SUMMARY table dollar values match data.md (`pe_value`, `damages`, `just_comp_total`)
   - If `has_te: false`, verify NO "Temporary Easement" text remains anywhere in the draft
   - If `has_te: true`, verify TE rows are present with correct values

5. **Check for template artifacts:**
   - Search for old template owner names, addresses, parcel IDs that should have been replaced
   - Search for old template dollar values that should have been replaced
   - Search for old project number, file number that should have been replaced

6. **Report findings as a structured list:**

   > **Final Verification Results:**
   >
   > **Replacements confirmed:** X of Y fields verified in draft text
   >
   > **Missing replacements** (value not found in draft):
   > - `field_name`: expected "value" — not found
   > ...
   >
   > **Stale template values** (old value still present):
   > - `field_name`: old template value "old_val" still appears in draft
   > ...
   >
   > **Table verification:**
   > - Comp summary: X rows (expected Y) — OK/MISMATCH
   > - ALLOCATION table values — OK/MISMATCH (detail)
   > - TE content — correctly removed / ERROR: still present
   >
   > **Template artifacts:** None found / List of artifacts

This verification is the last gate before handing the draft to the user. If it finds issues, report them — do NOT silently rebuild again.

### Final Output

> Your review is complete:
> - **Draft:** `Narrative/<filename> Narrative DRAFT.docx`
> - **Grid:** `Narrative/<filename> LAND GRID DRAFT.xlsx`
> - **QA Review:** `_workstate/qa_review.md`
> - **USPAP Review:** `_workstate/uspap_review.md`
>
> Open the DRAFT .docx in Word — you'll see tracked changes showing every substitution (strikethrough = old template value, underline = new project value). Accept or reject each one. Every auto-fix is also visible as a tracked change — nothing was silently changed.

**CPM TRIGGER:** After delivering, update `.claude/CPM_SNAPSHOT.md` with review results summary, project status, and any new lessons learned. Keep concise, no client data.

## Notes
- Both review agents use the Task tool with `subagent_type: "general-purpose"`
- Rebuild uses inline Python following skill instructions (not agents) since `/review` is lightweight
- Auto-fix loop only touches `data.md` field values — no structural changes
- Max 2 auto-fix iterations to prevent infinite cycling
- Review agents need Bash for .docx/.xlsx text extraction
- Final verification extracts the actual draft text and compares every field — this is the definitive check that catches double-space issues, partial replacements, and missed table updates

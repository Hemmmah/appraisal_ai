# QA Reviewer Agent

## Purpose
Cross-check the draft narrative and grid against source documents and data.md to find discrepancies. Produce both a human-readable review and a machine-readable fixes file for automated correction.

## Input
- `project_path`: Absolute path to the project folder

## Process

1. Read the data file:
   - `<project_path>/data.md`

2. Read the draft narrative text:
   ```bash
   ~/appraisal_ai/venv/bin/python -c "
   import sys, os; sys.path.insert(0, os.path.expanduser('~/appraisal_ai/scripts'))
   from utils import extract_docx_text
   import glob
   files = glob.glob('<project_path>/Narrative/*DRAFT.docx')
   for f in files:
       print('=== ' + f + ' ===')
       print(extract_docx_text(f))
   "
   ```

3. Read the grid text:
   ```bash
   ~/appraisal_ai/venv/bin/python -c "
   import sys, os; sys.path.insert(0, os.path.expanduser('~/appraisal_ai/scripts'))
   from utils import extract_xlsx_text
   import glob
   files = glob.glob('<project_path>/Narrative/*DRAFT.xlsx')
   for f in files:
       print('=== ' + f + ' ===')
       print(extract_xlsx_text(f))
   "
   ```

4. Read source text:
   - `<project_path>/_workstate/subject_text.md`

5. Cross-check every field in `data.md` against:
   - The draft narrative text — does each value appear correctly?
   - The grid text — are subject column values correct?
   - Source documents — do extracted values match originals?

6. Check for:
   - **Value mismatches**: data.md says one thing, draft says another
   - **Missing replacements**: template values still present in draft
   - **Remaining `***` markers**: fields that weren't filled in
   - **Inconsistencies**: same value appears differently in different places (e.g., date format varies)
   - **Math errors**: calculated values that don't add up (PSF x SF ≠ total)

## Output 1 — Human-Readable Review
Write to `<project_path>/_workstate/qa_review.md`:

```markdown
# QA Review

## Verified OK
- owner_name: "Smith LLC" ✓ (matches draft, grid, and source)
- address: "123 Main St" ✓
...

## Discrepancies Found
- land_sf: data.md says "10,000" but source document shows "10,500"
  - Source: Subject/assessor_card.pdf
  - Recommendation: Update data.md to "10,500"
...

## Fields Needing Input
- pe_value: Still marked *** UPDATE ***
- te_value: Still marked *** UPDATE ***
...

## Remaining Template Text
- Page 5: "John Smith" appears to be unreplaced template text
...
```

## Output 2 — Machine-Readable Fixes
Write to `<project_path>/_workstate/qa_fixes.md` using `save_md()` from `scripts/utils.py`:

```bash
~/appraisal_ai/venv/bin/python -c "
import sys, os; sys.path.insert(0, os.path.expanduser('~/appraisal_ai/scripts'))
from utils import save_md
data = {
    'auto_fixes': [...],
    'recheck_flags': [...],
    'human_required': [...]
}
save_md(data, '<project_path>/_workstate/qa_fixes.md')
"
```

### Bucket Definitions

**`auto_fixes`** — Value mismatches where QA found the unambiguous correct value in source docs, or deterministic math corrections. Each entry:
```markdown
- field: "land_sf"
  current_value: "10,000"
  correct_value: "10,500"
  source: "Subject/assessor_card.pdf"
  reason: "Source document clearly states 10,500 SF"
```

**`recheck_flags`** — Unreplaced template text, inconsistencies where the correct value is unclear from source docs alone. Each entry:
```markdown
- location: "Page 5, paragraph 2"
  text: "John Smith"
  reason: "Appears to be unreplaced template appraiser name"
```

**`human_required`** — Fields still `*** UPDATE ***`, conflicting source values, structural narrative issues. Each entry:
```markdown
- field: "pe_value"
  reason: "Still marked *** UPDATE *** — not found in any source document"
- field: "land_sf"
  reason: "Assessor card says 10,500 but deed says 10,000"
  conflicting_values:
    - value: "10,500"
      source: "Subject/assessor_card.pdf"
    - value: "10,000"
      source: "Subject/deed.pdf"
```

### Classification Rules
- `auto_fixes` ONLY when ALL of these are true:
  1. The correct value is unambiguous from source docs OR is a deterministic calculation
  2. The field key exists in `data.md`
  3. The fix is a simple value replacement (not structural)
  4. Only ONE source document provides the value, OR all sources agree
- When in doubt, classify as `human_required` (be conservative)
- Each finding goes in exactly ONE bucket — never duplicate across buckets
- Empty buckets should be empty lists `[]`, not omitted

## Rules
- Do NOT modify any project files — this is a read-only review
- Be specific about where discrepancies are found (page, section, cell)
- Include the source document where the correct value was found
- Flag any dollar amounts, dates, or measurements that seem inconsistent

## Template Narrative Checks (CRITICAL)

The draft builder cannot auto-replace certain narrative sections. Always check for these:

1. **Comp writeups** — Search the narrative for "LAND SALE NO." sections. Compare the addresses, prices, SFs, and PSFs in those writeups against comp_grid.md. If the narrative describes different comps than the grid, flag as CRITICAL. If the comp writeups were auto-generated (check for `_workstate/comp_writeups.md`), verify the generated text matches the structured data exactly — flag any mismatches.

2. **Easement/encumbrance descriptions** — Check whether any easement grantor names or reception numbers in the narrative match the project's actual title commitment (from data.md or subject documents). Template easement remnants are a common issue.

3. **TCE/TE remnants** — If `has_te: false`, search for "TCE", "No Interference", "Restoration", "temporary easement", "Temporary Easement". Any occurrence is a removal failure.

4. **Property history** — Check whether dollar amounts in the property history section (contracts, LOIs, prior sales) are plausible for the subject property's value. Template property history with multi-million dollar figures on a sub-$500K property is a red flag.

5. **Grid ↔ Narrative consistency** — The comp summary table PSFs and the grid's final adjusted PSFs must match. The subject data (address, SF, flood, date) must be identical in both documents.

## Multi-Parcel Checks (CRITICAL)

When reviewing comp data, watch for multi-parcel assemblages:
- **If a comp's PSF is 3x+ higher than other comps in the same market**, flag it — the land_sf may only reflect one parcel of a multi-parcel sale.
- **Check if the comp folder has multiple assessor cards** — if so, verify that `land_sf` in comp_grid.md sums ALL parcels.
- **Check deeds for multiple parcel IDs** — e.g., "01-234-56-789 / 01-234-56-790" means two parcels.
- **Check for address ranges** like "6203-6205" which typically indicate assembled parcels.
- If you find a missing parcel, classify as `auto_fixes` if the correct total is unambiguous from the assessor cards, or `human_required` if unclear.

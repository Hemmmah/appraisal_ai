---
name: grid
description: Build an updated adjustment grid .xlsx by reading the template and filling cells directly with openpyxl
user_invocable: true
---

# /grid — Build Adjustment Grid

## Usage
`/grid <project-folder-path> <template-type>`

Template types: `land-only`, `improved`

## What This Does
Copies the master grid template, then reads `data.md` and `_workstate/comp_grid.md` to fill both the subject column AND comp columns directly using openpyxl. No intermediate build script — Claude reads the template structure, identifies the correct cells, and writes values in.

## Steps

### 1. Load data files
- Read `<project-path>/data.md` using `load_md()` from `scripts/utils.py`
- Read `<project-path>/_workstate/comp_grid.md` using `load_md()` (if it exists; if not, only fill subject column)

### 2. Copy template to Narrative/
- Template source: `~/appraisal_ai/templates/<template-type>/grid.xlsx`
- Create `<project-path>/Narrative/` if it doesn't exist
- Output filename: `{file_number} {address} LAND GRID DRAFT.xlsx` (use `file_number` and `address` from data.md)
- Copy template to output path using `shutil.copy2()`

### 3. Inspect template structure BEFORE writing

**MANDATORY: Before writing any cells, dump the template structure to understand what you're working with.**

```python
from openpyxl import load_workbook
wb = load_workbook(output_path)  # Do NOT use data_only=True — preserves formulas

# Step A: List all sheet names
print("Sheets:", wb.sheetnames)

# Step B: Open the correct sheet BY NAME — NEVER use wb.active
ws = wb['Original Land Sale Grid']

# Step C: Dump existing values in rows you plan to write
# This lets you see what's already there (formulas, appraiser data, etc.)
for row in [2,3,7,11,15,21,25,28,29,31,34,35,37,38,44]:
    vals = []
    for col in ['B','C','D','E','F','G']:
        cell = ws[f'{col}{row}']
        val = cell.value
        if val is not None:
            vals.append(f"{col}{row}={repr(val)}")
    if vals:
        print(f"  Row {row}: {', '.join(vals)}")
```

Review the dump output. Identify:
- Which cells have formulas (do NOT overwrite)
- Which cells have appraiser-entered adjustment values (do NOT overwrite unless user explicitly asks)
- Which cells need updating with project data

### 4. Fill Subject column (B) from data.md

Write values into these cells (column B). Only write if the data.md field has a real value (not empty, not `*** UPDATE ***` / `*** VERIFY ***`):

| Cell | data.md field | Notes |
|------|----------------|-------|
| B2 | — | Write "N/A" (subject has no sale price) |
| B3 | — | Write "Fee Simple" |
| B7 | — | Write "Assumes Cash Equivalent" |
| B11 | — | Write "Assumes Market" |
| B15 | — | Write "Assumes None" |
| B21 | `effective_date` | Use `datetime` object, not string |
| B25 | `land_sf` | Integer |
| B28 | `address` + traffic/location description if available | Text |
| B29 | — | Write "N/A" (subject is benchmark) |
| B31 | `zoning` | Text |
| B34 | `flood_status` | Text |
| B35 | — | Write "—" (no flood adjustment for subject) |
| B37 | `land_sf` | Integer (same as B25) |
| B38 | — | Write "N/A" |
| B44 | `effective_date` | Use `datetime` object |

### 5. Fill Sale 1–5 columns (C–G) from comp_grid.md

`comp_grid.md` contains a list of comps. Map comp index to columns: comp 0 → C, comp 1 → D, ... comp 4 → G. If fewer than 5 comps, leave unused columns as-is.

For each comp, write:

| Cell row | comp_grid.md field | Notes |
|----------|---------------------|-------|
| 2 | `sale_price` | Integer (no $ or commas) |
| 3 | `real_property_rights` or default "Fee Simple" | Text |
| 7 | `financing` or default "Cash Equivalent" | Text |
| 11 | `conditions_of_sale` or default "Market" | Text |
| 15 | `expenditures_after` or default "None known" | Text |
| 21 | `sale_date` | `datetime` object |
| 25 | `land_sf` | Integer |
| 28 | `address` + location/traffic text | Text |
| 31 | `zoning` | Text |
| 34 | `flood_zone` | Text |

### 6. Adjustment cells — DO NOT OVERWRITE

**Adjustment rows (29, 32, 35, 38) contain appraiser judgment.** These are professional opinions that the appraiser enters manually in Excel. Never write to these cells unless:
- The cell is completely empty AND this is a fresh template (no prior appraiser work), OR
- The user explicitly asks you to set a specific adjustment value

If a template already has adjustment values filled in, leave them alone — even if they look wrong to you. The appraiser will update them in Excel after reviewing the grid.

### 7. Save the workbook
```python
wb.save(output_path)
wb.close()
```
Formulas auto-recalculate when the file is opened in Excel.

### 8. MANDATORY: Verify the output before delivering

**Re-open the saved file and check your work. Do not skip this step.**

```python
wb2 = load_workbook(output_path)
ws2 = wb2['Original Land Sale Grid']

# Verify subject column
for row in [21,25,28,34,37,44]:
    print(f"  B{row} = {ws2[f'B{row}'].value}")

# Verify comp columns weren't corrupted
for col in ['C','D','E','F','G']:
    price = ws2[f'{col}2'].value
    sf = ws2[f'{col}25'].value
    if price:
        print(f"  {col}: price={price}, sf={sf}")

# Verify formulas survived
for row in [5,9,13,17,19,22,23,40,41]:
    for col in ['C','D','E','F','G']:
        cell = ws2[f'{col}{row}']
        if cell.value and isinstance(cell.value, str) and cell.value.startswith('='):
            print(f"  Formula intact: {col}{row}")
            break

# Check the other sheet wasn't touched
if len(wb2.sheetnames) > 1:
    other = wb2.sheetnames[1] if wb2.sheetnames[0] == 'Original Land Sale Grid' else wb2.sheetnames[0]
    print(f"  Other sheet '{other}' exists (not modified)")

wb2.close()
```

If anything looks wrong, fix it before delivering to the user.

### 9. Report what was filled
Tell the user:
- How many subject cells were filled
- How many comp columns were filled
- Any fields that were skipped (missing data)
- Output file path

## Critical Rules

- **NEVER use `wb.active`.** Always open sheets by name: `wb['Original Land Sale Grid']`. The active sheet may not be the one you want.
- **NEVER overwrite formula cells.** Rows 5, 9, 13, 17, 19, 22, 23, 26, 40, 41, 46–50 contain formulas. Only write to cells that hold raw values or are empty.
- **NEVER overwrite appraiser adjustment values.** Rows 29, 32, 35, 38 contain professional judgment. Leave them unless explicitly asked to change.
- **Use `load_workbook(path)` without `data_only=True`** to preserve formulas.
- **Inspect before writing, verify after saving.** Steps 3 and 8 are mandatory — not optional.
- **Date cells** must use `datetime` objects (e.g., `datetime(2025, 6, 15)`), not strings.
- **Sale prices** are integers — no dollar signs, no commas.
- If fewer than 5 comps, leave unused columns as-is (template defaults).
- Run all Python through `~/appraisal_ai/venv/bin/python`.

## Notes
- `comp_grid.md` is produced by the Comp Grid Agent in Phase 2 of `/run`
- If `comp_grid.md` doesn't exist, only the subject column gets filled — this is fine for manual workflows
- The template grid has formulas for Adjusted Price, PSF, time adjustments, net physical adjustment, and final adjusted price — these all auto-calculate from the raw values you fill in
- Output goes to `<project-folder>/Narrative/`

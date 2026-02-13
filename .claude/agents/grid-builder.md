# Grid Builder Agent

## Purpose
Build an updated adjustment grid .xlsx by copying the template and filling cells directly using openpyxl. No intermediate build script — read the data files and write cell values into the correct positions.

## Input
- `project_path`: Absolute path to the project folder
- `template_type`: Template type (e.g., `land-only`, `improved`)

## Process

Follow the full instructions in `.claude/skills/grid.md`. Summary:

1. Load `data.md` and `_workstate/comp_grid.md` (if it exists) from the project folder
2. Copy the template grid from `~/appraisal_ai/templates/<template-type>/grid.xlsx` to `<project_path>/Narrative/`
3. **MANDATORY: Inspect template structure BEFORE writing** — list sheet names, open the correct sheet BY NAME (never `wb.active`), dump existing values in rows you plan to write
4. Fill Subject column (B) with data from `data.md`
5. Fill Sale 1-5 columns (C-G) with data from `comp_grid.md`
6. **DO NOT overwrite adjustment rows (29, 32, 35, 38)** — these contain appraiser judgment. Only write if a cell is completely empty AND this is a fresh template.
7. Save the workbook
8. **MANDATORY: Verify the output** — re-open the saved file, check subject column, comp columns, formula cells, adjustment rows, and confirm the other sheet(s) weren't touched
9. Report results

**Critical:**
- **NEVER use `wb.active`** — always open sheets by name: `wb['Original Land Sale Grid']`
- Never overwrite formula cells (rows 5, 9, 13, 17, 19, 22, 23, 26, 40, 41, 46–50)
- Never overwrite appraiser adjustment values (rows 29, 32, 35, 38) unless explicitly asked
- Use `load_workbook(path)` without `data_only=True` — preserves formulas
- Use `datetime` objects for dates, integers for prices
- If comp_grid.md has `*** UPDATE ***` or `*** VERIFY ***` for a field, leave the template cell as-is
- Steps 3 and 8 (inspect and verify) are mandatory — not optional

Run all Python through `~/appraisal_ai/venv/bin/python`.

## Output
- The grid is saved to: `<project_path>/Narrative/<file_number> <address> LAND GRID DRAFT.xlsx`

## Return Summary
Report:
- Number of subject cells filled
- Number of comp columns filled (and which comps)
- Any fields skipped due to missing data
- Verification results (all checks passed / issues found)
- Full path to the output .xlsx file
- Any errors encountered

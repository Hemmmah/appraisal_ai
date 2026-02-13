---
name: tables
description: Manipulate tables in Word (.docx) documents — general-purpose operations and appraisal-specific recipes
user_invocable: false
---

# Word Table Operations

## Overview
General-purpose table helpers in `scripts/utils.py` plus appraisal-specific recipes. All functions operate on lxml `etree` elements parsed from `word/document.xml` inside a `.docx` ZIP.

## Available Utility Functions

Import from `scripts/utils.py`:

```python
from utils import (
    find_table_by_text,   # Find a <w:tbl> by text content
    get_table_rows,       # List <w:tr> elements in a table
    get_row_cells,        # List <w:tc> elements in a row
    get_cell_text,        # Extract text from a cell
    get_row_text,         # Get list of cell strings from a row
    set_cell_text,        # Replace cell text (preserves formatting)
    find_row_by_text,     # Find (index, row) by search text
    remove_table_rows,    # Remove rows by index range
    add_table_row,        # Add a row with cell values
    remove_rows_by_text,  # Remove all rows matching text
)
```

## General-Purpose Operations

### Find a table
```python
tbl = find_table_by_text(root, 'Comparable Sales After Adjustments')
if tbl is None:
    print("Table not found")
```

### Read table contents
```python
rows = get_table_rows(tbl)
for row in rows:
    cells = get_row_text(row)  # ['Cell 1 text', 'Cell 2 text', ...]
    print(cells)
```

### Modify a cell
```python
rows = get_table_rows(tbl)
cells = get_row_cells(rows[2])  # Third row
set_cell_text(cells[0], 'New value')  # First cell
```

### Remove rows
```python
# Remove rows 2 through 5 (keeps header rows 0-1)
remove_table_rows(tbl, 2, 6)

# Remove all rows containing specific text
count = remove_rows_by_text(tbl, 'Temporary Easement')
```

### Add rows
```python
# Append a row
add_table_row(tbl, ['Comp 1', '$150'])

# Insert after row index 1 (after header), cloning formatting from row 2
rows = get_table_rows(tbl)
add_table_row(tbl, ['Comp 1', '$150'], after_idx=1, clone_format_from=rows[2])
```

### Find a specific row
```python
idx, row = find_row_by_text(tbl, 'Land Value')
if idx is not None:
    cells = get_row_cells(row)
    set_cell_text(cells[1], '$500,000')
```

---

## Appraisal Table Recipes

### Recipe: Update Comp Summary Table

Used by `/draft` to rebuild the "Comparable Sales After Adjustments" table from `comp_grid.md`.

**When to use:** After field replacements, when `_workstate/comp_grid.md` exists.

**Steps:**
1. Load comp_grid.md and parse effective_date from data.md
2. For each comp, calculate adjusted PSF:
   - `raw_psf = sale_price / land_sf`
   - `time_adj = raw_psf * (1 + months_since_sale * 0.0006)`
   - `flood_adj = ±5%` if flood zone mismatch between subject and comp
   - Skip comps with `*** UPDATE ***` in price
3. Sort comps by adjusted PSF ascending
4. Find table and rebuild:
   ```python
   import copy
   tbl = find_table_by_text(root, 'Comparable Sales After Adjustments')
   rows = get_table_rows(tbl)
   # Save a data row as format template BEFORE removing (preserves cell widths, fonts, alignment)
   format_row = copy.deepcopy(rows[2]) if len(rows) > 2 else None
   # Keep header rows (0 and 1), remove data rows
   remove_table_rows(tbl, 2)
   # Add sorted comp rows, cloning format from saved template row
   for comp in adjusted_psfs:
       add_table_row(tbl, [str(comp['num']), f" $       {comp['psf']} "], clone_format_from=format_row)
   ```
5. Update summary paragraph with range/average/median using `tracked_replace_across_runs`

**Key formula:**
```python
from datetime import datetime
months = (appraisal_date - sale_date).days / 30.42
time_adj_psf = raw_psf * (1 + months * 0.0006)
# Flood: +5% if comp in flood and subject not, -5% if reverse
final_psf = time_adj_psf * (1 + flood_adj)
```

### Recipe: Remove TE Table Rows

Used by `/draft` when `has_te: false` in data.md but the template has TE sections.

**When to use:** After field replacements, when project has no temporary easement but template does.

**Steps:**
1. Remove table rows containing "Temporary Easement" (case-sensitive check both capitalized and lowercase):
   ```python
   for tbl in root.iter(f'{W}tbl'):
       remove_rows_by_text(tbl, 'Temporary Easement')
       remove_rows_by_text(tbl, 'temporary easement')
   ```
2. Remove TE paragraphs (non-table) — handled separately in the draft skill's TE removal logic (paragraph-level, not table-level)

**Note:** This recipe only handles the table row portion. The full TE removal also deletes standalone paragraphs, rewrites mixed paragraphs, and removes calculation lines — see `/draft` step 4 for the complete logic.

### Recipe: Update ALLOCATION / SUMMARY Tables

Used to update dollar values in the ALLOCATION OF JUST COMPENSATION and SUMMARY OF THE ELEMENTS tables.

**When to use:** After all field replacements, to ensure dollar values in these tables match data.md.

**Steps:**
1. Find the ALLOCATION table:
   ```python
   alloc_tbl = find_table_by_text(root, 'ALLOCATION OF JUST COMPENSATION')
   ```
2. Find the SUMMARY table:
   ```python
   summ_tbl = find_table_by_text(root, 'SUMMARY OF THE ELEMENTS')
   ```
3. Update specific rows by label text:
   ```python
   # Example: update PE value row
   idx, row = find_row_by_text(alloc_tbl, 'Permanent Easement')
   if idx is not None:
       cells = get_row_cells(row)
       set_cell_text(cells[-1], pe_value)  # Dollar value in last cell
   ```
4. Fields to update (from data.md):
   - `pe_value` — Permanent Easement value
   - `damages` — Damages to remainder
   - `te_value` — Temporary Easement value (or remove row if no TE)
   - `just_comp_total` — Total just compensation

**Important:** Only update cells where data.md has real values. If a field is empty or `*** UPDATE ***`, leave the template value in place.

---

## Critical Rules

- **Table cell safety:** Never leave a `<w:tc>` without at least one `<w:p>`. When clearing cells, use `set_cell_text(cell, '')` — it preserves structure.
- **Formatting preservation:** Use `clone_format_from` in `add_table_row` when possible to match existing table styling (borders, shading, fonts).
- **Run through venv:** All Python executed via `~/appraisal_ai/venv/bin/python`.
- **Import path:** Always `sys.path.insert(0, os.path.expanduser('~/appraisal_ai/scripts'))` before importing from utils (ensure `os` is imported).

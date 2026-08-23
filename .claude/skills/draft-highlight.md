---
name: draft-highlight
description: Build a tracked-changes (or direct) narrative .docx for highlight-anchored template packs (anchor_mode: highlight) — position + yellow-highlight anchoring instead of literal-text matching. Used for Arabic/RTL and other templates where identical literal values ("-", "20", "1000") map to different fields.
user_invocable: true
---

# /draft-highlight — Build a Highlight-Anchored Narrative

## When this applies instead of `/draft`

`/draft` (see `draft.md`) matches literal old-text strings from `reference-data.md` and
replaces them — this works well for prose-heavy English narratives, but breaks down
when a template has many short, repeated literal values (dashes, small numbers,
single words) that mean different things depending on *where* they sit in the
document. Dense Arabic tabular templates (صك، مخطط، حدود أربعة...) are a common case.

A pack opts into this mode by shipping **`reference-data.json`** (instead of, or
alongside, `reference-data.md`) with `"_meta": {"anchor_mode": "highlight", ...}`.
The orchestrator picks the build path by checking which reference file the pack has:

- `templates/<pack>/reference-data.json` present → use this skill (`draft-highlight.md`)
- otherwise → use `.claude/skills/draft.md` (literal-text mode)

## Core principle

The template's **yellow highlights are the field markers**. A field's value is
never looked up by matching old text — it's looked up by **position**: which
table (by document order, depth-first into nested tables), which row, which
cell, *and* the presence of a highlighted run there. The template file's
structure and formatting are otherwise untouched. See
`templates/demo-ksa/reference-data.json` for a worked example (صك/مخطط/بلك/قطعة،
حدود أربعة، تواريخ هجرية مزدوجة) and `demo/setup_demo_ksa.py` /
`demo/run_demo_ksa.py` for a runnable end-to-end build + verification.

## reference-data.json shape

```json
{
  "_meta": {
    "template_name": "narrative.docx",
    "anchor_mode": "highlight",
    "number_format": "comma",
    "scope": "..."
  },
  "fields": {
    "deed_number": {"label": "رقم الصك", "type": "text", "required": true,
      "anchors": [{"t": 1, "r": 2, "c": 1}]},
    "deed_date_h": {"label": "تاريخ الصك (هجري)", "type": "date_h", "required": true,
      "anchors": [{"t": 1, "r": 2, "c": 2}]},
    "valuation_date_h": {"label": "تاريخ قياس القيمة (هجري)", "type": "date_h",
      "derive_hijri_from": "valuation_date_g",
      "anchors": [{"t": 5, "r": 4, "c": 3}]},
    "owner_name": {"label": "اسم المالك", "type": "text", "default_from": "client_name",
      "anchors": [{"t": 2, "r": 2, "c": 2}]},
    "location_composite": {"label": "وصف الموقع المركب", "type": "derived",
      "formula": "حي: {district} – قطعة رقم: {parcel_number}",
      "anchors": [{"t": 4, "r": 4, "c": 2}]}
  }
}
```

- `anchors`: list of `{t, r, c}` — 1-based table/row/cell, numbered by
  `utils.load_tables_dfs()` (document order, depth-first into nested tables).
  A field can have multiple anchors (the same value appears in more than one
  place in the report).
- `type`: `text` | `number` | `date_g` | `date_h` | `derived`. `number` values
  are formatted per `_meta.number_format` (`comma`, `comma2`, `plain`).
- `default_from`: fall back to another field's *resolved* value if this one
  isn't provided (e.g. `owner_name` defaults to `client_name`).
- `derive_hijri_from`: auto-derive a Hijri value from another field's
  *resolved* Gregorian value via `hijridate` (Umm al-Qura). **Always surfaced
  as a warning for the appraiser to confirm** — sighting-based edge cases
  exist near month boundaries.
- `default`: static fallback (e.g. `"داخل النطاق العمراني"`).
- `formula` (with `type: derived`): assembled from other resolved fields,
  Python `str.format()` style.
- `optional: true`: don't flag as skipped/missing if no value resolves.
- `render`: per-anchor text template, e.g. `"Sqm {v}"`.

## Steps

### 1. Verify inputs
- Confirm `<project-folder-path>/data.md` exists (else run `/scan` first)
- Confirm `~/appraisal_ai/templates/<template-type>/reference-data.json` and `narrative.docx` exist

### 2. Copy template to Narrative/
Same convention as `/draft`: `{file_number} {address} Narrative DRAFT.docx` in
`<project-path>/Narrative/`, via `shutil.copy2()`.

### 3. Run the fill engine
All logic lives in `scripts/utils.py` — no separate build script needed:

```python
import json, os, sys
sys.path.insert(0, os.path.expanduser('~/appraisal_ai/scripts'))
from utils import load_md, fill_highlighted_template

ref = json.load(open(os.path.expanduser('~/appraisal_ai/templates/<template-type>/reference-data.json'), encoding='utf-8'))
project = load_md('<project-path>/data.md')
proj_fields = project.get('fields', project)

report = fill_highlighted_template(
    template_path='<output-path>',   # the copied docx — edited in place
    output_path='<output-path>',
    fields=ref['fields'],
    data=proj_fields,
    mode='track_changes',            # or 'direct' — ask the user which (see below)
    author='Appraisal Tool',
    number_format=ref['_meta'].get('number_format', 'comma'),
)
print(f"filled={len(report['filled'])} skipped={len(report['skipped'])} "
      f"missing={len(report['missing'])} warnings={len(report['warnings'])}")
for m in report['missing']:
    print('MISSING:', m)
for w in report['warnings']:
    print(w)
```

### 4. Ask the user: direct or tracked-changes output
- **`track_changes`** (default/recommended): old highlighted text becomes a
  tracked deletion (`w:del`/`w:delText`, highlight preserved — a rejected
  change reverts to the original template state), new value becomes a
  tracked insertion (`w:ins`, highlight stripped). Opens in Word's Review
  pane; the appraiser accepts/rejects field by field.
- **`direct`**: overwrites text in place, strips highlight from filled
  fields. Clean output, no review step — best once the field map is trusted.

### 5. Report results
- Filled / skipped (no value given, kept as template placeholder) / missing
  (anchor position not found — template structure diverged from the map;
  **never guess a nearby cell**, report it) anchor counts
- Every `derive_hijri_from` warning — these need appraiser confirmation
- Full path to the output file

## Critical rules

- **Never match by text.** Position (`t`/`r`/`c`) + highlight presence only.
  Identical literals at different positions must never collide.
- **Never guess a missing anchor.** If a template edit shifted rows, report
  the miss — don't fall back to a nearby cell.
- **`derive_hijri_from` and `default_from` resolve against already-resolved
  values first, then raw project data** — so a chain like
  `issue_date_h ← issue_date_g ← default_from valuation_date_g` (where
  `issue_date_g` never appears literally in `data.md`) still resolves.
  (`resolve_anchor_values()` in `scripts/utils.py`.)
- **Auto-derived Hijri dates are never final** — always flagged as a warning
  for the appraiser, never silently accepted.
- **Multiple anchors per field must ALL be updated** — a field appearing in
  three places in the report needs all three positions filled consistently.
- **Run all Python through** `~/appraisal_ai/venv/bin/python`.

## Numbering tables (t)

`utils.load_tables_dfs(body)` numbers every `<w:tbl>` in document order,
descending depth-first into any tables nested inside a cell before moving to
the next top-level table. When building or updating a pack's field map,
dump this numbering first rather than guessing:

```python
from lxml import etree
import zipfile
from utils import load_tables_dfs, W
with zipfile.ZipFile('narrative.docx') as z:
    tree = etree.fromstring(z.read('word/document.xml'))
body = tree.find(f'{W}body')
for i, tbl in enumerate(load_tables_dfs(body), 1):
    rows = [r for r in tbl if etree.QName(r).localname == 'tr']
    print(f'table {i}: {len(rows)} rows')
```

## If the template changes

If the user sends a re-highlighted or restructured template version, re-dump
the table numbering (above), diff against `reference-data.json`, propose the
updated anchors for confirmation, then update the file. Never silently
re-guess anchors for a template that has diverged from the stored map.

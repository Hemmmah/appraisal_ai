---
name: appraisal-archive-search
description: >
  Scan, index, and search a directory of archived appraisal reports.
  Converts .docx narratives to searchable markdown, builds a master index
  with property metadata (address, type, value, date, client, county,
  appraiser, purpose), and searches the archive by filters or keywords.
  Use when: (1) setting up or updating an appraisal archive, (2) finding
  past appraisals by property type, location, date, or value range,
  (3) finding boilerplate language or narrative examples for a new
  assignment, (4) referencing similar past work before starting a report.
metadata:
  {
    "openclaw":
      {
        "emoji": "🔍",
        "requires": { "bins": ["python3", "npx"] },
      },
  }
---

# Appraisal Archive Search

Three scripts: **scan** (docx→md) → **build index** (extract metadata) → **search** (query by filters/keywords). Zero pip dependencies — stdlib Python + `npx mammoth` for conversion.

## Scan Archive

Convert .docx appraisal narratives to markdown. Walks year folders, prioritizes `NARRATIVE/` subfolders.

```bash
python3 scripts/scan_archive.py --archive-path /path/to/archives --output-path /path/to/md-output
```

Options: `--years 2020-2024` (filter years), `--force` (re-convert existing). Output: one `.md` per job folder.

## Build Index

Extract metadata from converted `.md` files into `INDEX.md` + `INDEX.json`.

```bash
python3 scripts/build_index.py --md-path /path/to/md-output
```

Extracts: job_number, property_address, property_type/subtype, client, effective_date, concluded_value, land_area, county, appraiser, purpose, approaches_used. See `references/field-extraction.md` for regex patterns.

## Search

Query the index. All filters are optional and combinable.

```bash
python3 scripts/search_archive.py --index /path/to/INDEX.json --type commercial --county Jefferson
```

| Flag | Example |
|------|---------|
| `--type` | `commercial`, `residential`, `land`, `agricultural`, `industrial` |
| `--subtype` | `office`, `sfr`, `ranch`, `conservation-easement` |
| `--county` | `Jefferson`, `Denver`, `Boulder` |
| `--purpose` | `condemnation`, `estate`, `lending`, `litigation` |
| `--date-from` / `--date-to` | `2022-01-01` |
| `--value-min` / `--value-max` | `500000` |
| `--keyword` | `"conservation easement"` (searches full .md content) |
| `--limit` | `5` (default 10) |

## Examples

```bash
# Condemnation appraisals in Jefferson County, 2022+
python3 scripts/search_archive.py --index INDEX.json --purpose condemnation --county Jefferson --date-from 2022-01-01

# Commercial properties $1M-$10M
python3 scripts/search_archive.py --index INDEX.json --type commercial --value-min 1000000 --value-max 10000000

# Conservation easement reports
python3 scripts/search_archive.py --index INDEX.json --keyword "conservation easement" --limit 20
```

Results are ranked by keyword relevance then date (newest first), output as a markdown table.

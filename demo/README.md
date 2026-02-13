# Demo Project

A complete set of fictional test data for running the appraisal_ai pipeline end-to-end.

## Quick Start

```bash
# 1. Run the setup script (generates template .docx and .xlsx)
~/appraisal_ai/venv/bin/python demo/setup_demo.py

# 2. Open Claude Code and run the pipeline
/run demo/Demo-Project demo-land
```

## What It Creates

**Project files** (checked into git as .txt):
- `Demo-Project/Subject/` — engagement letter, assessor card, deed
- `Demo-Project/Comparables/` — 4 sales, each with CoStar report + deed
- `Demo-Project/Exhibits/` — flood map info, zoning description

**Template files** (generated, gitignored):
- `templates/demo-land/narrative.docx` — full appraisal narrative
- `templates/demo-land/grid.xlsx` — adjustment grid with formulas

**Field mapping** (checked into git):
- `templates/demo-land/reference-data.yaml` — every replaceable value

## Fictional Property

**Subject:** 1200 Maple Street, Centerville, CO 80100
- 25,000 SF commercial lot, C-2 zoning, Zone X flood
- PE-10: 1,500 SF permanent easement, no temporary easement
- Concluded value: $50 PSF, $1,250,000 before taking

## Test Scenarios

| Scenario | What It Tests |
|----------|---------------|
| `has_te: false` | TE section removal (No Interference, Restoration, TCE clauses) |
| Comp 2 in flood zone | Flood adjustment logic (+5% when comp in flood, subject not) |
| HBU duplicate values | Both vacant/improved = "Retail Commercial Building" in template |
| 4 comps with deeds + CoStar | Deed-first extraction, CoStar cross-check |
| Template remove_sections | Stripping template-specific text (reception numbers, names) |

## Notes

- All data is fictional. No real properties, people, or transactions.
- The narrative.docx and grid.xlsx are NOT in git — run `setup_demo.py` to generate them.
- The project text files ARE in git so you can inspect them without running the script.

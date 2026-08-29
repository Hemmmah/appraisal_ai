# Demo Project

Fictional test data for running the appraisal_ai pipeline end-to-end.
Two packs are included:

| Pack | Language | Anchor mode | Script |
|------|----------|-------------|--------|
| `demo-land` | English | literal-text (`reference-data.md`) | `setup_demo.py` |
| `demo-ksa` | Arabic / RTL | highlight (`reference-data.json`) | `setup_demo_ksa.py` |

---

## English pack — `demo-land`

### Quick Start

```bash
# 1. Run the setup script (generates template .docx and .xlsx)
~/appraisal_ai/venv/bin/python demo/setup_demo.py

# 2. Open Claude Code and run the pipeline
/run demo/Demo-Project demo-land
```

### What It Creates

**Project files** (checked into git as .txt):
- `Demo-Project/Subject/` — engagement letter, assessor card, deed
- `Demo-Project/Comparables/` — 4 sales, each with CoStar report + deed
- `Demo-Project/Exhibits/` — flood map info, zoning description

**Template files** (generated; committed for demo-land):
- `templates/demo-land/narrative.docx` — full appraisal narrative
- `templates/demo-land/grid.xlsx` — adjustment grid with formulas

**Field mapping** (checked into git):
- `templates/demo-land/reference-data.md` — every replaceable value

### Fictional Property

**Subject:** 1200 Maple Street, Centerville, CO 80100
- 25,000 SF commercial lot, C-2 zoning, Zone X flood
- PE-10: 1,500 SF permanent easement, no temporary easement
- Concluded value: $50 PSF, $1,250,000 before taking

### Test Scenarios

| Scenario | What It Tests |
|----------|---------------|
| `has_te: false` | TE section removal (No Interference, Restoration, TCE clauses) |
| Comp 2 in flood zone | Flood adjustment logic (+5% when comp in flood, subject not) |
| HBU duplicate values | Both vacant/improved = "Retail Commercial Building" in template |
| 4 comps with deeds + CoStar | Deed-first extraction, CoStar cross-check |
| Template remove_sections | Stripping template-specific text (reception numbers, names) |

---

## Arabic / RTL pack — `demo-ksa` (highlight-anchor)

Dense tabular KSA fields (رقم الصك، رقم المخطط، الحدود الأربعة، تواريخ هجرية)
cannot use literal-text matching — identical placeholders (`---`, `20`, `1000`)
map to different fields by position. This pack uses **yellow highlights +
(table, row, cell) anchors** instead. See `.claude/skills/draft-highlight.md`.

### Quick Start

```bash
# 1. Regenerate the Arabic template + fictional data.md
~/appraisal_ai/venv/bin/python demo/setup_demo_ksa.py

# 2. Fill in both direct and track_changes modes and verify
~/appraisal_ai/venv/bin/python demo/run_demo_ksa.py
```

### What It Creates

- `templates/demo-ksa/narrative.docx` — RTL Word template with yellow-highlighted anchors
- `templates/demo-ksa/reference-data.json` — field map (`anchor_mode: highlight`)
- `demo/Demo-Project-KSA/data.md` — fictional project values (gitignored like other data.md files)
- `demo/Demo-Project-KSA/Narrative/*DRAFT*.docx` — generated drafts (gitignored)

### What It Exercises

| Feature | Detail |
|---------|--------|
| Position + highlight anchoring | 33 fields / 34 anchors across 6 tables |
| Dual Hijri/Gregorian dates | Auto-derive via `hijridate` (Umm al-Qura) with appraiser-confirm warnings |
| `default_from` / derive chains | e.g. `issue_date_h ← issue_date_g ← valuation_date_g` |
| Tracked changes | Exactly one `<w:del>` + `<w:ins>` per filled anchor |
| Optional empty fields | `built_area` left blank on purpose — placeholder stays |

### Claude workflow

```
/draft demo/Demo-Project-KSA demo-ksa
```

`draft.md` / `run.md` detect `reference-data.json` with `anchor_mode: highlight`
and route to `draft-highlight.md` automatically.

---

## Notes

- All data is fictional. No real properties, people, or transactions.
- `data.md` and Narrative drafts are gitignored (contain / are generated project data).
- Demo templates under `templates/demo-land/` and `templates/demo-ksa/` stay in the repo.

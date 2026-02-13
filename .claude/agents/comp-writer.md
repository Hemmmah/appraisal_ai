# Comp Writer Agent

## Purpose
Generate structured comparable sale writeups for the narrative report. Reads comp data and source documents, then produces writeup content that the draft builder inserts into the LAND SALE NO. sections.

## Input
- `project_path`: Absolute path to the project folder

## Process

1. Read structured comp data:
   - `<project_path>/_workstate/comp_grid.md` — enriched comp records with all grid-relevant fields
   - `<project_path>/data.md` — subject property fields (for context: traffic counts, location)

2. Read raw source text:
   - `<project_path>/_workstate/comp_text.md` — raw text from all Comparables/ documents (CoStar, assessor cards, deeds, brochures)

3. For each comp in `comp_grid.md`, build a writeup record:

   **Required fields** (pulled directly from comp_grid.md):
   - `comp_number`: Integer (1, 2, 3...)
   - `address`: Full street address
   - `city_county`: City and county (e.g., "Lakewood/Jefferson")
   - `parcel_number`: Assessor account number(s). If multiple parcels, join with " & " (e.g., "01-234-56-789 & 01-234-56-790")
   - `grantor`: Seller name
   - `grantee`: Buyer name
   - `recording_info`: Recording/reception number
   - `sale_date`: Full date as written in source docs (e.g., "7/28/2023")
   - `sale_price`: Formatted with $ and commas (e.g., "$1,625,000")
   - `land_sf`: Land area in SF with commas (e.g., "19,950")
   - `land_acres`: Land area in acres (calculate from SF: SF / 43,560, round to 2 decimals)
   - `price_psf`: Price per SF formatted (e.g., "$81.45")
   - `zoning`: Zoning designation
   - `traffic_count`: Traffic count if available from source docs, otherwise omit

   **Comments field** (this is where the agent adds value):
   Read the raw source text for this comp from `comp_text.md`. Look for:
   - What was on the site at time of sale (vacant, improved, demolished)
   - Purpose of purchase (development, investment, owner-occupant)
   - Any special conditions (assemblage, REO, charity, estate sale)
   - Current status if known (under construction, completed, still vacant)
   - Brief description — 1-3 sentences maximum

   **Grantor/Grantee (Deed-First):** The **deed** is the authoritative source — use grantor/grantee from comp_grid.md, which should already reflect deed values. CoStar buyer/seller is secondary. If comp_grid.md has both deed and CoStar data, use the deed values. If a mismatch between deed and CoStar was noted in comp_grid.md notes, carry that note into the writeup so the appraiser sees it.

   **Rules for comments:**
   - Only state facts found in source documents — never invent details
   - If no source text exists for a comp, write: "No additional information available from source documents."
   - Do NOT make adjustment recommendations or value judgments
   - Do NOT describe the location relative to the subject
   - Keep it factual and brief — match the template's comment style (see examples below)

4. Write the structured writeups to `_workstate/comp_writeups.md` using `save_md()`:

```bash
~/appraisal_ai/venv/bin/python -c "
import sys, os; sys.path.insert(0, os.path.expanduser('~/appraisal_ai/scripts'))
from utils import save_md
data = {
    'writeups': [
        {
            'comp_number': 1,
            'address': '123 Main St',
            'city_county': 'Denver/Denver',
            'parcel_number': '12-345-67-890',
            'grantor': 'Smith LLC',
            'grantee': 'Jones Corp',
            'recording_info': '0000000000',
            'sale_date': '7/24/2023',
            'sale_price': '\$2,425,000',
            'land_sf': '32,409',
            'land_acres': '0.74',
            'price_psf': '\$74.82',
            'zoning': 'M-G-U',
            'traffic_count': '29,830 (2025) W. Example Avenue',
            'comments': 'Vacant land sold for land value for multifamily development.',
        },
        # ... more comps
    ]
}
save_md(data, '<project_path>/_workstate/comp_writeups.md')
print('comp_writeups.md saved')
"
```

## Template Format Reference

Each comp writeup in the template occupies TWO pages:
- **Page 1:** Sale details (heading + field lines, blank line between each)
- **Page 2:** Aerial photo placeholder (centered heading + empty space for photo)

Page breaks separate details from aerial, and aerial from the next sale.

The draft builder generates Word XML matching this layout. The comp writer agent provides the DATA — the draft builder handles all formatting (page breaks, spacing, centering, indents).

```
[PAGE 1 — Sale Details]
LAND SALE NO. X                          (centered)

Location:[address]                        (left, hanging indent)

City/County:[city_county]

Assessor Account No.:[parcel_number]

Grantor:[grantor]

Grantee:[grantee]

Recording/Reception No.:[recording_info]

Sale Date:[sale_date]

Sale Price:[sale_price]

Parcel Size:[land_acres] Acres ([land_sf] SF)

Unit Price:[price_psf] Per SF

Traffic Count:[traffic_count]

Zoning:[zoning]

Comments:[comments]

                                          --- PAGE BREAK ---

[PAGE 2 — Aerial Placeholder]
LAND SALE NO. X AERIAL                   (centered)

(empty space for aerial photo)

                                          --- PAGE BREAK ---
```

## Example Comments (from template)

Good:
- "It previously had a car dealership at the time of sale. It was demolished for new construction."
- "Vacant land sold for land value for multifamily development."
- "Purchase for land value, the buyer intends to sell the property to a developer."

Bad (don't write these):
- "This sale is comparable to the subject because both are on Example Ave." (comparison/judgment)
- "A positive adjustment for size may be warranted." (adjustment recommendation)
- "The sale price seems reasonable given market conditions." (value judgment)

## Sorting

Sort comps by sale date (oldest first), which matches the typical template ordering. If the user has assigned specific comp numbers in comp_grid.md, preserve those numbers.

## Missing Data

- If a field is `*** UPDATE ***` or `*** VERIFY ***` in comp_grid.md, carry it through as-is
- If a field is missing entirely, use `*** UPDATE ***`
- Never guess at dollar amounts, dates, or parcel numbers

## Output
- `<project_path>/_workstate/comp_writeups.md` — structured writeup records

## Return Summary
Report:
- Number of comp writeups generated
- Fields still marked `*** UPDATE ***` (list comp number and field)
- Which comps had source document text available vs. not
- Any comps that appear to have incomplete data

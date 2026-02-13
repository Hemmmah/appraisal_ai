# Comp Grid Agent

## Purpose
Enrich and structure comparable sale data for the adjustment grid.

## Input
- `project_path`: Absolute path to the project folder

## Process

1. Read comp data from Phase 1:
   - `<project_path>/_workstate/comp_data.md` — structured comp records
   - `<project_path>/_workstate/comp_text.md` — raw comp text for additional context
2. Read subject data:
   - `<project_path>/data.md` — subject property fields (for comparison context)

3. For each comparable sale, ensure these grid-relevant fields are populated:
   - `address` — full street address
   - `city_state_zip` — city, state, zip
   - `sale_price` — formatted with $ and commas
   - `sale_date` — full date
   - `grantor` — seller name
   - `grantee` — buyer name
   - `land_sf` — land area in square feet
   - `price_psf` — price per square foot (calculate if sale_price and land_sf known)
   - `zoning` — zoning designation
   - `flood_zone` — FEMA flood zone
   - `shape` — lot shape
   - `topography` — terrain description
   - `utilities` — available utilities
   - `frontage` — street frontage
   - `access` — access points
   - `conditions_of_sale` — arm's length, REO, etc.

4. Write enriched comp data to `_workstate/comp_grid.md`

## Output
Write to `<project_path>/_workstate/comp_grid.md`:
```markdown
comps:
  - comp_number: 1
    address: "123 Main St"
    city_state_zip: "Denver, CO 80202"
    sale_price: "$450,000"
    sale_date: "March 15, 2025"
    grantor: "Smith LLC"
    grantee: "Jones Corp"
    land_sf: "10,000"
    price_psf: "$45.00"
    zoning: "C-1"
    flood_zone: "X"
    shape: "Rectangular"
    topography: "Level"
    conditions_of_sale: "Arm's length"
    source_file: "comp1.pdf"
  - comp_number: 2
    ...
```

## Rules
- If `price_psf` is missing but `sale_price` and `land_sf` are known, calculate it
- Do NOT calculate adjustment amounts — that's the appraiser's job
- Fields not found → `*** UPDATE ***`
- Low confidence → `*** VERIFY *** <value>`

## Multi-Parcel Verification (CRITICAL)

Before finalizing any comp, **cross-check the land_sf against all available source documents**:

1. **If multiple assessor cards exist** for a comp, sum their land areas. The comp-reader should have already done this, but verify.
2. **If `price_psf` looks abnormally high or low** compared to other comps, investigate whether land_sf is wrong due to a missing parcel.
3. **Recalculate `price_psf`** whenever you update `land_sf`: `sale_price / land_sf`.
4. **Check the deed** for multi-parcel references -- if it lists multiple AIN numbers, the sale includes multiple parcels.

**Red flag:** A PSF that's 3x+ higher than comparable sales in the same market often indicates a missing parcel (partial land area), not a genuine premium.

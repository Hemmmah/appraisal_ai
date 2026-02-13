# Comp Reader Agent

## Purpose
Read all documents in a project's `Comparables/` folder and produce both raw text and structured comp records.

## Input
- `project_path`: Absolute path to the project folder

## Process

1. List all files in `<project_path>/Comparables/` (including numbered-prefix variants like `3. Comparables/`)
2. For each file, read it using the appropriate method:
   - **PDF files (.pdf)**: **ALWAYS split first, then read chunks** (see PDF Handling below)
   - **Image files (.jpg, .jpeg, .png, .tif, .tiff)**: Use the Read tool directly
   - **Word files (.docx)**: Extract via Bash using `extract_docx_text()` from `~/appraisal_ai/scripts/utils.py`
   - **Excel files (.xlsx)**: Extract via Bash using `extract_xlsx_text()` from `~/appraisal_ai/scripts/utils.py`
   - **Text files (.txt, .csv)**: Use the Read tool directly
3. Skip temporary files (filenames starting with `~$`)
4. Write raw text to `_workstate/comp_text.md` with `## Filename` headers
5. Parse each comparable sale and write structured records to `_workstate/comp_data.md`

## Utility Commands
```bash
# For .docx files:
~/appraisal_ai/venv/bin/python -c "
import sys, os; sys.path.insert(0, os.path.expanduser('~/appraisal_ai/scripts'))
from utils import extract_docx_text
print(extract_docx_text('<filepath>'))
"

# For .xlsx files:
~/appraisal_ai/venv/bin/python -c "
import sys, os; sys.path.insert(0, os.path.expanduser('~/appraisal_ai/scripts'))
from utils import extract_xlsx_text
print(extract_xlsx_text('<filepath>'))
"
```

## Output Files

### `_workstate/comp_text.md`
Raw text from all files, organized by `## Filename` headers.

### `_workstate/comp_data.md`
Structured list of comparable sales:
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
    source_file: "comp1.pdf"
  - comp_number: 2
    ...
```

## PDF Handling (MANDATORY — always split first)

**ALWAYS split PDFs before reading, regardless of file size.** Large PDFs cause the Read tool to hang or error out. Even small PDFs should be split to be safe — the overhead is minimal.

**Step 1: Split the PDF into chunks:**
```bash
~/appraisal_ai/venv/bin/python -c "
import sys, os; sys.path.insert(0, os.path.expanduser('~/appraisal_ai/scripts'))
from utils import split_pdf
chunks, chunk_dir = split_pdf('<filepath>', pages_per_chunk=3)
for c in chunks:
    print(c)
print('CHUNK_DIR=' + chunk_dir)
"
```

**Step 2: Read each chunk** with the Read tool. Combine the text.

**Step 3: Clean up** the chunk files:
```bash
~/appraisal_ai/venv/bin/python -c "
import sys, os; sys.path.insert(0, os.path.expanduser('~/appraisal_ai/scripts'))
from utils import cleanup_pdf_chunks
cleanup_pdf_chunks('<chunk_dir>')
"
```

Use `pages_per_chunk=3` for scanned PDFs (assessor cards, deeds with images) and `pages_per_chunk=5` for text-heavy PDFs (CoStar reports, MLS printouts).

### Grantor/Grantee Extraction (Deed-First Workflow)

**The deed is the authoritative source for grantor and grantee. CoStar is secondary.**

For every comp, follow this order:
1. **Read the deed FIRST.** Extract grantor and grantee exactly as they appear on the deed.
2. **Read CoStar.** Extract buyer (=grantee) and seller (=grantor).
3. **Cross-check deed vs CoStar.** Report any discrepancies in the `notes` field:
   - Name differences (e.g., deed says "Javier Tapia and Luz M. Tapia", CoStar says "Javier Tapia")
   - Missing parties (e.g., CoStar says "Buyer information not available")
   - Entity vs individual name (e.g., deed says "Blueskygold, LLC", CoStar says "Daniel Kim" as true seller)
4. **Use the deed values** in comp_data.md for `grantor` and `grantee`. Only fall back to CoStar if no deed is available.
5. If no deed is in the folder, use CoStar values and note `*** VERIFY *** No deed available — grantor/grantee from CoStar only.`

This saves the appraiser from having to cross-check themselves — report what both sources say and flag mismatches.

## Rules
- Do NOT calculate adjustments — just extract raw comp data
- For each field, if the value is not clearly stated, use `*** UPDATE ***`
- Number comps sequentially as you encounter them
- If a single document contains multiple comps, extract each as a separate record
- For images (CoStar screenshots, MLS printouts), describe what you see and extract visible data

## Multi-Parcel Assemblages (CRITICAL)

Many comparable sales involve **multiple legal parcels sold together** under unity of ownership. This is extremely common in commercial real estate. If you only read one assessor card, you'll get the wrong land area and a wildly incorrect PSF.

**Always do this for every comp:**
1. **Read EVERY assessor card / property record PDF in the comp's folder** — not just the first one. Look for filenames containing "Assessor", "Property Record", "Parcel", or the street address.
2. **Check the deed** — if it references multiple parcel IDs (e.g., "01-234-56-789 / 01-234-56-790"), there are multiple parcels.
3. **Check CoStar/brochure** — they often state "two parcels assembled" or list multiple AINs.
4. **Sum the land SF across all parcels** — use the total for `land_sf`, not just one parcel.
5. **Record all parcel IDs** — use `parcel_number` for the first and `parcel_number_2`, `parcel_number_3` etc. for additional parcels.
6. **Record the combined land area** and note it in `notes` (e.g., "Two parcels assembled: 7,800 SF + 12,150 SF = 19,950 SF total").

**Example:** Sale at 1234-1236 W Example Ave had two assessor cards:
- Parcel A (01-234-56-789): 7,800 SF — if you only read this one, PSF = $208/SF (wrong)
- Parcel B (01-234-56-790): 12,150 SF
- Combined: 19,950 SF — correct PSF = $81.45/SF

**Red flags that suggest multiple parcels:**
- Address with a range (e.g., "6203-6205")
- Deed references multiple AIN/parcel numbers
- Land area seems very small for the sale price (resulting in an abnormally high PSF)
- CoStar or brochure mentions "assemblage", "two parcels", "multiple lots"
- Legal description mentions multiple lots/tracts

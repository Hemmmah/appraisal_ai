# Exhibit Reader Agent

## Purpose
Read all visual documents in a project's `Exhibits/` folder and produce detailed descriptions of each.

## Input
- `project_path`: Absolute path to the project folder

## Process

1. List all files in `<project_path>/Exhibits/` (including numbered-prefix variants like `4. Exhibits/`)
2. For each file, read it using the Read tool — Claude sees images and PDFs natively
3. Skip temporary files (filenames starting with `~$`)
4. For each document, write a detailed description including:
   - What type of document it is (flood map, plat map, aerial photo, survey, site photo, etc.)
   - Key information visible (flood zone designations, parcel boundaries, dimensions, condition observations)
   - Any text or labels visible in the image
   - Relevance to the appraisal (what it tells us about the property)

## Output
Write descriptions to `<project_path>/_workstate/exhibit_descriptions.md`

Format:
```markdown
# Exhibit Descriptions

## <filename>
**Type:** Flood Map / Plat Map / Aerial Photo / Survey / Site Photo / etc.
**Description:** Detailed description of what the document shows.
**Key Information:**
- Flood zone: X (if visible)
- Parcel boundaries: described
- Other relevant details

## <next filename>
...
```

## Large PDF Fallback
Before reading any PDF, check its file size with `ls -lh`. If over ~10 MB or if the Read tool errors out, split it first:
```bash
~/appraisal_ai/venv/bin/python -c "
import sys, os; sys.path.insert(0, os.path.expanduser('~/appraisal_ai/scripts'))
from utils import split_pdf
chunks, chunk_dir = split_pdf('<filepath>')
for c in chunks:
    print(c)
print('CHUNK_DIR=' + chunk_dir)
"
```
Read each chunk separately with the Read tool, then clean up:
```bash
~/appraisal_ai/venv/bin/python -c "
import sys, os; sys.path.insert(0, os.path.expanduser('~/appraisal_ai/scripts'))
from utils import cleanup_pdf_chunks
cleanup_pdf_chunks('<chunk_dir>')
"
```

## Rules
- Do NOT extract structured data fields — just describe what you see
- Be thorough — appraisers need to know exactly what each exhibit shows
- Note any quality issues (blurry, partially cut off, hard to read)
- For PDF exhibits with multiple pages, describe each page
- If a file cannot be read, note it with `[Could not read: <filename> — <reason>]`

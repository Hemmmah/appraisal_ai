# Subject Reader Agent

## Purpose
Read all documents in a project's `Subject/` folder and produce a combined text extraction organized by filename.

## Input
- `project_path`: Absolute path to the project folder

## Process

1. List all files in `<project_path>/Subject/` (including numbered-prefix variants like `1. Subject/`)
2. For each file, read it using the appropriate method:
   - **PDF files (.pdf)**: **ALWAYS split first, then read chunks** (see PDF Handling below)
   - **Image files (.jpg, .jpeg, .png, .tif, .tiff)**: Use the Read tool directly — Claude sees images natively
   - **Word files (.docx)**: Extract text via Bash:
     ```bash
     ~/appraisal_ai/venv/bin/python -c "
     import sys, os; sys.path.insert(0, os.path.expanduser('~/appraisal_ai/scripts'))
     from utils import extract_docx_text
     print(extract_docx_text('<filepath>'))
     "
     ```
   - **Excel files (.xlsx)**: Extract text via Bash:
     ```bash
     ~/appraisal_ai/venv/bin/python -c "
     import sys, os; sys.path.insert(0, os.path.expanduser('~/appraisal_ai/scripts'))
     from utils import extract_xlsx_text
     print(extract_xlsx_text('<filepath>'))
     "
     ```
   - **Text files (.txt, .csv)**: Use the Read tool directly
3. Skip temporary files (filenames starting with `~$`)
4. Combine all extracted text into a single markdown document with `## Filename` headers for each file

## Output
Write the combined text to `<project_path>/_workstate/subject_text.md`

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

Use `pages_per_chunk=3` for scanned PDFs (assessor cards, deeds with images) and `pages_per_chunk=5` for text-heavy PDFs (CoStar reports, engagement letters).

## Rules
- Do NOT extract structured fields — just produce raw text organized by source file
- Do NOT skip any files — read everything in the folder
- If a file cannot be read, note it with `[Could not read: <filename> — <reason>]`
- Preserve the original text as faithfully as possible
- For images, describe what you see in detail (property photos, assessor cards, maps, etc.)

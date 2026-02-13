# Appraisal Drafting Engine (Word Tracked Changes + Excel Grids)

Automated appraisal drafting tool that generates **Word narrative drafts with tracked changes** and **Excel adjustment grids / schedules** from **master templates** and **project workfile data**.

Designed for appraisers who want to replace the manual copy-paste-and-edit workflow while keeping the appraiser in control: every substitution is visible in Word Review mode and can be accepted/rejected.

---

## Setup (Step by Step — No Tech Experience Needed)

You don't need to know programming. You just need Claude Code installed and a terminal open. Follow these steps exactly.

### Step 1: Open a Terminal

- **Windows:** Open **PowerShell** (search "PowerShell" in the Start menu) or open **Ubuntu** if you have WSL installed
- **Mac:** Open **Terminal** (search "Terminal" in Spotlight, or find it in Applications → Utilities)

### Step 2: Start Claude Code

Type the following and press Enter:

```
claude
```

If Claude Code isn't installed yet, visit [claude.ai/claude-code](https://claude.ai/claude-code) for install instructions.

### Step 3: Tell Claude to Pull the Repo

Copy and paste this into Claude:

```
Create a folder called appraisal_ai in my home directory and clone this repo into it: https://github.com/chadru/appraisal_ai.git
```

Claude will create the folder and download the code for you.

### Step 4: Move Into the Folder and Restart Claude

Close Claude (type `/exit` or press `Ctrl+C`), then run:

```
cd ~/appraisal_ai
claude
```

### Step 5: Ask Claude to Walk You Through It

Now you're in the project. Tell Claude:

```
Review this codebase and help me get started. I'm an appraiser and I need help setting this up.
```

Claude will:
- Ask you to create a **new empty folder** for your project (e.g., `2026-001 123 Main St`)
- Tell you exactly how to copy the folder path and paste it in
- **Set up your project folder** with five subfolders: `Subject/`, `Narrative/`, `Comparables/`, `Exhibits/`, and `Template/`
- Tell you which files to drop into each folder
- Install any needed dependencies
- Scan your documents, help you review the extracted data, and build your draft

**How to give Claude your folder path:**
The easiest way is to **drag the folder from File Explorer (Windows) or Finder (Mac) directly into the terminal window** — it will paste the full path automatically.

Or copy manually:
- **Windows:** Open File Explorer, navigate to your project folder, click the **address bar** at the top — it will highlight the full path. Right-click and **Copy**, then paste it into Claude.
- **Mac:** Right-click the folder in Finder, hold **Option**, and click **"Copy as Pathname"**. Then paste it into Claude.

**That's it.** Claude handles the technical parts. You just answer its questions about your appraisal project.

---

## What It Does

Given a project folder and a selected template pack, the tool will:

- Scan a project workfile folder (`PDF`, `.docx`, `.xlsx`) and extract structured values into `data.md`
- Build a Word narrative draft where replacements appear as **tracked changes** (delete old → insert new)
- Build an Excel grid/schedule draft with subject data filled in and selected calculations recalculated
- Preserve the formatting of the master template (headings, styles, tables, spacing, etc.)

---

## Core Workflow

1) **Scan workfile → `data.md`**
2) **Review/edit `data.md`** (fill `*** UPDATE ***` fields, confirm `*** VERIFY ***` fields)
3) **Build narrative draft (`.docx`)** with tracked changes
4) **Build grid/schedule draft (`.xlsx`)** from the template pack

Outputs are written to the project's `Narrative/` folder by default.

---

## Quick Start

### Prerequisites

- Python 3.10+
- Set up a virtual environment and install Python dependencies:

```bash
cd ~/appraisal_ai
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell, not WSL):**
```powershell
cd ~\appraisal_ai
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

You'll need to activate the virtual environment each time you open a new terminal:
- **WSL/Linux/Mac:** `source ~/appraisal_ai/venv/bin/activate`
- **Windows PowerShell:** `~\appraisal_ai\venv\Scripts\Activate.ps1`

- Install OCR tools (required to read scanned PDFs):

**Windows (WSL/Ubuntu) or Linux:**
```bash
sudo apt-get update && sudo apt-get install -y tesseract-ocr poppler-utils
```

**Mac:**
```bash
brew install tesseract poppler
```

Claude will walk you through this if you're not sure how.

---

## Template Packs

This tool supports multiple appraisal types using a **template pack** system.

A template pack is a folder under `templates/<pack-name>/` containing:

- **`narrative.docx`** — a completed appraisal report used as the master template
- **`grid.xlsx`** (optional) — a completed adjustment grid / schedule template
- **`reference-data.md`** — every replaceable value extracted from the template (keyed by field name)
- **`rules.md`** (optional) — pack-specific rules (conditional sections, removals, calculations)

### Examples of Packs (customize to your setup)

- `res-1004` — URAR narrative + adjustment grid
- `res-1025` — 2–4 unit narrative + income schedule
- `commercial-retail` — narrative + rent roll + cap rate schedule
- `commercial-office` — narrative + income approach schedules
- `condemnation-land` — easement / partial acquisition narrative
- `condemnation-improved` — before/after, damages, cost-to-cure schedules
- `vacant-land` — vacant land narrative + land grid

You supply the completed templates. Packs are designed to be firm-specific and match your formatting, language, and workflow.

---

## Project Folder Structure

Each project uses this folder structure (Claude will create it for you):

```
2026-NNN Address/
├── Subject/         # Engagement letter, assessor card, deed, LOI, CoStar, etc.
├── Narrative/       # Output drafts go here
├── Comparables/     # Comp sheets, CoStar/MLS printouts, sale data
├── Exhibits/        # Maps, photos, figures
└── Template/        # Your completed appraisal (.docx) and grid (.xlsx) go here
```

---

## Commands (CLI)

### Step 1: Scan workfile → data.md

```bash
python scripts/scan_workfile.py "/path/to/2026-NNN Address"
```

### Step 2: Build narrative draft (tracked changes)

```bash
python scripts/build_draft.py "/path/to/2026-NNN Address" <pack-name>
```

Example:

```bash
python scripts/build_draft.py "/path/to/2026-NNN Address" condemnation-land
```

### Step 3: Build grid/schedule draft

```bash
python scripts/build_grid.py "/path/to/2026-NNN Address" <pack-name>
```

### Claude Code Slash Commands (Optional)

If using Claude Code, the tool can include slash commands:

| Command | Description |
|---------|-------------|
| `/scan <path>` | Extract data from workfile folder → `data.md` |
| `/draft <path> <pack>` | Build tracked-changes narrative `.docx` |
| `/grid <path> <pack>` | Build updated grid/schedule `.xlsx` |

---

## How It Works (High Level)

### Template-Driven Replacement

- `reference-data.md` defines all replaceable strings from your master template.
- During draft generation, the tool replaces each template reference value with the project value.
- Word output opens with Track Changes enabled so every change is reviewable.

### Conditional Content + Removals (Pack Rules)

Template packs may specify rules to:

- Remove template-specific paragraphs/sections (tracked deletion) when not applicable
- Toggle optional sections based on project flags (e.g., temp easement present, income approach used, cost approach included)
- Apply pack-specific mapping (alternate address formats, name variants, etc.)

### Excel Grids / Schedules

- `grid.xlsx` is treated as the master grid/schedule template.
- The tool fills the subject column and selected fields, then recalculates specified adjustments/schedules (pack-configurable).

---

## Project Data (`data.md`)

The scan step generates `data.md` with project fields.

- `*** UPDATE ***` = must be filled in manually
- `*** VERIFY ***` = detected automatically but should be confirmed

Example fields (varies by pack):

- `template_pack`
- `owner_name`
- `address`, `address_full`
- `parcel_id`
- `file_number`
- `effective_date`
- `land_sf`
- `zoning`
- `highest_and_best_use`
- `has_income_approach`
- `has_cost_approach`
- `has_sales_comps`
- `has_te` / `te_id` / `te_sf`
- `flood_status`

Packs can define additional fields unique to that appraisal type.

---

## Privacy / Data Handling

This tool runs locally on your machine, but **Claude Code sends your data to Anthropic's API for processing.** This means any workfile content, client names, addresses, financial data, and other project details you use with this tool will be transmitted to Anthropic's servers.

**Before using this tool with real client data:**

- Review your firm's data privacy and confidentiality policies
- Review [Anthropic's usage policy](https://www.anthropic.com/policies) and data handling practices
- Determine whether your clients' information can be processed by third-party AI services
- You are solely responsible for compliance with your firm's policies, client agreements, and applicable regulations (USPAP, state licensing board requirements, etc.)

**This tool is provided as-is. The authors are not responsible for how you handle client data.**

Additional recommended practices:

- Do not commit client templates (`.docx`, `.xlsx`) to git
- Gitignore draft outputs (`*DRAFT*`) and project folders
- Use a separate demo pack + fake project folder for any public demos

---

## Limitations

- Best results come from clean, consistent templates.
- Some replacements may require address/name variation lists (pack configurable).
- Complex Word formatting quirks (e.g., text split across multiple runs) are handled, but edge cases exist.

---

## License

This software is provided under a **limited use license**.

- **Permitted:** Personal and internal use within your own appraisal firm or practice. You may use this tool to produce appraisal reports for your own clients.
- **Not permitted without written authorization:** Reselling, sublicensing, redistributing, repackaging, or offering this tool (or any derivative of it) as a commercial product or service to third parties.
- **Not permitted:** Removing or altering license or attribution notices.

If you are interested in a commercial license, integration, or white-label arrangement, contact the author.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED. THE AUTHORS ARE NOT LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY ARISING FROM USE OF THIS SOFTWARE.

---

## Repository Layout

```
appraisal_ai/
├── scripts/
│   ├── scan_workfile.py         # Workfile scanner → data.md
│   ├── build_draft.py           # Template + data → tracked-changes .docx
│   ├── build_grid.py            # Grid template + data → updated .xlsx
│   └── utils.py                 # Markdown helpers, replacement utilities, etc.
├── templates/
│   ├── <pack-name>/
│   │   ├── narrative.docx       # Master template (local, not in git)
│   │   ├── grid.xlsx            # Master grid (optional; local, not in git)
│   │   ├── reference-data.md     # Replaceable values
│   │   └── rules.md              # Optional pack rules
├── requirements.txt
├── .gitignore
└── README.md
```

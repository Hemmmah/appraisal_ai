---
name: draft
description: Build a tracked-changes narrative .docx from template and data.md
user_invocable: true
---

# /draft — Build Tracked-Changes Narrative

## Usage
`/draft <project-folder-path> <template-type>`

Template types: `land-only`, `improved`

## What This Does
Reads the project's `data.md` and a master template, then produces a Word document with all field replacements shown as **tracked changes** (strikethrough old + underline new). The output opens in Word's Review mode so the appraiser can accept/reject each change.

No build script — Claude reads the template structure, builds replacements, and writes the docx directly using utility functions from `scripts/utils.py`.

## Steps

### 1. Verify inputs
- Confirm `<project-folder-path>/data.md` exists (if not, tell user to run `/scan` first)
- Confirm template type is valid and files exist at `~/appraisal_ai/templates/<template-type>/`
- Required template files: `reference-data.md` and `narrative.docx`
- If `narrative.docx` is not in the repo template folder, look in `<project-folder-path>/Template/` for a `.docx` file with "narrative" in the name, falling back to the first `.docx` found

### 2. Load data files
Run inline Python:
```python
import sys, os
sys.path.insert(0, os.path.expanduser('~/appraisal_ai/scripts'))
from utils import load_md

project_data = load_md('<project-path>/data.md')
ref_data = load_md(os.path.expanduser('~/appraisal_ai/templates/<template-type>/reference-data.md'))
print("Project data loaded:", len(project_data), "keys")
print("Reference data loaded:", len(ref_data.get('fields', {})), "fields")
```

### 3. Copy template to Narrative/
- Find or create `<project-path>/Narrative/` folder (support numbered-prefix variants like `2. Narrative/`)
- Generate output filename: `{file_number} {address} Narrative DRAFT.docx`
  - Get `file_number` and `address` from project data (try `address_forms[0]` if `address` is empty)
  - Clean address for filename: remove characters that aren't word chars, spaces, or hyphens
- Copy the template `.docx` to the output path using `shutil.copy2()`

### 4. Build and apply tracked-change replacements
Run a single inline Python script that does everything. Use `~/appraisal_ai/venv/bin/python` to execute.

```python
import os, re, sys, shutil, zipfile, tempfile, copy
from lxml import etree

sys.path.insert(0, os.path.expanduser('~/appraisal_ai/scripts'))
from utils import (
    W, load_md, reset_change_id, get_paragraph_text,
    tracked_replace_across_runs, merge_all_runs,
    find_table_by_text, get_table_rows, remove_table_rows, add_table_row,
    remove_rows_by_text, find_paragraphs_between, remove_paragraphs,
    make_paragraph, insert_paragraphs_after,
)

# --- Config ---
PROJECT_PATH = '<project-path>'
TEMPLATE_TYPE = '<template-type>'
OUTPUT_PATH = '<output-path>'  # full path to the copied docx in Narrative/
TEMPLATE_DOCX = '<template-docx-path>'  # original template for reference

TC_TAG = f'{W}tc'

# --- Load data ---
project_data = load_md(os.path.join(PROJECT_PATH, 'data.md'))
ref_data = load_md(os.path.expanduser(f'~/appraisal_ai/templates/{TEMPLATE_TYPE}/reference-data.md'))
proj_fields = project_data.get('fields', project_data)
ref_fields = ref_data.get('fields', {})

reset_change_id()

# --- Extract and parse document.xml ---
with zipfile.ZipFile(OUTPUT_PATH, 'r') as z:
    with z.open('word/document.xml') as f:
        tree = etree.parse(f)

# --- Merge fragmented runs ---
merge_all_runs(tree)
print("Merged fragmented XML runs")

# --- Normalize double spaces in Word XML ---
# Word inserts extra spaces between runs. After merge_all_runs some persist.
# Collapse them so reference values with double spaces can match.
root = tree.getroot()
double_space_fixed = 0
for t_elem in root.iter(f'{W}t'):
    if t_elem.text and '  ' in t_elem.text:
        new_text = re.sub(r'  +', ' ', t_elem.text)
        if new_text != t_elem.text:
            t_elem.text = new_text
            double_space_fixed += 1
if double_space_fixed:
    print(f"Normalized double spaces in {double_space_fixed} text elements")

# --- Build replacement map ---
replacements = []
skip_keys = {'address_forms', 'remove_sections', 'comps'}

# --- Detect duplicate reference values ---
# Some fields share the same template text (e.g., hbu_as_vacant and hbu_as_improved
# both say "Retail Commercial Building"). These are handled as special cases AFTER
# the main replacement loop — see the HBU special case block below.
# Skip these fields from the global replacement to prevent first-wins collision.
duplicate_value_fields = set()
seen_old_values = {}
for field, old_val in ref_fields.items():
    if field in skip_keys or not isinstance(old_val, str):
        continue
    if old_val in seen_old_values:
        duplicate_value_fields.add(field)
        duplicate_value_fields.add(seen_old_values[old_val])
    else:
        seen_old_values[old_val] = field

for field, old_val in ref_fields.items():
    if field in skip_keys or field in duplicate_value_fields:
        continue
    if not isinstance(old_val, str):
        continue
    new_val = proj_fields.get(field)
    if new_val and str(old_val) != str(new_val):
        replacements.append((str(old_val), str(new_val)))

# Address forms: replace each template address variation with project's first address form
ref_addresses = ref_fields.get('address_forms', [])
new_addresses = proj_fields.get('address_forms', [])
new_address_full = proj_fields.get('address_full', '')
if not new_address_full and new_addresses:
    new_address_full = new_addresses[0]

if ref_addresses and new_address_full:
    for old_addr in ref_addresses:
        if old_addr != new_address_full:
            replacements.append((old_addr, new_address_full))

# Property history (try multiple reference keys)
for key in ['property_history_1', 'property_history_2', 'property_history']:
    old_val = ref_fields.get(key)
    new_val = proj_fields.get(key) or proj_fields.get('property_history')
    if old_val and new_val and old_val != new_val:
        replacements.append((str(old_val), str(new_val)))

# Sort by length descending — longer matches first
replacements.sort(key=lambda x: len(x[0]), reverse=True)

# Normalize double spaces in old-text values to match the cleaned XML
replacements = [(re.sub(r'  +', ' ', old), new) for old, new in replacements]
print(f"Prepared {len(replacements)} replacements")

# --- Apply tracked-change replacements ---
body = root.find(f'{W}body')
paragraphs = list(body.iter(f'{W}p'))
replaced_count = 0
not_found = []

for old_text, new_text in replacements:
    found = False
    for para in paragraphs:
        safety = 0
        while safety < 50 and tracked_replace_across_runs(para, old_text, new_text):
            found = True
            replaced_count += 1
            safety += 1
    # Also replace inside hyperlinks
    HYPERLINK = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}hyperlink'
    for hl in root.iter(HYPERLINK):
        for run in hl.findall(f'{W}r'):
            t_elem = run.find(f'{W}t')
            if t_elem is not None and t_elem.text and old_text in t_elem.text:
                t_elem.text = t_elem.text.replace(old_text, new_text)
                found = True
                replaced_count += 1
    if not found:
        not_found.append(old_text[:60])

print(f"Applied {replaced_count} tracked-change replacements")
if not_found:
    print(f"Could not find {len(not_found)} reference values:")
    for nf in not_found:
        print(f"  - {nf}...")

# --- HBU special case (duplicate reference value) ---
# hbu_as_vacant and hbu_as_improved share the same template text
# ("Retail Commercial Building"). The template has 3 instances, ALL
# describing the improved/current use:
#   "Improvements:Retail Commercial Building"
#   "(Before Condition):Retail Commercial Building"
#   "(After Condition):Retail Commercial Building"
# Strategy:
#   1. Replace ALL instances of the old HBU value with hbu_as_improved
#   2. The hbu_as_vacant value appears only in narrative discussion — no
#      direct template text to replace (the appraiser writes it fresh)
hbu_old = re.sub(r'  +', ' ', str(ref_fields.get('hbu_as_vacant', '')))
hbu_improved_new = str(proj_fields.get('hbu_as_improved', ''))
hbu_replaced = 0
if hbu_old and hbu_improved_new and hbu_old != hbu_improved_new:
    for para in root.iter(f'{W}p'):
        text = get_paragraph_text(para)
        if hbu_old in text:
            if tracked_replace_across_runs(para, hbu_old, hbu_improved_new):
                hbu_replaced += 1
if hbu_replaced:
    print(f"Applied {hbu_replaced} HBU replacements ('{hbu_old}' → '{hbu_improved_new}')")

# --- Helper: safe paragraph removal ---
def safe_remove_paragraph(para):
    parent = para.getparent()
    if parent is None:
        return
    if parent.tag == TC_TAG:
        idx = list(parent).index(para)
        parent.remove(para)
        empty_p = etree.Element(f'{W}p')
        parent.insert(idx, empty_p)
    else:
        parent.remove(para)

# --- Handle TE section removal ---
# IMPORTANT: has_te is at the TOP LEVEL of data.md, not under fields:
has_te = project_data.get('has_te', proj_fields.get('has_te', True))
template_has_te = ref_data.get('has_te', True)
te_deleted = 0

if not has_te and template_has_te:
    te_id = ref_fields.get('te_id', 'TE-')
    te_value = ref_fields.get('te_value', '')
    te_primary_phrases = [
        'Value of the Temporary Easement',
        'value of the temporary easement',
        'Temporary Easement Language',
        'temporary easement is anticipated',
        'term of the TCE',
        'temporary construction easement',
        'lost rent calculation',
        'determine the value of the temporary',
        'No Interference',
        'upon the TCE',
        'Restoration',
        'obstruction will be placed, erected',
        'restore the TCE',
        'grantor covenants and agrees that no building',
    ]
    te_standalone_phrases = [
        'Temporary Easement (',
        'temporary easement (',
    ]

    # Step 1: Remove entire table rows containing "Temporary Easement"
    # Uses table helpers — see "Remove TE Table Rows" recipe in .claude/skills/tables.md
    for tbl in root.iter(f'{W}tbl'):
        te_deleted += remove_rows_by_text(tbl, 'Temporary Easement')
        te_deleted += remove_rows_by_text(tbl, 'temporary easement')

    # Step 2: Remove TE paragraphs (non-table)
    for para in list(body.iter(f'{W}p')):
        text = get_paragraph_text(para)
        if te_id and te_id in text:
            safe_remove_paragraph(para)
            te_deleted += 1
            continue
        if any(phrase in text for phrase in te_primary_phrases):
            safe_remove_paragraph(para)
            te_deleted += 1
            continue
        if any(phrase in text for phrase in te_standalone_phrases):
            if len(text.strip()) < 200:
                safe_remove_paragraph(para)
                te_deleted += 1
                continue
        # Remove TE calculation paragraphs (e.g. "879 SF x $75.00 PSF x 10% x 1 year = $6,593")
        if te_value and te_value in text and ('SF x' in text or 'x 1 year' in text):
            safe_remove_paragraph(para)
            te_deleted += 1
            continue
        # Rewrite mixed paragraphs
        te_rewrites = [
            ('and one temporary easement takings', 'taking'),
            ('and one temporary easement.', '.'),
            ('and one temporary easement ', ' '),
            ('one temporary construction easement and ', ''),
            ('one temporary construction easement (', ''),
            ('and temporary easement scenario', ''),
            ('permanent easement and temporary easement scenario', 'permanent easement scenario'),
            ('Finally, we address the value of the temporary easement and its impact on value.  ', ''),
            ('Finally, we address the value of the temporary easement and its impact on value. ', ''),
        ]
        for old_phrase, new_phrase in te_rewrites:
            if old_phrase in text:
                if tracked_replace_across_runs(para, old_phrase, new_phrase):
                    te_deleted += 1
    if te_deleted:
        print(f"Removed/rewrote {te_deleted} TE items")

# --- Handle remove_sections (merge from both ref and project data) ---
remove_list = (ref_fields.get('remove_sections', []) or []) + (proj_fields.get('remove_sections', []) or [])
# Normalize smart quotes to straight quotes for matching (Word uses Unicode
# right single quote U+2019 while Markdown data files have straight apostrophe U+0027)
smart_quote_map = {'\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"'}
sections_deleted = 0
if remove_list:
    for para in list(body.iter(f'{W}p')):
        text = get_paragraph_text(para)
        # Normalize smart quotes in paragraph text for matching
        text_norm = text
        for smart, straight in smart_quote_map.items():
            text_norm = text_norm.replace(smart, straight)
        for remove_text in remove_list:
            # Also normalize the search string
            remove_norm = remove_text
            for smart, straight in smart_quote_map.items():
                remove_norm = remove_norm.replace(smart, straight)
            if remove_norm in text_norm:
                safe_remove_paragraph(para)
                sections_deleted += 1
                break
    if sections_deleted:
        print(f"Removed {sections_deleted} template-specific paragraphs")

# --- Update comp summary table from comp_grid.md ---
import statistics as _stats
comp_grid_path = os.path.join(PROJECT_PATH, '_workstate', 'comp_grid.md')
if os.path.exists(comp_grid_path):
    from datetime import datetime as _dt
    comp_grid = load_md(comp_grid_path)
    appraisal_date_str = proj_fields.get('effective_date', '')
    try:
        appraisal_date = _dt.strptime(appraisal_date_str, '%B %d, %Y')
    except:
        appraisal_date = None

    if appraisal_date and comp_grid.get('comps'):
        adjusted_psfs = []
        days_per_month = 30.42
        monthly_rate = 0.0006
        subject_flood = proj_fields.get('flood_status', '').lower()
        subject_in_flood = 'flood' in subject_flood and 'not' not in subject_flood

        for c in comp_grid['comps']:
            price_str = str(c.get('sale_price', '0'))
            if '***' in price_str:
                continue
            price = int(re.sub(r'[^\d]', '', price_str))
            sf_str = str(c.get('land_sf', '0'))
            sf = int(re.sub(r'[^\d]', '', sf_str))
            if price == 0 or sf == 0:
                continue
            date_str = str(c.get('sale_date', ''))
            try:
                sale_date = _dt.strptime(date_str, '%B %d, %Y')
            except:
                continue
            raw_psf = price / sf
            months = (appraisal_date - sale_date).days / days_per_month
            time_adj_psf = raw_psf * (1 + months * monthly_rate)
            # Flood adjustment
            flood_adj = 0.0
            comp_flood = str(c.get('flood_zone', '')).lower()
            if '***' not in comp_flood:
                comp_in_flood = any(x in comp_flood for x in ['flood', '100-year', 'floodplain'])
                if comp_in_flood and not subject_in_flood:
                    flood_adj = 0.05
                elif subject_in_flood and not comp_in_flood:
                    flood_adj = -0.05
            final_psf = time_adj_psf * (1 + flood_adj)
            adjusted_psfs.append({'num': c.get('comp_number'), 'psf': round(final_psf)})

        if adjusted_psfs:
            adjusted_psfs.sort(key=lambda x: x['psf'])
            psf_values = [c['psf'] for c in adjusted_psfs]
            psf_low, psf_high = psf_values[0], psf_values[-1]
            psf_avg = round(sum(psf_values) / len(psf_values))
            psf_median = round(_stats.median(psf_values))

            # Find and rebuild the "Comparable Sales After Adjustments" table
            # Uses table helpers — see "Update Comp Summary Table" recipe in .claude/skills/tables.md
            tbl = find_table_by_text(root, 'Comparable Sales After Adjustments')
            if tbl is not None:
                rows = get_table_rows(tbl)
                format_row = copy.deepcopy(rows[2]) if len(rows) > 2 else None  # Save data row as format template
                remove_table_rows(tbl, 2)  # Keep header rows 0 and 1
                for comp in adjusted_psfs:
                    add_table_row(tbl, [str(comp['num']), f" $       {comp['psf']} "], clone_format_from=format_row)
                print(f"Updated comp summary table: {len(adjusted_psfs)} comps")

            # Update summary paragraph text
            ref_psf_summary = ref_fields.get('comp_psf_summary', '')
            if ref_psf_summary:
                # Normalize double spaces in reference text to match cleaned XML
                ref_psf_summary = re.sub(r'  +', ' ', ref_psf_summary)
                new_psf_summary = f"adjusted unit prices that range from ${psf_low} PSF to ${psf_high} PSF. The arithmetic average is ${psf_avg} PSF. The median is ${psf_median} PSF."
                for para in list(body.iter(f'{W}p')):
                    text = get_paragraph_text(para)
                    if ref_psf_summary in text:
                        tracked_replace_across_runs(para, ref_psf_summary, new_psf_summary)
                        print(f"Updated comp PSF summary: ${psf_low}-${psf_high}, avg ${psf_avg}, med ${psf_median}")
                        break

# --- Replace LAND SALE NO. writeup sections ---
comp_writeups_path = os.path.join(PROJECT_PATH, '_workstate', 'comp_writeups.md')
writeups_replaced = 0
if os.path.exists(comp_writeups_path):
    comp_writeups = load_md(comp_writeups_path)
    writeup_list = comp_writeups.get('writeups', [])

    if writeup_list:
        # Find the section boundaries: "LAND SALE MAP" to "Comparative Analysis and Land Value Conclusion"
        # The comp writeups live between these two landmarks
        all_paras = list(body.iter(f'{W}p'))

        # Find anchor points
        map_para = None
        analysis_para = None
        first_sale_para = None
        for para in all_paras:
            text = get_paragraph_text(para)
            if 'LAND SALE MAP' in text and map_para is None:
                map_para = para
            if 'LAND SALE NO.' in text and first_sale_para is None:
                first_sale_para = para
            if 'Comparative Analysis and Land Value Conclusion' in text:
                analysis_para = para
                break

        # Determine start: use first LAND SALE paragraph (or map_para if not found)
        section_start = first_sale_para or map_para

        if section_start is not None and analysis_para is not None:
            # Collect all paragraphs to remove (between start and analysis heading, exclusive of analysis)
            paras_to_remove = find_paragraphs_between(
                body, get_paragraph_text(section_start),
                'Comparative Analysis and Land Value Conclusion',
                inclusive_start=True, inclusive_end=False
            )

            if paras_to_remove:
                # Save the LAND SALE MAP paragraph (we'll keep it) and clone format from first sale heading
                # Find a heading paragraph to clone format from
                heading_format = None
                detail_format = None
                for para in paras_to_remove:
                    text = get_paragraph_text(para)
                    if 'LAND SALE NO.' in text and 'AERIAL' not in text:
                        heading_format = copy.deepcopy(para)
                    elif text.startswith('Location:') or text.startswith('City'):
                        detail_format = copy.deepcopy(para)
                    if heading_format and detail_format:
                        break

                # Get insertion anchor (paragraph before the section)
                section_start_parent = section_start.getparent()
                section_start_idx = list(section_start_parent).index(section_start)
                anchor_para = list(section_start_parent)[section_start_idx - 1] if section_start_idx > 0 else None

                # Remove old comp writeup paragraphs
                removed_count = remove_paragraphs(body, paras_to_remove)
                print(f"Removed {removed_count} old comp writeup paragraphs")

                # Build new comp writeup paragraphs
                # LAYOUT: Each comp gets TWO pages in the template:
                #   Page 1: Sale details (heading + field lines with blank lines between)
                #   Page 2: Aerial photo placeholder (centered heading + empty space)
                # Page breaks (<w:br w:type="page"/>) separate details from aerial,
                # and aerial from the next sale.
                #
                # FORMATTING: The template uses:
                #   - Empty paragraph between EVERY detail line
                #   - Headings centered (jc=center), detail lines left (jc=left)
                #   - Hanging indent on detail lines (ind left=3600 hanging=3600)
                #   - All paragraphs have line=240 spacing
                # Without blank-line separators the writeup looks "bunched up" in Word.

                def make_page_break_para(clone_from=None):
                    """Create an empty paragraph containing a page break."""
                    p = make_paragraph('', clone_format_from=clone_from)
                    # Add a run with a page break element
                    r = p.find(f'{W}r')
                    if r is None:
                        r = etree.SubElement(p, f'{W}r')
                    br = etree.SubElement(r, f'{W}br')
                    br.set(f'{W}type', 'page')
                    return p

                new_paras = []
                for wu_idx, wu in enumerate(writeup_list):
                    num = wu.get('comp_number', '?')

                    # --- PAGE 1: Sale Details ---
                    # Heading: LAND SALE NO. X (centered)
                    new_paras.append(make_paragraph(f'LAND SALE NO. {num}', clone_format_from=heading_format))
                    # Blank line after heading
                    new_paras.append(make_paragraph('', clone_format_from=heading_format))

                    # Detail lines — each followed by a blank paragraph
                    detail_lines = [
                        f"Location:{wu.get('address', '*** UPDATE ***')}",
                        f"City/County:{wu.get('city_county', '*** UPDATE ***')}",
                        f"Assessor Account No.:{wu.get('parcel_number', '*** UPDATE ***')}",
                        f"Grantor:{wu.get('grantor', '*** UPDATE ***')}",
                        f"Grantee:{wu.get('grantee', '*** UPDATE ***')}",
                        f"Recording/Reception No.:{wu.get('recording_info', '*** UPDATE ***')}",
                        f"Sale Date:{wu.get('sale_date', '*** UPDATE ***')}",
                        f"Sale Price:{wu.get('sale_price', '*** UPDATE ***')}",
                        f"Parcel Size:{wu.get('land_acres', '?')} Acres ({wu.get('land_sf', '?')} SF)",
                        f"Unit Price:{wu.get('price_psf', '*** UPDATE ***')} Per SF",
                    ]
                    # Optional traffic count
                    if wu.get('traffic_count'):
                        detail_lines.append(f"Traffic Count:{wu['traffic_count']}")
                    detail_lines.append(f"Zoning:{wu.get('zoning', '*** UPDATE ***')}")
                    detail_lines.append(f"Comments:{wu.get('comments', '*** UPDATE ***')}")

                    for line in detail_lines:
                        new_paras.append(make_paragraph(line, clone_format_from=detail_format))
                        new_paras.append(make_paragraph('', clone_format_from=detail_format))

                    # Page break after details → aerial goes on next page
                    new_paras.append(make_page_break_para(clone_from=detail_format))

                    # --- PAGE 2: Aerial Photo Placeholder ---
                    new_paras.append(make_paragraph('', clone_format_from=heading_format))
                    new_paras.append(make_paragraph(f'LAND SALE NO. {num} AERIAL', clone_format_from=heading_format))
                    # Empty paragraphs to fill the aerial page (photo placeholder space)
                    for _ in range(20):
                        new_paras.append(make_paragraph('', clone_format_from=heading_format))

                    # Page break before next sale (except after the last one)
                    if wu_idx < len(writeup_list) - 1:
                        new_paras.append(make_page_break_para(clone_from=heading_format))

                # Insert new paragraphs
                if anchor_para is not None:
                    inserted = insert_paragraphs_after(body, anchor_para, new_paras)
                    writeups_replaced = len(writeup_list)
                    print(f"Inserted {inserted} paragraphs for {writeups_replaced} comp writeups")
                else:
                    print("WARNING: Could not find anchor paragraph for comp writeup insertion")
        else:
            if section_start is None:
                print("WARNING: Could not find LAND SALE NO. section in template")
            if analysis_para is None:
                print("WARNING: Could not find 'Comparative Analysis' section boundary")
else:
    print("No comp_writeups.md found — comp writeup sections will remain as template text")
    print("WARNING: Comp writeups still contain template project's sales — appraiser must rewrite")

# --- Save modified XML back into docx ---
xml_bytes = etree.tostring(tree, xml_declaration=True, encoding='UTF-8', standalone=True)
# Fix XML declaration quotes (lxml uses single, Word expects double)
xml_bytes = xml_bytes.replace(
    b"<?xml version='1.0' encoding='UTF-8' standalone='yes'?>",
    b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
)

temp_dir = tempfile.mkdtemp()
temp_docx = os.path.join(temp_dir, 'temp.docx')
with zipfile.ZipFile(OUTPUT_PATH, 'r') as zin:
    with zipfile.ZipFile(temp_docx, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename == 'word/document.xml':
                zout.writestr(item, xml_bytes)
            else:
                zout.writestr(item, zin.read(item.filename))
shutil.move(temp_docx, OUTPUT_PATH)
shutil.rmtree(temp_dir, ignore_errors=True)

# --- Enable track changes in settings.xml ---
settings_ns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
temp_dir2 = tempfile.mkdtemp()
temp_docx2 = os.path.join(temp_dir2, 'temp.docx')
with zipfile.ZipFile(OUTPUT_PATH, 'r') as zin:
    with zipfile.ZipFile(temp_docx2, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename == 'word/settings.xml':
                settings_xml = zin.read(item.filename)
                settings_tree = etree.fromstring(settings_xml)
                tc = settings_tree.find(f'{{{settings_ns}}}trackChanges')
                if tc is None:
                    tc = etree.SubElement(settings_tree, f'{{{settings_ns}}}trackChanges')
                rv = settings_tree.find(f'{{{settings_ns}}}revisionView')
                if rv is None:
                    rv = etree.SubElement(settings_tree, f'{{{settings_ns}}}revisionView')
                rv.set(f'{{{settings_ns}}}markup', '1')
                new_xml = etree.tostring(settings_tree, xml_declaration=True, encoding='UTF-8', standalone=True)
                new_xml = new_xml.replace(
                    b"<?xml version='1.0' encoding='UTF-8' standalone='yes'?>",
                    b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                )
                zout.writestr(item, new_xml)
            else:
                zout.writestr(item, zin.read(item.filename))
shutil.move(temp_docx2, OUTPUT_PATH)
shutil.rmtree(temp_dir2, ignore_errors=True)

# --- Report review items ---
review_fields = [k for k, v in proj_fields.items() if isinstance(v, str) and '***' in v]
if review_fields:
    print(f"{len(review_fields)} fields still need manual input:")
    for rf in review_fields:
        print(f"  - {rf}")

if writeups_replaced:
    print(f"Comp writeups: {writeups_replaced} LAND SALE NO. sections replaced with project comps")
else:
    print("Comp writeups: NOT replaced — template comp writeups remain (appraiser must rewrite)")

print(f"\nDraft saved to: {OUTPUT_PATH}")
print("Open in Word and review tracked changes.")
```

**Before running:** Replace `<project-path>`, `<template-type>`, `<output-path>`, and `<template-docx-path>` with actual values determined in steps 1–3.

### 5. Report results
Tell the user:
- How many replacements were made
- What reference values couldn't be found in the template
- How many TE paragraphs were removed (if applicable)
- How many template-specific sections were removed
- Fields still needing manual input (`*** UPDATE ***` / `*** VERIFY ***`)
- Full path to the output file

## Critical Rules

- **Use utility functions from `scripts/utils.py`**: `W`, `load_md`, `reset_change_id`, `get_paragraph_text`, `tracked_replace_across_runs`, `merge_all_runs`, table helpers (`find_table_by_text`, `get_table_rows`, `remove_table_rows`, `add_table_row`, `remove_rows_by_text`), and section helpers (`find_paragraphs_between`, `remove_paragraphs`, `make_paragraph`, `insert_paragraphs_after`)
- **Double-space normalization**: After `merge_all_runs()`, collapse all double spaces in `<w:t>` elements with `re.sub(r'  +', ' ', text)`. Also normalize the old-text side of all replacements. Word inserts extra spaces between runs — without this step, many reference values won't match.
- **`has_te` is at the top level of data.md**, not under `fields:`. Always read it as `project_data.get('has_te', proj_fields.get('has_te', True))`.
- **`remove_sections` from both sources**: Merge `ref_fields['remove_sections']` and `proj_fields['remove_sections']` — templates and projects can both specify sections to remove. (These are loaded from reference-data.md and data.md respectively.)
- **Safe paragraph removal**: When removing a paragraph whose parent is `<w:tc>` (table cell), replace with empty `<w:p>` — never leave a cell empty or Word will corrupt
- **TE table rows**: Use `remove_rows_by_text()` to remove entire table rows containing "Temporary Easement". Also remove TE calculation paragraphs (containing the TE dollar value and "SF x"). See `.claude/skills/tables.md`.
- **Table format cloning**: When rebuilding tables (comp summary), save a `copy.deepcopy()` of an existing data row BEFORE removing rows, then pass it as `clone_format_from` when adding new rows. This preserves cell widths, fonts, alignment, and borders.
- **XML declaration fix**: After `etree.tostring()`, always replace single-quote XML declaration with double-quote version
- **Context-aware replacements**: Fields with `_context` companion keys in reference-data.md are replaced by finding the specific table row containing the context label, not by global find-replace. This prevents duplicate old-value collisions. See "Known Replacement Edge Cases" section.
- **Replacement order**: Sort by old-text length descending so longer matches are tried first
- **Address forms**: Replace each template address variation with the project's first address form
- **Hyperlinks**: Also check and replace text inside `<w:hyperlink>` runs — they're nested and get missed by `tracked_replace_across_runs`
- **Run all Python through** `~/appraisal_ai/venv/bin/python`
- **Never use "N/A" as a field value** — empty fields should be empty strings so the build skips them

## Known Replacement Edge Cases

These are field types that fail with standard global find-replace. The build script handles each one differently:

### 1. Word Caps-Styled Fields (Phantom Values)
Some text in Word appears as ALL CAPS but the underlying XML stores mixed-case text with a `<w:caps/>` formatting property. Example: "EXAMPLE HOLDINGS, LLC" is stored as "Example Holdings, LLC" with caps styling. The all-caps version does NOT exist as literal text.

**How to handle:** Do NOT list the caps version as a separate reference field. The mixed-case field replacement handles it — when "Example Holdings, LLC" becomes "Hector Vargas and Alma Vargas", Word's caps formatting renders it as "HECTOR VARGAS AND ALMA VARGAS" automatically. If you see `owner_name_caps` or similar `_caps` fields in reference-data.md, they should be commented out with this explanation.

### 2. Duplicate Reference Values (Context-Aware Replacement)
When two fields share the same template text (e.g., `hbu_as_vacant` and `hbu_as_improved` both say "Retail Commercial Building"), global find-replace changes ALL instances to the first field's new value, leaving none for the second.

**How to handle:** Add a `_context` companion key in reference-data.md (e.g., `hbu_as_vacant_context: "As Vacant"`). The build script detects `_context` keys and routes those fields to context-aware replacement: it finds the table row or paragraph containing the context label, then replaces only within that specific cell. See the "Context-aware replacements" block in the inline Python above.

### 3. Split-Run Dollar Formatting
Word sometimes formats dollar amounts with the `$` sign and the number in separate XML runs, connected by tab stops or spacing attributes rather than literal space characters. Example: "$ 75" in the template may never appear as continuous text even after `merge_all_runs()`.

**How to handle:** Do NOT list these as reference values. They are phantom text. Use more specific variants that DO exist as literal text (e.g., `psf_concluded_4: "$75 PSF"`, `psf_concluded_5: "$75.00 per square foot"`). The spaced-dollar format (`"$ 75"`) should be commented out in reference-data.md.

## Known Limitations — Sections That Cannot Be Auto-Replaced

The draft skill handles field-value replacements (addresses, dates, dollar amounts, names). It does NOT handle these template narrative sections, which are unique prose per project:

### 1. Comparable Sale Writeups (LAND SALE NO. 1, 2, 3...)
**If `_workstate/comp_writeups.md` exists** (generated by the Comp Writer agent in Phase 3), the draft builder will automatically replace the template's LAND SALE NO. sections with new writeups built from project comp data. The old template comp paragraphs are removed and new paragraphs are inserted with the project's actual comps. This is a hard replacement (not tracked changes) since the entire section content changes.

**If `comp_writeups.md` does NOT exist**, the template's comp writeups remain in place. Warn the user:
> "The comparable sale writeup section (LAND SALE NO. 1, 2, 3...) still contains the template project's sales. You must rewrite these with your actual comparables."

The comp summary table (Comparable Sales After Adjustments) IS always handled — it gets rebuilt from comp_grid.md. The comp range, date range, and PSF summary lines are also replaced via reference-data.md fields.

### 2. Easement / Encumbrance Descriptions
The template's title/easement section describes specific easements from the template property (grantor names, reception numbers, descriptions). These are not field values — they're narrative text.

**What to do:** Add the template easement reception numbers to `remove_sections` in reference-data.md so those paragraphs get stripped. Then warn the user to add their project's actual easement descriptions.

### 3. Property-Specific Narrative (neighbors, site description, property history)
Some narrative sections describe template-specific details (e.g., "1453 Example Street lies to the south"). Field replacement handles named fields (surrounding_north, surrounding_east, etc.) but may miss embedded references.

**What to do:** Add unique template-specific text fragments to `remove_sections` in reference-data.md. The Phase 5 final review should check for any remaining template property references.

## Notes
- The draft uses Word tracked changes (w:del + w:ins XML) so every replacement is visible
- If `has_te: false` in data.md but the template has TE sections, those paragraphs are hard-removed (not tracked-deleted)
- **TE removal also covers TCE clauses**: "No Interference", "Restoration", "upon the TCE", and related covenant language are removed when `has_te: false`
- Template-specific sections listed in `remove_sections` are also hard-removed
- Fields with `*** UPDATE ***` or `*** REVIEW ***` in data.md are flagged in output
- Output goes to `<project-folder>/Narrative/` as `{file_number} {address} Narrative DRAFT.docx`
- **Comp adjusted PSF summary table**: If `_workstate/comp_grid.md` exists, the script calculates adjusted PSFs and rebuilds the comp summary table using helpers from `scripts/utils.py`. See the "Update Comp Summary Table" recipe in `.claude/skills/tables.md` for details. Comps with `*** UPDATE ***` prices are skipped. These are preliminary values based on default adjustments — the user may refine after finalizing the grid in Excel.
- **Table operations**: All table manipulation (find, read, modify, add/remove rows) uses helper functions from `scripts/utils.py`. See `.claude/skills/tables.md` for the full API and appraisal-specific recipes.

#!/usr/bin/env python3
"""
build_index.py — Parse converted .md appraisal files and build a master index.

Extracts structured metadata (address, type, value, date, etc.) from each file
and outputs INDEX.md (human-readable table) + INDEX.json (programmatic search).

Zero pip dependencies — stdlib only.

Usage:
    python3 build_index.py --md-path /path/to/md-archives
    python3 build_index.py --md-path /path/to/md-archives --output /path/to/INDEX.md
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path


# ── Compiled regex patterns ──────────────────────────────────────────────────

# Job number
RE_JOB_NUMBER = [
    re.compile(r'File\s*No\.?\s*[:.]?\s*(\d{4}-\d{2,4})', re.IGNORECASE),
    re.compile(r'File\s*#\s*[:.]?\s*(\d{4}-\d{2,4})', re.IGNORECASE),
    re.compile(r'Job\s*(?:No|Number|#)\.?\s*[:.]?\s*(\d{4}-\d{2,4})', re.IGNORECASE),
    re.compile(r'Our\s*File\s*[:.]?\s*(\d{4}-\d{2,4})', re.IGNORECASE),
]
RE_JOB_FROM_FILENAME = re.compile(r'(\d{4}-\d{2,4})')

# Address
RE_ADDRESS = [
    re.compile(r'RE:\s*(.+?)(?:\n|$)', re.IGNORECASE),
    re.compile(r'Re:\s*(.+?)(?:\n|$)'),
    re.compile(r'Subject\s*Property:\s*(.+?)(?:\n|$)', re.IGNORECASE),
    re.compile(r'Property\s*Address:\s*(.+?)(?:\n|$)', re.IGNORECASE),
]

# Effective date
RE_DATE = [
    re.compile(r'Date\s*of\s*Valuation\s*[:.]?\s*(.+?)(?:\n|$)', re.IGNORECASE),
    re.compile(r'Effective\s*Date\s*[:.]?\s*(.+?)(?:\n|$)', re.IGNORECASE),
    re.compile(r'Valuation\s*Date\s*[:.]?\s*(.+?)(?:\n|$)', re.IGNORECASE),
    re.compile(r'[Aa]s\s+of\s+(\w+\s+\d{1,2},?\s+\d{4})'),
]

# Value
RE_DOLLAR = re.compile(r'\$\s*([\d,]+(?:\.\d{2})?)')

VALUE_CONTEXT_PHRASES = [
    'market value', 'value of the subject', 'value conclusion',
    'appraised value', 'just compensation', 'total compensation',
    'concluded value', 'final value',
]

# Land area
RE_LAND_SF = re.compile(r'([\d,]+(?:\.\d+)?)\s*(?:square\s*feet|sq\.?\s*ft\.?|SF)', re.IGNORECASE)
RE_LAND_AC = re.compile(r'([\d,]+(?:\.\d+)?)\s*(?:acres?|AC)', re.IGNORECASE)

# County
RE_COUNTY = [
    re.compile(r'(\w+)\s+County', re.IGNORECASE),
    re.compile(r'County\s+of\s+(\w+)', re.IGNORECASE),
]

VALID_CO_COUNTIES = {
    'adams', 'arapahoe', 'boulder', 'broomfield', 'clear creek', 'denver',
    'douglas', 'eagle', 'el paso', 'garfield', 'gilpin', 'grand', 'jefferson',
    'larimer', 'mesa', 'park', 'pitkin', 'pueblo', 'routt', 'summit', 'weld',
    'chaffee', 'delta', 'gunnison', 'lake', 'la plata', 'montrose', 'morgan',
    'otero', 'rio blanco', 'san miguel', 'teller',
}

# Client
RE_CLIENT = [
    re.compile(r'[Dd]ear\s+(Mr\.|Ms\.|Mrs\.|Dr\.)\s*(.+?)(?:\n|,|:|$)'),
    re.compile(r'[Dd]ear\s+(.+?)(?:\n|:|,|$)'),
    re.compile(r'[Aa]ttention:\s*(.+?)(?:\n|$)'),
]

# Appraiser
RE_APPRAISER = re.compile(
    r'([\w][\w\s,.]+?),?\s*(?:MAI|SRA|ASA|AI-GRS|Certified\s*General)',
    re.IGNORECASE
)

# Purpose
RE_PURPOSE = [
    re.compile(r'[Pp]urpose\s*(?:of\s*(?:the\s*)?)?[Aa]ppraisal\s*[:.]?\s*(.+?)(?:\n|$)'),
    re.compile(r'[Ii]ntended\s*[Uu]se\s*[:.]?\s*(.+?)(?:\n|$)'),
]

# Approaches
RE_APPROACHES = [
    (re.compile(r'[Ss]ales\s*[Cc]omparison\s*[Aa]pproach'), 'sales-comparison'),
    (re.compile(r'[Cc]ost\s*[Aa]pproach'), 'cost'),
    (re.compile(r'[Ii]ncome\s*(?:[Cc]apitalization\s*)?[Aa]pproach'), 'income'),
    (re.compile(r'[Dd]irect\s*[Cc]apitalization'), 'income'),
]

# Property type keywords (order matters — first match wins)
PROPERTY_TYPE_RULES = [
    (r'conservation\s*easement', 'special-purpose', 'conservation-easement'),
    (r'vacant\s*land|unimproved\s*land|land\s*valuation|land\s*only', 'land', 'vacant'),
    (r'single.family|single-family|SFR|\bresidence\b', 'residential', 'sfr'),
    (r'multi.?family|apartment|duplex|triplex|fourplex', 'residential', 'multifamily'),
    (r'condominium|condo\b|townhome|townhouse', 'residential', 'condo'),
    (r'mobile\s*home|manufactured\s*home', 'residential', 'manufactured'),
    (r'office\s*building|office\s*space', 'commercial', 'office'),
    (r'retail|shopping\s*center|strip\s*mall|strip\s*center', 'commercial', 'retail'),
    (r'restaurant|food\s*service', 'commercial', 'restaurant'),
    (r'hotel|motel|hospitality', 'commercial', 'hospitality'),
    (r'warehouse|distribution|industrial', 'industrial', 'warehouse'),
    (r'manufacturing|plant|factory', 'industrial', 'manufacturing'),
    (r'ranch|agricultural|farm\b|grazing|irrigated', 'agricultural', 'ranch'),
    (r'church|school|hospital|government', 'special-purpose', 'institutional'),
    (r'mixed.?use', 'mixed-use', 'mixed-use'),
    (r'\bcommercial\b', 'commercial', 'general'),
    (r'\bresidential\b', 'residential', 'general'),
]

PROPERTY_TYPE_COMPILED = [
    (re.compile(pattern, re.IGNORECASE), ptype, subtype)
    for pattern, ptype, subtype in PROPERTY_TYPE_RULES
]

PURPOSE_RULES = [
    (r'litigation|lawsuit|court', 'litigation'),
    (r'estate|trust|probate|death|decedent', 'estate'),
    (r'lending|mortgage|loan|financing', 'lending'),
    (r'condemnation|eminent\s*domain|acquisition|CDOT|partial\s*taking', 'condemnation'),
    (r'tax\s*(?:appeal)?|property\s*tax', 'tax-appeal'),
    (r'insurance|replacement\s*cost', 'insurance'),
    (r'partnership|dissolution|buyout', 'partnership'),
    (r'relocation|advisory', 'advisory'),
]

PURPOSE_COMPILED = [
    (re.compile(pattern, re.IGNORECASE), purpose)
    for pattern, purpose in PURPOSE_RULES
]


# ── Extraction functions ─────────────────────────────────────────────────────

def extract_job_number(text, filename):
    """Extract job/file number from text or filename."""
    # Try text patterns first (first 50 lines)
    head = '\n'.join(text.split('\n')[:50])
    for pat in RE_JOB_NUMBER:
        m = pat.search(head)
        if m:
            return m.group(1)
    # Fallback to filename
    m = RE_JOB_FROM_FILENAME.search(filename)
    return m.group(1) if m else ''


def extract_address(text):
    """Extract property address from text."""
    head = '\n'.join(text.split('\n')[:100])
    for pat in RE_ADDRESS:
        m = pat.search(head)
        if m:
            addr = m.group(1).strip()
            # Clean up markdown formatting
            addr = re.sub(r'\*+', '', addr)
            addr = addr.rstrip('.')
            addr = addr.strip()
            if len(addr) > 5:  # Sanity check
                return addr
    return ''


def parse_date_string(date_str):
    """Try to parse a date string into YYYY-MM-DD format."""
    date_str = date_str.strip().rstrip('.')
    # Remove ordinal suffixes
    date_str = re.sub(r'(\d+)(?:st|nd|rd|th)', r'\1', date_str)

    formats = [
        '%B %d, %Y',     # January 15, 2024
        '%B %d %Y',      # January 15 2024
        '%m/%d/%Y',      # 01/15/2024
        '%m-%d-%Y',      # 01-15-2024
        '%Y-%m-%d',      # 2024-01-15
        '%b %d, %Y',     # Jan 15, 2024
        '%b %d %Y',      # Jan 15 2024
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str[:30], fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    return ''


def extract_effective_date(text):
    """Extract effective/valuation date."""
    for pat in RE_DATE:
        m = pat.search(text)
        if m:
            parsed = parse_date_string(m.group(1))
            if parsed:
                return parsed
    return ''


def extract_value(text):
    """Extract concluded value — look for dollar amounts near value-related phrases."""
    text_lower = text.lower()
    best_value = ''
    best_distance = float('inf')

    for phrase in VALUE_CONTEXT_PHRASES:
        idx = text_lower.find(phrase)
        if idx == -1:
            continue
        # Search within 500 chars of the phrase
        window = text[max(0, idx - 200):idx + 500]
        for m in RE_DOLLAR.finditer(window):
            raw = m.group(1).replace(',', '')
            try:
                val = float(raw)
            except ValueError:
                continue
            # Prefer larger round values (appraisal conclusions)
            distance = abs(m.start() - 200)  # Distance from phrase
            if val >= 10000 and distance < best_distance:
                best_value = f"${m.group(1)}"
                best_distance = distance

    return best_value


def extract_land_area(text):
    """Extract land area in SF and/or acres."""
    sf_match = RE_LAND_SF.search(text)
    ac_match = RE_LAND_AC.search(text)

    parts = []
    if sf_match:
        parts.append(f"{sf_match.group(1)} SF")
    if ac_match:
        parts.append(f"{ac_match.group(1)} ac")
    return ', '.join(parts)


def extract_county(text):
    """Extract county name."""
    for pat in RE_COUNTY:
        for m in pat.finditer(text):
            county = m.group(1).strip()
            if county.lower() in VALID_CO_COUNTIES:
                return county.title()
            # Also check two-word counties
            # Look behind for "El " or "Clear " etc.
    return ''


def extract_client(text):
    """Extract client name from transmittal letter."""
    head = '\n'.join(text.split('\n')[:50])
    for pat in RE_CLIENT:
        m = pat.search(head)
        if m:
            # Some patterns have 2 groups (title + name), some have 1
            if pat.groups == 2 and m.lastindex == 2:
                client = (m.group(1) + ' ' + m.group(2)).strip()
            else:
                client = m.group(m.lastindex).strip()
            client = re.sub(r'\*+', '', client)
            client = client.rstrip(':,.')
            if len(client) > 2:
                return client
    return ''


def extract_appraiser(text):
    """Extract appraiser name from certification section."""
    # Search last 30% of document (certification is near the end)
    tail_start = int(len(text) * 0.7)
    tail = text[tail_start:]
    m = RE_APPRAISER.search(tail)
    if m:
        name = m.group(1).strip().rstrip(',')
        # Cleanup: remove leading line artifacts
        name = re.sub(r'^[\s\n]+', '', name)
        lines = name.split('\n')
        name = lines[-1].strip()  # Take last line if multi-line match
        if len(name) > 2 and len(name) < 60:
            return name
    return ''


def classify_property_type(text):
    """Classify property type and subtype from text keywords."""
    for pat, ptype, subtype in PROPERTY_TYPE_COMPILED:
        if pat.search(text):
            return ptype, subtype
    return 'unknown', ''


def classify_purpose(text):
    """Classify appraisal purpose from text keywords."""
    # Try explicit purpose lines first
    for pat in RE_PURPOSE:
        m = pat.search(text)
        if m:
            purpose_text = m.group(1).lower()
            for rule_pat, purpose in PURPOSE_COMPILED:
                if rule_pat.search(purpose_text):
                    return purpose

    # Fall back to full-text keyword scan
    for rule_pat, purpose in PURPOSE_COMPILED:
        if rule_pat.search(text):
            return purpose

    return 'general'


def extract_approaches(text):
    """Find which valuation approaches are used."""
    found = set()
    for pat, name in RE_APPROACHES:
        if pat.search(text):
            found.add(name)
    return ', '.join(sorted(found)) if found else ''


def extract_metadata(text, filename):
    """Extract all metadata fields from a markdown appraisal file."""
    ptype, subtype = classify_property_type(text)
    return {
        'job_number': extract_job_number(text, filename),
        'property_address': extract_address(text),
        'property_type': ptype,
        'property_subtype': subtype,
        'client': extract_client(text),
        'effective_date': extract_effective_date(text),
        'concluded_value': extract_value(text),
        'land_area': extract_land_area(text),
        'county': extract_county(text),
        'state': 'CO',
        'appraiser': extract_appraiser(text),
        'purpose': classify_purpose(text),
        'approaches_used': extract_approaches(text),
        'file_path': '',  # Set by caller
    }


# ── Index building ───────────────────────────────────────────────────────────

def build_index(md_path, output_path=None):
    """Scan all .md files and build INDEX.md + INDEX.json."""
    md_path = Path(md_path)

    if output_path:
        index_md_path = Path(output_path)
    else:
        index_md_path = md_path / 'INDEX.md'
    index_json_path = index_md_path.with_suffix('.json')

    if not md_path.is_dir():
        print(f"ERROR: Markdown path does not exist: {md_path}", file=sys.stderr)
        sys.exit(1)

    entries = []
    total = 0
    errors = 0

    # Walk all .md files
    for root, dirs, files in sorted(os.walk(md_path)):
        for filename in sorted(files):
            if not filename.endswith('.md'):
                continue
            if filename in ('INDEX.md', 'README.md'):
                continue

            filepath = os.path.join(root, filename)
            rel_path = os.path.relpath(filepath, md_path)
            total += 1

            try:
                text = Path(filepath).read_text(encoding='utf-8', errors='replace')
            except Exception as e:
                print(f"  WARN: Could not read {rel_path}: {e}", file=sys.stderr)
                errors += 1
                continue

            meta = extract_metadata(text, filename)
            meta['file_path'] = rel_path
            entries.append(meta)

            if total % 100 == 0:
                print(f"  Processed {total} files...")

    print(f"Processed {total} files total ({errors} errors).")

    # Sort by job number (newest first)
    entries.sort(key=lambda e: e.get('job_number', ''), reverse=True)

    # Write INDEX.json
    with open(index_json_path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    print(f"Wrote {index_json_path} ({len(entries)} entries)")

    # Write INDEX.md
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    lines = [
        '# Appraisal Archive Index',
        f'Generated: {now}',
        f'Total files: {len(entries)}',
        '',
        '| Job # | Address | Type | Subtype | County | Date | Value | Client | File |',
        '|-------|---------|------|---------|--------|------|-------|--------|------|',
    ]
    for e in entries:
        row = '| {} | {} | {} | {} | {} | {} | {} | {} | {} |'.format(
            e.get('job_number', ''),
            e.get('property_address', '')[:50],
            e.get('property_type', ''),
            e.get('property_subtype', ''),
            e.get('county', ''),
            e.get('effective_date', ''),
            e.get('concluded_value', ''),
            e.get('client', '')[:30],
            e.get('file_path', ''),
        )
        lines.append(row)

    with open(index_md_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f"Wrote {index_md_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Build a searchable index from converted appraisal markdown files.'
    )
    parser.add_argument(
        '--md-path', required=True,
        help='Root directory of converted .md files'
    )
    parser.add_argument(
        '--output', default=None,
        help='Output path for INDEX.md (default: <md-path>/INDEX.md)'
    )

    args = parser.parse_args()
    build_index(args.md_path, args.output)


if __name__ == '__main__':
    main()

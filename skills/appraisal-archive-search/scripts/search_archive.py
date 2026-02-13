#!/usr/bin/env python3
"""
search_archive.py — Search the appraisal archive index by filters and keywords.

Reads INDEX.json and returns matching appraisals ranked by relevance.

Zero pip dependencies — stdlib only.

Usage:
    python3 search_archive.py --index /path/to/INDEX.json --type commercial
    python3 search_archive.py --index /path/to/INDEX.json --county Jefferson --date-from 2022-01-01
    python3 search_archive.py --index /path/to/INDEX.json --keyword "conservation easement" --limit 5
    python3 search_archive.py --index /path/to/INDEX.json --type land --value-min 500000 --value-max 5000000
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


def parse_value_string(val_str):
    """Parse a dollar string like '$1,500,000' into a float."""
    if not val_str:
        return None
    cleaned = re.sub(r'[^\d.]', '', val_str)
    try:
        return float(cleaned)
    except ValueError:
        return None


def matches_filter(entry, args):
    """Check if an entry matches all specified filters. Returns True/False."""
    # Property type
    if args.type:
        if entry.get('property_type', '').lower() != args.type.lower():
            return False

    # Property subtype
    if args.subtype:
        if entry.get('property_subtype', '').lower() != args.subtype.lower():
            return False

    # County
    if args.county:
        if args.county.lower() not in entry.get('county', '').lower():
            return False

    # Purpose
    if args.purpose:
        if args.purpose.lower() not in entry.get('purpose', '').lower():
            return False

    # Date range
    eff_date = entry.get('effective_date', '')
    if args.date_from and eff_date:
        if eff_date < args.date_from:
            return False
    if args.date_to and eff_date:
        if eff_date > args.date_to:
            return False

    # Value range
    val = parse_value_string(entry.get('concluded_value', ''))
    if args.value_min is not None:
        if val is None or val < args.value_min:
            return False
    if args.value_max is not None:
        if val is None or val > args.value_max:
            return False

    return True


def keyword_search(entry, keyword, md_base_path):
    """Check if keyword appears in the entry metadata or the full .md content.
    Returns a relevance score (0 = no match, higher = better)."""
    kw = keyword.lower()
    score = 0

    # Check metadata fields
    for field in ['property_address', 'client', 'property_type', 'property_subtype',
                  'county', 'purpose', 'appraiser', 'job_number']:
        if kw in entry.get(field, '').lower():
            score += 2

    # Check full .md content if path available
    if md_base_path and entry.get('file_path'):
        md_file = os.path.join(md_base_path, entry['file_path'])
        try:
            text = Path(md_file).read_text(encoding='utf-8', errors='replace').lower()
            count = text.count(kw)
            if count > 0:
                score += min(count, 10)  # Cap at 10 to avoid one file dominating
        except (OSError, IOError):
            pass

    return score


def search_archive(index_path, args):
    """Search the index and return matching entries."""
    index_path = Path(index_path)

    if not index_path.exists():
        print(f"ERROR: Index file not found: {index_path}", file=sys.stderr)
        sys.exit(1)

    with open(index_path, 'r', encoding='utf-8') as f:
        entries = json.load(f)

    # Determine md base path for keyword search
    md_base_path = str(index_path.parent)

    # Filter
    results = []
    for entry in entries:
        if not matches_filter(entry, args):
            continue

        # Keyword search (if specified)
        if args.keyword:
            score = keyword_search(entry, args.keyword, md_base_path)
            if score == 0:
                continue
            entry = dict(entry)  # Copy to avoid mutating original
            entry['_relevance'] = score
        else:
            entry = dict(entry)
            entry['_relevance'] = 0

        results.append(entry)

    # Sort: by relevance (desc) then by date (desc)
    results.sort(key=lambda e: (e.get('_relevance', 0), e.get('effective_date', '')), reverse=True)

    # Limit
    limit = args.limit or 10
    results = results[:limit]

    return results


def format_results(results):
    """Format results as a markdown table for stdout."""
    if not results:
        return "No matching appraisals found."

    lines = [
        f"**Found {len(results)} matching appraisal(s):**",
        '',
        '| # | Job # | Address | Type | County | Date | Value | Client | File |',
        '|---|-------|---------|------|--------|------|-------|--------|------|',
    ]
    for i, e in enumerate(results, 1):
        row = '| {} | {} | {} | {} | {} | {} | {} | {} | {} |'.format(
            i,
            e.get('job_number', ''),
            e.get('property_address', '')[:45],
            e.get('property_type', ''),
            e.get('county', ''),
            e.get('effective_date', ''),
            e.get('concluded_value', ''),
            e.get('client', '')[:25],
            e.get('file_path', ''),
        )
        lines.append(row)

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Search the appraisal archive index.'
    )
    parser.add_argument(
        '--index', required=True,
        help='Path to INDEX.json file'
    )
    parser.add_argument('--type', default=None, help='Property type filter (e.g., commercial, residential, land)')
    parser.add_argument('--subtype', default=None, help='Property subtype filter (e.g., office, sfr, ranch)')
    parser.add_argument('--county', default=None, help='County filter')
    parser.add_argument('--date-from', default=None, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--date-to', default=None, help='End date (YYYY-MM-DD)')
    parser.add_argument('--value-min', type=float, default=None, help='Minimum concluded value')
    parser.add_argument('--value-max', type=float, default=None, help='Maximum concluded value')
    parser.add_argument('--keyword', default=None, help='Full-text keyword search')
    parser.add_argument('--purpose', default=None, help='Purpose filter (e.g., condemnation, estate, lending)')
    parser.add_argument('--limit', type=int, default=10, help='Max results (default 10)')

    args = parser.parse_args()
    results = search_archive(args.index, args)
    print(format_results(results))


if __name__ == '__main__':
    main()

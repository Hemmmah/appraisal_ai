#!/usr/bin/env python3
"""
scan_archive.py — Walk an archive directory tree, find .docx files, convert to markdown.

Uses `npx mammoth` for conversion (zero pip dependencies).

Usage:
    python3 scan_archive.py --archive-path /path/to/archives --output-path /path/to/md-output
    python3 scan_archive.py --archive-path /path/to/archives --output-path /path/to/md-output --years 2020-2024
    python3 scan_archive.py --archive-path /path/to/archives --output-path /path/to/md-output --force
"""

import argparse
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path


def slugify(text):
    """Convert a string to a filesystem-safe slug."""
    # Normalize unicode
    text = unicodedata.normalize('NFKD', text)
    # Replace common separators with hyphens
    text = re.sub(r'[\s_/\\]+', '-', text)
    # Remove non-alphanumeric chars (keep hyphens and periods)
    text = re.sub(r'[^\w\-.]', '', text)
    # Collapse multiple hyphens
    text = re.sub(r'-{2,}', '-', text)
    # Strip leading/trailing hyphens
    text = text.strip('-')
    return text.lower()


def parse_year_filter(years_str):
    """Parse a year filter string like '2020-2024' or '2020,2022,2024' into a set of ints."""
    if not years_str:
        return None
    years = set()
    for part in years_str.split(','):
        part = part.strip()
        if '-' in part:
            start, end = part.split('-', 1)
            for y in range(int(start.strip()), int(end.strip()) + 1):
                years.add(y)
        else:
            years.add(int(part))
    return years


def extract_year_from_folder(folder_name):
    """Try to extract a 4-digit year from a folder name like '2024 FILES'."""
    match = re.search(r'((?:19|20)\d{2})', folder_name)
    return int(match.group(1)) if match else None


def find_docx_files(job_dir):
    """Find .docx files in a job directory, prioritizing NARRATIVE subfolder."""
    docx_files = []

    # Check NARRATIVE subfolder first (case-insensitive)
    for item in sorted(os.listdir(job_dir)):
        item_path = os.path.join(job_dir, item)
        if os.path.isdir(item_path) and item.upper() in ('NARRATIVE', 'NARRATIVES'):
            for f in sorted(os.listdir(item_path)):
                if f.lower().endswith('.docx') and not f.startswith('~$'):
                    docx_files.append(os.path.join(item_path, f))

    # If no NARRATIVE folder or it's empty, check job root
    if not docx_files:
        for f in sorted(os.listdir(job_dir)):
            fp = os.path.join(job_dir, f)
            if os.path.isfile(fp) and f.lower().endswith('.docx') and not f.startswith('~$'):
                docx_files.append(fp)

    return docx_files


def convert_docx_to_md(docx_path):
    """Convert a .docx file to markdown using npx mammoth. Returns markdown text or None."""
    try:
        result = subprocess.run(
            ['npx', 'mammoth', str(docx_path), '--output-format=markdown'],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            return result.stdout
        else:
            # mammoth writes conversion output to stdout, warnings to stderr
            # Some warnings are normal — only fail if no output at all
            if result.stdout.strip():
                return result.stdout
            print(f"  WARN: mammoth failed for {docx_path}: {result.stderr[:200]}", file=sys.stderr)
            return None
    except subprocess.TimeoutExpired:
        print(f"  WARN: mammoth timed out for {docx_path}", file=sys.stderr)
        return None
    except FileNotFoundError:
        print("ERROR: 'npx' not found. Install Node.js to use mammoth.", file=sys.stderr)
        sys.exit(1)


def scan_archive(archive_path, output_path, year_filter=None, force=False, include_xlsx=False):
    """Main scan function. Walk archive, convert docx, write md files."""
    archive_path = Path(archive_path)
    output_path = Path(output_path)

    if not archive_path.is_dir():
        print(f"ERROR: Archive path does not exist: {archive_path}", file=sys.stderr)
        sys.exit(1)

    output_path.mkdir(parents=True, exist_ok=True)

    total_converted = 0
    total_failures = 0
    total_skipped = 0

    # Walk top-level year folders
    year_folders = []
    for item in sorted(os.listdir(archive_path)):
        item_path = archive_path / item
        if not item_path.is_dir():
            continue
        year = extract_year_from_folder(item)
        if year is None:
            continue
        if year_filter and year not in year_filter:
            continue
        year_folders.append((year, item, item_path))

    if not year_folders:
        print("No year folders found matching the filter.", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(year_folders)} year folder(s) to process.")

    for year, folder_name, year_path in year_folders:
        year_output = output_path / str(year)
        year_output.mkdir(parents=True, exist_ok=True)

        year_count = 0
        year_failures = 0

        # Walk job folders inside the year
        try:
            job_entries = sorted(os.listdir(year_path))
        except PermissionError:
            print(f"  WARN: Permission denied: {year_path}", file=sys.stderr)
            continue

        for job_name in job_entries:
            job_path = year_path / job_name
            if not job_path.is_dir():
                continue

            slug = slugify(job_name)
            if not slug:
                continue

            md_output_file = year_output / f"{slug}.md"

            # Skip if already converted (unless --force)
            if md_output_file.exists() and not force:
                total_skipped += 1
                continue

            # Find docx files
            try:
                docx_files = find_docx_files(str(job_path))
            except PermissionError:
                print(f"  WARN: Permission denied: {job_path}", file=sys.stderr)
                year_failures += 1
                continue

            if not docx_files:
                continue

            # Convert each docx and combine
            combined_md = []
            job_failed = False

            for docx_path in docx_files:
                docx_name = os.path.basename(docx_path)
                md_text = convert_docx_to_md(docx_path)
                if md_text is None:
                    job_failed = True
                    continue

                if len(docx_files) > 1:
                    combined_md.append(f"## Source: {docx_name}\n\n{md_text}")
                else:
                    combined_md.append(md_text)

            if combined_md:
                header = f"# {job_name}\n\n"
                header += f"**Source folder:** {job_path}\n\n---\n\n"
                full_md = header + '\n\n---\n\n'.join(combined_md)

                md_output_file.write_text(full_md, encoding='utf-8')
                year_count += 1
                total_converted += 1
                print(f"  [{year}] {slug}.md ({len(docx_files)} docx)")
            elif job_failed:
                year_failures += 1
                total_failures += 1

        print(f"YEAR_DONE:{year}:{year_count}:{year_failures}")

    print(f"ALL_DONE:{total_converted}:{total_failures}:{total_skipped}")


def main():
    parser = argparse.ArgumentParser(
        description='Scan appraisal archive directories and convert .docx files to markdown.'
    )
    parser.add_argument(
        '--archive-path', required=True,
        help='Root archive directory (e.g., /path/to/Archives)'
    )
    parser.add_argument(
        '--output-path', required=True,
        help='Where to write converted .md files'
    )
    parser.add_argument(
        '--years', default=None,
        help='Year filter: comma-separated or range (e.g., "2020-2024" or "2020,2022")'
    )
    parser.add_argument(
        '--force', action='store_true',
        help='Re-convert even if .md already exists'
    )
    parser.add_argument(
        '--include-xlsx', action='store_true',
        help='Also convert .xlsx grid files (not implemented yet)'
    )

    args = parser.parse_args()
    year_filter = parse_year_filter(args.years)

    scan_archive(
        archive_path=args.archive_path,
        output_path=args.output_path,
        year_filter=year_filter,
        force=args.force,
        include_xlsx=args.include_xlsx,
    )


if __name__ == '__main__':
    main()

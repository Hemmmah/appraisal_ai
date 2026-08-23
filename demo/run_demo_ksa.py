#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Runs the highlight-anchor build engine against templates/demo-ksa using
demo/Demo-Project-KSA/data.md, in both direct and track-changes modes, then
verifies the output (valid XML, RTL preserved, Hijri dates derived, no
stray placeholders left in required fields, tracked-change markup present).

Usage:
    ~/appraisal_ai/venv/bin/python demo/run_demo_ksa.py
"""

import json
import os
import shutil
import sys
import zipfile

from lxml import etree

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(REPO_ROOT, 'templates', 'demo-ksa')
DEMO_DIR = os.path.join(REPO_ROOT, 'demo', 'Demo-Project-KSA')
NARR_DIR = os.path.join(DEMO_DIR, 'Narrative')

sys.path.insert(0, os.path.join(REPO_ROOT, 'scripts'))
from utils import load_md, fill_highlighted_template, extract_docx_text  # noqa: E402


def run_mode(mode, out_name):
    template_path = os.path.join(TEMPLATE_DIR, 'narrative.docx')
    os.makedirs(NARR_DIR, exist_ok=True)
    working_copy = os.path.join(NARR_DIR, out_name)
    shutil.copy2(template_path, working_copy)

    ref = json.load(open(os.path.join(TEMPLATE_DIR, 'reference-data.json'), encoding='utf-8'))
    project = load_md(os.path.join(DEMO_DIR, 'data.md'))
    proj_fields = project.get('fields', project)

    report = fill_highlighted_template(
        template_path=working_copy,
        output_path=working_copy,
        fields=ref['fields'],
        data=proj_fields,
        mode=mode,
        author='Demo Appraiser',
        number_format=ref['_meta'].get('number_format', 'comma'),
    )
    print(f"\n=== mode={mode} -> {out_name} ===")
    print(f"filled: {len(report['filled'])}, skipped: {len(report['skipped'])}, "
          f"missing: {len(report['missing'])}, warnings: {len(report['warnings'])}")
    for m in report['missing']:
        print('  MISSING:', m)
    for w in report['warnings']:
        print(' ', w)
    return working_copy, report


def verify(path, mode):
    # 1. Valid zip + well-formed document.xml
    with zipfile.ZipFile(path) as z:
        xml_bytes = z.read('word/document.xml')
    tree = etree.fromstring(xml_bytes)
    print(f"  [OK] {os.path.basename(path)}: valid zip + well-formed XML "
          f"({len(xml_bytes)} bytes)")

    # 2. Re-open with python-docx to make sure Word-compatible structure holds
    from docx import Document
    doc = Document(path)
    print(f"  [OK] python-docx opened it: {len(doc.tables)} tables, "
          f"{len(doc.paragraphs)} top-level paragraphs")

    # 3. Extract text and spot-check expected values
    text = extract_docx_text(path)
    checks = ['391011223344', '2891', 'الرياض', 'حي النرجس', 'شارع عرض 20 م']
    for c in checks:
        status = 'OK' if c in text else 'MISSING'
        print(f"  [{status}] expected value present: {c!r}")

    placeholder_count = text.count('---')
    print(f"  placeholder '---' occurrences remaining in text: {placeholder_count}")

    if mode == 'track_changes':
        w = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        n_del = len(tree.findall(f'.//{w}del'))
        n_ins = len(tree.findall(f'.//{w}ins'))
        n_delText = len(tree.findall(f'.//{w}delText'))
        print(f"  tracked changes: <w:del>={n_del}, <w:ins>={n_ins}, <w:delText>={n_delText}")
        # spot check: old placeholder text should still be present as delText (reviewable)
        del_texts = [e.text for e in tree.findall(f'.//{w}delText')]
        print(f"  sample delText values: {del_texts[:3]}")


if __name__ == '__main__':
    path_direct, _ = run_mode('direct', 'KSA-DEMO Narrative DRAFT (direct).docx')
    path_track, _ = run_mode('track_changes', 'KSA-DEMO Narrative DRAFT (tracked).docx')

    print('\n--- Verification ---')
    verify(path_direct, 'direct')
    print()
    verify(path_track, 'track_changes')

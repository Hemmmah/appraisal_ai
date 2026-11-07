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


def verify(path, mode, ref_fields, proj_fields, derived_or_defaulted):
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

    # Optional empty fields (e.g. built_area on a land-only demo) leave their
    # yellow "---" placeholders in place by design — count only unexpected leftovers.
    optional_empty = 0
    for key, spec in ref_fields.items():
        if not spec.get('optional'):
            continue
        val = proj_fields.get(key)
        if val in (None, ''):
            optional_empty += len(spec.get('anchors', []))
    placeholder_count = text.count('---')
    unexpected = placeholder_count - optional_empty
    print(f"  placeholder '---' remaining: {placeholder_count} "
          f"(optional-empty expected: {optional_empty}, unexpected: {unexpected})")
    if unexpected > 0:
        print(f"  [WARN] {unexpected} unexpected placeholder(s) still in the draft")
    else:
        print("  [OK] no unexpected placeholders (optional empty fields may keep ---)")

    # 4. RTL / bidi structure must survive fill (Word visual check still recommended)
    w = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    n_bidi = len(tree.findall(f'.//{w}bidi'))
    n_rtl = len(tree.findall(f'.//{w}rtl'))
    n_bidi_visual = len(tree.findall(f'.//{w}bidiVisual'))
    print(f"  RTL markup: <w:bidi>={n_bidi}, <w:rtl>={n_rtl}, <w:bidiVisual>={n_bidi_visual}")
    if n_bidi > 0 and n_rtl > 0:
        print("  [OK] RTL paragraph + run direction markers present after fill")
    else:
        print("  [WARN] RTL markers missing or stripped — open in Word and check direction")

    # 5. Hijri Arabic-Indic month names should appear for date_h fields
    hijri_markers = ['هـ', 'رجب', 'محرم', 'صفر', 'رمضان', 'شوال']
    found_hijri = [m for m in hijri_markers if m in text]
    if found_hijri:
        print(f"  [OK] Hijri Arabic rendering present: {found_hijri}")
    else:
        print("  [WARN] no Arabic Hijri markers found in draft text")

    # 6. Filled insertion runs should not retain yellow highlight
    #    (placeholders that stay empty/optional may still be yellow)
    yellow_on_ins = 0
    for ins in tree.findall(f'.//{w}ins'):
        for hl in ins.findall(f'.//{w}highlight'):
            if hl.get(f'{w}val') == 'yellow':
                yellow_on_ins += 1
    print(f"  yellow highlight remaining on <w:ins> runs: {yellow_on_ins}")
    if yellow_on_ins == 0:
        print("  [OK] no yellow highlight left on inserted (new) text")
    else:
        print("  [WARN] yellow highlight still on some insertions")

    if mode == 'track_changes':
        n_del = len(tree.findall(f'.//{w}del'))
        n_ins = len(tree.findall(f'.//{w}ins'))
        n_delText = len(tree.findall(f'.//{w}delText'))
        print(f"  tracked changes: <w:del>={n_del}, <w:ins>={n_ins}, <w:delText>={n_delText}")
        # spot check: old placeholder text should still be present as delText (reviewable)
        del_texts = [e.text for e in tree.findall(f'.//{w}delText')]
        print(f"  sample delText values: {del_texts[:3]}")
        expected_fills = sum(
            len(spec.get('anchors', []))
            for key, spec in ref_fields.items()
            if proj_fields.get(key) not in (None, '') or key in derived_or_defaulted
        )
        if n_del == n_ins == expected_fills:
            print(f"  [OK] tracked-change count matches filled anchors ({expected_fills})")
        else:
            print(f"  [WARN] tracked-change count {n_del}/{n_ins} vs expected fills {expected_fills}")

        # settings.xml must enable Track Changes so Word shows Review UI
        with zipfile.ZipFile(path) as z:
            settings = etree.fromstring(z.read('word/settings.xml'))
        if settings.find(f'{w}trackRevisions') is not None:
            print("  [OK] word/settings.xml has <w:trackRevisions/>")
        else:
            print("  [WARN] <w:trackRevisions/> missing from settings.xml")


if __name__ == '__main__':
    ref = json.load(open(os.path.join(TEMPLATE_DIR, 'reference-data.json'), encoding='utf-8'))
    project = load_md(os.path.join(DEMO_DIR, 'data.md'))
    proj_fields = project.get('fields', project)
    ref_fields = ref['fields']

    # Keys that resolve without an explicit data.md value (defaults / Hijri derive).
    from utils import resolve_anchor_values
    _warnings = []
    resolved = resolve_anchor_values(ref_fields, proj_fields, _warnings)
    derived_or_defaulted = {k for k in resolved if proj_fields.get(k) in (None, '')}

    path_direct, _ = run_mode('direct', 'KSA-DEMO Narrative DRAFT (direct).docx')
    path_track, _ = run_mode('track_changes', 'KSA-DEMO Narrative DRAFT (tracked).docx')

    print('\n--- Verification ---')
    verify(path_direct, 'direct', ref_fields, proj_fields, derived_or_defaulted)
    print()
    verify(path_track, 'track_changes', ref_fields, proj_fields, derived_or_defaulted)

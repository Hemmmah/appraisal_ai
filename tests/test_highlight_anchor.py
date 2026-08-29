#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for highlight-anchor helpers in scripts/utils.py."""

import os
import sys
import tempfile
import unittest
import zipfile

from lxml import etree

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, 'scripts'))

from utils import (  # noqa: E402
    cell_at,
    fill_highlighted_template,
    format_hijri_arabic,
    fmt_number,
    gregorian_to_hijri,
    highlighted_runs,
    load_tables_dfs,
    resolve_anchor_values,
)

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def _make_docx_with_highlighted_cell(path, placeholder='---'):
    """Minimal docx: one 1x1 table cell with a yellow-highlighted run."""
    from docx import Document
    from docx.enum.text import WD_COLOR_INDEX

    doc = Document()
    table = doc.add_table(rows=1, cols=1)
    cell = table.cell(0, 0)
    cell.text = ''
    p = cell.paragraphs[0]
    run = p.add_run(placeholder)
    run.font.highlight_color = WD_COLOR_INDEX.YELLOW
    doc.save(path)


class HighlightHelpersTest(unittest.TestCase):
    def test_fmt_number(self):
        self.assertEqual(fmt_number(612.5, 'comma'), '612.50')
        self.assertEqual(fmt_number(1000, 'comma'), '1,000')
        self.assertEqual(fmt_number(1000, 'plain'), '1000')
        self.assertEqual(fmt_number(12.345, 'comma2'), '12.35')

    def test_gregorian_to_hijri(self):
        # Cross-checked against hijridate / Umm al-Qura for 2026-01-15
        self.assertEqual(gregorian_to_hijri('2026-01-15'), '1447-07-26')
        self.assertIsNone(gregorian_to_hijri('not-a-date'))

    def test_format_hijri_arabic(self):
        out = format_hijri_arabic('1447-07-26')
        self.assertIn('رجب', out)
        self.assertIn('هـ', out)
        # Arabic-Indic digits
        self.assertTrue(any('\u0660' <= ch <= '\u0669' for ch in out))

    def test_resolve_anchor_values_chain(self):
        fields = {
            'valuation_date_g': {'label': 'vg', 'type': 'date_g'},
            'issue_date_g': {
                'label': 'ig', 'type': 'date_g',
                'default_from': 'valuation_date_g',
            },
            'issue_date_h': {
                'label': 'ih', 'type': 'date_h',
                'derive_hijri_from': 'issue_date_g',
            },
        }
        data = {'valuation_date_g': '2026-01-15'}
        warnings = []
        vals = resolve_anchor_values(fields, data, warnings)
        self.assertEqual(vals['issue_date_g'], '2026-01-15')
        self.assertEqual(vals['issue_date_h'], '1447-07-26')
        self.assertTrue(any('issue_date_h' in w for w in warnings))

    def test_resolve_derived_formula(self):
        fields = {
            'district': {'label': 'd', 'type': 'text'},
            'parcel_number': {'label': 'p', 'type': 'text'},
            'location_composite': {
                'label': 'loc', 'type': 'derived',
                'formula': 'حي: {district} – قطعة رقم: {parcel_number}',
            },
        }
        data = {'district': 'النرجس', 'parcel_number': '114'}
        vals = resolve_anchor_values(fields, data, [])
        self.assertEqual(vals['location_composite'], 'حي: النرجس – قطعة رقم: 114')

    def test_load_tables_and_highlight_fill_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, 'src.docx')
            out = os.path.join(tmp, 'out.docx')
            _make_docx_with_highlighted_cell(src)

            fields = {
                'deed_number': {
                    'label': 'رقم الصك',
                    'type': 'text',
                    'anchors': [{'t': 1, 'r': 1, 'c': 1}],
                },
            }
            report = fill_highlighted_template(
                src, out, fields, {'deed_number': '391011223344'},
                mode='direct',
            )
            self.assertEqual(len(report['filled']), 1)
            self.assertEqual(report['missing'], [])
            self.assertEqual(report['skipped'], [])

            with zipfile.ZipFile(out) as z:
                root = etree.fromstring(z.read('word/document.xml'))
            body = root.find(f'{W}body')
            tables = load_tables_dfs(body)
            self.assertEqual(len(tables), 1)
            cell = cell_at(tables, 1, 1, 1)
            txt = ''.join(t.text or '' for t in cell.iter(f'{W}t'))
            self.assertEqual(txt, '391011223344')
            # Highlight stripped in direct mode
            self.assertEqual(highlighted_runs(cell), [])

    def test_tracked_replace_produces_del_and_ins(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, 'src.docx')
            out = os.path.join(tmp, 'out.docx')
            _make_docx_with_highlighted_cell(src)

            fields = {
                'city': {
                    'label': 'المدينة',
                    'type': 'text',
                    'anchors': [{'t': 1, 'r': 1, 'c': 1}],
                },
            }
            report = fill_highlighted_template(
                src, out, fields, {'city': 'الرياض'},
                mode='track_changes',
            )
            self.assertEqual(len(report['filled']), 1)

            with zipfile.ZipFile(out) as z:
                root = etree.fromstring(z.read('word/document.xml'))
            self.assertEqual(len(root.findall(f'.//{W}del')), 1)
            self.assertEqual(len(root.findall(f'.//{W}ins')), 1)
            del_text = root.find(f'.//{W}delText').text
            ins_text = root.find(f'.//{W}ins//{W}t').text
            self.assertEqual(del_text, '---')
            self.assertEqual(ins_text, 'الرياض')


if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KSA Demo Template Setup Script (highlight-anchor pack)

Generates a complete Arabic/RTL demo pack for testing the highlight-anchor
build path (see .claude/skills/draft-highlight.md):
  - templates/demo-ksa/narrative.docx  — RTL Word template with yellow-
    highlighted table cells at fixed (table, row, cell) anchors
  - templates/demo-ksa/reference-data.json — field map (label, type,
    anchors, defaults, Hijri derivation) consumed by
    utils.fill_highlighted_template()
  - demo/Demo-Project-KSA/data.md — fictional project data (no real
    property, owner, or deed information)

Usage:
    ~/appraisal_ai/venv/bin/python demo/setup_demo_ksa.py

After running, test the highlight-anchor engine with:
    ~/appraisal_ai/venv/bin/python demo/run_demo_ksa.py
"""

import json
import os
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml.ns import qn
from docx.shared import Pt

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(REPO_ROOT, 'templates', 'demo-ksa')
DEMO_DIR = os.path.join(REPO_ROOT, 'demo', 'Demo-Project-KSA')

sys.path.insert(0, os.path.join(REPO_ROOT, 'scripts'))
from utils import save_md  # noqa: E402

FONT = 'Arial'
PLACEHOLDER = '---'  # highlighted placeholder text sitting at every anchor


# ── RTL helpers ───────────────────────────────────────────────────────────

def set_rtl_paragraph(paragraph, align=WD_ALIGN_PARAGRAPH.RIGHT):
    paragraph.alignment = align
    pPr = paragraph._p.get_or_add_pPr()
    bidi = pPr.makeelement(qn('w:bidi'), {})
    pPr.append(bidi)


def style_run(run, size=11, bold=False, highlight=False):
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = rPr.makeelement(qn('w:rFonts'), {})
        rPr.append(rFonts)
    rFonts.set(qn('w:ascii'), FONT)
    rFonts.set(qn('w:hAnsi'), FONT)
    rFonts.set(qn('w:cs'), FONT)
    # Mark complex-script / RTL so Word keeps Arabic shaping after fill
    if rPr.find(qn('w:rtl')) is None:
        rPr.append(rPr.makeelement(qn('w:rtl'), {}))
    if rPr.find(qn('w:cs')) is None:
        rPr.append(rPr.makeelement(qn('w:cs'), {}))
    lang = rPr.find(qn('w:lang'))
    if lang is None:
        lang = rPr.makeelement(qn('w:lang'), {
            qn('w:val'): 'ar-SA',
            qn('w:bidi'): 'ar-SA',
        })
        rPr.append(lang)
    else:
        lang.set(qn('w:val'), 'ar-SA')
        lang.set(qn('w:bidi'), 'ar-SA')
    if highlight:
        run.font.highlight_color = WD_COLOR_INDEX.YELLOW
    return run


def add_rtl_heading(doc, text, size=14):
    p = doc.add_paragraph()
    set_rtl_paragraph(p, WD_ALIGN_PARAGRAPH.CENTER)
    style_run(p.add_run(text), size=size, bold=True)
    return p


def add_rtl_table(doc, rows, cols):
    tbl = doc.add_table(rows=rows, cols=cols)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.style = 'Table Grid'
    tblPr = tbl._tbl.tblPr
    bidi_visual = tblPr.makeelement(qn('w:bidiVisual'), {})
    tblPr.append(bidi_visual)
    return tbl


def fill_cell(cell, text, bold=False, highlight=False, size=11):
    cell.text = ''
    p = cell.paragraphs[0]
    set_rtl_paragraph(p)
    style_run(p.add_run(text), size=size, bold=bold, highlight=highlight)


# ── Build narrative.docx ─────────────────────────────────────────────────

def build_template():
    doc = Document()

    sectPr = doc.sections[0]._sectPr
    bidi = sectPr.makeelement(qn('w:bidi'), {})
    sectPr.append(bidi)

    add_rtl_heading(doc, 'تقرير تقييم عقاري', size=18)
    add_rtl_heading(doc, 'إعداد: شركة التقييم العقاري النموذجية', size=11)
    doc.add_paragraph()

    # Table 1 — بيانات الصك والمخطط
    add_rtl_heading(doc, 'أولاً: بيانات الصك والمخطط', size=13)
    t1 = add_rtl_table(doc, rows=2, cols=6)
    headers = ['رقم الصك', 'تاريخ الصك (هجري)', 'المساحة حسب الصك (م²)',
               'رقم المخطط', 'رقم البلك', 'رقم القطعة']
    for c, h in enumerate(headers):
        fill_cell(t1.rows[0].cells[c], h, bold=True)
    for c in range(6):
        fill_cell(t1.rows[1].cells[c], PLACEHOLDER, highlight=True)
    doc.add_paragraph()

    # Table 2 — العميل والمالك والغرض
    add_rtl_heading(doc, 'ثانياً: بيانات العميل والمالك وغرض التقييم', size=13)
    t2 = add_rtl_table(doc, rows=2, cols=4)
    headers = ['اسم العميل / طالب التقييم', 'اسم المالك', 'الغرض من التقييم', 'نوع مستند الملكية']
    for c, h in enumerate(headers):
        fill_cell(t2.rows[0].cells[c], h, bold=True)
    for c in range(4):
        fill_cell(t2.rows[1].cells[c], PLACEHOLDER, highlight=True)
    doc.add_paragraph()

    # Table 3 — الموقع
    add_rtl_heading(doc, 'ثالثاً: الموقع', size=13)
    t3 = add_rtl_table(doc, rows=2, cols=4)
    headers = ['المدينة', 'الحي', 'خط الطول', 'خط العرض']
    for c, h in enumerate(headers):
        fill_cell(t3.rows[0].cells[c], h, bold=True)
    for c in range(4):
        fill_cell(t3.rows[1].cells[c], PLACEHOLDER, highlight=True)
    doc.add_paragraph()

    # Table 4 — الحدود الأربعة
    add_rtl_heading(doc, 'رابعاً: الحدود الأربعة', size=13)
    t4 = add_rtl_table(doc, rows=5, cols=3)
    fill_cell(t4.rows[0].cells[0], 'الجهة', bold=True)
    fill_cell(t4.rows[0].cells[1], 'الحد المجاور', bold=True)
    fill_cell(t4.rows[0].cells[2], 'الطول (م)', bold=True)
    directions = ['شمالاً', 'جنوباً', 'شرقاً', 'غرباً']
    for i, d in enumerate(directions, start=1):
        fill_cell(t4.rows[i].cells[0], d, bold=True)
        fill_cell(t4.rows[i].cells[1], PLACEHOLDER, highlight=True)
        fill_cell(t4.rows[i].cells[2], PLACEHOLDER, highlight=True)
    doc.add_paragraph()

    # Table 5 — التواريخ (هجري وميلادي)
    add_rtl_heading(doc, 'خامساً: التواريخ', size=13)
    t5 = add_rtl_table(doc, rows=5, cols=3)
    fill_cell(t5.rows[0].cells[0], 'التاريخ', bold=True)
    fill_cell(t5.rows[0].cells[1], 'ميلادي', bold=True)
    fill_cell(t5.rows[0].cells[2], 'هجري', bold=True)
    date_labels = ['تاريخ معاينة الموقع', 'تاريخ التكليف', 'تاريخ قياس القيمة', 'تاريخ إصدار التقرير']
    for i, lbl in enumerate(date_labels, start=1):
        fill_cell(t5.rows[i].cells[0], lbl, bold=True)
        fill_cell(t5.rows[i].cells[1], PLACEHOLDER, highlight=True)
        fill_cell(t5.rows[i].cells[2], PLACEHOLDER, highlight=True)
    doc.add_paragraph()

    # Table 6 — المساحات
    add_rtl_heading(doc, 'سادساً: المساحات', size=13)
    t6 = add_rtl_table(doc, rows=2, cols=4)
    headers = ['المساحة حسب الصك (م²)', 'المساحة حسب الطبيعة (م²)',
               'المساحة المعتمدة في التقييم (م²)', 'مسطحات البناء التقريبية (م²)']
    for c, h in enumerate(headers):
        fill_cell(t6.rows[0].cells[c], h, bold=True)
    for c in range(4):
        fill_cell(t6.rows[1].cells[c], PLACEHOLDER, highlight=True)
    doc.add_paragraph()

    p = doc.add_paragraph()
    set_rtl_paragraph(p, WD_ALIGN_PARAGRAPH.RIGHT)
    style_run(p.add_run(
        'هذا التقرير أُعد وفقاً لمعايير التقييم الدولية (IVS) وأنظمة الهيئة السعودية للمقيّمين المعتمدين (تقييم). '
        'الخلايا المظللة باللون الأصفر أعلاه هي مواضع المرساة التي يعبّئها محرك القالب — انظر '
        'reference-data.json لخريطة الحقول الكاملة.'
    ), size=10)

    os.makedirs(TEMPLATE_DIR, exist_ok=True)
    out_path = os.path.join(TEMPLATE_DIR, 'narrative.docx')
    doc.save(out_path)
    print(f'Wrote {out_path}')


# ── Build reference-data.json (field map) ────────────────────────────────

def build_reference_data():
    fields = {
        'deed_number': {'label': 'رقم الصك', 'type': 'text', 'required': True,
                         'anchors': [{'t': 1, 'r': 2, 'c': 1}]},
        'deed_date_h': {'label': 'تاريخ الصك (هجري)', 'type': 'date_h', 'required': True,
                         'anchors': [{'t': 1, 'r': 2, 'c': 2}]},
        'land_area_deed': {'label': 'المساحة حسب الصك (م2)', 'type': 'number', 'required': True,
                            'anchors': [{'t': 1, 'r': 2, 'c': 3}, {'t': 6, 'r': 2, 'c': 1}]},
        'plan_number': {'label': 'رقم المخطط', 'type': 'text', 'required': True,
                         'anchors': [{'t': 1, 'r': 2, 'c': 4}]},
        'block_number': {'label': 'رقم البلك', 'type': 'text',
                          'anchors': [{'t': 1, 'r': 2, 'c': 5}]},
        'parcel_number': {'label': 'رقم قطعة الأرض', 'type': 'text', 'required': True,
                           'anchors': [{'t': 1, 'r': 2, 'c': 6}]},

        'client_name': {'label': 'اسم العميل / طالب التقييم', 'type': 'text', 'required': True,
                         'anchors': [{'t': 2, 'r': 2, 'c': 1}]},
        'owner_name': {'label': 'اسم المالك', 'type': 'text', 'default_from': 'client_name',
                        'anchors': [{'t': 2, 'r': 2, 'c': 2}]},
        'valuation_purpose': {'label': 'الغرض من التقييم', 'type': 'text', 'default': 'للأغراض المحاسبية',
                               'anchors': [{'t': 2, 'r': 2, 'c': 3}]},
        'document_type': {'label': 'نوع مستند الملكية', 'type': 'text', 'default': 'صك إلكتروني',
                           'anchors': [{'t': 2, 'r': 2, 'c': 4}]},

        'city': {'label': 'المدينة', 'type': 'text', 'required': True,
                  'anchors': [{'t': 3, 'r': 2, 'c': 1}]},
        'district': {'label': 'الحي', 'type': 'text', 'required': True,
                      'anchors': [{'t': 3, 'r': 2, 'c': 2}]},
        'longitude': {'label': 'خط الطول', 'type': 'text',
                       'anchors': [{'t': 3, 'r': 2, 'c': 3}]},
        'latitude': {'label': 'خط العرض', 'type': 'text',
                      'anchors': [{'t': 3, 'r': 2, 'c': 4}]},

        'boundary_north': {'label': 'الحد الشمالي', 'type': 'text',
                            'anchors': [{'t': 4, 'r': 2, 'c': 2}]},
        'boundary_north_len': {'label': 'طول الحد الشمالي (م)', 'type': 'number',
                                'anchors': [{'t': 4, 'r': 2, 'c': 3}]},
        'boundary_south': {'label': 'الحد الجنوبي', 'type': 'text',
                            'anchors': [{'t': 4, 'r': 3, 'c': 2}]},
        'boundary_south_len': {'label': 'طول الحد الجنوبي (م)', 'type': 'number',
                                'anchors': [{'t': 4, 'r': 3, 'c': 3}]},
        'boundary_east': {'label': 'الحد الشرقي', 'type': 'text',
                           'anchors': [{'t': 4, 'r': 4, 'c': 2}]},
        'boundary_east_len': {'label': 'طول الحد الشرقي (م)', 'type': 'number',
                               'anchors': [{'t': 4, 'r': 4, 'c': 3}]},
        'boundary_west': {'label': 'الحد الغربي', 'type': 'text',
                           'anchors': [{'t': 4, 'r': 5, 'c': 2}]},
        'boundary_west_len': {'label': 'طول الحد الغربي (م)', 'type': 'number',
                               'anchors': [{'t': 4, 'r': 5, 'c': 3}]},

        'inspection_date_g': {'label': 'تاريخ معاينة الموقع (ميلادي)', 'type': 'date_g', 'required': True,
                               'anchors': [{'t': 5, 'r': 2, 'c': 2}]},
        'inspection_date_h': {'label': 'تاريخ معاينة الموقع (هجري)', 'type': 'date_h',
                               'derive_hijri_from': 'inspection_date_g',
                               'anchors': [{'t': 5, 'r': 2, 'c': 3}]},
        'engagement_date_g': {'label': 'تاريخ التكليف (ميلادي)', 'type': 'date_g',
                               'anchors': [{'t': 5, 'r': 3, 'c': 2}]},
        'engagement_date_h': {'label': 'تاريخ التكليف (هجري)', 'type': 'date_h',
                               'derive_hijri_from': 'engagement_date_g',
                               'anchors': [{'t': 5, 'r': 3, 'c': 3}]},
        'valuation_date_g': {'label': 'تاريخ قياس القيمة (ميلادي)', 'type': 'date_g', 'required': True,
                              'anchors': [{'t': 5, 'r': 4, 'c': 2}]},
        'valuation_date_h': {'label': 'تاريخ قياس القيمة (هجري)', 'type': 'date_h',
                              'derive_hijri_from': 'valuation_date_g',
                              'anchors': [{'t': 5, 'r': 4, 'c': 3}]},
        'issue_date_g': {'label': 'تاريخ إصدار التقرير (ميلادي)', 'type': 'date_g',
                          'default_from': 'valuation_date_g',
                          'anchors': [{'t': 5, 'r': 5, 'c': 2}]},
        'issue_date_h': {'label': 'تاريخ إصدار التقرير (هجري)', 'type': 'date_h',
                          'derive_hijri_from': 'issue_date_g',
                          'anchors': [{'t': 5, 'r': 5, 'c': 3}]},

        'land_area_actual': {'label': 'المساحة حسب الطبيعة (م2)', 'type': 'number',
                              'default_from': 'land_area_deed',
                              'anchors': [{'t': 6, 'r': 2, 'c': 2}]},
        'land_area_adopted': {'label': 'المساحة المعتمدة في التقييم (م2)', 'type': 'number',
                               'default_from': 'land_area_deed',
                               'anchors': [{'t': 6, 'r': 2, 'c': 3}]},
        'built_area': {'label': 'مسطحات البناء التقريبية (م2)', 'type': 'number', 'optional': True,
                        'anchors': [{'t': 6, 'r': 2, 'c': 4}]},
    }

    ref_data = {
        '_meta': {
            'template_name': 'narrative.docx',
            'template_type': 'demo-ksa',
            'anchor_mode': 'highlight',
            'description': 'حزمة تجريبية عربية بمرساة التظليل — يُعبَّى بالتظليل الأصفر وليس بمطابقة النص',
            'number_format': 'comma',
            'scope': 'البيانات الأساسية للعقار فقط (صك/مخطط/حدود/تواريخ) — القيم النهائية والمقارنات خارج النطاق',
        },
        'fields': fields,
    }
    out_path = os.path.join(TEMPLATE_DIR, 'reference-data.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(ref_data, f, ensure_ascii=False, indent=2)
    print(f'Wrote {out_path}')


# ── Build fictional demo project data ────────────────────────────────────

def build_demo_project():
    data = {
        'template_type': 'demo-ksa',
        'fields': {
            'deed_number': '391011223344',
            'deed_date_h': '1444-05-12',
            'land_area_deed': 612.5,
            'plan_number': '2891',
            'block_number': '7',
            'parcel_number': '114',
            'client_name': 'شركة الابتكار العقاري المحدودة',
            'owner_name': 'عبدالرحمن بن سالم القحطاني',
            'valuation_purpose': 'لأغراض التمويل العقاري',
            'document_type': 'صك إلكتروني',
            'city': 'الرياض',
            'district': 'حي النرجس',
            'longitude': '46.6753',
            'latitude': '24.8247',
            'boundary_north': 'شارع عرض 20 م',
            'boundary_north_len': 24.5,
            'boundary_south': 'قطعة رقم 113',
            'boundary_south_len': 24.5,
            'boundary_east': 'شارع عرض 15 م',
            'boundary_east_len': 25.0,
            'boundary_west': 'قطعة رقم 115',
            'boundary_west_len': 25.0,
            'inspection_date_g': '2026-01-10',
            'engagement_date_g': '2026-01-05',
            'valuation_date_g': '2026-01-15',
            'land_area_actual': 612.5,
            'land_area_adopted': 612.5,
            'built_area': '',
        },
    }
    os.makedirs(DEMO_DIR, exist_ok=True)
    out_path = os.path.join(DEMO_DIR, 'data.md')
    save_md(data, out_path, title='بيانات المشروع التجريبي — KSA Demo')
    print(f'Wrote {out_path}')


if __name__ == '__main__':
    build_template()
    build_reference_data()
    build_demo_project()
    print('\nDone. Next: ~/appraisal_ai/venv/bin/python demo/run_demo_ksa.py')

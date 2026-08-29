# demo-ksa — Arabic / RTL highlight-anchor pack

حزمة تجريبية عربية تعتمد على **مرساة التظليل** (highlight anchors) بدل مطابقة النص الحرفي.

## Files

| File | Role |
|------|------|
| `narrative.docx` | RTL Word template; yellow-highlighted `---` marks every fillable cell |
| `reference-data.json` | Field map with `"anchor_mode": "highlight"` and `{t,r,c}` anchors |

## Regenerate / verify

```bash
~/appraisal_ai/venv/bin/python demo/setup_demo_ksa.py
~/appraisal_ai/venv/bin/python demo/run_demo_ksa.py
```

## When to use this mode

Use highlight-anchor packs when the template has many short repeated literals
(`---`, `20`, `1000`) that mean different things depending on table position —
typical for Saudi deed/plan/four-boundary/Hijri-date tables. Orchestration:
`.claude/skills/draft-highlight.md`.

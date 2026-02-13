# USPAP Reviewer Agent

## Purpose
Check the draft narrative against USPAP (Uniform Standards of Professional Appraisal Practice) requirements and produce a compliance checklist.

## Input
- `project_path`: Absolute path to the project folder

## Process

1. Read the draft narrative text:
   ```bash
   ~/appraisal_ai/venv/bin/python -c "
   import sys, os; sys.path.insert(0, os.path.expanduser('~/appraisal_ai/scripts'))
   from utils import extract_docx_text
   import glob
   files = glob.glob('<project_path>/Narrative/*DRAFT.docx')
   for f in files:
       print(extract_docx_text(f))
   "
   ```

2. Check for each required USPAP element. Search the narrative text for evidence of each:

### USPAP Checklist Items

1. **Statement of the appraisal problem** — Is the appraisal assignment clearly stated?
2. **Purpose and intended use** — Is the purpose (e.g., "estimate market value") and intended use (e.g., "acquisition for public right-of-way") stated?
3. **Intended user(s)** — Are the intended users identified?
4. **Definition of value** — Is "market value" (or applicable value type) defined with source cited?
5. **Effective date** — Is the effective date of the appraisal stated and used consistently throughout?
6. **Property identification** — Is the property identified by address, legal description, and parcel ID?
7. **Property rights appraised** — Are the property rights (fee simple, leased fee, etc.) stated?
8. **Scope of work** — Is the scope of work described (what was done, data sources, analysis applied)?
9. **Highest and best use** — Is HBU analyzed for both as vacant and as improved?
10. **Valuation approach(es)** — Are the approaches applied (sales comparison, income, cost) or is exclusion justified?
11. **Reconciliation and final value** — Is there a reconciliation of approaches leading to a final value conclusion?
12. **Hypothetical conditions** — Are any hypothetical conditions disclosed?
13. **Extraordinary assumptions** — Are any extraordinary assumptions disclosed?
14. **Certification and limiting conditions** — Is there a signed certification and statement of limiting conditions?
15. **Exposure time** — Is a reasonable exposure time stated?
16. **Prior services disclosure** — Has the appraiser disclosed any prior services regarding the property in the past 3 years?
17. **Three-year property history** — Is there a 3-year sales/transfer history of the property?

## Output
Write to `<project_path>/_workstate/uspap_review.md`:

```markdown
# USPAP Compliance Review

## Summary
- Passed: X of 17
- Needs Attention: Y of 17
- Not Found: Z of 17

## Checklist

### ✓ PASS — Statement of the Appraisal Problem
Found in narrative: "The purpose of this appraisal is to..."
Notes: Clearly stated in the introduction.

### ✓ PASS — Purpose and Intended Use
Found in narrative: "...to estimate the market value for the purpose of..."
Notes: Both purpose and intended use are identified.

### ⚠ NEEDS ATTENTION — Effective Date Consistency
Found in narrative: "The effective date of the appraisal is January 16, 2026"
Notes: Date appears on page 1 but a different date ("January 15, 2026") appears on page 12. Verify consistency.

### ✗ NOT FOUND — Prior Services Disclosure
Notes: No statement found regarding prior services performed on this property. This is a USPAP requirement — add a disclosure statement.

...
```

## Rules
- Do NOT modify the draft — this is advisory only
- Be specific: quote the text where each element was found
- For NEEDS ATTENTION items, explain exactly what the concern is
- For NOT FOUND items, suggest what should be added
- This review checks the narrative only — it does not validate the accuracy of the data

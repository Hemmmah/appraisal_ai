# Field Extraction Patterns

Regex patterns and strategies for extracting structured metadata from appraisal narrative markdown text. Used by `build_index.py`.

## Job Number

Look for "File No." or similar in the first ~50 lines of the document.

```
File\s*No\.?\s*[:.]?\s*(\d{4}-\d{2,4})
File\s*#\s*[:.]?\s*(\d{4}-\d{2,4})
Job\s*(?:No|Number|#)\.?\s*[:.]?\s*(\d{4}-\d{2,4})
Our\s*File\s*[:.]?\s*(\d{4}-\d{2,4})
```

Fallback: extract from filename if it matches pattern `YYYY-NNN` or `YYYY-NN`.

## Property Address

Primary: look for "RE:" line in the transmittal letter (first ~100 lines).

```
RE:\s*(.+?)(?:\n|$)
Re:\s*(.+?)(?:\n|$)
Subject\s*Property:\s*(.+?)(?:\n|$)
Property\s*Address:\s*(.+?)(?:\n|$)
```

The address may span two lines (street + city/state/zip). Capture the line after RE: as well if it looks like a city/state pattern:

```
,\s*(?:CO|Colorado)\s*\d{5}
```

Cleanup: strip leading/trailing whitespace, remove trailing periods, remove bold markdown (`**`).

## Property Type Classification

Scan the full document for keywords. Assign the FIRST match from this priority list:

| Keywords | Type | Subtype |
|----------|------|---------|
| `conservation easement` | special-purpose | conservation-easement |
| `condemnation`, `eminent domain`, `partial taking`, `just compensation` | (keep existing type) | (set purpose=condemnation) |
| `vacant land`, `unimproved land`, `land valuation`, `land only` | land | vacant |
| `single.family`, `single-family`, `SFR`, `residence` | residential | sfr |
| `multi.?family`, `apartment`, `duplex`, `triplex`, `fourplex` | residential | multifamily |
| `condominium`, `condo`, `townhome`, `townhouse` | residential | condo |
| `mobile home`, `manufactured home` | residential | manufactured |
| `office building`, `office space` | commercial | office |
| `retail`, `shopping center`, `strip mall`, `strip center` | commercial | retail |
| `restaurant`, `food service` | commercial | restaurant |
| `hotel`, `motel`, `hospitality` | commercial | hospitality |
| `warehouse`, `distribution`, `industrial` | industrial | warehouse |
| `manufacturing`, `plant`, `factory` | industrial | manufacturing |
| `ranch`, `agricultural`, `farm`, `grazing`, `irrigated` | agricultural | ranch |
| `church`, `school`, `hospital`, `government` | special-purpose | institutional |
| `mixed.?use` | mixed-use | mixed-use |
| `commercial` | commercial | general |
| `residential` | residential | general |

Case-insensitive matching. If no keywords match, set type to `unknown`.

## Effective Date

Look for date of valuation or effective date, typically in the transmittal letter or certification.

```
[Dd]ate\s*of\s*[Vv]aluation\s*[:.]?\s*(.+?)(?:\n|$)
[Ee]ffective\s*[Dd]ate\s*[:.]?\s*(.+?)(?:\n|$)
[Aa]s\s*of\s+(\w+\s+\d{1,2},?\s+\d{4})
[Vv]aluation\s*[Dd]ate\s*[:.]?\s*(.+?)(?:\n|$)
```

Parse the captured text into a date. Common formats:
- `January 15, 2024`
- `01/15/2024`
- `1/15/2024`
- `January 15th, 2024`

Normalize output to `YYYY-MM-DD`.

## Concluded Value

Look for the final value conclusion. Search near "Market Value", "value conclusion", or in the certification.

```
\$\s*([\d,]+(?:\.\d{2})?)
```

Strategy: find paragraphs containing these phrases and extract dollar amounts:
- `market value`
- `value of the subject`
- `value conclusion`
- `appraised value`
- `just compensation`
- `total compensation`
- `concluded.*value`

If multiple dollar amounts found, prefer:
1. The one nearest "market value" or "concluded value"
2. The largest round number (appraisal conclusions are typically round)
3. The last one in the certification section

## Land Area

Look for land size in SF or acres.

```
([\d,]+(?:\.\d+)?)\s*(?:square\s*feet|sq\.?\s*ft\.?|SF)
([\d,]+(?:\.\d+)?)\s*(?:acres?|AC)
```

If both SF and acres are found, keep both. Prefer the value near "land area", "site area", or "lot size" headings.

## County

```
(\w+)\s*County
County\s*of\s*(\w+)
```

Common Colorado counties to validate against: Adams, Arapahoe, Boulder, Broomfield, Clear Creek, Denver, Douglas, Eagle, El Paso, Garfield, Gilpin, Grand, Jefferson, Larimer, Mesa, Park, Pitkin, Pueblo, Routt, Summit, Weld.

## Client

Look in the transmittal letter (first ~50 lines).

```
[Dd]ear\s+(Mr\.|Ms\.|Mrs\.|Dr\.)\s*(.+?)(?:\n|,|$)
[Dd]ear\s+(.+?)(?:\n|:|,|$)
[Aa]ttention:\s*(.+?)(?:\n|$)
```

Also check the addressee block (lines 2-8 of the document, look for a name above a company/address).

## Appraiser

Look in the certification or signature block, typically near end of document.

```
(\w[\w\s,.]+),?\s*(?:MAI|SRA|ASA|AI-GRS|Certified\s*General)
```

Also look for "Prepared by:" or "Appraised by:" lines.

## Purpose / Intended Use

```
[Pp]urpose\s*(?:of\s*(?:the\s*)?)?[Aa]ppraisal\s*[:.]?\s*(.+?)(?:\n|$)
[Ii]ntended\s*[Uu]se\s*[:.]?\s*(.+?)(?:\n|$)
```

Classify into categories:
- Keywords `litigation`, `lawsuit`, `court` → litigation
- Keywords `estate`, `trust`, `probate`, `death`, `decedent` → estate
- Keywords `lending`, `mortgage`, `loan`, `financing` → lending
- Keywords `condemnation`, `eminent domain`, `acquisition`, `CDOT`, `partial taking` → condemnation
- Keywords `tax`, `property tax`, `appeal` → tax-appeal
- Keywords `insurance`, `replacement cost` → insurance
- Keywords `partnership`, `dissolution`, `buyout` → partnership
- Keywords `relocation`, `advisory` → advisory
- Default: `general`

## Approaches Used

Scan for mentions of valuation approaches.

```
[Ss]ales\s*[Cc]omparison\s*[Aa]pproach
[Cc]ost\s*[Aa]pproach
[Ii]ncome\s*(?:[Cc]apitalization\s*)?[Aa]pproach
[Dd]irect\s*[Cc]apitalization
```

Return as comma-separated list: `sales-comparison, cost, income`.

## General Extraction Guidelines

1. **Don't hallucinate.** If a field can't be found with reasonable confidence, leave it blank.
2. **First match wins** for most fields (the transmittal letter is at the top, most reliable).
3. **Normalize whitespace** — collapse multiple spaces, strip markdown formatting.
4. **Handle encoding** — OneDrive filenames may have smart quotes, em-dashes, special chars. Use `errors='replace'` when reading.
5. **Performance** — compile regex patterns once, reuse across files. The archive has ~4k files.

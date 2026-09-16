# phi-deterministic-rules — regex rules for the 19 PHI labels

**Internal use only.** A stdlib-only Python library of 52 deterministic rules that locate and redact the 19 PHI
labels used in the Biogen de-identification deliverable: `person_name`, `doctor_name`, `signature_block`, `date`,
`age_90_plus`, `identified_number`, `phone`, `fax`, `email`, `url`, `ip_address`, `address`, `zip_code`, `location`,
`hospital_name`, `organization`, `amount`, `device_id`, `study_id`.

The rules were derived from **470,445,960 spans that the de-identification model actually redacted** across
19.1 M records (clinical notes, OCR exports, HTML/XML notes and progressnotes vendor XML), by censusing the shapes
and contexts of those spans per label and then scoring candidate regexes against them. Every regex in this
README is the one the package runs: the rule sections below are generated from the code and a test fails if
they drift. This is a deterministic pass and a safety net, not a replacement for the model where names appear
in running prose (see Limitations).

## Quick start

```bash
pip install -e .                      # or vendor the phi_rules/ directory; no dependencies
python -m pytest -q                   # fixtures, engine contract, README in sync
python -m phi_rules.selftest          # the same fixtures without pytest
phi-rules redact -i notes.jsonl --field note_raw -o out.jsonl          # adds "redacted"
phi-rules find   -i notes.jsonl --field note_raw -o spans.jsonl        # adds "spans" (label, rule, start, end)
cat notes.jsonl | phi-rules redact --field text > out.jsonl            # stdin -> stdout
phi-rules redact --format csv -i notes.csv --field note -o out.csv
```

```python
from phi_rules import find, redact

text = "Patient Name: Mary Ann Jones, DOB: 04/06/1959, Ph: (555) 123-4567."
find(text)     # [Span(label='person_name', rule='patient_labelled', start=14, end=28, text='Mary Ann Jones'), ...]
redact(text)   # 'Patient Name: ((person_name)), DOB: ((date)), Ph: ((phone)).'
redact(text, placeholder="[{label}]", cutoff_year=1937)
```

Exit status of the CLI: 0 ok, 1 self-test failures, 2 bad arguments. `find`/`--spans` never emit the span text,
only label, rule and offsets.

## How it works

1. Every rule is a Python `re` pattern with a named group `val` (three rules also use `val2`/`val3`). Rules run on
   the **raw text, markup included**: a shared fragment `GAP` absorbs tags, HTML entities and whitespace between a
   label and its value, and the markup rules accept raw or HTML-escaped quotes and brackets.
2. Each `val*` match is a candidate span. Candidates are dropped when the value contains `((` (an upstream
   placeholder) or is in `SKIP_VALUES` (`true`, `none`, `0`, `Admin`, …). A rule's `relabel` hook may change the
   label per match (the city-state-ZIP rule emits `address`, `address`, `zip_code`; the markup rules map the
   attribute or element NAME to a label; the ip rule drops octets over 255).
3. A `date` whose year is at or below `CUTOFF_YEAR` (**1936**, i.e. 2026 − 90) becomes `age_90_plus`. The constant
   is fixed so re-runs are reproducible; pass `cutoff_year` to move it.
4. Overlaps are resolved by sorting candidates by (start, longest first) and sweeping: at the same start the longer
   span wins, an earlier span beats a later overlapping one. Over-redaction is the safe side.
5. `redact()` replaces every span with `placeholder.format(label=…)`, default `((label))` — the same vocabulary the
   model produced, so outputs are interchangeable.

## The 19 labels

Share = share of the 470 M model-redacted spans (progressnotes vendor XML contributes 89% of them, almost all
`identified_number`). Recall = share of the model's spans in a stratified 42,991-record sample that a rule of the
same label / same family covers entirely (`docs/evaluation.md` has the intervals and the per-table-group view).

| label | definition (from the de-identification prompts) | share of spans | recall, same label | recall, same family |
|---|---|---:|---:|---:|
| person_name | patient, relative, caretaker, staff named in the body of a note | 4.74% | 23.5% | 47.4% |
| doctor_name | a clinician's name (Dr./credential/provider context), credential excluded | 5.13% | 62.7% | 69.6% |
| signature_block | signature, dictation, cc:, "signed by" lines, user logins | 2.80% | 49.4% | 62.8% |
| date | a birth or death date (any format); no other date is PHI | 1.55% | 86.0% | 89.4% |
| age_90_plus | an age of 90+, or a DOB implying it | 0.43% | 57.5% | 87.0% |
| identified_number | MRN, SSN, account/insurance/encounter/order numbers, any id-keyed value | 74.32% | 33.1% | 33.2% |
| phone | phone, pager, extension | 0.31% | 64.4% | 64.7% |
| fax | fax number (nearest label decides) | 0.21% | 91.5% | 93.9% |
| email | e-mail address | 0.00% | 60.7% | 60.7% |
| url | URL in visible text | 0.02% | 74.8% | 74.8% |
| ip_address | dotted quad | 0.00% | 0.0% | 0.0% |
| address | street, city, state attached to city/ZIP, county | 5.04% | 72.3% | 72.5% |
| zip_code | ZIP / postal code | 1.52% | 80.9% | 83.0% |
| location | room, bed, unit, ward, clinic site | 0.24% | 29.5% | 30.4% |
| hospital_name | hospital / facility name | 2.36% | 40.1% | 40.7% |
| organization | employer, insurer, school, company | 1.27% | 1.6% | 67.3% |
| amount | financial amounts | 0.06% | 90.1% | 90.1% |
| device_id | device serial numbers | 0.01% | 43.8% | 43.8% |
| study_id | trial / protocol / subject ids | 0.01% | 39.5% | 42.7% |

Families: names (person / doctor / signature), dates (date / age_90_plus), numbers (identified_number / phone / fax /
device / study), places (address / zip / location), institutions (hospital / organization). The model's own label
choice inside a family is context-driven and inconsistent (8,430 literals occur under all three name labels), so
consume the rules at the family level unless the exact label matters.

## Policy decisions

The rules follow ten explicit choices where the model was inconsistent or the prompts draw a line — only labelled
birth/death dates, never redact by shape alone, structural XML ids and presentational attributes skipped, system
accounts skipped, upstream placeholders untouched, `href` not redacted, `$` amounts redacted, over-redaction on
ties, family-level labels. They are listed with their rationale in [`docs/policy.md`](docs/policy.md); Data
Engineering owns them.

## Rules by PHI type

Each rule: what it matches, the census evidence, its measured precision (same label / same family / any model span;
"unhit" spans are a lower bound on false positives because the model's own misses land there), the flags, and the
**exact regex** with all shared fragments expanded. Examples show what `find()` returns on synthetic text.

<!-- BEGIN GENERATED: rules -->
### Dates and ages  (`phi_rules/dates.py`)

Only a labelled birth or death date is PHI; every other date is clinical data. 66% of the model's date spans are a bare 4-digit year behind a DOB label. The engine promotes a `date` whose year is at or below `CUTOFF_YEAR` (1936) to `age_90_plus`.

#### `dob_labelled`  → `date`

A DOB / Date of Birth / Birthdate / DOD label (any case, markup allowed between label and value, 'is/was/of' filler allowed) followed by a date value; the value shapes are, longest first, ISO with optional time, US numeric, 2-digit year, day-Mon-year, Mon day year, compact 8-digit, bare 4-digit year. 92% same-label / 99.6% family precision; the difference is the age_90_plus promotion.

Evaluation: fired 12,877; precision same label 92.1%, same family 99.6%, any model span 99.7%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?<![A-Za-z])(?i:(?:D\.?\s?O\.?\s?B\.?(?:\s+source)?|date\s+of\s+birth|birth\s*date|birthdate|born(?:\s+on)?|D\.?O\.?D\.?|date\s+of\s+death|deceased(?:\s+date|\s+on)?|death\s+date))(?![A-Za-z])(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}(?:[:#=\-–]|is|was|of)?(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}(?:[:#=\-](?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8})?(?P<val>(?i:(?:(?:18|19|20)\d{2}-\d{1,2}-\d{1,2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?)?|\d{1,2}[-/.]\d{1,2}[-/.](?:18|19|20)\d{2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2}|\d{1,2}[- ](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?[- ,]+\d{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+(?:18|19|20)\d{2}|(?:18|19|20)\d{2}\d{2}\d{2}|(?:18|19|20)\d{2})))
```

Examples (what `find()` returns):

- `Patient DOB: 04/06/1959 was seen.` → date=`04/06/1959`
- `<tr><th>DOB</th><td>1950</td></tr>` → date=`1950`
- `Date of Birth: 1931-05-02` → age_90_plus=`1931-05-02`
- `DOB Source: 1950-03-04` → date=`1950-03-04`

#### `dob_after_guarantor_tokens`  → `date`

Corpus-specific: the upstream de-identifier masked the guarantor / patient name tokens of a demographic line and left the birth year after them ('((GUARANTORLASTNAME)), ((GUARANTORFIRSTNAME)) ((GUARANTORMIDDLEINITIAL)) 1957'). 144k+ spans; 82% precision.

Evaluation: fired 5,213; precision same label 81.3%, same family 82.7%, any model span 82.7%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
\(\((?:GUARANTOR|PATIENT)[A-Z_]*NAME[A-Z_]*\)\)(?:[ ,]*\(\((?:GUARANTOR|PATIENT)[A-Z_]*\)\))*[ ,]+(?P<val>(?:18|19|20)\d{2}|(?:18|19|20)\d{2}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/(?:18|19|20)\d{2})(?![\d/-])
```

Examples (what `find()` returns):

- `((GUARANTORLASTNAME)), ((GUARANTORFIRSTNAME)) ((GUARANTORMIDDLEINITIAL)) 1957 F` → date=`1957`

#### `birth_v_attribute`  → `date`

Vendor-XML / CCDA birth date carried in a V= or value= attribute of a birth element.

Evaluation: fired 284; precision same label 84.9%, same family 99.6%, any model span 99.6%.

Flags: re.IGNORECASE. Value group: `val`.

```text
(?:<|&lt;)(?:birth_dttm|birthTime|birth_date|dob)\b[^<>&]*?\b(?:V|value)\s*=\s*(?:\"|&quot;)(?P<val>\d{4}[\d\-T:. ]{0,20})(?:\"|&quot;)
```

Examples (what `find()` returns):

- `<birth_dttm V="1931-05-02T00:00:00"/>` → age_90_plus=`1931-05-02T00:00:00`

#### `age_labelled_90plus`  → `age_90_plus`

'Age: 92' style: an age label followed by a number from 90 to 119. Ages under 90 are not PHI.

Evaluation: fired 147; precision same label 57.8%, same family 57.8%, any model span 58.5%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?<![A-Za-z])(?i:(?:age|aged|yo|y/o))(?![A-Za-z])(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}(?:[:#=\-–]|is|was|of)?(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}(?:[:#=\-](?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8})?(?P<val>(?i:(?:9\d|1[01]\d)(?![\d])))
```

Examples (what `find()` returns):

- `Age: 92 Gender: F` → age_90_plus=`92`

#### `age_suffix_90plus`  → `age_90_plus`

'92 yo', '95-year-old', '101 yrs': a number from 90 to 119 followed by an age suffix.

Evaluation: fired 504; precision same label 63.7%, same family 63.7%, any model span 63.7%.

Flags: re.IGNORECASE. Value group: `val`.

```text
(?<!\d)(?P<val>9\d|1[01]\d)\s?(?:-?\s?(?:yo|y/o|y\.o\.|yrs?|years?)(?:[- ]old)?)\b
```

Examples (what `find()` returns):

- `a 94 yo female` → age_90_plus=`94`
- `a 101-year-old man` → age_90_plus=`101`

### Identifiers, devices and studies  (`phi_rules/identifiers.py`)

identified_number is 74% of all model-redacted spans; outside structured markup 78% are plain digit runs behind a label. The LABEL carries the signal: a bare number is never redacted by shape.

#### `id_labelled`  → `identified_number`

An identifier label (MRN, Patient ID, Chart #, Account/Insurance/Policy/Group/Member/Subscriber #, Encounter/Visit/Accession/Specimen/Order #, ID#, SSN, NPI:, DEA:, License/Claim/Case/Report/Document/Ref/File #) followed by a 3-30 character alphanumeric value. Short acronyms (ID, SSN, NPI, DEA) need an explicit marker so 'DEA' inside a hex string cannot fire. 81% precision.

Evaluation: fired 18,377; precision same label 81.0%, same family 81.0%, any model span 81.3%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?<![A-Za-z0-9])(?i:(?:MRN|MR\s?#|medical\s+record\s+(?:number|no\.?|#)|patient\s*id(?:entifier)?|patientid|pt\s*id|chart\s*(?:id|#|no\.?|number)|account\s*(?:id|#|no\.?|number)|acct\s*(?:#|no\.?)|insurance\s*(?:id|#|no\.?|number)|policy(?:/group)?\s*(?:#|no\.?|number)|group\s*(?:#|no\.?|number|id)|member\s*(?:id|#|no\.?|number)|subscriber\s*(?:id|#|no\.?)|encounter\s*(?:id|#|no\.?|number)|visit\s*(?:id|#|no\.?|number)|admission\s*(?:#|no\.?|number)|accession\s*(?:#|no\.?|number)|specimen\s*(?:id|#|no\.?)|order\s*(?:#|no\.?|id|number)|req(?:uisition)?\s*(?:#|no\.?)|ID\s*(?:#|no\.?|number)|ID(?=\s*:)|SSN(?=\s*[#:]|\s)|social\s+security(?:\s+(?:number|#|no\.?))?|NPI\s*[#:]|DEA\s*[#:]|license\s*(?:#|no\.?|number)|claim\s*(?:#|no\.?|number)|guarantor\s*(?:id|#|no\.?)|case\s*(?:#|no\.?|number)|report\s*(?:#|no\.?|number)|document\s*(?:id|#|no\.?)|ref(?:erence)?\s*(?:#|no\.?|number)|file\s*(?:#|no\.?)))(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}[:#=\-\u2013]?(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}(?:[:#=\-](?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8})?(?P<val>[A-Za-z0-9][A-Za-z0-9\-/.]{2,29})
```

Examples (what `find()` returns):

- `MRN: 00123456 Encounter` → identified_number=`00123456`
- `Insurance # : XYZ12345678<br>` → identified_number=`XYZ12345678`
- `Order # 1234567890 placed` → identified_number=`1234567890`

#### `id_attribute`  → `identified_number`

An identifier key written as key=value or key:value outside quoted markup (URLs, query strings, key/value dumps): patientid=8842719, encounter_no: 1234. 71% precision.

Evaluation: fired 2,342; precision same label 71.2%, same family 71.2%, any model span 71.3%.

Flags: re.IGNORECASE. Value group: `val`.

```text
(?:patient|chart|account|encounter|visit|member|subscriber|person|record|order|specimen|accession|document|guarantor|policy)_?(?:id|no|num|number)\s*['\"]?\s*[:=]\s*['\"]?(?P<val>[A-Za-z0-9][A-Za-z0-9\-/.]{2,29})
```

Examples (what `find()` returns):

- `view.aspx?menu=1&patientid=8842719&x` → identified_number=`8842719`

#### `xml_id_extension`  → `identified_number`

CCDA <id root=… extension=…/>: the extension is the record identifier (the root is an OID, never PHI). Inert in the evaluation sample -- the archived progressnotes are vendor XML rather than CCDA -- kept for CCDA inputs.

Evaluation: inert in the sample (never fired).

Flags: re.IGNORECASE. Value group: `val`.

```text
<id\b[^>]*\bextension\s*=\s*[\"'](?P<val>[^\"']{2,40})[\"']
```

Examples (what `find()` returns):

- `<id root="2.16.840.1" extension="MRN-77812"/>` → identified_number=`MRN-77812`

#### `ssn_shape`  → `identified_number`

A US Social Security Number shape ddd-dd-dddd on its own (no label needed).

Evaluation: fired 6; precision same label 100.0%, same family 100.0%, any model span 100.0%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?<![\d-])(?P<val>\d{3}-\d{2}-\d{4})(?![\d-])
```

Examples (what `find()` returns):

- `SSN 123-45-6789 on file` → identified_number=`123-45-6789`

#### `device_labelled`  → `device_id`

Serial Number / S/N / SN / Scanner # / Device ID / Implant ID / Model # / Lot # / UDI followed by an alphanumeric value that contains a digit. Low precision in the sample (device_id is 26k spans corpus-wide); DE should decide whether device serials are in scope.

Evaluation: fired 506; precision same label 5.5%, same family 31.4%, any model span 31.6%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?<![A-Za-z])(?i:(?:serial\s+(?:number|no\.?|#)|serial|s/n|sn|scanner\s*#|device\s+id|implant\s+id|model\s*(?:#|no\.?)|lot\s*(?:#|no\.?)|udi))(?![A-Za-z])(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}[:#=\-\u2013]?(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}(?:[:#=\-](?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8})?(?P<val>(?i:(?=[A-Za-z0-9\-]*\d)[A-Za-z0-9][A-Za-z0-9\-]{3,24}))
```

Examples (what `find()` returns):

- `Serial Number: SN0012345X was` → device_id=`SN0012345X`

#### `study_labelled`  → `study_id`

Protocol / Study # / Subject ID / Participant / Site Number / Screening / Randomization / Enrollment / IRB label followed by a code containing a digit. 'study' alone is never a trigger (imaging studies).

Evaluation: fired 135; precision same label 31.1%, same family 84.4%, any model span 84.4%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?<![A-Za-z])(?i:(?:protocol(?:\s*(?:#|no\.?|number|id))?|study\s*(?:#|no\.?|number|id)|subject\s*(?:#|no\.?|number|id)|participant(?:\s*(?:#|no\.?|number|id))?|site\s*(?:#|no\.?|number)|screening\s*(?:#|no\.?|number|id)|randomi[sz]ation\s*(?:#|no\.?|number|id)|enrollment\s*(?:#|no\.?|number|id)|IRB\s*(?:#|no\.?)?))(?![A-Za-z])(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}[:#=\-\u2013]?(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}(?:[:#=\-](?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8})?(?P<val>(?i:(?=[A-Za-z0-9\-]*\d)[A-Za-z0-9][A-Za-z0-9\-]{2,24}))
```

Examples (what `find()` returns):

- `Protocol: AB1-CD-2345 Subject` → study_id=`AB1-CD-2345`

#### `nct_shape`  → `study_id`

A ClinicalTrials.gov registry number NCTnnnnnnnn.

Evaluation: fired 9; precision same label 77.8%, same family 77.8%, any model span 77.8%.

Flags: re.IGNORECASE. Value group: `val`.

```text
(?P<val>NCT\d{8})
```

Examples (what `find()` returns):

- `registered as NCT01234567` → study_id=`NCT01234567`

### Phone, fax, e-mail, URL, IP  (`phi_rules/contact.py`)

Formatted 10-digit numbers are phones on their own; bare digit runs need a Phone/Fax label, a `tel:` link, a phone-named attribute or the position right after a ZIP. E-mail and URLs are pure shapes.

#### `phone_after_zip_or_comma`  → `phone`

A bare 10-digit number directly after a ZIP code (…NY 10000-1234 5555551234) or after a comma in an address / signature line. 98% precision.

Evaluation: fired 580; precision same label 98.4%, same family 99.8%, any model span 99.8%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?:(?<=\d{5}\s)|(?<=\d{4}\s)|(?<=,\s)|(?<=,))(?P<val>\d{10})(?![\d-])
```

Examples (what `find()` returns):

- `((PatientCity)), NY 10000-1234 5555551234 Fax` → address=`NY`, zip_code=`10000-1234`, phone=`5555551234`

#### `fax_labelled`  → `fax`

Fax / Facsimile / Fax # label followed by a phone-shaped value. 97% precision; 94% same-family recall.

Evaluation: fired 2,298; precision same label 96.9%, same family 97.8%, any model span 97.8%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?<![A-Za-z])(?i:(?:fax|facsimile|fax\s*(?:#|no\.?|number)))(?![A-Za-z])(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}(?:[:#=\-–]|is|was|of)?(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}(?:[:#=\-](?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8})?(?P<val>(?i:(?:\+?1[-.\s]?)?(?:\(\d{3}\)\s?|\d{3}[-./\s])\d{3}[-.\s]\d{4}|\+?1?\d{10}|\d{3}-\d{4}))
```

Examples (what `find()` returns):

- `Fax: 555-765-4321` → fax=`555-765-4321`

#### `phone_labelled`  → `phone`

Phone / Ph / Tel / Cell / Mobile / Pager / Office / Home / Work label followed by a phone-shaped value (formatted, bare 10/11 digits, or 7-digit local). 98% precision.

Evaluation: fired 2,668; precision same label 97.9%, same family 99.0%, any model span 99.0%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?<![A-Za-z])(?i:(?:phone|ph|tel|telephone|cell|mobile|pager|pgr|contact|call|office|home|work|main|direct)(?:\s*(?:#|no\.?|number))?)(?![A-Za-z])(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}(?:[:#=\-–]|is|was|of)?(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}(?:[:#=\-](?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8})?(?P<val>(?i:(?:\+?1[-.\s]?)?(?:\(\d{3}\)\s?|\d{3}[-./\s])\d{3}[-.\s]\d{4}|\+?1?\d{10}|\d{3}-\d{4}))
```

Examples (what `find()` returns):

- `Ph: (555) 123-4567` → phone=`(555) 123-4567`
- `Cell 5550101234` → phone=`5550101234`

#### `phone_formatted_unlabelled`  → `phone`

A formatted North-American number with no label: (555) 123-4567, 555-123-4567, 555.123.4567, +1 555-123-4567. 89% same-label / 96% family precision (some are labelled fax).

Evaluation: fired 961; precision same label 88.6%, same family 97.0%, any model span 97.1%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?<![\d(-])(?P<val>(?:\+?1[-.\s]?)?(?:\(\d{3}\)\s?|\d{3}[-.]\s?)\d{3}[-.]\d{4})(?![\d-])
```

Examples (what `find()` returns):

- `call 555-123-4567 today` → phone=`555-123-4567`

#### `tel_href`  → `phone`

The number inside an HTML tel: link.

Evaluation: fired 18; precision same label 100.0%, same family 100.0%, any model span 100.0%.

Flags: re.IGNORECASE. Value group: `val`.

```text
tel:(?P<val>\+?[\d\-().\s]{7,20})
```

Examples (what `find()` returns):

- `<a href="tel:+15550101234">call</a>` → phone=`+15550101234`

#### `email_shape`  → `email`

local@domain.tld. 100% precision in the sample; e-mail is rare in this corpus (20k spans).

Evaluation: fired 17; precision same label 100.0%, same family 100.0%, any model span 100.0%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?<![A-Za-z0-9._%+-])(?P<val>[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})
```

Examples (what `find()` returns):

- `contact jane.doe@example.org for` → email=`jane.doe@example.org`

#### `url_scheme`  → `url`

http(s):// or www. URLs. 98% precision.

Evaluation: fired 48; precision same label 97.9%, same family 97.9%, any model span 97.9%.

Flags: re.IGNORECASE. Value group: `val`.

```text
(?P<val>\bhttps?://[^\s<>\"'()]+|\bwww\.[^\s<>\"'()]+)
```

Examples (what `find()` returns):

- `visit https://portal.example.com/x?y=1 now` → url=`https://portal.example.com/x?y=1`

#### `url_bare_domain`  → `url`

A bare domain (portal.example.com, example.org/path) without a scheme. 69% precision: vendor domains in boilerplate were often left alone by the reference model.

Evaluation: fired 387; precision same label 68.5%, same family 69.0%, any model span 69.5%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?<![\w@.\-/])(?P<val>[A-Za-z][A-Za-z0-9\-]{1,40}(?:\.[A-Za-z0-9\-]{1,40})*\.(?:com|org|net|edu|gov|io|us|info|health)(?:/[^\s<>\"']*)?)(?![\w.\-])
```

Examples (what `find()` returns):

- `go to portal.example.com/results` → url=`portal.example.com/results`

#### `ip_shape`  → `ip_address`  (label decided per match by the rule's relabel hook)

Dotted quad with every octet <= 255 (OIDs like 2.16.840.1 are excluded by the octet check). 294 spans corpus-wide, 0/23 hits in the sample -- near-irrelevant here, kept for completeness.

Evaluation: fired 23; precision same label 0.0%, same family 0.0%, any model span 0.0%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?<![\d.])(?P<val>(?:\d{1,3}\.){3}\d{1,3})(?![\d.])
```

Examples (what `find()` returns):

- `from 192.168.10.44 at` → ip_address=`192.168.10.44`

### Amounts  (`phi_rules/amount.py`)

Financial values only -- never doses, lab values, vitals or scores.

#### `dollar_amount`  → `amount`

A currency amount with $ (optional thousands separators and cents). 91% recall; 42% precision against the reference because the model left most fee-schedule tables alone -- a policy call for DE (see docs/policy.md).

Evaluation: fired 1,730; precision same label 42.4%, same family 42.4%, any model span 42.7%.

Flags: re.IGNORECASE. Value group: `val`.

```text
(?P<val>\$\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?)(?![\d])
```

Examples (what `find()` returns):

- `a fee of $25.00 applies` → amount=`$25.00`
- `balance $1,250` → amount=`$1,250`

#### `amount_labelled`  → `amount`

Balance / Copay / Deductible / Fee / Charge / Amount due / Payment / Cost / Total label followed by a decimal amount with or without $. 12% precision in the sample (n=86): 'Total' also labels counts.

Evaluation: fired 86; precision same label 11.6%, same family 11.6%, any model span 11.6%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?<![A-Za-z])(?i:(?:balance|copay|co-pay|coinsurance|deductible|fee|charge|amount\s+due|payment|cost|total|owed))(?![A-Za-z])(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}(?:[:#=\-–]|is|was|of)?(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}(?:[:#=\-](?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8})?(?P<val>(?i:\$?\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})))
```

Examples (what `find()` returns):

- `Copay: 40.00 due` → amount=`40.00`

### Addresses, ZIP codes and locations  (`phi_rules/places.py`)

The model splits `City, ST 12345` into city and state (address) and ZIP (zip_code) -- 32% of all address spans are bare state codes for that reason. Structured lines are deterministic; a city alone in prose needs a gazetteer.

#### `addr_v_attribute`  → `address`  (label decided per match by the rule's relabel hook)

Vendor-XML address block with values in V= attributes: <LINE_1 V=…> <CTY V=…> <STA V=…> -> address, <ZIP V=…> -> zip_code, <PHONE V=…> -> phone, <FAX V=…> -> fax. 99.6% precision.

Evaluation: fired 1,299; precision same label 99.6%, same family 99.6%, any model span 99.6%.

Flags: re.IGNORECASE. Value group: `val`.

```text
(?:<|&lt;)(?P<tag>LINE_?\d|STA|CTY|ZIP|CITY|STATE|STREET|ADDR|PHONE|FAX|TEL)\b[^<>&]*?\bV\s*=\s*(?:\"|&quot;)(?P<val>[^\"&]{1,60})(?:\"|&quot;)
```

Examples (what `find()` returns):

- `<ADDR><LINE_1 V="12 Main St"/><CTY V="Anytown"/><STA V="MI"/><ZIP V="48000"/><PHONE V="5555551212"/></ADDR>` → address=`12 Main St`, address=`Anytown`, address=`MI`, zip_code=`48000`, phone=`5555551212`

#### `city_state_zip`  → `address`  (label decided per match by the rule's relabel hook)

The 'City, ST 12345' line: a city of 1-3 capitalised words, a real US state code (not glued to a preceding word), a 5- or 9-digit ZIP; markup may sit between the parts. Emits city and state as address and the ZIP as zip_code (three groups val/val2/val3). 88% same-label / 95% family precision.

Evaluation: fired 13,173; precision same label 88.2%, same family 95.3%, any model span 96.6%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`, `val2`, `val3`.

```text
(?<![A-Za-z])(?P<val>[A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]+){0,2}),?(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}(?<![A-Za-z])(?P<val2>(?:A[LKZR]|C[AOT]|D[EC]|FL|GA|HI|I[DLNA]|K[SY]|LA|M[EDAINSOT]|N[EVHJMYCD]|O[HKR]|PA|RI|S[CD]|T[NX]|UT|V[TA]|W[AVIY]|PR|VI|GU))\.?(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}(?P<val3>\d{5}(?:-\d{4})?)(?![\d-])
```

Examples (what `find()` returns):

- `Sample Hills, MI 48000` → address=`Sample Hills`, address=`MI`, zip_code=`48000`
- `Anytown,<br/> MI 48000-1234` → address=`Anytown`, address=`MI`, zip_code=`48000-1234`

#### `upstream_city_then_state`  → `address`

Corpus-specific: the upstream de-identifier masked the city token and left the state after it ('((PATIENTCITY)), FL'). 74% precision.

Evaluation: fired 7,164; precision same label 73.9%, same family 74.0%, any model span 79.0%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
\(\([A-Za-z_]*(?:CITY|City)[A-Za-z_]*\)\)\s*,?(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}(?P<val>[A-Z]{2}|[A-Z][a-z]+)(?=[\s,.<]|$)
```

Examples (what `find()` returns):

- `((PATIENTCITY)), FL 33000` → address=`FL`, zip_code=`33000`

#### `street_line`  → `address`

A street line: house number, optional direction, 1-4 capitalised words, a street suffix (St, Ave, Rd, Blvd, Dr, Ln, Ct, Way, Pkwy, Hwy, Pl, Ter, Cir, Trl, Sq, Loop, Route …), optional Suite/Apt/Unit/Bldg/Floor. The words must be capitalised so medication sigs ('take 1 tablet by oral route daily') cannot match. 94% precision.

Evaluation: fired 11,683; precision same label 94.3%, same family 94.4%, any model span 94.9%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?<![\w#])(?P<val>\d{1,6}[A-Za-z]?\s+(?:[NSEW]\.?\s+|(?:North|South|East|West)\s+)?(?:[A-Z0-9][A-Za-z0-9'.\-]*\s+){1,4}(?i:St(?:reet)?|Ave(?:nue)?|Rd|Road|Blvd|Boulevard|Dr(?:ive)?|Ln|Lane|Ct|Court|Way|Pkwy|Parkway|Hwy|Highway|Pl(?:ace)?|Ter(?:race)?|Cir(?:cle)?|Trl|Trail|Sq(?:uare)?|Loop|Route|Rte|Pike|Turnpike|Tpke)\.?(?:\s*,?\s*(?i:Suite|Ste|Apt|Unit|#|Bldg|Building|Floor|Fl|Rm|Room)\.?\s*#?\s*[A-Za-z0-9\-]+)?)(?![A-Za-z])
```

Examples (what `find()` returns):

- `at 1234 E Sample Creek Rd, Suite 100 and` → address=`1234 E Sample Creek Rd, Suite 100`
- `1234 MAIN ST, SUITE 100` → address=`1234 MAIN ST, SUITE 100`

#### `po_box`  → `address`

P.O. Box nnn. 81% precision.

Evaluation: fired 348; precision same label 84.2%, same family 84.5%, any model span 85.6%.

Flags: re.IGNORECASE. Value group: `val`.

```text
(?P<val>P\.?\s?O\.?\s?Box\s+\d+)
```

Examples (what `find()` returns):

- `mail to PO Box 1234` → address=`PO Box 1234`

#### `address_labelled`  → `address`

Address / Street / Residence / Home or Mailing address label followed by the rest of the line. 32% precision -- the value is whatever follows to the end of the line; keep only where the other address rules do not fire.

Evaluation: fired 1,804; precision same label 31.7%, same family 32.9%, any model span 39.7%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?<![A-Za-z])(?i:(?:address|addr|street(?:\s+address)?|residence|home\s+address|mailing\s+address))(?![A-Za-z])(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}(?:[:#=\-–]|is|was|of)?(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}(?:[:#=\-](?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8})?(?P<val>(?i:[^<>\n]{5,80}?(?=\s*(?:<|\n|$))))
```

Examples (what `find()` returns):

- `Home Address: 12 Sample Ave<br>` → address=`12 Sample Ave`

#### `zip_labelled`  → `zip_code`

Zip / Zip Code / Postal Code label followed by a 5- or 9-digit ZIP. 100% precision in the sample.

Evaluation: fired 108; precision same label 100.0%, same family 100.0%, any model span 100.0%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?<![A-Za-z])(?i:(?:zip(?:\s*code)?|postal\s*code))(?![A-Za-z])(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}(?:[:#=\-–]|is|was|of)?(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}(?:[:#=\-](?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8})?(?P<val>(?i:\d{5}(?:-\d{4})?(?!\d)))
```

Examples (what `find()` returns):

- `Zip: 48000` → zip_code=`48000`

#### `zip_after_state`  → `zip_code`

A 5- or 9-digit ZIP right after a US state code (…, MI 48000). 92% same-label / 95% family precision.

Evaluation: fired 4,670; precision same label 92.2%, same family 95.3%, any model span 96.3%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?<![A-Za-z0-9])(?:A[LKZR]|C[AOT]|D[EC]|FL|GA|HI|I[DLNA]|K[SY]|LA|M[EDAINSOT]|N[EVHJMYCD]|O[HKR]|PA|RI|S[CD]|T[NX]|UT|V[TA]|W[AVIY]|PR|VI|GU)\.?(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}(?P<val>\d{5}(?:-\d{4})?)(?![\d-])
```

Examples (what `find()` returns):

- `Anytown, MI 48000-1234` → address=`Anytown`, address=`MI`, zip_code=`48000-1234`

#### `location_labelled`  → `location`

Patient Location / Charted Location / Location / Loc / Room / Bed / Ward / Service Dept. / Department label with a colon or table-cell boundary, followed by a short value. 35% same-label / 40% family precision and ~30% recall: most location spans in the corpus are clinic or site names in free text -- lexicon territory.

Evaluation: fired 2,839; precision same label 35.2%, same family 40.0%, any model span 65.4%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?<![A-Za-z])(?i:(?:patient\s+location|charted\s+location|location|loc|room|rm|bed|ward|service\s+dept\.?|service\s+department|clinic\s+site|department))(?:\s*:\s*|\s*(?:</t[hd]>|&lt;/t[hd]&gt;)?\s*(?:<td[^>]*>|&lt;td[^&]*&gt;)\s*)(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;){0,6}(?P<val>[^<>\n,;|]{1,40}?)(?=\s*(?:<|&lt;|\n|,|;|\||$))
```

Examples (what `find()` returns):

- `Patient Location: MS Clinic 3<br>` → location=`MS Clinic 3`
- `<th>Service Dept. <td>Neurology 2` → location=`Neurology 2`

### Hospitals and organizations  (`phi_rules/orgs.py`)

Institutional suffixes (`… Hospital`, `… Medical Center`, `… Clinic`, `… Inc`) and Facility / Employer labels. The model used hospital_name and organization interchangeably for 10k literals; score them as one family.

#### `org_with_suffix`  → `hospital_name`  (label decided per match by the rule's relabel hook)

A capitalised phrase (up to 6 words, 'of/the/and/&/at' allowed) ending in an institutional suffix: Hospital, Medical Center, Health System, Clinic, Institute, Laboratories, Pharmacy, University, Physicians, Associates, Foundation, Inc, LLC, Corp … Corporate suffixes (Inc/LLC/Corp/University/College) relabel to organization. 57% same-label / 66% family precision.

Evaluation: fired 7,220; precision same label 57.3%, same family 66.4%, any model span 67.4%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?<![A-Za-z])(?P<val>[A-Z][A-Za-z&.'\-]*(?:\s+(?:of|the|and|for|&|at)\s+|\s+)(?:[A-Z][A-Za-z&.'\-]*(?:\s+(?:of|the|and|&|at)\s+|\s+)){0,5}(?:Hospital|Medical\s+Cent(?:er|re)|Health\s*(?:care)?\s*System|Healthcare|Clinic|Regional\s+Medical\s+Center|Cancer\s+(?:Center|Institute)|Institute|Laboratories|Pharmacy|University|College|Physicians|Associates|Medical\s+Group|Foundation|Inc\.?|LLC|L\.L\.C\.|Corp(?:oration)?\.?|Co\.|Urgent\s+Care|Family\s+(?:Practice|Medicine)|Medical\s+Associates|Neurology\s+Associates|Health\s+Partners|Medical\s+Practice))(?![A-Za-z])
```

Examples (what `find()` returns):

- `referred to Example General Hospital for` → hospital_name=`Example General Hospital`
- `works at Northwind Widgets Inc. as` → organization=`Northwind Widgets Inc.`

#### `hospital_labelled`  → `hospital_name`

Hospital / Facility / Facility Name / Performing Lab / Performed at / Referring Facility / Institution / Pharmacy label with a colon or cell boundary, followed by a capitalised value to the end of the cell/line. 70% same-label / 77% family precision.

Evaluation: fired 1,953; precision same label 69.8%, same family 77.4%, any model span 82.3%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?<![A-Za-z])(?i:(?:hospital|facility|facility\s+name|performing\s+lab(?:oratory)?|performed\s+at|referring\s+facility|institution|pharmacy(?:\s+name)?))(?:\s*:\s*|\s*(?:</t[hd]>|&lt;/t[hd]&gt;)?\s*(?:<td[^>]*>|&lt;td[^&]*&gt;)\s*)(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;){0,6}(?P<val>[A-Z][^<>&\n,;|]{2,60}?)(?=\s*(?:<|&lt;|\n|,|;|\||$))
```

Examples (what `find()` returns):

- `Facility Name: Example General<br>` → hospital_name=`Example General`

#### `employer_labelled`  → `organization`

Employer Name: / employed by / works at / member of the / affiliated with … followed by a capitalised value. 53% same-label / 60% family precision.

Evaluation: fired 274; precision same label 53.3%, same family 54.4%, any model span 58.0%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?<![A-Za-z])(?i:(?:employer(?:\s+name)?\s*:|employed\s+(?:by|at)|works\s+(?:at|for)|member\s+of\s+the|affiliated\s+with(?:\s+the)?))(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}(?P<val>[A-Z][^<>&\n,;|]{2,60}?)(?=\s*(?:<|&lt;|\n|,|;|\||\.|$))
```

Examples (what `find()` returns):

- `Employer Name : Acme Motors<br>` → organization=`Acme Motors`

### Names: person, doctor, signature  (`phi_rules/names.py`)

The hard class. Anchors (Dr., a credential, Provider:, Signed by:, Mr./Mrs., a relative word, `<given>`) are deterministic; about half of all person_name spans in the corpus have no anchor and need a lexicon or a model.

#### `after_final_column`  → `doctor_name`

Lab-result tables: the ordering clinician in the column after '| Final |'. 82% same-label / 99% family precision.

Evaluation: fired 1,374; precision same label 82.0%, same family 99.1%, any model span 99.1%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
\|\s*Final\s*\|\s*(?P<val>(?:[A-Z]\.?\s+)?(?:(?!(?:DOB|DOD|MRN|Age|Sex|Gender|Date|Phone|Fax|Address|Room|Location|Patient|Provider|Physician|Visit|Encounter|Account|Insurance|Dr|MD|DO|NP|PA|RN|Male|Female|Ph|Tel|Cell|Pager|Email|Signed|Dictated|Printed|Page|Report|Result|Results|Information|Preference|Place|Name|Value|Range|Status|Type|Number|History|Summary|Data|List|Note|Notes|Time|Test|Tests|Order|Orders|Medication|Medications|Diagnosis|Problem|Plan|Assessment|Exam|Vitals|Labs|Lab|Allergies|Allergy|Service|Department|Clinic|Hospital|Unit|Level|Total|Amount|Balance|Due|Payment|Code|Description|Comments|Comment|Reason|Source|Site|Referral|Consult|Progress|Discharge|Admission|Admit|Chief|Complaint|Family|Social|Review|Systems|Present|Illness|The|This|These|That|Your|You|We|Our|Please|Negative|Positive|Normal|Abnormal|Final|Pending|See|Not|None|Yes|Unknown|Other|Same|New|Old|For|And|With|Are|Was|Were|Has|Have|Per|From)(?![A-Za-z]))[A-Z][A-Za-z'\-]{1,24})(?:,?\s+(?:(?!(?:DOB|DOD|MRN|Age|Sex|Gender|Date|Phone|Fax|Address|Room|Location|Patient|Provider|Physician|Visit|Encounter|Account|Insurance|Dr|MD|DO|NP|PA|RN|Male|Female|Ph|Tel|Cell|Pager|Email|Signed|Dictated|Printed|Page|Report|Result|Results|Information|Preference|Place|Name|Value|Range|Status|Type|Number|History|Summary|Data|List|Note|Notes|Time|Test|Tests|Order|Orders|Medication|Medications|Diagnosis|Problem|Plan|Assessment|Exam|Vitals|Labs|Lab|Allergies|Allergy|Service|Department|Clinic|Hospital|Unit|Level|Total|Amount|Balance|Due|Payment|Code|Description|Comments|Comment|Reason|Source|Site|Referral|Consult|Progress|Discharge|Admission|Admit|Chief|Complaint|Family|Social|Review|Systems|Present|Illness|The|This|These|That|Your|You|We|Our|Please|Negative|Positive|Normal|Abnormal|Final|Pending|See|Not|None|Yes|Unknown|Other|Same|New|Old|For|And|With|Are|Was|Were|Has|Have|Per|From)(?![A-Za-z]))(?:[A-Z][A-Za-z'\-]{1,24}|[A-Z]\.?))){0,3})
```

Examples (what `find()` returns):

- `| 2024-01-01 12:00 | Final | Jordan Q Sample` → doctor_name=`Jordan Q Sample`

#### `elem_v_attribute`  → `person_name`

Vendor-XML name parts carried in V= attributes: <GIV V=…/> <FAM V=…/> <MID V=…/>. 74% family precision (these are mostly provider names in the corpus, which the model labelled doctor_name).

Evaluation: fired 2,606; precision same label 9.8%, same family 72.9%, any model span 72.9%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?:<|&lt;)(?P<tag>GIV|FAM|MID|PFX|SFX|given|family|middle|prefix|suffix)\b[^<>&]*?\bV\s*=\s*(?:\"|&quot;)(?P<val>[^\"&]{1,40})(?:\"|&quot;)
```

Examples (what `find()` returns):

- `<person_name><nm><GIV V="Mary"/><FAM V="Jones"/></nm></person_name>` → person_name=`Mary`, person_name=`Jones`

#### `dr_prefix`  → `doctor_name`

'Dr.' or 'Dr' followed by a name (up to four tokens). The title is not part of the value. 81% same-label / 84% family precision.

Evaluation: fired 11,562; precision same label 80.6%, same family 83.6%, any model span 83.9%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?<![A-Za-z])Dr\.?\s+(?P<val>(?:[A-Z]\.?\s+)?(?:(?!(?:DOB|DOD|MRN|Age|Sex|Gender|Date|Phone|Fax|Address|Room|Location|Patient|Provider|Physician|Visit|Encounter|Account|Insurance|Dr|MD|DO|NP|PA|RN|Male|Female|Ph|Tel|Cell|Pager|Email|Signed|Dictated|Printed|Page|Report|Result|Results|Information|Preference|Place|Name|Value|Range|Status|Type|Number|History|Summary|Data|List|Note|Notes|Time|Test|Tests|Order|Orders|Medication|Medications|Diagnosis|Problem|Plan|Assessment|Exam|Vitals|Labs|Lab|Allergies|Allergy|Service|Department|Clinic|Hospital|Unit|Level|Total|Amount|Balance|Due|Payment|Code|Description|Comments|Comment|Reason|Source|Site|Referral|Consult|Progress|Discharge|Admission|Admit|Chief|Complaint|Family|Social|Review|Systems|Present|Illness|The|This|These|That|Your|You|We|Our|Please|Negative|Positive|Normal|Abnormal|Final|Pending|See|Not|None|Yes|Unknown|Other|Same|New|Old|For|And|With|Are|Was|Were|Has|Have|Per|From)(?![A-Za-z]))[A-Z][A-Za-z'\-]{1,24})(?:,?\s+(?:(?!(?:DOB|DOD|MRN|Age|Sex|Gender|Date|Phone|Fax|Address|Room|Location|Patient|Provider|Physician|Visit|Encounter|Account|Insurance|Dr|MD|DO|NP|PA|RN|Male|Female|Ph|Tel|Cell|Pager|Email|Signed|Dictated|Printed|Page|Report|Result|Results|Information|Preference|Place|Name|Value|Range|Status|Type|Number|History|Summary|Data|List|Note|Notes|Time|Test|Tests|Order|Orders|Medication|Medications|Diagnosis|Problem|Plan|Assessment|Exam|Vitals|Labs|Lab|Allergies|Allergy|Service|Department|Clinic|Hospital|Unit|Level|Total|Amount|Balance|Due|Payment|Code|Description|Comments|Comment|Reason|Source|Site|Referral|Consult|Progress|Discharge|Admission|Admit|Chief|Complaint|Family|Social|Review|Systems|Present|Illness|The|This|These|That|Your|You|We|Our|Please|Negative|Positive|Normal|Abnormal|Final|Pending|See|Not|None|Yes|Unknown|Other|Same|New|Old|For|And|With|Are|Was|Were|Has|Have|Per|From)(?![A-Za-z]))(?:[A-Z][A-Za-z'\-]{1,24}|[A-Z]\.?))){0,3})
```

Examples (what `find()` returns):

- `seen by Dr. John Smith today` → doctor_name=`John Smith`

#### `name_with_credential`  → `doctor_name`

A name followed by a clinical credential: MD, DO, NP, PA(-C), RN, LPN, CNA, PhD, DPM, FACP, MBBS, APRN, CRNP, DDS, OD, PsyD (dots optional). The credential is not part of the value. 57% same-label / 91% family precision (the model often labelled these signature_block).

Evaluation: fired 38,986; precision same label 56.6%, same family 91.4%, any model span 92.5%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?<![A-Za-z])(?P<val>(?:[A-Z]\.?\s+)?(?:(?!(?:DOB|DOD|MRN|Age|Sex|Gender|Date|Phone|Fax|Address|Room|Location|Patient|Provider|Physician|Visit|Encounter|Account|Insurance|Dr|MD|DO|NP|PA|RN|Male|Female|Ph|Tel|Cell|Pager|Email|Signed|Dictated|Printed|Page|Report|Result|Results|Information|Preference|Place|Name|Value|Range|Status|Type|Number|History|Summary|Data|List|Note|Notes|Time|Test|Tests|Order|Orders|Medication|Medications|Diagnosis|Problem|Plan|Assessment|Exam|Vitals|Labs|Lab|Allergies|Allergy|Service|Department|Clinic|Hospital|Unit|Level|Total|Amount|Balance|Due|Payment|Code|Description|Comments|Comment|Reason|Source|Site|Referral|Consult|Progress|Discharge|Admission|Admit|Chief|Complaint|Family|Social|Review|Systems|Present|Illness|The|This|These|That|Your|You|We|Our|Please|Negative|Positive|Normal|Abnormal|Final|Pending|See|Not|None|Yes|Unknown|Other|Same|New|Old|For|And|With|Are|Was|Were|Has|Have|Per|From)(?![A-Za-z]))[A-Z][A-Za-z'\-]{1,24})(?:,?\s+(?:(?!(?:DOB|DOD|MRN|Age|Sex|Gender|Date|Phone|Fax|Address|Room|Location|Patient|Provider|Physician|Visit|Encounter|Account|Insurance|Dr|MD|DO|NP|PA|RN|Male|Female|Ph|Tel|Cell|Pager|Email|Signed|Dictated|Printed|Page|Report|Result|Results|Information|Preference|Place|Name|Value|Range|Status|Type|Number|History|Summary|Data|List|Note|Notes|Time|Test|Tests|Order|Orders|Medication|Medications|Diagnosis|Problem|Plan|Assessment|Exam|Vitals|Labs|Lab|Allergies|Allergy|Service|Department|Clinic|Hospital|Unit|Level|Total|Amount|Balance|Due|Payment|Code|Description|Comments|Comment|Reason|Source|Site|Referral|Consult|Progress|Discharge|Admission|Admit|Chief|Complaint|Family|Social|Review|Systems|Present|Illness|The|This|These|That|Your|You|We|Our|Please|Negative|Positive|Normal|Abnormal|Final|Pending|See|Not|None|Yes|Unknown|Other|Same|New|Old|For|And|With|Are|Was|Were|Has|Have|Per|From)(?![A-Za-z]))(?:[A-Z][A-Za-z'\-]{1,24}|[A-Z]\.?))){0,3})(?:\s*,\s*|\s+)(?:M\.?D\.?|D\.?O\.?|N\.?P\.?|P\.?A\.?(?:-C)?|R\.?N\.?|L\.?P\.?N\.?|C\.?N\.?A\.?|Ph\.?D\.?|D\.?P\.?M\.?|F\.?A\.?C\.?P\.?|M\.?B\.?B\.?S\.?|A\.?P\.?R\.?N\.?|C\.?R\.?N\.?P\.?|D\.?D\.?S\.?|O\.?D\.?|Psy\.?D\.?)(?![A-Za-z])
```

Examples (what `find()` returns):

- `Ordered by Jane Q. Public, MD on` → doctor_name=`Jane Q. Public`

#### `provider_labelled`  → `doctor_name`

Provider / Physician / Ordering Provider / Referring Physician / PCP / Surgeon / Laboratory Director … with a colon or table-cell boundary, followed by a name (optional Dr.). 68% same-label / 86% family precision.

Evaluation: fired 4,189; precision same label 67.5%, same family 86.8%, any model span 89.1%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?<![A-Za-z])(?i:(?:(?:ordering|referring|attending|treating|consulting|requesting|primary\s+care|responsible|admitting|rendering|supervising|performing|interpreting|reading)\s+(?:provider|physician|md|doctor|practitioner|clinician)|provider|physician|PCP|surgeon|pathologist|radiologist|neurologist|cardiologist|laboratory\s+director|medical\s+director))(?:\s*:\s*|\s*(?:</t[hd]>|&lt;/t[hd]&gt;)?\s*(?:<td[^>]*>|&lt;td[^&]*&gt;)\s*)(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;){0,6}(?:Dr\.?\s+)?(?P<val>(?:[A-Z]\.?\s+)?(?:(?!(?:DOB|DOD|MRN|Age|Sex|Gender|Date|Phone|Fax|Address|Room|Location|Patient|Provider|Physician|Visit|Encounter|Account|Insurance|Dr|MD|DO|NP|PA|RN|Male|Female|Ph|Tel|Cell|Pager|Email|Signed|Dictated|Printed|Page|Report|Result|Results|Information|Preference|Place|Name|Value|Range|Status|Type|Number|History|Summary|Data|List|Note|Notes|Time|Test|Tests|Order|Orders|Medication|Medications|Diagnosis|Problem|Plan|Assessment|Exam|Vitals|Labs|Lab|Allergies|Allergy|Service|Department|Clinic|Hospital|Unit|Level|Total|Amount|Balance|Due|Payment|Code|Description|Comments|Comment|Reason|Source|Site|Referral|Consult|Progress|Discharge|Admission|Admit|Chief|Complaint|Family|Social|Review|Systems|Present|Illness|The|This|These|That|Your|You|We|Our|Please|Negative|Positive|Normal|Abnormal|Final|Pending|See|Not|None|Yes|Unknown|Other|Same|New|Old|For|And|With|Are|Was|Were|Has|Have|Per|From)(?![A-Za-z]))[A-Z][A-Za-z'\-]{1,24})(?:,?\s+(?:(?!(?:DOB|DOD|MRN|Age|Sex|Gender|Date|Phone|Fax|Address|Room|Location|Patient|Provider|Physician|Visit|Encounter|Account|Insurance|Dr|MD|DO|NP|PA|RN|Male|Female|Ph|Tel|Cell|Pager|Email|Signed|Dictated|Printed|Page|Report|Result|Results|Information|Preference|Place|Name|Value|Range|Status|Type|Number|History|Summary|Data|List|Note|Notes|Time|Test|Tests|Order|Orders|Medication|Medications|Diagnosis|Problem|Plan|Assessment|Exam|Vitals|Labs|Lab|Allergies|Allergy|Service|Department|Clinic|Hospital|Unit|Level|Total|Amount|Balance|Due|Payment|Code|Description|Comments|Comment|Reason|Source|Site|Referral|Consult|Progress|Discharge|Admission|Admit|Chief|Complaint|Family|Social|Review|Systems|Present|Illness|The|This|These|That|Your|You|We|Our|Please|Negative|Positive|Normal|Abnormal|Final|Pending|See|Not|None|Yes|Unknown|Other|Same|New|Old|For|And|With|Are|Was|Were|Has|Have|Per|From)(?![A-Za-z]))(?:[A-Z][A-Za-z'\-]{1,24}|[A-Z]\.?))){0,3})
```

Examples (what `find()` returns):

- `<th>Ordering Provider</th><td>Casey J Sampleton</td>` → doctor_name=`Casey J Sampleton`

#### `by_verb_name`  → `doctor_name`

'performed by / read by / seen by / ordered by …' followed by a name of at least two tokens. 40% same-label / 81% family precision (the model labels these doctor, person or signature depending on context).

Evaluation: fired 818; precision same label 39.5%, same family 79.5%, any model span 89.9%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?<![A-Za-z])(?i:(?:performed|read|interpreted|reviewed|ordered|examined|requested|seen|evaluated|treated|referred|followed)\s+by)(?![A-Za-z])(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}[:#=\-\u2013]?(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}(?:[:#=\-](?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8})?(?:Dr\.?\s+)?(?P<val>(?:(?!(?:DOB|DOD|MRN|Age|Sex|Gender|Date|Phone|Fax|Address|Room|Location|Patient|Provider|Physician|Visit|Encounter|Account|Insurance|Dr|MD|DO|NP|PA|RN|Male|Female|Ph|Tel|Cell|Pager|Email|Signed|Dictated|Printed|Page|Report|Result|Results|Information|Preference|Place|Name|Value|Range|Status|Type|Number|History|Summary|Data|List|Note|Notes|Time|Test|Tests|Order|Orders|Medication|Medications|Diagnosis|Problem|Plan|Assessment|Exam|Vitals|Labs|Lab|Allergies|Allergy|Service|Department|Clinic|Hospital|Unit|Level|Total|Amount|Balance|Due|Payment|Code|Description|Comments|Comment|Reason|Source|Site|Referral|Consult|Progress|Discharge|Admission|Admit|Chief|Complaint|Family|Social|Review|Systems|Present|Illness|The|This|These|That|Your|You|We|Our|Please|Negative|Positive|Normal|Abnormal|Final|Pending|See|Not|None|Yes|Unknown|Other|Same|New|Old|For|And|With|Are|Was|Were|Has|Have|Per|From)(?![A-Za-z]))[A-Z][A-Za-z'\-]{1,24})(?:,?\s+(?:(?!(?:DOB|DOD|MRN|Age|Sex|Gender|Date|Phone|Fax|Address|Room|Location|Patient|Provider|Physician|Visit|Encounter|Account|Insurance|Dr|MD|DO|NP|PA|RN|Male|Female|Ph|Tel|Cell|Pager|Email|Signed|Dictated|Printed|Page|Report|Result|Results|Information|Preference|Place|Name|Value|Range|Status|Type|Number|History|Summary|Data|List|Note|Notes|Time|Test|Tests|Order|Orders|Medication|Medications|Diagnosis|Problem|Plan|Assessment|Exam|Vitals|Labs|Lab|Allergies|Allergy|Service|Department|Clinic|Hospital|Unit|Level|Total|Amount|Balance|Due|Payment|Code|Description|Comments|Comment|Reason|Source|Site|Referral|Consult|Progress|Discharge|Admission|Admit|Chief|Complaint|Family|Social|Review|Systems|Present|Illness|The|This|These|That|Your|You|We|Our|Please|Negative|Positive|Normal|Abnormal|Final|Pending|See|Not|None|Yes|Unknown|Other|Same|New|Old|For|And|With|Are|Was|Were|Has|Have|Per|From)(?![A-Za-z]))(?:[A-Z][A-Za-z'\-]{1,24}|[A-Z]\.?))){1,3})
```

Examples (what `find()` returns):

- `Study performed by Jordan Q Sample and` → doctor_name=`Jordan Q Sample`

#### `signature_labelled`  → `signature_block`

Electronically signed by / Signed / Dictated by / Transcribed by / Printed by / Entered by / cc: / Sincerely … followed by a name with an optional credential (the credential IS part of a signature block). 56% same-label / 79% family precision.

Evaluation: fired 10,442; precision same label 56.4%, same family 79.3%, any model span 79.4%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?<![A-Za-z])(?i:(?:electronically\s+signed\s+by|e-?signed\s+by|signed\s+by|signed|dictated\s+by|transcribed\s+by|printed\s+by|entered\s+by|authenticated\s+by|verified\s+by|approved\s+by|recorded\s+by|attested\s+by|completed\s+by|documented\s+by|scribed\s+by|cc|sincerely|regards|respectfully|thank\s+you))(?![A-Za-z])(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}[:#=\-\u2013]?(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}(?:[:#=\-](?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8})?(?:Dr\.?\s+)?(?P<val>(?:[A-Z]\.?\s+)?(?:(?!(?:DOB|DOD|MRN|Age|Sex|Gender|Date|Phone|Fax|Address|Room|Location|Patient|Provider|Physician|Visit|Encounter|Account|Insurance|Dr|MD|DO|NP|PA|RN|Male|Female|Ph|Tel|Cell|Pager|Email|Signed|Dictated|Printed|Page|Report|Result|Results|Information|Preference|Place|Name|Value|Range|Status|Type|Number|History|Summary|Data|List|Note|Notes|Time|Test|Tests|Order|Orders|Medication|Medications|Diagnosis|Problem|Plan|Assessment|Exam|Vitals|Labs|Lab|Allergies|Allergy|Service|Department|Clinic|Hospital|Unit|Level|Total|Amount|Balance|Due|Payment|Code|Description|Comments|Comment|Reason|Source|Site|Referral|Consult|Progress|Discharge|Admission|Admit|Chief|Complaint|Family|Social|Review|Systems|Present|Illness|The|This|These|That|Your|You|We|Our|Please|Negative|Positive|Normal|Abnormal|Final|Pending|See|Not|None|Yes|Unknown|Other|Same|New|Old|For|And|With|Are|Was|Were|Has|Have|Per|From)(?![A-Za-z]))[A-Z][A-Za-z'\-]{1,24})(?:,?\s+(?:(?!(?:DOB|DOD|MRN|Age|Sex|Gender|Date|Phone|Fax|Address|Room|Location|Patient|Provider|Physician|Visit|Encounter|Account|Insurance|Dr|MD|DO|NP|PA|RN|Male|Female|Ph|Tel|Cell|Pager|Email|Signed|Dictated|Printed|Page|Report|Result|Results|Information|Preference|Place|Name|Value|Range|Status|Type|Number|History|Summary|Data|List|Note|Notes|Time|Test|Tests|Order|Orders|Medication|Medications|Diagnosis|Problem|Plan|Assessment|Exam|Vitals|Labs|Lab|Allergies|Allergy|Service|Department|Clinic|Hospital|Unit|Level|Total|Amount|Balance|Due|Payment|Code|Description|Comments|Comment|Reason|Source|Site|Referral|Consult|Progress|Discharge|Admission|Admit|Chief|Complaint|Family|Social|Review|Systems|Present|Illness|The|This|These|That|Your|You|We|Our|Please|Negative|Positive|Normal|Abnormal|Final|Pending|See|Not|None|Yes|Unknown|Other|Same|New|Old|For|And|With|Are|Was|Were|Has|Have|Per|From)(?![A-Za-z]))(?:[A-Z][A-Za-z'\-]{1,24}|[A-Z]\.?))){0,3}(?:(?:\s*,\s*|\s+)(?:M\.?D\.?|D\.?O\.?|N\.?P\.?|P\.?A\.?(?:-C)?|R\.?N\.?|L\.?P\.?N\.?|C\.?N\.?A\.?|Ph\.?D\.?|D\.?P\.?M\.?|F\.?A\.?C\.?P\.?|M\.?B\.?B\.?S\.?|A\.?P\.?R\.?N\.?|C\.?R\.?N\.?P\.?|D\.?D\.?S\.?|O\.?D\.?|Psy\.?D\.?))?)
```

Examples (what `find()` returns):

- `ELECTRONICALLY SIGNED BY: JOHNSON, MARY` → signature_block=`JOHNSON, MARY`
- `Sincerely, Jane Q. Public, MD` → doctor_name=`Sincerely, Jane Q. Public`

#### `usersig_login`  → `signature_block`

EHR user logins at the end of a cell or line: 2-12 lowercase letters + 1-3 digits, optionally '.dddd' (the census shape 'aaaaaaaa99.999'). 70% precision.

Evaluation: fired 377; precision same label 69.8%, same family 70.3%, any model span 74.0%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?<![A-Za-z0-9])(?P<val>[a-z]{2,12}\d{1,3}(?:\.\d{1,4})?)(?=\s*(?:</|\[|\n|$))
```

Examples (what `find()` returns):

- `Entered by asample12.345</td>` → signature_block=`asample12.345`

#### `patient_labelled`  → `person_name`

Patient Name / Name / Patient / Guarantor / Mother / Spouse / Emergency Contact … with a colon or table-cell boundary followed by a name. 48% same-label / 56% family precision -- 'Name:' also labels test names.

Evaluation: fired 3,591; precision same label 48.4%, same family 55.8%, any model span 59.7%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?<![A-Za-z])(?i:(?:patient(?:'s)?\s+name|pt\.?\s+name|name|patient|pt|client|resident|member\s+name|guarantor(?:\s+name)?|mother|father|wife|husband|daughter|son|spouse|partner|caregiver|guardian|emergency\s+contact|contact(?:\s+person)?|next\s+of\s+kin|informant))(?:\s*:\s*|\s*(?:</t[hd]>|&lt;/t[hd]&gt;)?\s*(?:<td[^>]*>|&lt;td[^&]*&gt;)\s*)(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;){0,6}(?P<val>(?:[A-Z]\.?\s+)?(?:(?!(?:DOB|DOD|MRN|Age|Sex|Gender|Date|Phone|Fax|Address|Room|Location|Patient|Provider|Physician|Visit|Encounter|Account|Insurance|Dr|MD|DO|NP|PA|RN|Male|Female|Ph|Tel|Cell|Pager|Email|Signed|Dictated|Printed|Page|Report|Result|Results|Information|Preference|Place|Name|Value|Range|Status|Type|Number|History|Summary|Data|List|Note|Notes|Time|Test|Tests|Order|Orders|Medication|Medications|Diagnosis|Problem|Plan|Assessment|Exam|Vitals|Labs|Lab|Allergies|Allergy|Service|Department|Clinic|Hospital|Unit|Level|Total|Amount|Balance|Due|Payment|Code|Description|Comments|Comment|Reason|Source|Site|Referral|Consult|Progress|Discharge|Admission|Admit|Chief|Complaint|Family|Social|Review|Systems|Present|Illness|The|This|These|That|Your|You|We|Our|Please|Negative|Positive|Normal|Abnormal|Final|Pending|See|Not|None|Yes|Unknown|Other|Same|New|Old|For|And|With|Are|Was|Were|Has|Have|Per|From)(?![A-Za-z]))[A-Z][A-Za-z'\-]{1,24})(?:,?\s+(?:(?!(?:DOB|DOD|MRN|Age|Sex|Gender|Date|Phone|Fax|Address|Room|Location|Patient|Provider|Physician|Visit|Encounter|Account|Insurance|Dr|MD|DO|NP|PA|RN|Male|Female|Ph|Tel|Cell|Pager|Email|Signed|Dictated|Printed|Page|Report|Result|Results|Information|Preference|Place|Name|Value|Range|Status|Type|Number|History|Summary|Data|List|Note|Notes|Time|Test|Tests|Order|Orders|Medication|Medications|Diagnosis|Problem|Plan|Assessment|Exam|Vitals|Labs|Lab|Allergies|Allergy|Service|Department|Clinic|Hospital|Unit|Level|Total|Amount|Balance|Due|Payment|Code|Description|Comments|Comment|Reason|Source|Site|Referral|Consult|Progress|Discharge|Admission|Admit|Chief|Complaint|Family|Social|Review|Systems|Present|Illness|The|This|These|That|Your|You|We|Our|Please|Negative|Positive|Normal|Abnormal|Final|Pending|See|Not|None|Yes|Unknown|Other|Same|New|Old|For|And|With|Are|Was|Were|Has|Have|Per|From)(?![A-Za-z]))(?:[A-Z][A-Za-z'\-]{1,24}|[A-Z]\.?))){0,3})
```

Examples (what `find()` returns):

- `Patient Name: Mary Ann Jones DOB` → person_name=`Mary Ann Jones`

#### `relative_named`  → `person_name`

'his wife Mary', 'her daughter, Anne Smith': a relative word followed by one or two capitalised names. 89% precision.

Evaluation: fired 303; precision same label 88.8%, same family 89.1%, any model span 89.8%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?<![A-Za-z])(?i:(?:his|her|their)\s+(?:mother|father|wife|husband|daughter|son|spouse|partner|caregiver|sister|brother|friend|neighbor|niece|nephew|granddaughter|grandson|aunt|uncle))(?:,|\s+named|\s+is)?\s+(?P<val>(?:(?!(?:DOB|DOD|MRN|Age|Sex|Gender|Date|Phone|Fax|Address|Room|Location|Patient|Provider|Physician|Visit|Encounter|Account|Insurance|Dr|MD|DO|NP|PA|RN|Male|Female|Ph|Tel|Cell|Pager|Email|Signed|Dictated|Printed|Page|Report|Result|Results|Information|Preference|Place|Name|Value|Range|Status|Type|Number|History|Summary|Data|List|Note|Notes|Time|Test|Tests|Order|Orders|Medication|Medications|Diagnosis|Problem|Plan|Assessment|Exam|Vitals|Labs|Lab|Allergies|Allergy|Service|Department|Clinic|Hospital|Unit|Level|Total|Amount|Balance|Due|Payment|Code|Description|Comments|Comment|Reason|Source|Site|Referral|Consult|Progress|Discharge|Admission|Admit|Chief|Complaint|Family|Social|Review|Systems|Present|Illness|The|This|These|That|Your|You|We|Our|Please|Negative|Positive|Normal|Abnormal|Final|Pending|See|Not|None|Yes|Unknown|Other|Same|New|Old|For|And|With|Are|Was|Were|Has|Have|Per|From)(?![A-Za-z]))[A-Z][A-Za-z'\-]{1,24})(?:\s+(?:(?!(?:DOB|DOD|MRN|Age|Sex|Gender|Date|Phone|Fax|Address|Room|Location|Patient|Provider|Physician|Visit|Encounter|Account|Insurance|Dr|MD|DO|NP|PA|RN|Male|Female|Ph|Tel|Cell|Pager|Email|Signed|Dictated|Printed|Page|Report|Result|Results|Information|Preference|Place|Name|Value|Range|Status|Type|Number|History|Summary|Data|List|Note|Notes|Time|Test|Tests|Order|Orders|Medication|Medications|Diagnosis|Problem|Plan|Assessment|Exam|Vitals|Labs|Lab|Allergies|Allergy|Service|Department|Clinic|Hospital|Unit|Level|Total|Amount|Balance|Due|Payment|Code|Description|Comments|Comment|Reason|Source|Site|Referral|Consult|Progress|Discharge|Admission|Admit|Chief|Complaint|Family|Social|Review|Systems|Present|Illness|The|This|These|That|Your|You|We|Our|Please|Negative|Positive|Normal|Abnormal|Final|Pending|See|Not|None|Yes|Unknown|Other|Same|New|Old|For|And|With|Are|Was|Were|Has|Have|Per|From)(?![A-Za-z]))[A-Z][A-Za-z'\-]{1,24}))?)
```

Examples (what `find()` returns):

- `accompanied by his wife Mary Jones today` → person_name=`Mary Jones`

#### `honorific`  → `person_name`

Mr. / Mrs. / Ms. / Miss / Mx followed by a name. 97% precision.

Evaluation: fired 2,447; precision same label 96.8%, same family 97.2%, any model span 97.2%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?<![A-Za-z])(?:Mr|Mrs|Ms|Miss|Mx)\.?\s+(?P<val>(?:[A-Z]\.?\s+)?(?:(?!(?:DOB|DOD|MRN|Age|Sex|Gender|Date|Phone|Fax|Address|Room|Location|Patient|Provider|Physician|Visit|Encounter|Account|Insurance|Dr|MD|DO|NP|PA|RN|Male|Female|Ph|Tel|Cell|Pager|Email|Signed|Dictated|Printed|Page|Report|Result|Results|Information|Preference|Place|Name|Value|Range|Status|Type|Number|History|Summary|Data|List|Note|Notes|Time|Test|Tests|Order|Orders|Medication|Medications|Diagnosis|Problem|Plan|Assessment|Exam|Vitals|Labs|Lab|Allergies|Allergy|Service|Department|Clinic|Hospital|Unit|Level|Total|Amount|Balance|Due|Payment|Code|Description|Comments|Comment|Reason|Source|Site|Referral|Consult|Progress|Discharge|Admission|Admit|Chief|Complaint|Family|Social|Review|Systems|Present|Illness|The|This|These|That|Your|You|We|Our|Please|Negative|Positive|Normal|Abnormal|Final|Pending|See|Not|None|Yes|Unknown|Other|Same|New|Old|For|And|With|Are|Was|Were|Has|Have|Per|From)(?![A-Za-z]))[A-Z][A-Za-z'\-]{1,24})(?:,?\s+(?:(?!(?:DOB|DOD|MRN|Age|Sex|Gender|Date|Phone|Fax|Address|Room|Location|Patient|Provider|Physician|Visit|Encounter|Account|Insurance|Dr|MD|DO|NP|PA|RN|Male|Female|Ph|Tel|Cell|Pager|Email|Signed|Dictated|Printed|Page|Report|Result|Results|Information|Preference|Place|Name|Value|Range|Status|Type|Number|History|Summary|Data|List|Note|Notes|Time|Test|Tests|Order|Orders|Medication|Medications|Diagnosis|Problem|Plan|Assessment|Exam|Vitals|Labs|Lab|Allergies|Allergy|Service|Department|Clinic|Hospital|Unit|Level|Total|Amount|Balance|Due|Payment|Code|Description|Comments|Comment|Reason|Source|Site|Referral|Consult|Progress|Discharge|Admission|Admit|Chief|Complaint|Family|Social|Review|Systems|Present|Illness|The|This|These|That|Your|You|We|Our|Please|Negative|Positive|Normal|Abnormal|Final|Pending|See|Not|None|Yes|Unknown|Other|Same|New|Old|For|And|With|Are|Was|Were|Has|Have|Per|From)(?![A-Za-z]))(?:[A-Z][A-Za-z'\-]{1,24}|[A-Z]\.?))){0,3})
```

Examples (what `find()` returns):

- `Mr. Robert Brown reports` → person_name=`Robert Brown`

#### `salutation`  → `person_name`

Dear / Hi / Hello / RE: followed by a name (letters and portal messages). 42% same-label / 48% family precision.

Evaluation: fired 270; precision same label 42.2%, same family 49.6%, any model span 50.4%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?<![A-Za-z])(?:Dear|Hi|Hello|Hey|RE|Re)[:,]?\s+(?P<val>(?:[A-Z]\.?\s+)?(?:(?!(?:DOB|DOD|MRN|Age|Sex|Gender|Date|Phone|Fax|Address|Room|Location|Patient|Provider|Physician|Visit|Encounter|Account|Insurance|Dr|MD|DO|NP|PA|RN|Male|Female|Ph|Tel|Cell|Pager|Email|Signed|Dictated|Printed|Page|Report|Result|Results|Information|Preference|Place|Name|Value|Range|Status|Type|Number|History|Summary|Data|List|Note|Notes|Time|Test|Tests|Order|Orders|Medication|Medications|Diagnosis|Problem|Plan|Assessment|Exam|Vitals|Labs|Lab|Allergies|Allergy|Service|Department|Clinic|Hospital|Unit|Level|Total|Amount|Balance|Due|Payment|Code|Description|Comments|Comment|Reason|Source|Site|Referral|Consult|Progress|Discharge|Admission|Admit|Chief|Complaint|Family|Social|Review|Systems|Present|Illness|The|This|These|That|Your|You|We|Our|Please|Negative|Positive|Normal|Abnormal|Final|Pending|See|Not|None|Yes|Unknown|Other|Same|New|Old|For|And|With|Are|Was|Were|Has|Have|Per|From)(?![A-Za-z]))[A-Z][A-Za-z'\-]{1,24})(?:,?\s+(?:(?!(?:DOB|DOD|MRN|Age|Sex|Gender|Date|Phone|Fax|Address|Room|Location|Patient|Provider|Physician|Visit|Encounter|Account|Insurance|Dr|MD|DO|NP|PA|RN|Male|Female|Ph|Tel|Cell|Pager|Email|Signed|Dictated|Printed|Page|Report|Result|Results|Information|Preference|Place|Name|Value|Range|Status|Type|Number|History|Summary|Data|List|Note|Notes|Time|Test|Tests|Order|Orders|Medication|Medications|Diagnosis|Problem|Plan|Assessment|Exam|Vitals|Labs|Lab|Allergies|Allergy|Service|Department|Clinic|Hospital|Unit|Level|Total|Amount|Balance|Due|Payment|Code|Description|Comments|Comment|Reason|Source|Site|Referral|Consult|Progress|Discharge|Admission|Admit|Chief|Complaint|Family|Social|Review|Systems|Present|Illness|The|This|These|That|Your|You|We|Our|Please|Negative|Positive|Normal|Abnormal|Final|Pending|See|Not|None|Yes|Unknown|Other|Same|New|Old|For|And|With|Are|Was|Were|Has|Have|Per|From)(?![A-Za-z]))(?:[A-Z][A-Za-z'\-]{1,24}|[A-Z]\.?))){0,3})
```

Examples (what `find()` returns):

- `Dear John Smith,` → person_name=`John Smith`

#### `after_upstream_name_tokens`  → `person_name`

Corpus-specific: the upstream de-identifier masked the first and last name tokens and left a middle name or suffix after them ('((PATIENT_NAME)), ((PATIENT_NAME)) Marie'). 37% precision -- the reference model was inconsistent on trailing initials.

Evaluation: fired 987; precision same label 36.8%, same family 36.8%, any model span 38.4%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
\(\((?:PATIENT|Patient)_?(?:NAME|Name)\)\)(?:\s*,?\s*\(\((?:PATIENT|Patient)_?(?:NAME|Name)\)\))+\s+(?P<val>(?:(?!(?:DOB|DOD|MRN|Age|Sex|Gender|Date|Phone|Fax|Address|Room|Location|Patient|Provider|Physician|Visit|Encounter|Account|Insurance|Dr|MD|DO|NP|PA|RN|Male|Female|Ph|Tel|Cell|Pager|Email|Signed|Dictated|Printed|Page|Report|Result|Results|Information|Preference|Place|Name|Value|Range|Status|Type|Number|History|Summary|Data|List|Note|Notes|Time|Test|Tests|Order|Orders|Medication|Medications|Diagnosis|Problem|Plan|Assessment|Exam|Vitals|Labs|Lab|Allergies|Allergy|Service|Department|Clinic|Hospital|Unit|Level|Total|Amount|Balance|Due|Payment|Code|Description|Comments|Comment|Reason|Source|Site|Referral|Consult|Progress|Discharge|Admission|Admit|Chief|Complaint|Family|Social|Review|Systems|Present|Illness|The|This|These|That|Your|You|We|Our|Please|Negative|Positive|Normal|Abnormal|Final|Pending|See|Not|None|Yes|Unknown|Other|Same|New|Old|For|And|With|Are|Was|Were|Has|Have|Per|From)(?![A-Za-z]))[A-Z][A-Za-z'\-]{1,24}))(?![A-Za-z])
```

Examples (what `find()` returns):

- `((PATIENT_NAME)), ((PATIENT_NAME)) Marie DOB` → person_name=`Marie`

#### `xml_name_parts`  → `person_name`

CCDA / vendor name parts as element text: <given>Mary</given><family>Jones</family>. 0/509 hits in the evaluation sample because those values were already upstream placeholders in this corpus; kept for CCDA inputs.

Evaluation: fired 509; precision same label 0.0%, same family 0.0%, any model span 0.0%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
<(?:given|family|prefix|suffix|GIV|FAM|MID|firstname|lastname|middlename)\b[^>]*>\s*(?P<val>[^<]{1,40}?)\s*</
```

Examples (what `find()` returns):

- `<given>Mary</given><family>Jones</family>` → person_name=`Mary`, person_name=`Jones`

### Structured markup (key decides the label)  (`phi_rules/markup.py`)

In XML, CCDA, vendor exports and escaped HTML the attribute / element / JSON KEY decides the label. One key-to-label map recovered 60-99% of every label in the progressnotes exports.

#### `json_by_name`  → `identified_number`  (label decided per match by the rule's relabel hook)

A JSON string field: the KEY decides the label via the key-to-label map (e.g. "CREATEDBY" -> signature_block, "PATIENTID" -> identified_number). Keys that map to nothing are ignored.

Evaluation: fired 315; precision same label 98.1%, same family 98.1%, any model span 98.1%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
\"(?P<attr>[A-Za-z_][\w.-]{1,40})\"\s*:\s*\"(?P<val>[^\"]{1,80})\"
```

Examples (what `find()` returns):

- `{"SOURCE":"backfill","CREATEDBY":"asample","PATIENTID":"884"}` → signature_block=`asample`, identified_number=`884`

#### `attr_by_name`  → `identified_number`  (label decided per match by the rule's relabel hook)

An XML/HTML attribute (raw or HTML-escaped quotes): the attribute NAME decides the label -- PharmacyCity= -> address, PharmacyPhone= -> phone, DOB= -> date, orderingmdid= -> identified_number, CreatedUserName= -> signature_block. Presentational attributes, structural ids, enum/boolean values and system accounts are skipped. This is the single highest-yield rule on vendor XML; its precision against the reference model is ~43% only because the model itself redacted the same keys inconsistently.

Evaluation: fired 708,918; precision same label 40.3%, same family 42.8%, any model span 43.4%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?<![\w.-])(?P<attr>[A-Za-z_][\w.:-]{1,40}#?)\s*=\s*(?:\"|&quot;|')(?P<val>[^\"'&<>]{1,80}?)(?:\"|&quot;|')
```

Examples (what `find()` returns):

- `<Rx PharmacyCity="Anytown" PharmacyState="MI" PharmacyZip="48000" PharmacyPhone="5555551212" orderingmdid="4471" CreatedBy="3" CreatedUserName="asample"/>` → address=`Anytown`, address=`MI`, zip_code=`48000`, phone=`5555551212`, identified_number=`4471`, identified_number=`3`, signature_block=`asample`

#### `elem_by_name`  → `identified_number`  (label decided per match by the rule's relabel hook)

A leaf XML element (raw or escaped): the tag NAME decides the label -- <encounterID>, <HospitalName>, <doctor>, <DOB>, <PharmacyFax>. Same key map and skips as attr_by_name; ~92% precision.

Evaluation: fired 55,888; precision same label 91.7%, same family 92.2%, any model span 92.2%.

Flags: none (case handled inside the pattern with `(?i:…)`). Value group: `val`.

```text
(?:<|&lt;)(?P<tag>[A-Za-z_][\w.:-]{1,40}#?)(?:\s[^<>&]*?)?(?:>|&gt;)\s*(?P<val>[^<>&]{1,80}?)\s*(?:<|&lt;)/(?P=tag)(?:>|&gt;)
```

Examples (what `find()` returns):

- `<encounterID>88213</encounterID><HospitalName>Example General</HospitalName><doctor>Jordan Q Sample</doctor>` → identified_number=`88213`, hospital_name=`Example General`, doctor_name=`Jordan Q Sample`
- `&lt;DOB&gt;1950-03-04&lt;/DOB&gt;` → date=`1950-03-04`
<!-- END GENERATED: rules -->

## Structured markup: the key-to-label map

<!-- BEGIN GENERATED: key-mapping -->
The key (attribute name, element name or JSON key) is lowercased, `-` removed, `:` → `_`, trailing `#`/digits dropped, then:

1. keys in `PRESENTATIONAL`, keys shorter than 2 characters, and keys matching `STRUCTURAL_KEYS` → not PHI;
2. an age key (`age`, `patientage`, …) → `age_90_plus` if the value is ≥ 90, else not PHI;
3. the first matching row below decides the label, subject to a value-shape check (phones need 7 digits, ZIPs `ddddd(-dddd)`, dates a 4-digit year, names/places a letter; a numeric value under a user/created-by key becomes `identified_number`).

| key regex (search on the normalised key) | label |
|---|---|
| `(?:phone|tel(?:ephone)?|mobile|cell|pager)` | phone |
| `fax` | fax |
| `(?:zip|postal)` | zip_code |
| `(?:city|state|county|address|addr|street|country)` | address |
| `(?:dob|birth|dod|death)` | date |
| `(?:e-?mail)` | email |
| `(?:url|website|web)` | url |
| `(?:user_?name|userid|user_?id|login|createdby|changedby|modifiedby|enteredby|signedby|author)` | signature_block |
| `(?:pharmacy|facility|hospital|clinic|organi[sz]ation|employer|practice|institution|lab(?:oratory)?)(?:.*name)?$` | hospital_name |
| `(?:doctor|physician|provider|prescriber|ordering|referring|attending|md|surgeon|pcp)(?:.*name)?$` | doctor_name |
| `^(?:f|l|m)name$|(?:first|last|given|family|middle|sur|full|patient|pt|guarantor|spouse|contact|person|member|display|nick|maiden)_?name$|^(?:giv|fam|mid|pfx|sfx)$` | person_name |
| `(?:serial|device|implant)` | device_id |
| `(?:protocol|study|subject|participant|screening|randomi[sz]ation)` | study_id |
| `(?:ssn|mrn|npi|dea|identifier|acct|account)$|(?:id|ids|no|num|number|key|ref|seq)#?$` | identified_number |

`PRESENTATIONAL` (never PHI-bearing): `align`, `alt`, `bgcolor`, `border`, `c`, `cellpadding`, `cellspacing`, `charset`, `class`, `code`, `codesystem`, `codesystemname`, `color`, `colspan`, `content`, `dir`, `displayname`, `e`, `encoding`, `face`, `for`, `headers`, `height`, `href`, `http-equiv`, `id`, `k`, `lang`, `n`, `name`, `nowrap`, `onclick`, `p`, `r`, `rel`, `role`, `root`, `rowspan`, `s`, `scope`, `size`, `src`, `style`, `t`, `target`, `templateid`, `title`, `type`, `unit`, `v`, `valign`, `value`, `version`, `width`, `x`, `xmlns`, `y`

`STRUCTURAL_KEYS` (internal schema ids, skipped by policy):

```text
(?:category|item|prop|struct|cat|exam|type|template|section|concept|group|list|field|form|question|answer|option|code|flowsheet|sheet|status|unit|mode|sort|version|schema|def|definition|element|el|node|parent|child|style|layout|page|tab|panel|column|col|row|cell|level|rank|resource|ros|doc|component|attachment|file|image|img|medication|med|drug|rx|dose|order|result|lab|test|panel|obs|observation|problem|diagnosis|dx|allergy|proc|procedure|cpt|icd|ndc|loinc|snomed)(?:id|ids|no|num|number|key|ref|seq)$
```

`SKIP_VALUES` (enum / boolean / system-account values, skipped for every rule): `-`, `--`, `0`, `admin`, `administrator`, `auto`, `backfill`, `conversion`, `default`, `false`, `import`, `interface`, `n`, `n/a`, `na`, `no`, `none`, `null`, `system`, `test`, `true`, `unknown`, `user`, `y`, `yes` and the empty string.
<!-- END GENERATED: key-mapping -->

## Building blocks

<!-- BEGIN GENERATED: blocks -->
Shared fragments, already expanded inside every rule above (so the rule regexes are complete). Shown here so they are recognisable.

**`GAP`**

```text
(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}
```

**`SEP`**

```text
(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}(?:[:#=\-–]|is|was|of)?(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}(?:[:#=\-](?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8})?
```

**`SEP_STRICT`**

```text
(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}[:#=\-\u2013]?(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}(?:[:#=\-](?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8})?
```

**`SEP_KV`**

```text
(?:\s*:\s*|\s*(?:</t[hd]>|&lt;/t[hd]&gt;)?\s*(?:<td[^>]*>|&lt;td[^&]*&gt;)\s*)(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;){0,6}
```

**`STATES`**

```text
(?:A[LKZR]|C[AOT]|D[EC]|FL|GA|HI|I[DLNA]|K[SY]|LA|M[EDAINSOT]|N[EVHJMYCD]|O[HKR]|PA|RI|S[CD]|T[NX]|UT|V[TA]|W[AVIY]|PR|VI|GU)
```

**`YEAR`**

```text
(?:18|19|20)\d{2}
```

**`MONTH`**

```text
(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?
```

**`DATE_VALUE`**

```text
(?:(?:18|19|20)\d{2}-\d{1,2}-\d{1,2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?)?|\d{1,2}[-/.]\d{1,2}[-/.](?:18|19|20)\d{2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2}|\d{1,2}[- ](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?[- ,]+\d{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+(?:18|19|20)\d{2}|(?:18|19|20)\d{2}\d{2}\d{2}|(?:18|19|20)\d{2})
```

**`NOT_KW`**

```text
(?!(?:DOB|DOD|MRN|Age|Sex|Gender|Date|Phone|Fax|Address|Room|Location|Patient|Provider|Physician|Visit|Encounter|Account|Insurance|Dr|MD|DO|NP|PA|RN|Male|Female|Ph|Tel|Cell|Pager|Email|Signed|Dictated|Printed|Page|Report|Result|Results|Information|Preference|Place|Name|Value|Range|Status|Type|Number|History|Summary|Data|List|Note|Notes|Time|Test|Tests|Order|Orders|Medication|Medications|Diagnosis|Problem|Plan|Assessment|Exam|Vitals|Labs|Lab|Allergies|Allergy|Service|Department|Clinic|Hospital|Unit|Level|Total|Amount|Balance|Due|Payment|Code|Description|Comments|Comment|Reason|Source|Site|Referral|Consult|Progress|Discharge|Admission|Admit|Chief|Complaint|Family|Social|Review|Systems|Present|Illness|The|This|These|That|Your|You|We|Our|Please|Negative|Positive|Normal|Abnormal|Final|Pending|See|Not|None|Yes|Unknown|Other|Same|New|Old|For|And|With|Are|Was|Were|Has|Have|Per|From)(?![A-Za-z]))
```

**`NAME_TOKEN`**

```text
(?:(?!(?:DOB|DOD|MRN|Age|Sex|Gender|Date|Phone|Fax|Address|Room|Location|Patient|Provider|Physician|Visit|Encounter|Account|Insurance|Dr|MD|DO|NP|PA|RN|Male|Female|Ph|Tel|Cell|Pager|Email|Signed|Dictated|Printed|Page|Report|Result|Results|Information|Preference|Place|Name|Value|Range|Status|Type|Number|History|Summary|Data|List|Note|Notes|Time|Test|Tests|Order|Orders|Medication|Medications|Diagnosis|Problem|Plan|Assessment|Exam|Vitals|Labs|Lab|Allergies|Allergy|Service|Department|Clinic|Hospital|Unit|Level|Total|Amount|Balance|Due|Payment|Code|Description|Comments|Comment|Reason|Source|Site|Referral|Consult|Progress|Discharge|Admission|Admit|Chief|Complaint|Family|Social|Review|Systems|Present|Illness|The|This|These|That|Your|You|We|Our|Please|Negative|Positive|Normal|Abnormal|Final|Pending|See|Not|None|Yes|Unknown|Other|Same|New|Old|For|And|With|Are|Was|Were|Has|Have|Per|From)(?![A-Za-z]))(?:[A-Z][A-Za-z'\-]{1,24}|[A-Z]\.?))
```

**`NAME_WORD`**

```text
(?:(?!(?:DOB|DOD|MRN|Age|Sex|Gender|Date|Phone|Fax|Address|Room|Location|Patient|Provider|Physician|Visit|Encounter|Account|Insurance|Dr|MD|DO|NP|PA|RN|Male|Female|Ph|Tel|Cell|Pager|Email|Signed|Dictated|Printed|Page|Report|Result|Results|Information|Preference|Place|Name|Value|Range|Status|Type|Number|History|Summary|Data|List|Note|Notes|Time|Test|Tests|Order|Orders|Medication|Medications|Diagnosis|Problem|Plan|Assessment|Exam|Vitals|Labs|Lab|Allergies|Allergy|Service|Department|Clinic|Hospital|Unit|Level|Total|Amount|Balance|Due|Payment|Code|Description|Comments|Comment|Reason|Source|Site|Referral|Consult|Progress|Discharge|Admission|Admit|Chief|Complaint|Family|Social|Review|Systems|Present|Illness|The|This|These|That|Your|You|We|Our|Please|Negative|Positive|Normal|Abnormal|Final|Pending|See|Not|None|Yes|Unknown|Other|Same|New|Old|For|And|With|Are|Was|Were|Has|Have|Per|From)(?![A-Za-z]))[A-Z][A-Za-z'\-]{1,24})
```

**`NAME`**

```text
(?:[A-Z]\.?\s+)?(?:(?!(?:DOB|DOD|MRN|Age|Sex|Gender|Date|Phone|Fax|Address|Room|Location|Patient|Provider|Physician|Visit|Encounter|Account|Insurance|Dr|MD|DO|NP|PA|RN|Male|Female|Ph|Tel|Cell|Pager|Email|Signed|Dictated|Printed|Page|Report|Result|Results|Information|Preference|Place|Name|Value|Range|Status|Type|Number|History|Summary|Data|List|Note|Notes|Time|Test|Tests|Order|Orders|Medication|Medications|Diagnosis|Problem|Plan|Assessment|Exam|Vitals|Labs|Lab|Allergies|Allergy|Service|Department|Clinic|Hospital|Unit|Level|Total|Amount|Balance|Due|Payment|Code|Description|Comments|Comment|Reason|Source|Site|Referral|Consult|Progress|Discharge|Admission|Admit|Chief|Complaint|Family|Social|Review|Systems|Present|Illness|The|This|These|That|Your|You|We|Our|Please|Negative|Positive|Normal|Abnormal|Final|Pending|See|Not|None|Yes|Unknown|Other|Same|New|Old|For|And|With|Are|Was|Were|Has|Have|Per|From)(?![A-Za-z]))[A-Z][A-Za-z'\-]{1,24})(?:,?\s+(?:(?!(?:DOB|DOD|MRN|Age|Sex|Gender|Date|Phone|Fax|Address|Room|Location|Patient|Provider|Physician|Visit|Encounter|Account|Insurance|Dr|MD|DO|NP|PA|RN|Male|Female|Ph|Tel|Cell|Pager|Email|Signed|Dictated|Printed|Page|Report|Result|Results|Information|Preference|Place|Name|Value|Range|Status|Type|Number|History|Summary|Data|List|Note|Notes|Time|Test|Tests|Order|Orders|Medication|Medications|Diagnosis|Problem|Plan|Assessment|Exam|Vitals|Labs|Lab|Allergies|Allergy|Service|Department|Clinic|Hospital|Unit|Level|Total|Amount|Balance|Due|Payment|Code|Description|Comments|Comment|Reason|Source|Site|Referral|Consult|Progress|Discharge|Admission|Admit|Chief|Complaint|Family|Social|Review|Systems|Present|Illness|The|This|These|That|Your|You|We|Our|Please|Negative|Positive|Normal|Abnormal|Final|Pending|See|Not|None|Yes|Unknown|Other|Same|New|Old|For|And|With|Are|Was|Were|Has|Have|Per|From)(?![A-Za-z]))(?:[A-Z][A-Za-z'\-]{1,24}|[A-Z]\.?))){0,3}
```

**`CRED`**

```text
(?:M\.?D\.?|D\.?O\.?|N\.?P\.?|P\.?A\.?(?:-C)?|R\.?N\.?|L\.?P\.?N\.?|C\.?N\.?A\.?|Ph\.?D\.?|D\.?P\.?M\.?|F\.?A\.?C\.?P\.?|M\.?B\.?B\.?S\.?|A\.?P\.?R\.?N\.?|C\.?R\.?N\.?P\.?|D\.?D\.?S\.?|O\.?D\.?|Psy\.?D\.?)
```

**`PHONE_VALUE`**

```text
(?:\+?1[-.\s]?)?(?:\(\d{3}\)\s?|\d{3}[-./\s])\d{3}[-.\s]\d{4}|\+?1?\d{10}|\d{3}-\d{4}
```

**`IDV`**

```text
[A-Za-z0-9][A-Za-z0-9\-/.]{2,29}
```

**`LOC_VALUE`**

```text
[^<>\n,;|]{1,40}?
```

**`ORG_SUFFIX`**

```text
(?:Hospital|Medical\s+Cent(?:er|re)|Health\s*(?:care)?\s*System|Healthcare|Clinic|Regional\s+Medical\s+Center|Cancer\s+(?:Center|Institute)|Institute|Laboratories|Pharmacy|University|College|Physicians|Associates|Medical\s+Group|Foundation|Inc\.?|LLC|L\.L\.C\.|Corp(?:oration)?\.?|Co\.|Urgent\s+Care|Family\s+(?:Practice|Medicine)|Medical\s+Associates|Neurology\s+Associates|Health\s+Partners|Medical\s+Practice)
```

**`ORG_NAME`**

```text
[A-Z][A-Za-z&.'\-]*(?:\s+(?:of|the|and|for|&|at)\s+|\s+)(?:[A-Z][A-Za-z&.'\-]*(?:\s+(?:of|the|and|&|at)\s+|\s+)){0,5}(?:Hospital|Medical\s+Cent(?:er|re)|Health\s*(?:care)?\s*System|Healthcare|Clinic|Regional\s+Medical\s+Center|Cancer\s+(?:Center|Institute)|Institute|Laboratories|Pharmacy|University|College|Physicians|Associates|Medical\s+Group|Foundation|Inc\.?|LLC|L\.L\.C\.|Corp(?:oration)?\.?|Co\.|Urgent\s+Care|Family\s+(?:Practice|Medicine)|Medical\s+Associates|Neurology\s+Associates|Health\s+Partners|Medical\s+Practice)
```
<!-- END GENERATED: blocks -->

## Portability

The patterns use Python `re` semantics: named groups `(?P<val>…)`, fixed-width lookbehind, scoped inline flags
`(?i:…)`, lazy quantifiers, backreferences (`(?P=tag)` in `elem_by_name`). Java, Spark and .NET engines take
`(?<val>…)` for named groups and `\k<tag>` for the backreference; PCRE takes both. The rules are **not RE2-safe**
(lookbehind and backreferences). `GAP`/`SEP` are bounded (`{0,8}`) so there is no catastrophic backtracking; the
`NAME` rules are the slowest because `NOT_KW` is a long alternation evaluated per token.

## Evaluation

Measured on 42,991 records / 89 parts across five table groups against the model's spans of the same records;
tables in [`docs/evaluation.md`](docs/evaluation.md). Headlines, same-family recall by group:

| label | notes tables (run 1) | HTML/XML re-run | OCR run 1 | OCR run 2 | progressnotes (vendor XML) |
|---|---:|---:|---:|---:|---:|
| date | n<200 | 98.3% | 86.6% | 86.9% | 93.9% |
| zip_code | n<200 | 79.4% | 69.6% | 69.1% | 95.0% |
| fax | n<200 | 99.8% | 83.0% | 69.7% | 99.8% |
| phone | n<200 | 98.2% | 56.6% | 57.1% | 55.8% |
| address | 35.4% | 53.0% | 53.1% | 55.5% | 93.2% |
| doctor_name | 85.8% | 87.4% | 68.0% | 70.3% | 63.1% |
| person_name | 60.3% | 66.8% | 32.2% | 38.9% | 49.1% |
| signature_block | 61.4% | 70.2% | 47.7% | 59.3% | 66.1% |
| identified_number | 47.5% | 55.8% | 39.4% | 36.9% | 32.8% |
| hospital_name | 9.6% | 7.4% | 20.6% | 18.7% | 84.5% |
| organization | 15.1% | 15.7% | 10.4% | 10.3% | 91.3% |
| location | 21.7% | 64.9% | 27.3% | 20.3% | 11.4% |

Rules to treat with care: `attr_by_name` (43% precision — the reference model itself was a coin flip on vendor-XML
ids), `dollar_amount` (42%, fee schedules), `location_labelled` (40%), `url_bare_domain` (69%), `ip_shape` (0/23),
`xml_name_parts` (0/509 — the values were already upstream placeholders in this corpus), `amount_labelled` (12%),
`xml_id_extension` (inert in the sample). They ship documented rather than switched off.

## Limitations — what still needs a lexicon or the model

- A name in running prose with no anchor (about half of all `person_name` spans).
- Facility and organization names without an institutional suffix outside structured markup (7–20% recall in
  notes and OCR); the mined literals are highly concentrated, so a facility / city / clinician lexicon built from
  the census closes most of this gap.
- Clinic and site names as `location`.
- Identifiers with no key or label near them; the rules deliberately never redact bare numbers.
- OCR text with broken casing or spacing (lower-case street lines, `JohnSmith`).

## Development

```bash
python -m pytest -q                              # all tests
python -m phi_rules.selftest                     # fixtures without pytest
python tools/render_readme.py                    # regenerate the generated README sections
python tools/render_readme.py --check            # what tests/test_readme_sync.py runs
python tools/phi_hygiene_check.py                # nothing from the PHI pipeline leaked into the repo
```

To add a rule: append a `Rule(label, name, pattern, flags, doc, examples, relabel)` to the right module in
`phi_rules/`, add its name to `RULE_ORDER` in `phi_rules/__init__.py`, add a positive and a negative fixture to
`phi_rules/selftest.py`, regenerate the README. Patterns are plain `r"…"` strings joined with `+` — never
f-strings, whose `{n,m}` quantifiers silently become tuples.

```
phi_rules/          _blocks.py engine.py dates.py identifiers.py contact.py amount.py places.py orgs.py names.py
                    markup.py selftest.py __main__.py
tests/              test_fixtures.py test_engine.py test_readme_sync.py
docs/               evaluation.md policy.md
tools/              render_readme.py phi_hygiene_check.py
```

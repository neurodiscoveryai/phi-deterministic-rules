# Onboarding — phi-deterministic-rules

Welcome. This repository is the deterministic (no-LLM) PHI detection pass for the Biogen de-identification
deliverable: 52 regular-expression rules covering the 19 PHI labels the pipeline uses, packaged as a stdlib-only
Python library with a CLI. This guide gets you from zero to running it, understanding why it looks the way it
does, and changing it safely. Budget about an hour.

## 1. What problem this solves

The deliverable de-identified ~19 million clinical records (free-text notes, OCR exports, HTML/XML notes and
vendor-XML progressnotes) with an LLM that returned PHI entities which a binder replaced with `((label))`
placeholders. That costs GPU time and is non-deterministic. We recovered every span the model redacted — 470
million of them — censused what they look like and what sits next to them, and wrote rules for the patterns that
are truly deterministic: a labelled date of birth, a formatted phone number, `City, ST 12345`, `Dr. X`, `X, MD`,
`Signed by:`, an XML attribute whose name says what it holds. Those rules are this repository.

It is a **safety net and a first pass**, not a full replacement: a bare name in running prose, a facility name
without an institutional suffix, or a clinic mentioned in passing still needs a lexicon or the model. The README's
"Limitations" section says exactly where the line is.

## 2. Set up

```bash
git clone <this repo> && cd phi-deterministic-rules
pip install -e .              # Python >= 3.9, no third-party dependencies
python -m pytest -q           # 11 tests: fixtures, engine contract, README in sync
phi-rules --version
```

Try it:

```bash
printf '%s\n' '{"id":1,"note":"Patient Name: Mary Ann Jones, DOB: 04/06/1959, Ph: (555) 123-4567."}' \
  | phi-rules redact --field note --spans
```

You should see `((person_name))`, `((date))` and `((phone))` in `redacted`, and a `spans` list with label, rule
and offsets — never the span text.

## 3. The mental model (read this twice)

- **19 labels, 5 families.** names (person_name, doctor_name, signature_block), dates (date, age_90_plus), numbers
  (identified_number, phone, fax, device_id, study_id), places (address, zip_code, location), institutions
  (hospital_name, organization), plus email, url, ip_address, amount. The model's label choice *inside* a family is
  driven by context and is inconsistent (the same surname is person/doctor/signature depending on the anchor), so
  consume results at the family level unless the exact label matters.
- **Rules anchor on context, not on shape.** A bare number, a bare year, a bare state code or a capitalised word is
  never redacted on its own; the prompts and the model agree those are clinical data. Rules fire on a label
  (`MRN:`, `DOB:`, `Fax:`), a structural position (`<th>Provider</th><td>`, `| Final |`), a shape that is PHI by
  itself (`(555) 123-4567`, `x@y.org`, `City, ST 12345`), or — in XML/JSON — the **key name** (`PharmacyCity=`,
  `<encounterID>`, `"CREATEDBY":`).
- **The engine** runs every rule, keeps each `val*` group as a candidate, drops values containing `((` (upstream
  placeholders) or in `SKIP_VALUES` (`true`, `none`, `Admin`, …), lets a rule's `relabel` hook fix the label per
  match, promotes a `date` whose year ≤ `CUTOFF_YEAR` (1936) to `age_90_plus`, then resolves overlaps: sort by
  (start, longest first), sweep greedily. Over-redaction is the safe direction.
- **Policy decisions are explicit.** `docs/policy.md` lists the ten choices (structural XML ids skipped, system
  accounts skipped, `href` not redacted, `$` amounts redacted, …). If your use case disagrees, change the code and
  the document together.

## 4. Reading the README

The README is long on purpose: every rule appears with its **exact regex**, flags, value group, one paragraph of
evidence and measured precision, and worked examples that are computed at render time. Those sections are generated
from the code by `tools/render_readme.py`; a test fails if they drift, so the regex you read is the regex that runs.
Start with "How it works" and "The 19 labels", then read the rule sections for the family you care about.
`docs/evaluation.md` has the full recall/precision tables with confidence intervals and the per-table-group view.

## 5. How the numbers were produced (so you can trust or distrust them)

1. Spans were recovered from the pipeline's own output (source and de-identified text side by side) by aligning the
   two; a record's spans were kept only if they reproduced the binder's own per-label tally and rebuilt the
   de-identified text byte for byte (0.07% of records failed and were excluded).
2. The census counted, per label, value shapes (`A`/`a`/`9`), left-context triggers and structural labels.
3. Candidate regexes were scored on the SOURCE text of a stratified sample (89 parts, 42,991 records, five table
   groups) by character overlap with the model's spans: recall per label (same label / same family / any rule) and
   precision per rule. "Unhit" rule spans are a **lower bound** on false positives because the model's own misses
   land there.
4. The reference is the model, not ground truth. On vendor-XML structural ids it redacted the same key in roughly
   half the records; on system accounts it labelled `Admin` a signature. The rules follow a stated policy instead.

## 6. Using it in a data pipeline

- **Python**: `from phi_rules import find, redact`; `find(text)` returns `Span(label, rule, start, end, text)`;
  `redact(text, placeholder="(({label}))", cutoff_year=1936)`.
- **CLI / batch**: `phi-rules redact --format jsonl|csv -i IN --field NAME -o OUT`; stdin/stdout when omitted.
- **Other engines**: patterns use Python `re` semantics — `(?P<val>…)` named groups, lookbehind, scoped `(?i:…)`,
  lazy quantifiers, one backreference `(?P=tag)`. Java/Spark/.NET take `(?<val>…)` and `\k<tag>`. Not RE2-safe.
  All repeats are bounded (`{0,8}`), so there is no catastrophic backtracking; the name rules are the slowest
  because `NOT_KW` is a long alternation.
- **Placeholders** default to `((label))`, the same vocabulary the model produced, so outputs are interchangeable.

## 7. Making a change

```bash
# 1. edit phi_rules/<type>.py  -- plain r"..." strings joined with +, value group named val
# 2. add the rule name to RULE_ORDER in phi_rules/__init__.py
# 3. add a positive AND a realistic negative fixture in phi_rules/selftest.py
python -m pytest -q
python tools/render_readme.py                     # regenerate the rule sections
python tools/phi_hygiene_check.py --lexicons /home/gitartha/biogen_deliverable_phi/span_census
git commit -am "..."
```

Two traps everyone hits once: an f-string pattern turns `{2,60}` into a tuple and the rule silently never matches;
a case-sensitive compile of a rule whose label is written in lowercase makes the label case-sensitive too. The
tests catch the first; keep labels as `(?i:…)` groups for the second.

## 8. Never

- Never put real names, addresses, identifiers or document excerpts in this repository — fixtures, docs, commits,
  issues. Everything here is synthetic; the hygiene check compares every file against the mined name lexicons (read
  from the pipeline directory, never copied).
- Never hand-edit a generated README section.
- Never redact by shape alone (bare numbers, years, state names), and never change `CUTOFF_YEAR` without saying so.
- Never treat precision "against the model" as precision against truth.

## 9. Glossary

- **span**: a `(label, start, end)` slice of the source text that a rule (or the model) redacted.
- **family**: the group of labels the model used interchangeably (names, dates, numbers, places, institutions).
- **anchor / trigger**: the label, keyword or structural position a rule requires next to a value.
- **key-to-label map**: `KEY_RULES` in `phi_rules/markup.py`, mapping attribute/element/JSON key names to labels.
- **upstream placeholder**: a `((TOKEN))` left by an earlier de-identification pass; never touched.
- **cut-off year**: birth years at or below it imply age ≥ 90 and become `age_90_plus`.

## 10. Who to ask

The pipeline that produced the evidence, the census and the evaluation lives in the Biogen deliverable repository
(`phi_rules.py --eval` there re-scores this rule set against the PHI census). Questions about the rules, the policy
choices or the numbers go to the deliverable owner; questions about integrating the package go to Data Engineering.

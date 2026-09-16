# Policy decisions built into the rules

These are choices, not measurements. Each one is where the reference model was inconsistent or where the
de-identification prompts draw a line; Data Engineering owns them and may change them.

1. **Only labelled birth and death dates are PHI.** Admission, visit, procedure, lab and signing dates are clinical
   data and are never redacted. A bare 4-digit year is redacted only behind a DOB/DOD label (or in the corpus-
   specific guarantor line). The birth year decides `date` vs `age_90_plus`; the cut-off is the fixed constant
   `CUTOFF_YEAR = 1936` (2026 − 90) so re-runs are reproducible -- bump it each year, or pass `cutoff_year`.
2. **Never redact by shape alone**: bare numbers, bare years, bare 2-letter state codes and state names, capitalised
   words. Identifiers need a key or label; states need a city or ZIP next to them; names need an anchor.
3. **Structural identifiers are skipped** (`FlowsheetID`, `CategoryId`, `StatusID`, `TemplateId`, …): the reference
   model redacted them in about half of the records and left them in the other half. `STRUCTURAL_KEYS` in
   `phi_rules/markup.py` holds the list.
4. **Presentational HTML attributes are skipped** (`class`, `id`, `name`, `style`, `href`, `src`, `alt`, `title`, code-set
   attributes such as `code`, `codeSystem`, `root`, `templateId`). Real identifiers in HTML live in visible text or in
   `data-*` / vendor attributes, which the key map still catches.
5. **System accounts and enum values are skipped** (`Admin`, `System`, `Interface`, `true`, `none`, `0`, …):
   `SKIP_VALUES` in `phi_rules/engine.py`. The model labelled `Admin` a signature in ~15% of progressnotes rows.
6. **Upstream placeholders are never touched.** Any value containing `((` is an earlier de-identification pass's
   token and is left as is.
7. **`href` / `src` URLs are not redacted** although the HTML prompt asked for it: the model did not do it either, and
   internal links are not patient PHI. `url_scheme` / `url_bare_domain` still catch URLs in visible text.
8. **Amounts**: `$` values are redacted wherever they appear (the prompt says financial values only; the model left most
   fee-schedule tables alone, hence 42% precision against it). Drop `dollar_amount` if fee schedules should stay.
9. **Over-redaction on ties.** When two candidate spans start at the same position the longer one wins; when spans
   overlap the earlier one wins. For PHI, redacting a little clinical text is the lesser harm.
10. **Labels inside a family are anchor-driven.** The same surname is `person_name` in the body, `doctor_name` after a
    credential and `signature_block` after "Signed by"; the model did the same, inconsistently. Score and consume
    the rules at the family level (names / places / institutions / numbers / dates) unless the exact label matters.

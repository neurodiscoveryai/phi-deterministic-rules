# CLAUDE.md — phi-deterministic-rules

Deterministic regex rules for the 19 PHI labels of the Biogen de-identification deliverable, packaged for the
Data Engineering team. 52 rules, one module per PHI-type group, a small engine, a CLI, synthetic fixtures, and a
README whose rule sections are generated from the code. Read this before changing anything.

    phi_rules/_blocks.py   shared regex fragments (GAP, SEP, NAME, DATE_VALUE, ...)   plain r"..." strings only
    phi_rules/engine.py    Rule, Span, find(), redact(), CUTOFF_YEAR, SKIP_VALUES
    phi_rules/<type>.py    dates identifiers contact amount places orgs names markup   -> each exposes RULES
    phi_rules/__init__.py  GROUPS (by type, for docs) and RULE_ORDER (evaluation order, load-bearing)
    phi_rules/selftest.py  73 synthetic fixtures, 24 negatives   python -m phi_rules.selftest
    tools/render_readme.py regenerates README between <!-- BEGIN/END GENERATED: ... --> markers
    tools/phi_hygiene_check.py  nothing from the PHI pipeline may be in this repo

## Hard rules

1. **No PHI, ever.** No real names, addresses, identifiers, phone numbers or document excerpts anywhere: not in
   fixtures, docs, comments, commit messages or issue text. Fixtures are invented (`Casey J Sampleton`, `Anytown,
   MI 48000`, 555 numbers). Before every commit run
   `python tools/phi_hygiene_check.py --lexicons /home/gitartha/biogen_deliverable_phi/span_census`
   (the lexicons are read in place from the pipeline directory and are never copied here). Copy nothing from that
   directory except regex strings and numeric evaluation tables.
2. **Patterns are plain `r"..."` strings joined with `+`.** Never an f-string: an `rf"..."` pattern turned `{2,60}`
   into the tuple `(2, 60)` and two rules silently matched nothing until the evaluation's "inert" column showed it.
   `tests/test_engine.py` rejects doubled braces and tuple reprs, but write it right the first time.
3. **Label case lives inside the pattern.** Labels are `(?i:...)` scoped groups compiled with `flags=0`; a
   case-sensitive compile once silently disabled `ELECTRONICALLY SIGNED BY`. Only ten rules carry `re.IGNORECASE`
   and that is deliberate (see `RULE_ORDER` neighbours in the type modules).
4. **`RULE_ORDER` is load-bearing.** Overlap resolution is sort by (start, longest first) and a greedy sweep; ties
   at equal start and length go to the earlier rule. Adding a rule means appending its name there too; the
   package asserts the count and the name set at import.
5. **The README is generated where it says so.** Never hand-edit between `<!-- BEGIN GENERATED: ... -->` and its
   `END` marker; edit `Rule.doc` / `Rule.examples` / `GROUP_INTRO` and run `python tools/render_readme.py`.
   `tests/test_readme_sync.py` fails the build on drift.
6. **`CUTOFF_YEAR` is a fixed constant (1936 = 2026 − 90), not `date.today()`.** Re-runs must be reproducible.
   Bump it deliberately once a year and say so in the commit; callers can pass `cutoff_year`.
7. **Policy is written down, not implied.** Anything that decides what is *not* redacted (structural ids, system
   accounts, presentational attributes, `href`, fee schedules, bare numbers/years/states) is in `docs/policy.md`.
   Change the code and the document together.
8. **Every rule ships with a positive AND a negative fixture** in `phi_rules/selftest.py`, and the negative must be
   the realistic near miss (`DOBUTAMINE` for DOB, a medication sig for a street line, a GUID for a ZIP, an OID for an
   IP). A suite that only proves the happy path proves nothing.
9. **Numbers come from the evaluation, not from memory.** Precision/recall quoted in `Rule.doc` and the README must
   match `docs/evaluation.md`, which holds only the numeric tables of the final evaluation run in the pipeline.
   Re-evaluating means re-running `phi_rules.py --eval` there (it needs the PHI census) and re-transcribing tables.

## Commands

    pip install -e .                                   # no dependencies
    python -m pytest -q                                # fixtures, engine contract, README sync
    python -m phi_rules.selftest                       # fixtures without pytest
    python tools/render_readme.py [--check]            # regenerate / verify README
    python tools/phi_hygiene_check.py [--lexicons DIR] # PHI leak scan (run with --lexicons before committing)
    phi-rules redact -i in.jsonl --field note_raw -o out.jsonl
    phi-rules find   -i in.jsonl --field note_raw --spans

## Where it came from, in one paragraph

Every span the de-identification model redacted (470,445,960 verified spans over 19.1 M records) was recovered by
re-aligning source and de-identified text in the pipeline repository, censused per label (shapes, left-context
triggers, structural labels), and turned into candidate regexes that were scored against the model's own spans on
a stratified 42,991-record sample. The port here was proven byte-identical to the pipeline's `phi_rules.py`
(52/52 pattern strings and flags, zero span differences on 2,648 real records). The model is the reference, not
ground truth: it was a coin flip on vendor-XML structural ids and labelled system accounts as signatures, which is
why several policy choices exist and why precision "against the model" is a lower bound.

## When adding or changing a rule

1. Write the pattern as concatenated `r"..."` pieces reusing `_blocks.py`; name the value group `val`.
2. Add `Rule(label, name, pattern, flags, doc, examples, relabel)` to the type module and the name to `RULE_ORDER`.
3. Add a positive and a near-miss negative fixture to `selftest.py`; run `python -m pytest -q`.
4. Regenerate the README; run the hygiene check with `--lexicons`; commit code, fixtures and README together.
5. If the change should ship with numbers, re-run the evaluation in the pipeline repo and update
   `docs/evaluation.md` in the same change.

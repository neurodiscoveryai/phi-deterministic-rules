#!/usr/bin/env python3
"""Regenerate the generated sections of README.md from the package, so the documented regexes are the shipped ones.

    python tools/render_readme.py            # rewrite README.md in place
    python tools/render_readme.py --check    # exit 1 if README.md is out of date (used by tests)

Sections are delimited by  <!-- BEGIN GENERATED: name -->  /  <!-- END GENERATED: name -->  with name in
{rules, key-mapping, blocks}. Everything outside the markers is hand-written and left alone.
"""
import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import phi_rules  # noqa: E402
from phi_rules import GROUPS, find  # noqa: E402
from phi_rules._blocks import BLOCKS  # noqa: E402
from phi_rules.markup import KEY_RULES, PRESENTATIONAL, STRUCTURAL_KEYS  # noqa: E402
from phi_rules.engine import SKIP_VALUES  # noqa: E402

README = os.path.join(ROOT, "README.md")
EVAL = os.path.join(ROOT, "docs", "evaluation.md")

GROUP_INTRO = {
    "dates": "Only a labelled birth or death date is PHI; every other date is clinical data. 66% of the model's date spans are a bare "
             "4-digit year behind a DOB label. The engine promotes a `date` whose year is at or below `CUTOFF_YEAR` (1936) to `age_90_plus`.",
    "identifiers": "identified_number is 74% of all model-redacted spans; outside structured markup 78% are plain digit runs behind a label. "
                   "The LABEL carries the signal: a bare number is never redacted by shape.",
    "contact": "Formatted 10-digit numbers are phones on their own; bare digit runs need a Phone/Fax label, a `tel:` link, a phone-named "
               "attribute or the position right after a ZIP. E-mail and URLs are pure shapes.",
    "amount": "Financial values only -- never doses, lab values, vitals or scores.",
    "places": "The model splits `City, ST 12345` into city and state (address) and ZIP (zip_code) -- 32% of all address spans are bare state "
              "codes for that reason. Structured lines are deterministic; a city alone in prose needs a gazetteer.",
    "orgs": "Institutional suffixes (`… Hospital`, `… Medical Center`, `… Clinic`, `… Inc`) and Facility / Employer labels. The model used "
            "hospital_name and organization interchangeably for 10k literals; score them as one family.",
    "names": "The hard class. Anchors (Dr., a credential, Provider:, Signed by:, Mr./Mrs., a relative word, `<given>`) are deterministic; "
             "about half of all person_name spans in the corpus have no anchor and need a lexicon or a model.",
    "markup": "In XML, CCDA, vendor exports and escaped HTML the attribute / element / JSON KEY decides the label. One key-to-label map "
              "recovered 60-99% of every label in the progressnotes exports.",
}


def flags_str(f):
    names = [n for n in ("IGNORECASE", "MULTILINE", "DOTALL", "VERBOSE") if f & getattr(re, n)]
    return ", ".join("re." + n for n in names) if names else "none (case handled inside the pattern with `(?i:…)`)"


def precision_table():
    """rule -> (fired, same, family, any) parsed from docs/evaluation.md; {} if the file is absent."""
    out = {}
    if not os.path.isfile(EVAL):
        return out
    sec = False
    for line in open(EVAL, encoding="utf-8"):
        if line.startswith("## Precision per rule"):
            sec = True; continue
        if sec and line.startswith("## "):
            break
        if sec:
            m = re.match(r"(\w+)\s+(INERT|[\d,]+)\s*(.*)", line)
            if m:
                cells = re.findall(r"(-?[\d.]+)% \[", m.group(3))
                out[m.group(1)] = (m.group(2), cells)
    return out


def render_rules():
    prec = precision_table()
    L = []
    for title, mod, rules in GROUPS:
        L.append(f"### {title}  (`phi_rules/{mod}.py`)\n")
        L.append(GROUP_INTRO.get(mod, "") + "\n")
        for r in rules:
            L.append(f"#### `{r.name}`  → `{r.label}`" + ("  (label decided per match by the rule's relabel hook)" if r.relabel else "") + "\n")
            L.append(r.doc + "\n")
            p = prec.get(r.name)
            if p:
                if p[0] == "INERT":
                    L.append("Evaluation: inert in the sample (never fired).\n")
                else:
                    c = p[1]
                    L.append(f"Evaluation: fired {p[0]}; precision same label {c[0]}%, same family {c[1]}%, any model span {c[2]}%.\n" if len(c) >= 3 else f"Evaluation: fired {p[0]}.\n")
            L.append(f"Flags: {flags_str(r.flags)}. Value group: `val`" + (", `val2`, `val3`" if "val3" in r.compiled().groupindex else "") + ".\n")
            L.append("```text\n" + r.pattern + "\n```\n")
            if r.examples:
                L.append("Examples (what `find()` returns):\n")
                for ex in r.examples:
                    got = ", ".join(f"{s.label}=`{s.text}`" for s in find(ex)) or "nothing"
                    L.append(f"- `{ex}` → {got}")
                L.append("")
    return "\n".join(L)


def render_key_mapping():
    L = ["The key (attribute name, element name or JSON key) is lowercased, `-` removed, `:` → `_`, trailing `#`/digits dropped, then:\n",
         "1. keys in `PRESENTATIONAL`, keys shorter than 2 characters, and keys matching `STRUCTURAL_KEYS` → not PHI;",
         "2. an age key (`age`, `patientage`, …) → `age_90_plus` if the value is ≥ 90, else not PHI;",
         "3. the first matching row below decides the label, subject to a value-shape check (phones need 7 digits, ZIPs `ddddd(-dddd)`, dates a 4-digit year, names/places a letter; a numeric value under a user/created-by key becomes `identified_number`).\n",
         "| key regex (search on the normalised key) | label |", "|---|---|"]
    for pat, lab in KEY_RULES:
        L.append(f"| `{pat.pattern}` | {lab} |")
    L.append("\n`PRESENTATIONAL` (never PHI-bearing): " + ", ".join(f"`{k}`" for k in sorted(PRESENTATIONAL)) + "\n")
    L.append("`STRUCTURAL_KEYS` (internal schema ids, skipped by policy):\n\n```text\n" + STRUCTURAL_KEYS.pattern + "\n```\n")
    L.append("`SKIP_VALUES` (enum / boolean / system-account values, skipped for every rule): " + ", ".join(f"`{v}`" for v in sorted(SKIP_VALUES) if v) + " and the empty string.")
    return "\n".join(L)


def render_blocks():
    L = ["Shared fragments, already expanded inside every rule above (so the rule regexes are complete). Shown here so they are recognisable.\n"]
    for name, pat in BLOCKS.items():
        L.append(f"**`{name}`**\n\n```text\n{pat}\n```\n")
    return "\n".join(L)


def splice(text, name, body):
    b, e = f"<!-- BEGIN GENERATED: {name} -->", f"<!-- END GENERATED: {name} -->"
    i, j = text.index(b) + len(b), text.index(e)
    return text[:i] + "\n" + body.rstrip() + "\n" + text[j:]


def render(text):
    text = splice(text, "rules", render_rules())
    text = splice(text, "key-mapping", render_key_mapping())
    text = splice(text, "blocks", render_blocks())
    return text


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    cur = open(README, encoding="utf-8").read()
    new = render(cur)
    if a.check:
        if new != cur:
            print("README.md is out of date: run  python tools/render_readme.py"); return 1
        print("README.md in sync"); return 0
    open(README, "w", encoding="utf-8").write(new)
    print(f"README.md regenerated ({len(new)/1e3:.0f} KB, {len(phi_rules.RULES)} rules)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Command line: redact or locate PHI in JSONL / CSV records, or run the self-test.

    phi-rules redact -i notes.jsonl --field note_raw -o out.jsonl        # adds "redacted"
    phi-rules find   -i notes.jsonl --field note_raw --spans             # adds "spans" (label, rule, start, end -- never the text)
    cat notes.jsonl | phi-rules redact --field text > out.jsonl
    phi-rules redact --format csv -i notes.csv --field note -o out.csv
    phi-rules selftest

Exit status: 0 ok, 1 self-test failures, 2 bad arguments.
"""
import argparse
import csv
import json
import sys

from . import CUTOFF_YEAR, __version__, find, redact


def main(argv=None):
    ap = argparse.ArgumentParser(prog="phi-rules", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["redact", "find", "selftest"])
    ap.add_argument("-i", "--input", help="input file (default stdin)")
    ap.add_argument("-o", "--output", help="output file (default stdout)")
    ap.add_argument("--format", choices=["jsonl", "csv"], default="jsonl")
    ap.add_argument("--field", default="text", help="record field holding the text (default: text)")
    ap.add_argument("--placeholder", default="(({label}))", help="format for redacted spans (default: (({label})))")
    ap.add_argument("--spans", action="store_true", help="also emit spans as label/rule/start/end (redact) -- never the span text")
    ap.add_argument("--cutoff-year", type=int, default=CUTOFF_YEAR, help=f"birth year at or below this is age_90_plus (default {CUTOFF_YEAR})")
    ap.add_argument("--version", action="version", version=__version__)
    a = ap.parse_args(argv)
    if a.command == "selftest":
        from .selftest import run
        return run()
    fin = open(a.input, encoding="utf-8", newline="") if a.input else sys.stdin
    fout = open(a.output, "w", encoding="utf-8", newline="") if a.output else sys.stdout
    try:
        if a.format == "jsonl":
            for line in fin:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                _process(rec, a)
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
        else:
            reader = csv.DictReader(fin)
            extra = (["redacted"] if a.command == "redact" else []) + (["spans"] if a.spans or a.command == "find" else [])
            writer = csv.DictWriter(fout, fieldnames=list(reader.fieldnames or []) + extra)
            writer.writeheader()
            for rec in reader:
                _process(rec, a)
                if "spans" in rec:
                    rec["spans"] = json.dumps(rec["spans"])
                writer.writerow(rec)
    finally:
        if a.input:
            fin.close()
        if a.output:
            fout.close()
    return 0


def _process(rec, a):
    text = rec.get(a.field)
    if not isinstance(text, str):
        return
    spans = find(text, cutoff_year=a.cutoff_year)
    if a.command == "redact":
        rec["redacted"] = redact(text, a.placeholder, spans=spans)
    if a.command == "find" or a.spans:
        rec["spans"] = [{"label": s.label, "rule": s.rule, "start": s.start, "end": s.end} for s in spans]


if __name__ == "__main__":
    sys.exit(main())

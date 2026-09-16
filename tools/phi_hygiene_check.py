#!/usr/bin/env python3
"""Fail if anything that belongs to the PHI pipeline leaked into this repository.

    python tools/phi_hygiene_check.py                       # forbidden fragments in tracked files
    python tools/phi_hygiene_check.py --lexicons DIR        # also scan every line against lexicon_*.tsv (never copied)

Never writes. Exit 1 on any hit. The lexicon scan prints the file:line and a masked hit (first char + '*').
"""
import argparse
import glob
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORBIDDEN = ["span_census", "lexicon_", "eval_src", "spans-0", "s3_pn", "biogen_deliverable_phi", "custom_id", "ndai-neuro-audit",
             "output_b2", "archive_ocr_run1"]
STOP = set("""the and for with from that this name date phone patient hospital medical center clinic health system group
associates family practice general sample example anytown test admin system user unknown none null true false main street
suite road avenue city state north south east west lake hill hills creek river park view point spring springs valley
mary ann jones smith john jane public robert brown johnson casey jordan sampleton northwind widgets acme motors
mary ann mary ann jones robert brown jane q public john smith casey j sampleton jordan q sample johnson mary
email e-mail fax phone number clinical medical center pharmacy laboratory final pending provider physician doctor
orderingmdid patientid encounterid createdby createdusername flowsheet flowsheetid categoryid itemid statusid
signed signature dictated printed entered electronically sincerely regards facility employer organization
protocol subject participant serial scanner device model study site zip code postal address location room bed unit
insurance member policy account chart record encounter visit order specimen accession claim license report document
identified identifier amount balance copay total fee charge payment cost neurology oncology cardiology imaging
radiology surgery internal medicine urgent care family medicine emergency first last block class out outpatient inpatient biogen deliverable medicare medicaid tricare
jane doe marie wilson guardian primary brain infusion interface pipeline hooks ground little short target county office
admission allergy problem observation regional institute laboratories university physicians cancer court parkway
social security department of neurology ms clinic main st""".split())
# multi-word synthetic / generic grams (the split() above only yields single words)
STOP |= {"jane doe", "social security", "department of neurology", "ms clinic", "main st", "mary ann", "mary ann jones", "robert brown",
         "jane q public", "john smith", "casey j sampleton", "jordan q sample", "johnson mary", "regional medical center", "cancer center",
         "university physicians", "example general", "example general hospital", "northwind widgets", "acme motors", "sample hills",
         "sample creek"}


def tracked_files():
    try:
        out = subprocess.run(["git", "-C", ROOT, "ls-files", "--cached", "--others", "--exclude-standard"],
                             capture_output=True, text=True, check=True).stdout.split()
    except Exception:
        out = []
    if not out:                                      # not a git checkout: every file except .git/
        out = [os.path.relpath(p, ROOT) for p in glob.glob(os.path.join(ROOT, "**", "*"), recursive=True)
               if os.path.isfile(p) and "/.git/" not in p]
    me = os.path.relpath(os.path.abspath(__file__), ROOT)
    return [f for f in out if f != me and not f.endswith((".pyc",))]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--lexicons", help="directory holding lexicon_*.tsv (count<TAB>literal); read only")
    ap.add_argument("--min-len", type=int, default=5)
    ap.add_argument("--show", action="store_true", help="print hits unmasked (local triage only)")
    ap.add_argument("--all-lexicons", action="store_true", help="scan every lexicon, not only the three name lexicons (noisy: generic words)")
    a = ap.parse_args(argv)
    hits = 0
    files = tracked_files()
    for f in files:
        try:
            txt = open(os.path.join(ROOT, f), encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for frag in FORBIDDEN:
            if frag in txt:
                print(f"{f}: forbidden fragment {frag!r}"); hits += 1
    if a.lexicons:
        lex = set()
        names = ["person_name", "doctor_name", "signature_block"] if not a.all_lexicons else ["*"]
        files_lex = [f for n in names for f in glob.glob(os.path.join(a.lexicons, f"lexicon_{n}.tsv"))]
        for p in files_lex:
            for line in open(p, encoding="utf-8", errors="replace"):
                parts = line.rstrip("\n").split("\t", 1)
                if len(parts) == 2:
                    lit = parts[1].strip().lower()
                    words_ = lit.split()
                    if len(lit) >= a.min_len and lit not in STOP and not lit.isdigit() and (len(words_) > 1 or len(lit) >= 6):
                        lex.add(lit)
        print(f"lexicon literals loaded: {len(lex):,}")
        for f in files:
            for i, line in enumerate(open(os.path.join(ROOT, f), encoding="utf-8", errors="replace"), 1):
                words = re.findall(r"[a-z][a-z'\-]+", line.lower())
                for n in (1, 2, 3, 4):
                    for k in range(len(words) - n + 1):
                        gram = " ".join(words[k:k + n])
                        if gram in lex and gram not in STOP and len(gram) >= a.min_len and not all(w in STOP for w in words[k:k + n]):
                            print(f"{f}:{i}: lexicon hit {gram if a.show else gram[0] + '*' * (len(gram) - 1)}"); hits += 1
    print("hygiene:", "FAIL" if hits else "OK", f"({len(files)} files)")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())

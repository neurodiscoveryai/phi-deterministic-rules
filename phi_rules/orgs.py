"""hospital_name and organization (the 'institutions' family; the reference model used the two labels
interchangeably for 10k literals, so score them together)."""
import re

from ._blocks import GAP, ORG_NAME, SEP_KV
from .engine import Rule

_CORPORATE = re.compile(r"(?i)\b(?:inc|llc|corp|company|co\.|university|college|school|employer)\b")


def _org_or_hospital(m, group, value):
    return "organization" if _CORPORATE.search(value) else "hospital_name"


RULES = [
    Rule("hospital_name", "org_with_suffix",
         r"(?<![A-Za-z])(?P<val>" + ORG_NAME + r")(?![A-Za-z])",
         doc="A capitalised phrase (up to 6 words, 'of/the/and/&/at' allowed) ending in an institutional suffix: Hospital, "
             "Medical Center, Health System, Clinic, Institute, Laboratories, Pharmacy, University, Physicians, Associates, "
             "Foundation, Inc, LLC, Corp … Corporate suffixes (Inc/LLC/Corp/University/College) relabel to organization. "
             "57% same-label / 66% family precision.",
         examples=("referred to Example General Hospital for", "works at Northwind Widgets Inc. as"),
         relabel=_org_or_hospital),
    Rule("hospital_name", "hospital_labelled",
         r"(?<![A-Za-z])(?i:(?:hospital|facility|facility\s+name|performing\s+lab(?:oratory)?|performed\s+at|referring\s+facility|institution|pharmacy(?:\s+name)?))" + SEP_KV + r"(?P<val>[A-Z][^<>&\n,;|]{2,60}?)(?=\s*(?:<|&lt;|\n|,|;|\||$))",
         doc="Hospital / Facility / Facility Name / Performing Lab / Performed at / Referring Facility / Institution / Pharmacy label "
             "with a colon or cell boundary, followed by a capitalised value to the end of the cell/line. 70% same-label / 77% "
             "family precision.",
         examples=("Facility Name: Example General<br>",)),
    Rule("organization", "employer_labelled",
         r"(?<![A-Za-z])(?i:(?:employer(?:\s+name)?\s*:|employed\s+(?:by|at)|works\s+(?:at|for)|member\s+of\s+the|affiliated\s+with(?:\s+the)?))" + GAP + r"(?P<val>[A-Z][^<>&\n,;|]{2,60}?)(?=\s*(?:<|&lt;|\n|,|;|\||\.|$))",
         doc="Employer Name: / employed by / works at / member of the / affiliated with … followed by a capitalised value. "
             "53% same-label / 60% family precision.",
         examples=("Employer Name : Acme Motors<br>",)),
]

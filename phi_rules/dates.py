"""date and age_90_plus.

Under the de-identification prompts only a birth or death date is PHI; every other date is clinical data.
The census confirms the model behaved that way: 66% of date spans are a bare 4-digit year, 19% ISO datetimes,
the rest US / day-Mon-year forms -- always behind a DOB/DOD label, a <th>DOB</th><td> cell, a DOB="…"
attribute, a <DOB> / <birth_dttm V="…"> element, or the corpus-specific demographic line
"((GUARANTORLASTNAME)), ((GUARANTORFIRSTNAME)) ((GUARANTORMIDDLEINITIAL)) 1957". The engine promotes a
date whose year is <= CUTOFF_YEAR to age_90_plus; explicit ages of 90+ are matched here.
"""
import re

from ._blocks import DATE_VALUE, YEAR, labelled
from .engine import Rule

RULES = [
    Rule("date", "dob_labelled",
         labelled(r"(?:D\.?\s?O\.?\s?B\.?(?:\s+source)?|date\s+of\s+birth|birth\s*date|birthdate|born(?:\s+on)?|D\.?O\.?D\.?|date\s+of\s+death|deceased(?:\s+date|\s+on)?|death\s+date)", DATE_VALUE),
         doc="A DOB / Date of Birth / Birthdate / DOD label (any case, markup allowed between label and value, 'is/was/of' "
             "filler allowed) followed by a date value; the value shapes are, longest first, ISO with optional time, "
             "US numeric, 2-digit year, day-Mon-year, Mon day year, compact 8-digit, bare 4-digit year. 92% same-label / "
             "99.6% family precision; the difference is the age_90_plus promotion.",
         examples=("Patient DOB: 04/06/1959 was seen.", "<tr><th>DOB</th><td>1950</td></tr>", "Date of Birth: 1931-05-02",
                   "DOB Source: 1950-03-04")),
    Rule("date", "dob_after_guarantor_tokens",
         r"\(\((?:GUARANTOR|PATIENT)[A-Z_]*NAME[A-Z_]*\)\)(?:[ ,]*\(\((?:GUARANTOR|PATIENT)[A-Z_]*\)\))*[ ,]+(?P<val>" + YEAR + r"|" + YEAR + r"-\d{2}-\d{2}|\d{1,2}/\d{1,2}/" + YEAR + r")(?![\d/-])",
         doc="Corpus-specific: the upstream de-identifier masked the guarantor / patient name tokens of a demographic line and "
             "left the birth year after them ('((GUARANTORLASTNAME)), ((GUARANTORFIRSTNAME)) ((GUARANTORMIDDLEINITIAL)) 1957'). "
             "144k+ spans; 82% precision.",
         examples=("((GUARANTORLASTNAME)), ((GUARANTORFIRSTNAME)) ((GUARANTORMIDDLEINITIAL)) 1957 F",)),
    Rule("date", "birth_v_attribute",
         r"(?:<|&lt;)(?:birth_dttm|birthTime|birth_date|dob)\b[^<>&]*?\b(?:V|value)\s*=\s*(?:\"|&quot;)(?P<val>\d{4}[\d\-T:. ]{0,20})(?:\"|&quot;)", re.I,
         doc="Vendor-XML / CCDA birth date carried in a V= or value= attribute of a birth element.",
         examples=('<birth_dttm V="1931-05-02T00:00:00"/>',)),
    Rule("age_90_plus", "age_labelled_90plus",
         labelled(r"(?:age|aged|yo|y/o)", r"(?:9\d|1[01]\d)(?![\d])"),
         doc="'Age: 92' style: an age label followed by a number from 90 to 119. Ages under 90 are not PHI.",
         examples=("Age: 92 Gender: F",)),
    Rule("age_90_plus", "age_suffix_90plus",
         r"(?<!\d)(?P<val>9\d|1[01]\d)\s?(?:-?\s?(?:yo|y/o|y\.o\.|yrs?|years?)(?:[- ]old)?)\b", re.I,
         doc="'92 yo', '95-year-old', '101 yrs': a number from 90 to 119 followed by an age suffix.",
         examples=("a 94 yo female", "a 101-year-old man")),
]

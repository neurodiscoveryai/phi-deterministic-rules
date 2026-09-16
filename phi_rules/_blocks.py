"""Shared regex building blocks.

Every block is a plain ``r"..."`` string joined by ``+`` -- never an f-string -- so a quantifier such as
``{1,24}`` can never be mis-read as a format field (an ``rf"..."`` pattern once turned ``{2,60}`` into the
tuple ``(2, 60)`` and two rules silently matched nothing). Blocks are inlined into the rule patterns, so
the regexes shown in the README are complete and copy-pasteable.
"""

# Markup (raw or HTML-escaped), entities and whitespace that may sit between a label and its value.
GAP = r"(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;|&#160;|&#xa0;|\*|\u00a0){0,8}"

# A colon, or a table-cell boundary (</th><td>, <th>Label <td>) -- the strict separator used for
# structured labels such as Provider / Patient Name / Location.
SEP_KV = (r"(?:\s*:\s*|\s*(?:</t[hd]>|&lt;/t[hd]&gt;)?\s*(?:<td[^>]*>|&lt;td[^&]*&gt;)\s*)"
          + r"(?:\s|<[^<>]{0,200}>|&lt;[^&]{0,200}&gt;|&nbsp;){0,6}")

# Loose label -> value separator: punctuation or the copulas is/was/of (DOB: "date of birth is 1950").
SEP = GAP + r"(?:[:#=\-–]|is|was|of)?" + GAP + r"(?:[:#=\-]" + GAP + r")?"

# Strict separator: punctuation only, no filler words.
SEP_STRICT = GAP + r"[:#=\-\u2013]?" + GAP + r"(?:[:#=\-]" + GAP + r")?"

# US state / territory codes.
STATES = r"(?:A[LKZR]|C[AOT]|D[EC]|FL|GA|HI|I[DLNA]|K[SY]|LA|M[EDAINSOT]|N[EVHJMYCD]|O[HKR]|PA|RI|S[CD]|T[NX]|UT|V[TA]|W[AVIY]|PR|VI|GU)"

YEAR = r"(?:18|19|20)\d{2}"
MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?"

# Date value shapes, longest first: ISO (optionally with time), US numeric, 2-digit year, day-Mon-year,
# Mon day, year, compact 8-digit, bare 4-digit year.
DATE_VALUE = (r"(?:" + YEAR + r"-\d{1,2}-\d{1,2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?)?"
              + r"|\d{1,2}[-/.]\d{1,2}[-/.]" + YEAR
              + r"|\d{1,2}[-/.]\d{1,2}[-/.]\d{2}"
              + r"|\d{1,2}[- ]" + MONTH + r"[- ,]+\d{2,4}"
              + r"|" + MONTH + r"\s+\d{1,2},?\s+" + YEAR
              + r"|" + YEAR + r"\d{2}\d{2}"
              + r"|" + YEAR + r")")

# Capitalised words that must not be swallowed as a name token (field labels, sentence starters).
NOT_KW = (r"(?!(?:DOB|DOD|MRN|Age|Sex|Gender|Date|Phone|Fax|Address|Room|Location|Patient|Provider|Physician|Visit|Encounter|Account|Insurance|Dr|MD|DO|NP|PA|RN|Male|Female|Ph|Tel|Cell|Pager|Email|Signed|Dictated|Printed|Page|Report|Result|Results|"
          r"Information|Preference|Place|Name|Value|Range|Status|Type|Number|History|Summary|Data|List|Note|Notes|Time|Test|Tests|Order|Orders|Medication|Medications|Diagnosis|Problem|Plan|Assessment|Exam|Vitals|Labs|Lab|Allergies|Allergy|"
          r"Service|Department|Clinic|Hospital|Unit|Level|Total|Amount|Balance|Due|Payment|Code|Description|Comments|Comment|Reason|Source|Site|Referral|Consult|Progress|Discharge|Admission|Admit|Chief|Complaint|Family|Social|Review|Systems|Present|Illness|"
          r"The|This|These|That|Your|You|We|Our|Please|Negative|Positive|Normal|Abnormal|Final|Pending|See|Not|None|Yes|Unknown|Other|Same|New|Old|For|And|With|Are|Was|Were|Has|Have|Per|From)(?![A-Za-z]))")

# A name token: a capitalised word or an initial; a name: optional leading initial, one word, up to
# three more tokens (John A. Smith / SMITH, JOHN / J. Smith).
NAME_TOKEN = r"(?:" + NOT_KW + r"(?:[A-Z][A-Za-z'\-]{1,24}|[A-Z]\.?))"
NAME_WORD = r"(?:" + NOT_KW + r"[A-Z][A-Za-z'\-]{1,24})"
NAME = r"(?:[A-Z]\.?\s+)?" + NAME_WORD + r"(?:,?\s+" + NAME_TOKEN + r"){0,3}"

# Clinical credentials that follow a clinician's name.
CRED = r"(?:M\.?D\.?|D\.?O\.?|N\.?P\.?|P\.?A\.?(?:-C)?|R\.?N\.?|L\.?P\.?N\.?|C\.?N\.?A\.?|Ph\.?D\.?|D\.?P\.?M\.?|F\.?A\.?C\.?P\.?|M\.?B\.?B\.?S\.?|A\.?P\.?R\.?N\.?|C\.?R\.?N\.?P\.?|D\.?D\.?S\.?|O\.?D\.?|Psy\.?D\.?)"

# Phone value shapes: formatted 10-digit, bare 10/11-digit, 7-digit local (only meaningful when labelled).
PHONE_VALUE = (r"(?:\+?1[-.\s]?)?(?:\(\d{3}\)\s?|\d{3}[-./\s])\d{3}[-.\s]\d{4}"
               r"|\+?1?\d{10}"
               r"|\d{3}-\d{4}")

# Identifier value: 3-30 alphanumerics with -/. separators.
IDV = r"[A-Za-z0-9][A-Za-z0-9\-/.]{2,29}"

# Location value: short, no markup, no list separators.
LOC_VALUE = r"[^<>\n,;|]{1,40}?"

# Institutional suffixes; a capitalised phrase ending in one of these is a facility or organization.
ORG_SUFFIX = (r"(?:Hospital|Medical\s+Cent(?:er|re)|Health\s*(?:care)?\s*System|Healthcare|Clinic|Regional\s+Medical\s+Center|"
              r"Cancer\s+(?:Center|Institute)|Institute|Laboratories|Pharmacy|University|College|"
              r"Physicians|Associates|Medical\s+Group|Foundation|Inc\.?|LLC|L\.L\.C\.|Corp(?:oration)?\.?|Co\.|"
              r"Urgent\s+Care|Family\s+(?:Practice|Medicine)|Medical\s+Associates|Neurology\s+Associates|Health\s+Partners|Medical\s+Practice)")
ORG_NAME = (r"[A-Z][A-Za-z&.'\-]*(?:\s+(?:of|the|and|for|&|at)\s+|\s+)(?:[A-Z][A-Za-z&.'\-]*(?:\s+(?:of|the|and|&|at)\s+|\s+)){0,5}"
            + ORG_SUFFIX)

BLOCKS = {
    "GAP": GAP, "SEP": SEP, "SEP_STRICT": SEP_STRICT, "SEP_KV": SEP_KV, "STATES": STATES, "YEAR": YEAR,
    "MONTH": MONTH, "DATE_VALUE": DATE_VALUE, "NOT_KW": NOT_KW, "NAME_TOKEN": NAME_TOKEN, "NAME_WORD": NAME_WORD,
    "NAME": NAME, "CRED": CRED, "PHONE_VALUE": PHONE_VALUE, "IDV": IDV, "LOC_VALUE": LOC_VALUE,
    "ORG_SUFFIX": ORG_SUFFIX, "ORG_NAME": ORG_NAME,
}


def labelled(label, value, ci_value=True, strict=False):
    """Pattern for ``<label><separator><value>``: the label is always case-insensitive (scoped ``(?i:...)``);
    the value is case-insensitive unless ``ci_value=False`` (names and organizations keep their case)."""
    v = "(?i:" + value + ")" if ci_value else value
    return (r"(?<![A-Za-z])(?i:" + label + r")(?![A-Za-z])" + (SEP_STRICT if strict else SEP) + r"(?P<val>" + v + r")")

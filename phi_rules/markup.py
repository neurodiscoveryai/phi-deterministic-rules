"""Structured markup: the attribute / element / JSON KEY decides the label.

In XML, CCDA, vendor exports and escaped HTML the PHI sits in values whose key names it: ``PharmacyCity="…"``,
``orderingmdid="…"``, ``DOB="…"``, ``<encounterID>…</encounterID>``, ``"CREATEDBY":"…"``. One key-to-label map
recovers 60-99% of every label in such documents (progressnotes census). Presentational HTML attributes and
structural ids (category / item / flowsheet …) are skipped by policy; system accounts and enum values are
skipped via SKIP_VALUES.
"""
import re

from .engine import Rule

# Attribute names that are DOM hooks, code-set plumbing or layout -- never PHI-bearing.
PRESENTATIONAL = frozenset({"class", "id", "style", "for", "headers", "scope", "type", "role", "align", "border", "width",
                            "height", "colspan", "rowspan", "xmlns", "version", "encoding", "root", "codesystem",
                            "codesystemname", "templateid", "code", "displayname", "unit", "value", "lang", "dir", "title",
                            "alt", "href", "src", "rel", "target", "content", "http-equiv", "charset", "name", "valign",
                            "bgcolor", "color", "size", "face", "cellpadding", "cellspacing", "nowrap", "onclick",
                            "e", "c", "v", "t", "s", "p", "r", "n", "k", "x", "y"})

# Internal schema identifiers (FlowsheetID, CategoryId, StatusID ...): a policy choice -- the reference model
# redacted these in about half of the records; this library never does.
STRUCTURAL_KEYS = re.compile(r"(?:category|item|prop|struct|cat|exam|type|template|section|concept|group|list|field|form|question|answer|"
                             r"option|code|flowsheet|sheet|status|unit|mode|sort|version|schema|def|definition|element|el|node|parent|child|"
                             r"style|layout|page|tab|panel|column|col|row|cell|level|rank|resource|ros|doc|component|attachment|file|image|img|"
                             r"medication|med|drug|rx|dose|order|result|lab|test|panel|obs|observation|problem|diagnosis|dx|allergy|proc|procedure|cpt|icd|ndc|loinc|snomed)(?:id|ids|no|num|number|key|ref|seq)$")

# (regex on the lowercased key, label) -- first match wins.
KEY_RULES = [
    (re.compile(r"(?:phone|tel(?:ephone)?|mobile|cell|pager)"), "phone"),
    (re.compile(r"fax"), "fax"),
    (re.compile(r"(?:zip|postal)"), "zip_code"),
    (re.compile(r"(?:city|state|county|address|addr|street|country)"), "address"),
    (re.compile(r"(?:dob|birth|dod|death)"), "date"),
    (re.compile(r"(?:e-?mail)"), "email"),
    (re.compile(r"(?:url|website|web)"), "url"),
    (re.compile(r"(?:user_?name|userid|user_?id|login|createdby|changedby|modifiedby|enteredby|signedby|author)"), "signature_block"),
    (re.compile(r"(?:pharmacy|facility|hospital|clinic|organi[sz]ation|employer|practice|institution|lab(?:oratory)?)(?:.*name)?$"), "hospital_name"),
    (re.compile(r"(?:doctor|physician|provider|prescriber|ordering|referring|attending|md|surgeon|pcp)(?:.*name)?$"), "doctor_name"),
    (re.compile(r"^(?:f|l|m)name$|(?:first|last|given|family|middle|sur|full|patient|pt|guarantor|spouse|contact|person|member|display|nick|maiden)_?name$|^(?:giv|fam|mid|pfx|sfx)$"), "person_name"),
    (re.compile(r"(?:serial|device|implant)"), "device_id"),
    (re.compile(r"(?:protocol|study|subject|participant|screening|randomi[sz]ation)"), "study_id"),
    (re.compile(r"(?:ssn|mrn|npi|dea|identifier|acct|account)$|(?:id|ids|no|num|number|key|ref|seq)#?$"), "identified_number"),
]


def label_for_key(key, value):
    """Label implied by an attribute / element / JSON key (lowercased, trailing ``#``/digits dropped);
    ``None`` means the value is not PHI-bearing. Value-shape checks keep e.g. ``Phone="N/A"`` out."""
    k = re.sub(r"[\d#]+$", "", key.lower().replace("-", "").replace(":", "_"))
    if k in PRESENTATIONAL or len(k) < 2 or STRUCTURAL_KEYS.fullmatch(k):
        return None
    if k in ("age", "patientage", "pt_age", "ageyears", "age_years"):
        m = re.match(r"\s*(\d{2,3})", value)
        return "age_90_plus" if m and int(m.group(1)) >= 90 else None
    for pat, lab in KEY_RULES:
        if pat.search(k):
            if lab in ("phone", "fax") and not re.search(r"\d{7}", re.sub(r"\D", "", value)):
                return None
            if lab == "zip_code" and not re.fullmatch(r"\d{5}(?:-?\d{4})?", value.strip()):
                return None
            if lab == "date" and not re.search(r"\d{4}", value):
                return None
            if lab in ("identified_number", "study_id", "device_id") and not re.search(r"[A-Za-z0-9]", value):
                return None
            if lab in ("person_name", "doctor_name", "signature_block", "hospital_name", "address") and not re.search(r"[A-Za-z]", value):
                return "identified_number" if lab == "signature_block" and re.fullmatch(r"\d+", value.strip()) else None   # CreatedBy="3"
            return lab
    return None


def _by_attr(m, group, value):
    return label_for_key(m.group("attr"), value)


def _by_tag(m, group, value):
    return label_for_key(m.group("tag"), value)


RULES = [
    Rule("identified_number", "json_by_name",
         r"\"(?P<attr>[A-Za-z_][\w.-]{1,40})\"\s*:\s*\"(?P<val>[^\"]{1,80})\"", 0,
         doc="A JSON string field: the KEY decides the label via the key-to-label map (e.g. \"CREATEDBY\" -> signature_block, "
             "\"PATIENTID\" -> identified_number). Keys that map to nothing are ignored.",
         examples=('{"SOURCE":"backfill","CREATEDBY":"asample","PATIENTID":"884"}',), relabel=_by_attr),
    Rule("identified_number", "attr_by_name",
         r"(?<![\w.-])(?P<attr>[A-Za-z_][\w.:-]{1,40}#?)\s*=\s*(?:\"|&quot;|')(?P<val>[^\"'&<>]{1,80}?)(?:\"|&quot;|')", 0,
         doc="An XML/HTML attribute (raw or HTML-escaped quotes): the attribute NAME decides the label -- PharmacyCity= -> address, "
             "PharmacyPhone= -> phone, DOB= -> date, orderingmdid= -> identified_number, CreatedUserName= -> signature_block. "
             "Presentational attributes, structural ids, enum/boolean values and system accounts are skipped. This is the single "
             "highest-yield rule on vendor XML; its precision against the reference model is ~43% only because the model itself "
             "redacted the same keys inconsistently.",
         examples=('<Rx PharmacyCity="Anytown" PharmacyState="MI" PharmacyZip="48000" PharmacyPhone="5555551212" orderingmdid="4471" CreatedBy="3" CreatedUserName="asample"/>',),
         relabel=_by_attr),
    Rule("identified_number", "elem_by_name",
         r"(?:<|&lt;)(?P<tag>[A-Za-z_][\w.:-]{1,40}#?)(?:\s[^<>&]*?)?(?:>|&gt;)\s*(?P<val>[^<>&]{1,80}?)\s*(?:<|&lt;)/(?P=tag)(?:>|&gt;)", 0,
         doc="A leaf XML element (raw or escaped): the tag NAME decides the label -- <encounterID>, <HospitalName>, <doctor>, "
             "<DOB>, <PharmacyFax>. Same key map and skips as attr_by_name; ~92% precision.",
         examples=("<encounterID>88213</encounterID><HospitalName>Example General</HospitalName><doctor>Jordan Q Sample</doctor>",
                   "&lt;DOB&gt;1950-03-04&lt;/DOB&gt;"),
         relabel=_by_tag),
]

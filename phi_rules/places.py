"""address, zip_code, location.

The model splits a "City, ST 12345" line into city and state (both address) and the ZIP (zip_code); 32% of all
address spans are bare 2-letter state codes for that reason. Structured lines (City-ST-ZIP, street lines, PO
boxes, City/State/Zip attributes) are deterministic; a city name alone in prose needs a gazetteer.
"""
import re

from ._blocks import GAP, LOC_VALUE, SEP_KV, STATES, labelled
from .engine import Rule


def _csz(m, group, value):
    return "zip_code" if group == "val3" else "address"


def _addr_v(m, group, value):
    t = m.group("tag").upper()
    lab = "zip_code" if t == "ZIP" else "phone" if t in ("PHONE", "TEL") else "fax" if t == "FAX" else "address"
    if lab == "zip_code" and not re.fullmatch(r"\d{5}(?:-?\d{4})?", value.strip()):
        return None
    if lab in ("phone", "fax") and not re.search(r"\d{7}", re.sub(r"\D", "", value)):
        return None
    return lab


RULES = [
    Rule("address", "addr_v_attribute",
         r"(?:<|&lt;)(?P<tag>LINE_?\d|STA|CTY|ZIP|CITY|STATE|STREET|ADDR|PHONE|FAX|TEL)\b[^<>&]*?\bV\s*=\s*(?:\"|&quot;)(?P<val>[^\"&]{1,60})(?:\"|&quot;)", re.I,
         doc="Vendor-XML address block with values in V= attributes: <LINE_1 V=…> <CTY V=…> <STA V=…> -> address, <ZIP V=…> -> "
             "zip_code, <PHONE V=…> -> phone, <FAX V=…> -> fax. 99.6% precision.",
         examples=('<ADDR><LINE_1 V="12 Main St"/><CTY V="Anytown"/><STA V="MI"/><ZIP V="48000"/><PHONE V="5555551212"/></ADDR>',),
         relabel=_addr_v),
    Rule("address", "city_state_zip",
         r"(?<![A-Za-z])(?P<val>[A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]+){0,2}),?" + GAP + r"(?<![A-Za-z])(?P<val2>" + STATES + r")\.?" + GAP + r"(?P<val3>\d{5}(?:-\d{4})?)(?![\d-])",
         doc="The 'City, ST 12345' line: a city of 1-3 capitalised words, a real US state code (not glued to a preceding word), "
             "a 5- or 9-digit ZIP; markup may sit between the parts. Emits city and state as address and the ZIP as zip_code "
             "(three groups val/val2/val3). 88% same-label / 95% family precision.",
         examples=("Sample Hills, MI 48000", "Anytown,<br/> MI 48000-1234"), relabel=_csz),
    Rule("address", "upstream_city_then_state",
         r"\(\([A-Za-z_]*(?:CITY|City)[A-Za-z_]*\)\)\s*,?" + GAP + r"(?P<val>[A-Z]{2}|[A-Z][a-z]+)(?=[\s,.<]|$)",
         doc="Corpus-specific: the upstream de-identifier masked the city token and left the state after it "
             "('((PATIENTCITY)), FL'). 74% precision.",
         examples=("((PATIENTCITY)), FL 33000",)),
    Rule("address", "street_line",
         r"(?<![\w#])(?P<val>\d{1,6}[A-Za-z]?\s+(?:[NSEW]\.?\s+|(?:North|South|East|West)\s+)?(?:[A-Z0-9][A-Za-z0-9'.\-]*\s+){1,4}"
         r"(?i:St(?:reet)?|Ave(?:nue)?|Rd|Road|Blvd|Boulevard|Dr(?:ive)?|Ln|Lane|Ct|Court|Way|Pkwy|Parkway|Hwy|Highway|Pl(?:ace)?|Ter(?:race)?|Cir(?:cle)?|Trl|Trail|Sq(?:uare)?|Loop|Route|Rte|Pike|Turnpike|Tpke)\.?"
         r"(?:\s*,?\s*(?i:Suite|Ste|Apt|Unit|#|Bldg|Building|Floor|Fl|Rm|Room)\.?\s*#?\s*[A-Za-z0-9\-]+)?)(?![A-Za-z])",
         doc="A street line: house number, optional direction, 1-4 capitalised words, a street suffix (St, Ave, Rd, Blvd, Dr, Ln, "
             "Ct, Way, Pkwy, Hwy, Pl, Ter, Cir, Trl, Sq, Loop, Route …), optional Suite/Apt/Unit/Bldg/Floor. The words must be "
             "capitalised so medication sigs ('take 1 tablet by oral route daily') cannot match. 94% precision.",
         examples=("at 1234 E Sample Creek Rd, Suite 100 and", "1234 MAIN ST, SUITE 100")),
    Rule("address", "po_box",
         r"(?P<val>P\.?\s?O\.?\s?Box\s+\d+)", re.I,
         doc="P.O. Box nnn. 81% precision.",
         examples=("mail to PO Box 1234",)),
    Rule("address", "address_labelled",
         labelled(r"(?:address|addr|street(?:\s+address)?|residence|home\s+address|mailing\s+address)", r"[^<>\n]{5,80}?(?=\s*(?:<|\n|$))"),
         doc="Address / Street / Residence / Home or Mailing address label followed by the rest of the line. 32% precision -- the "
             "value is whatever follows to the end of the line; keep only where the other address rules do not fire.",
         examples=("Home Address: 12 Sample Ave<br>",)),
    Rule("zip_code", "zip_labelled",
         labelled(r"(?:zip(?:\s*code)?|postal\s*code)", r"\d{5}(?:-\d{4})?(?!\d)"),
         doc="Zip / Zip Code / Postal Code label followed by a 5- or 9-digit ZIP. 100% precision in the sample.",
         examples=("Zip: 48000",)),
    Rule("zip_code", "zip_after_state",
         r"(?<![A-Za-z0-9])" + STATES + r"\.?" + GAP + r"(?P<val>\d{5}(?:-\d{4})?)(?![\d-])",
         doc="A 5- or 9-digit ZIP right after a US state code (…, MI 48000). 92% same-label / 95% family precision.",
         examples=("Anytown, MI 48000-1234",)),
    Rule("location", "location_labelled",
         r"(?<![A-Za-z])(?i:(?:patient\s+location|charted\s+location|location|loc|room|rm|bed|ward|service\s+dept\.?|service\s+department|clinic\s+site|department))" + SEP_KV + r"(?P<val>" + LOC_VALUE + r")(?=\s*(?:<|&lt;|\n|,|;|\||$))",
         doc="Patient Location / Charted Location / Location / Loc / Room / Bed / Ward / Service Dept. / Department label with a "
             "colon or table-cell boundary, followed by a short value. 35% same-label / 40% family precision and ~30% recall: most "
             "location spans in the corpus are clinic or site names in free text -- lexicon territory.",
         examples=("Patient Location: MS Clinic 3<br>", "<th>Service Dept. <td>Neurology 2")),
]

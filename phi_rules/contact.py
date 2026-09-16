"""phone, fax, email, url, ip_address.

Formatted 10-digit numbers are phones on their own (prompt rule: an unlabelled ambiguous number defaults to
phone); a bare 10-digit run needs a Phone/Fax label, a tel: link, a phone-named attribute, or the position
right after a ZIP in an address block. Fax is decided by the nearest label. E-mail and URLs are pure shapes.
"""
import re

from ._blocks import PHONE_VALUE, labelled
from .engine import Rule


def _ip_octets(m, group, value):
    return None if any(int(o) > 255 for o in value.split(".")) else "ip_address"


RULES = [
    Rule("phone", "phone_after_zip_or_comma",
         r"(?:(?<=\d{5}\s)|(?<=\d{4}\s)|(?<=,\s)|(?<=,))(?P<val>\d{10})(?![\d-])",
         doc="A bare 10-digit number directly after a ZIP code (…NY 10000-1234 5555551234) or after a comma in an address / "
             "signature line. 98% precision.",
         examples=("((PatientCity)), NY 10000-1234 5555551234 Fax",)),
    Rule("fax", "fax_labelled",
         labelled(r"(?:fax|facsimile|fax\s*(?:#|no\.?|number))", PHONE_VALUE),
         doc="Fax / Facsimile / Fax # label followed by a phone-shaped value. 97% precision; 94% same-family recall.",
         examples=("Fax: 555-765-4321",)),
    Rule("phone", "phone_labelled",
         labelled(r"(?:phone|ph|tel|telephone|cell|mobile|pager|pgr|contact|call|office|home|work|main|direct)(?:\s*(?:#|no\.?|number))?", PHONE_VALUE),
         doc="Phone / Ph / Tel / Cell / Mobile / Pager / Office / Home / Work label followed by a phone-shaped value "
             "(formatted, bare 10/11 digits, or 7-digit local). 98% precision.",
         examples=("Ph: (555) 123-4567", "Cell 5550101234")),
    Rule("phone", "phone_formatted_unlabelled",
         r"(?<![\d(-])(?P<val>(?:\+?1[-.\s]?)?(?:\(\d{3}\)\s?|\d{3}[-.]\s?)\d{3}[-.]\d{4})(?![\d-])",
         doc="A formatted North-American number with no label: (555) 123-4567, 555-123-4567, 555.123.4567, +1 555-123-4567. "
             "89% same-label / 96% family precision (some are labelled fax).",
         examples=("call 555-123-4567 today",)),
    Rule("phone", "tel_href",
         r"tel:(?P<val>\+?[\d\-().\s]{7,20})", re.I,
         doc="The number inside an HTML tel: link.",
         examples=('<a href="tel:+15550101234">call</a>',)),
    Rule("email", "email_shape",
         r"(?<![A-Za-z0-9._%+-])(?P<val>[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
         doc="local@domain.tld. 100% precision in the sample; e-mail is rare in this corpus (20k spans).",
         examples=("contact jane.doe@example.org for",)),
    Rule("url", "url_scheme",
         r"(?P<val>\bhttps?://[^\s<>\"'()]+|\bwww\.[^\s<>\"'()]+)", re.I,
         doc="http(s):// or www. URLs. 98% precision.",
         examples=("visit https://portal.example.com/x?y=1 now",)),
    Rule("url", "url_bare_domain",
         r"(?<![\w@.\-/])(?P<val>[A-Za-z][A-Za-z0-9\-]{1,40}(?:\.[A-Za-z0-9\-]{1,40})*\.(?:com|org|net|edu|gov|io|us|info|health)(?:/[^\s<>\"']*)?)(?![\w.\-])",
         doc="A bare domain (portal.example.com, example.org/path) without a scheme. 69% precision: vendor domains in boilerplate "
             "were often left alone by the reference model.",
         examples=("go to portal.example.com/results",)),
    Rule("ip_address", "ip_shape",
         r"(?<![\d.])(?P<val>(?:\d{1,3}\.){3}\d{1,3})(?![\d.])",
         doc="Dotted quad with every octet <= 255 (OIDs like 2.16.840.1 are excluded by the octet check). 294 spans corpus-wide, "
             "0/23 hits in the sample -- near-irrelevant here, kept for completeness.",
         examples=("from 192.168.10.44 at",), relabel=_ip_octets),
]

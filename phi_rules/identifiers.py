"""identified_number, device_id, study_id.

identified_number is 74% of all model-redacted spans (340M of them in progressnotes, where every attribute
value under an identifier-like key was redacted). Outside structured markup 78% of spans are plain digit runs
behind a label: MRN, Patient ID, Insurance #, Group #, Account ID, ID#, or an identifier key in a URL/attribute
(patientid=…). The LABEL carries the signal: a bare number is never redacted by shape (code sets, doses and
counts look identical). Structured-markup keys are handled in markup.py.
"""
import re

from ._blocks import IDV, SEP_STRICT, labelled
from .engine import Rule

RULES = [
    Rule("identified_number", "id_labelled",
         r"(?<![A-Za-z0-9])(?i:(?:MRN|MR\s?#|medical\s+record\s+(?:number|no\.?|#)|patient\s*id(?:entifier)?|patientid|pt\s*id|chart\s*(?:id|#|no\.?|number)|"
         r"account\s*(?:id|#|no\.?|number)|acct\s*(?:#|no\.?)|insurance\s*(?:id|#|no\.?|number)|policy(?:/group)?\s*(?:#|no\.?|number)|group\s*(?:#|no\.?|number|id)|"
         r"member\s*(?:id|#|no\.?|number)|subscriber\s*(?:id|#|no\.?)|encounter\s*(?:id|#|no\.?|number)|visit\s*(?:id|#|no\.?|number)|admission\s*(?:#|no\.?|number)|"
         r"accession\s*(?:#|no\.?|number)|specimen\s*(?:id|#|no\.?)|order\s*(?:#|no\.?|id|number)|req(?:uisition)?\s*(?:#|no\.?)|"
         r"ID\s*(?:#|no\.?|number)|ID(?=\s*:)|SSN(?=\s*[#:]|\s)|social\s+security(?:\s+(?:number|#|no\.?))?|NPI\s*[#:]|DEA\s*[#:]|license\s*(?:#|no\.?|number)|claim\s*(?:#|no\.?|number)|"
         r"guarantor\s*(?:id|#|no\.?)|case\s*(?:#|no\.?|number)|report\s*(?:#|no\.?|number)|document\s*(?:id|#|no\.?)|ref(?:erence)?\s*(?:#|no\.?|number)|file\s*(?:#|no\.?)))"
         + SEP_STRICT + r"(?P<val>" + IDV + r")",
         doc="An identifier label (MRN, Patient ID, Chart #, Account/Insurance/Policy/Group/Member/Subscriber #, Encounter/Visit/"
             "Accession/Specimen/Order #, ID#, SSN, NPI:, DEA:, License/Claim/Case/Report/Document/Ref/File #) followed by a "
             "3-30 character alphanumeric value. Short acronyms (ID, SSN, NPI, DEA) need an explicit marker so 'DEA' inside a "
             "hex string cannot fire. 81% precision.",
         examples=("MRN: 00123456 Encounter", "Insurance # : XYZ12345678<br>", "Order # 1234567890 placed")),
    Rule("identified_number", "id_attribute",
         r"(?:patient|chart|account|encounter|visit|member|subscriber|person|record|order|specimen|accession|document|guarantor|policy)_?(?:id|no|num|number)\s*['\"]?\s*[:=]\s*['\"]?(?P<val>" + IDV + r")", re.I,
         doc="An identifier key written as key=value or key:value outside quoted markup (URLs, query strings, key/value dumps): "
             "patientid=8842719, encounter_no: 1234. 71% precision.",
         examples=("view.aspx?menu=1&patientid=8842719&x",)),
    Rule("identified_number", "xml_id_extension",
         r"<id\b[^>]*\bextension\s*=\s*[\"'](?P<val>[^\"']{2,40})[\"']", re.I,
         doc="CCDA <id root=… extension=…/>: the extension is the record identifier (the root is an OID, never PHI). Inert in the "
             "evaluation sample -- the archived progressnotes are vendor XML rather than CCDA -- kept for CCDA inputs.",
         examples=('<id root="2.16.840.1" extension="MRN-77812"/>',)),
    Rule("identified_number", "ssn_shape",
         r"(?<![\d-])(?P<val>\d{3}-\d{2}-\d{4})(?![\d-])",
         doc="A US Social Security Number shape ddd-dd-dddd on its own (no label needed).",
         examples=("SSN 123-45-6789 on file",)),
    Rule("device_id", "device_labelled",
         labelled(r"(?:serial\s+(?:number|no\.?|#)|serial|s/n|sn|scanner\s*#|device\s+id|implant\s+id|model\s*(?:#|no\.?)|lot\s*(?:#|no\.?)|udi)",
                  r"(?=[A-Za-z0-9\-]*\d)[A-Za-z0-9][A-Za-z0-9\-]{3,24}", strict=True),
         doc="Serial Number / S/N / SN / Scanner # / Device ID / Implant ID / Model # / Lot # / UDI followed by an alphanumeric "
             "value that contains a digit. Low precision in the sample (device_id is 26k spans corpus-wide); DE should decide "
             "whether device serials are in scope.",
         examples=("Serial Number: SN0012345X was",)),
    Rule("study_id", "study_labelled",
         labelled(r"(?:protocol(?:\s*(?:#|no\.?|number|id))?|study\s*(?:#|no\.?|number|id)|subject\s*(?:#|no\.?|number|id)|participant(?:\s*(?:#|no\.?|number|id))?|site\s*(?:#|no\.?|number)|screening\s*(?:#|no\.?|number|id)|randomi[sz]ation\s*(?:#|no\.?|number|id)|enrollment\s*(?:#|no\.?|number|id)|IRB\s*(?:#|no\.?)?)",
                  r"(?=[A-Za-z0-9\-]*\d)[A-Za-z0-9][A-Za-z0-9\-]{2,24}", strict=True),
         doc="Protocol / Study # / Subject ID / Participant / Site Number / Screening / Randomization / Enrollment / IRB label "
             "followed by a code containing a digit. 'study' alone is never a trigger (imaging studies).",
         examples=("Protocol: AB1-CD-2345 Subject",)),
    Rule("study_id", "nct_shape",
         r"(?P<val>NCT\d{8})", re.I,
         doc="A ClinicalTrials.gov registry number NCTnnnnnnnn.",
         examples=("registered as NCT01234567",)),
]

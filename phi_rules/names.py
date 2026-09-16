"""person_name, doctor_name, signature_block -- the 'names' family.

Names are the hard class. The model's choice between the three labels is context, not text (8,430 literals
occur under all three), so detect at the family level and let the anchor assign the label: Dr. / a credential /
a provider label -> doctor_name; Signed by / Dictated by / logins -> signature_block; Patient Name / honorifics /
relatives / salutations -> person_name. About half of all person_name spans have no anchor at all (a name in
running prose); those need a lexicon or a model.
"""
from ._blocks import CRED, NAME, NAME_TOKEN, NAME_WORD, SEP_KV, SEP_STRICT
from .engine import Rule

RULES = [
    Rule("doctor_name", "after_final_column",
         r"\|\s*Final\s*\|\s*(?P<val>" + NAME + r")",
         doc="Lab-result tables: the ordering clinician in the column after '| Final |'. 82% same-label / 99% family precision.",
         examples=("| 2024-01-01 12:00 | Final | Jordan Q Sample",)),
    Rule("person_name", "elem_v_attribute",
         r"(?:<|&lt;)(?P<tag>GIV|FAM|MID|PFX|SFX|given|family|middle|prefix|suffix)\b[^<>&]*?\bV\s*=\s*(?:\"|&quot;)(?P<val>[^\"&]{1,40})(?:\"|&quot;)",
         doc="Vendor-XML name parts carried in V= attributes: <GIV V=…/> <FAM V=…/> <MID V=…/>. 74% family precision (these are "
             "mostly provider names in the corpus, which the model labelled doctor_name).",
         examples=('<person_name><nm><GIV V="Mary"/><FAM V="Jones"/></nm></person_name>',)),
    Rule("doctor_name", "dr_prefix",
         r"(?<![A-Za-z])Dr\.?\s+(?P<val>" + NAME + r")",
         doc="'Dr.' or 'Dr' followed by a name (up to four tokens). The title is not part of the value. 81% same-label / 84% "
             "family precision.",
         examples=("seen by Dr. John Smith today",)),
    Rule("doctor_name", "name_with_credential",
         r"(?<![A-Za-z])(?P<val>" + NAME + r")(?:\s*,\s*|\s+)" + CRED + r"(?![A-Za-z])",
         doc="A name followed by a clinical credential: MD, DO, NP, PA(-C), RN, LPN, CNA, PhD, DPM, FACP, MBBS, APRN, CRNP, DDS, OD, "
             "PsyD (dots optional). The credential is not part of the value. 57% same-label / 91% family precision (the model "
             "often labelled these signature_block).",
         examples=("Ordered by Jane Q. Public, MD on",)),
    Rule("doctor_name", "provider_labelled",
         r"(?<![A-Za-z])(?i:(?:(?:ordering|referring|attending|treating|consulting|requesting|primary\s+care|responsible|admitting|rendering|supervising|performing|interpreting|reading)\s+(?:provider|physician|md|doctor|practitioner|clinician)|provider|physician|PCP|surgeon|pathologist|radiologist|neurologist|cardiologist|laboratory\s+director|medical\s+director))" + SEP_KV + r"(?:Dr\.?\s+)?(?P<val>" + NAME + r")",
         doc="Provider / Physician / Ordering Provider / Referring Physician / PCP / Surgeon / Laboratory Director … with a colon "
             "or table-cell boundary, followed by a name (optional Dr.). 68% same-label / 86% family precision.",
         examples=("<th>Ordering Provider</th><td>Casey J Sampleton</td>",)),
    Rule("doctor_name", "by_verb_name",
         r"(?<![A-Za-z])(?i:(?:performed|read|interpreted|reviewed|ordered|examined|requested|seen|evaluated|treated|referred|followed)\s+by)(?![A-Za-z])" + SEP_STRICT + r"(?:Dr\.?\s+)?(?P<val>" + NAME_WORD + r"(?:,?\s+" + NAME_TOKEN + r"){1,3})",
         doc="'performed by / read by / seen by / ordered by …' followed by a name of at least two tokens. 40% same-label / 81% "
             "family precision (the model labels these doctor, person or signature depending on context).",
         examples=("Study performed by Jordan Q Sample and",)),
    Rule("signature_block", "signature_labelled",
         r"(?<![A-Za-z])(?i:(?:electronically\s+signed\s+by|e-?signed\s+by|signed\s+by|signed|dictated\s+by|transcribed\s+by|printed\s+by|entered\s+by|authenticated\s+by|verified\s+by|approved\s+by|recorded\s+by|attested\s+by|completed\s+by|documented\s+by|scribed\s+by|cc|sincerely|regards|respectfully|thank\s+you))(?![A-Za-z])" + SEP_STRICT + r"(?:Dr\.?\s+)?(?P<val>" + NAME + r"(?:(?:\s*,\s*|\s+)" + CRED + r")?)",
         doc="Electronically signed by / Signed / Dictated by / Transcribed by / Printed by / Entered by / cc: / Sincerely … followed "
             "by a name with an optional credential (the credential IS part of a signature block). 56% same-label / 79% family "
             "precision.",
         examples=("ELECTRONICALLY SIGNED BY: JOHNSON, MARY", "Sincerely, Jane Q. Public, MD")),
    Rule("signature_block", "usersig_login",
         r"(?<![A-Za-z0-9])(?P<val>[a-z]{2,12}\d{1,3}(?:\.\d{1,4})?)(?=\s*(?:</|\[|\n|$))",
         doc="EHR user logins at the end of a cell or line: 2-12 lowercase letters + 1-3 digits, optionally '.dddd' "
             "(the census shape 'aaaaaaaa99.999'). 70% precision.",
         examples=("Entered by asample12.345</td>",)),
    Rule("person_name", "patient_labelled",
         r"(?<![A-Za-z])(?i:(?:patient(?:'s)?\s+name|pt\.?\s+name|name|patient|pt|client|resident|member\s+name|guarantor(?:\s+name)?|mother|father|wife|husband|daughter|son|spouse|partner|caregiver|guardian|emergency\s+contact|contact(?:\s+person)?|next\s+of\s+kin|informant))" + SEP_KV + r"(?P<val>" + NAME + r")",
         doc="Patient Name / Name / Patient / Guarantor / Mother / Spouse / Emergency Contact … with a colon or table-cell boundary "
             "followed by a name. 48% same-label / 56% family precision -- 'Name:' also labels test names.",
         examples=("Patient Name: Mary Ann Jones DOB",)),
    Rule("person_name", "relative_named",
         r"(?<![A-Za-z])(?i:(?:his|her|their)\s+(?:mother|father|wife|husband|daughter|son|spouse|partner|caregiver|sister|brother|friend|neighbor|niece|nephew|granddaughter|grandson|aunt|uncle))(?:,|\s+named|\s+is)?\s+(?P<val>" + NAME_WORD + r"(?:\s+" + NAME_WORD + r")?)",
         doc="'his wife Mary', 'her daughter, Anne Smith': a relative word followed by one or two capitalised names. 89% precision.",
         examples=("accompanied by his wife Mary Jones today",)),
    Rule("person_name", "honorific",
         r"(?<![A-Za-z])(?:Mr|Mrs|Ms|Miss|Mx)\.?\s+(?P<val>" + NAME + r")",
         doc="Mr. / Mrs. / Ms. / Miss / Mx followed by a name. 97% precision.",
         examples=("Mr. Robert Brown reports",)),
    Rule("person_name", "salutation",
         r"(?<![A-Za-z])(?:Dear|Hi|Hello|Hey|RE|Re)[:,]?\s+(?P<val>" + NAME + r")",
         doc="Dear / Hi / Hello / RE: followed by a name (letters and portal messages). 42% same-label / 48% family precision.",
         examples=("Dear John Smith,",)),
    Rule("person_name", "after_upstream_name_tokens",
         r"\(\((?:PATIENT|Patient)_?(?:NAME|Name)\)\)(?:\s*,?\s*\(\((?:PATIENT|Patient)_?(?:NAME|Name)\)\))+\s+(?P<val>" + NAME_WORD + r")(?![A-Za-z])",
         doc="Corpus-specific: the upstream de-identifier masked the first and last name tokens and left a middle name or suffix "
             "after them ('((PATIENT_NAME)), ((PATIENT_NAME)) Marie'). 37% precision -- the reference model was inconsistent on "
             "trailing initials.",
         examples=("((PATIENT_NAME)), ((PATIENT_NAME)) Marie DOB",)),
    Rule("person_name", "xml_name_parts",
         r"<(?:given|family|prefix|suffix|GIV|FAM|MID|firstname|lastname|middlename)\b[^>]*>\s*(?P<val>[^<]{1,40}?)\s*</",
         doc="CCDA / vendor name parts as element text: <given>Mary</given><family>Jones</family>. 0/509 hits in the evaluation "
             "sample because those values were already upstream placeholders in this corpus; kept for CCDA inputs.",
         examples=("<given>Mary</given><family>Jones</family>",)),
]

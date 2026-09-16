"""Synthetic fixtures for every rule family: positives AND negatives (the control). Runnable without pytest:

    python -m phi_rules.selftest

Every string here is invented; none comes from the corpus the rules were derived from.
"""
from .engine import find

# (name, text, expected [(label, value), ...] in document order)
CASES = [
    # dates / ages
    ("dob plain", "Patient DOB: 04/06/1959 was seen.", [("date", "04/06/1959")]),
    ("dob bare year in table cell", "<tr><th>DOB</th><td>1950</td></tr>", [("date", "1950")]),
    ("dob with year <= cutoff -> age_90_plus", "Date of Birth: 1931-05-02", [("age_90_plus", "1931-05-02")]),
    ("dob after upstream guarantor tokens", "((GUARANTORLASTNAME)), ((GUARANTORFIRSTNAME)) ((GUARANTORMIDDLEINITIAL)) 1957 F", [("date", "1957")]),
    ("dob source label", "1931-05-02 <br> DOB Source: 1931-05-02", [("age_90_plus", "1931-05-02")]),
    ("dob attribute with time", 'DOB="1931-05-02T00:00:00" PatAgeInDays="34000"', [("age_90_plus", "1931-05-02T00:00:00")]),
    ("birth_dttm V attribute", '<birth_dttm V="1931-05-02T00:00:00"/>', [("age_90_plus", "1931-05-02T00:00:00")]),
    ("escaped DOB element", "&lt;DOB&gt;1950-03-04&lt;/DOB&gt;", [("date", "1950-03-04")]),
    ("age 92 labelled", "Age: 92 Gender: F", [("age_90_plus", "92")]),
    ("age element", "<age>92</age><age>61</age>", [("age_90_plus", "92")]),
    # identifiers
    ("mrn", "MRN: 00123456 Encounter", [("identified_number", "00123456")]),
    ("insurance #", "Insurance # : XYZ12345678<br>", [("identified_number", "XYZ12345678")]),
    ("patientid in a query string", "view.aspx?menu=1&patientid=8842719&x", [("identified_number", "8842719")]),
    ("xml id extension", '<id root="2.16.840.1" extension="MRN-77812"/>', [("identified_number", "MRN-77812")]),
    ("ssn shape", "SSN 123-45-6789 on file", [("identified_number", "123-45-6789")]),
    ("10-digit order number is an id, not a phone", "Order # 1234567890 placed", [("identified_number", "1234567890")]),
    ("device serial", "Serial Number: SN0012345X was", [("device_id", "SN0012345X")]),
    ("study protocol", "Protocol: AB1-CD-2345 Subject", [("study_id", "AB1-CD-2345")]),
    # contact
    ("phone + fax labelled", "Ph: (555) 123-4567 Fax: 555-765-4321", [("phone", "(555) 123-4567"), ("fax", "555-765-4321")]),
    ("formatted phone unlabelled", "call 555-123-4567 today", [("phone", "555-123-4567")]),
    ("phone after zip", "((PatientCity)), NY 10000-1234 5555551234 Fax", [("address", "NY"), ("zip_code", "10000-1234"), ("phone", "5555551234")]),
    ("email", "contact jane.doe@example.org for", [("email", "jane.doe@example.org")]),
    ("url", "visit https://portal.example.com/x?y=1 now", [("url", "https://portal.example.com/x?y=1")]),
    # amounts
    ("dollar amount", "a fee of $25.00 applies", [("amount", "$25.00")]),
    # places
    ("city state zip", "Sample Hills, MI 48000", [("address", "Sample Hills"), ("address", "MI"), ("zip_code", "48000")]),
    ("city state zip with markup", "Anytown,<br/> MI 48000-1234", [("address", "Anytown"), ("address", "MI"), ("zip_code", "48000-1234")]),
    ("street line", "at 1234 E Sample Creek Rd, Suite 100 and", [("address", "1234 E Sample Creek Rd, Suite 100")]),
    ("street line upper case", "at 1234 MAIN ST, SUITE 100 and", [("address", "1234 MAIN ST, SUITE 100")]),
    ("upstream city then state", "((PATIENTCITY)), FL 33000", [("address", "FL"), ("zip_code", "33000")]),
    ("location labelled", "Patient Location: MS Clinic 3<br>", [("location", "MS Clinic 3")]),
    ("V-attribute address block", '<ADDR><LINE_1 V="12 Main St"/><CTY V="Anytown"/><STA V="MI"/><ZIP V="48000"/><PHONE V="5555551212"/></ADDR>',
     [("address", "12 Main St"), ("address", "Anytown"), ("address", "MI"), ("zip_code", "48000"), ("phone", "5555551212")]),
    # institutions
    ("hospital with suffix", "referred to Example General Hospital for", [("hospital_name", "Example General Hospital")]),
    ("organization with corporate suffix", "works at Northwind Widgets Inc. as", [("organization", "Northwind Widgets Inc.")]),
    ("employer labelled", "Employer Name : Acme Motors<br>", [("organization", "Acme Motors")]),
    # names
    ("dr prefix", "seen by Dr. John Smith today", [("doctor_name", "John Smith")]),
    ("name with credential", "Ordered by Jane Q. Public, MD on", [("doctor_name", "Jane Q. Public")]),
    ("provider table cell", "<th>Ordering Provider</th><td>Casey J Sampleton</td>", [("doctor_name", "Casey J Sampleton")]),
    ("final column doctor", "| 2024-01-01 12:00 | Final | Casey J Sampleton", [("doctor_name", "Casey J Sampleton")]),
    ("signature upper case", "ELECTRONICALLY SIGNED BY: JOHNSON, MARY", [("signature_block", "JOHNSON, MARY")]),
    ("patient name labelled", "Patient Name: Mary Ann Jones DOB", [("person_name", "Mary Ann Jones")]),
    ("initial inside a name survives", "Patient Name: Mary A. Jones", [("person_name", "Mary A. Jones")]),
    ("honorific", "Mr. Robert Brown reports", [("person_name", "Robert Brown")]),
    ("xml given/family", "<given>Mary</given><family>Jones</family>", [("person_name", "Mary"), ("person_name", "Jones")]),
    ("GIV/FAM V attributes", '<person_name><nm><GIV V="Mary"/><FAM V="Jones"/></nm></person_name>', [("person_name", "Mary"), ("person_name", "Jones")]),
    # structured markup
    ("attributes city/state/zip/phone", 'PharmacyCity="Anytown" PharmacyState="MI" PharmacyZip="48000" PharmacyPhone="5555551212"',
     [("address", "Anytown"), ("address", "MI"), ("zip_code", "48000"), ("phone", "5555551212")]),
    ("attribute ids; structural FlowsheetID skipped", '<Row orderingmdid="4471" FlowsheetID="12" CreatedBy="3" CreatedUserName="asample"/>',
     [("identified_number", "4471"), ("identified_number", "3"), ("signature_block", "asample")]),
    ("escaped attribute quotes", 'PharmacyCity=&quot;Anytown&quot; PharmacyState=&quot;MI&quot;', [("address", "Anytown"), ("address", "MI")]),
    ("elements by name", "<encounterID>88213</encounterID><HospitalName>Example General</HospitalName><doctor>Jordan Q Sample</doctor>",
     [("identified_number", "88213"), ("hospital_name", "Example General"), ("doctor_name", "Jordan Q Sample")]),
    ("json keys", '{"SOURCE":"backfill","CREATEDBY":"asample","PATIENTID":"884"}', [("signature_block", "asample"), ("identified_number", "884")]),
    # --- negatives: the control. Clinical data that must survive. ---
    ("clinical dates are not PHI", "MRI brain 2012 showed lesions; admitted 03/04/2021", []),
    ("doses and counts are not ids", "Neurontin 600 mg t.i.d. Treatment # 86", []),
    ("lab values are not amounts", "glucose 105 mg/dL, WBC 7.2", []),
    ("code sets are not ids", "ICD-10 G35 CPT 99214 LOINC 2345-7", []),
    ("standalone state names", "moved from Ohio last year; NY resident", []),
    ("ages under 90", "Age: 61 years old, 45 yo male", []),
    ("OID is not an id", '<templateId root="2.16.840.1.113883.10.20.22.1.1"/>', []),
    ("upstream placeholders untouched", "((PATIENTNAME)) seen with ((GUARANTORLASTNAME))", []),
    ("dose-like number is not a phone", "vitamin D 50000 IU weekly", []),
    ("generic word 'name'", "the name of the medication was changed", []),
    ("DOBUTAMINE is not DOB", "DOBUTAMINE 2012 infusion", []),
    ("department in prose", "seen in the department of neurology", []),
    ("e-mail-like ratio", "ratio 2@3 high", []),
    ("a year in prose", "in 1998 she had surgery", []),
    ("structural ids skipped", '<CategoryId>123</CategoryId><ItemId>456</ItemId> StatusID="7"', []),
    ("system accounts skipped", 'CreatedUserName="Admin" LastChangedUserName="System"', []),
    ("BRAIN is not the state IN", 'ReferralReason="MRI BRAIN 70553"', []),
    ("medication sig is not a street", 'SIG="take 1 tablet by oral route daily"', []),
    ("hex blob is not DEA", 'fm="1DA12345-F123-11D2-A1F1-00DEA0000062" key a3e12dea41', []),
    ("presentational attributes skipped", '<div class="item" id="x1" style="left: 10px" name="q">Med Primary: MEDICARE</div>', []),
    ("placeholder values skipped", 'PatientName="((PATIENT_NAME))" <given>((PATIENT_FIRST_NAME))</given>', []),
    ("flowsheet name is not a person", 'FlowSheetName="OB Lab Flowsheet" Description="Custom"', []),
    ("GUID is not a ZIP", 'id="EB12345A-1234-56A7-89B0-ABCDEF123456"', []),
    ("code attributes skipped", '<code code="12345-6" codeSystem="2.16.840.1.113883.6.1" displayName="Glucose"/>', []),
]


def outcome(text):
    return [(s.label, s.text) for s in find(text)]


def run(cases=CASES, verbose=True):
    fails = []
    for name, text, want in cases:
        got = outcome(text)
        ok = got == want
        if verbose:
            print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"\n        got  {got!r}\n        want {want!r}"))
        if not ok:
            fails.append(name)
    if verbose:
        print(f"\n{len(fails)} FAILED of {len(cases)}" if fails else f"\nALL PASSED ({len(cases)} cases, "
              f"{sum(1 for _, _, w in cases if not w)} of them negatives)")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(run())

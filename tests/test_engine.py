"""Engine contract: overlap resolution, cut-off year, skipping, redact round-trip, pattern well-formedness."""
import re

import phi_rules
from phi_rules import CUTOFF_YEAR, LABELS, RULES, Rule, Span, find, label_for_key, redact
from phi_rules.engine import candidates


def test_rule_set_shape():
    assert len(RULES) == 52
    assert len({r.name for r in RULES}) == 52
    assert {r.label for r in RULES} <= LABELS
    assert len(LABELS) == 19
    for r in RULES:
        p = r.compiled()
        assert "val" in p.groupindex, r.name
        assert "{{" not in r.pattern and "}}" not in r.pattern, r.name          # doubled braces = leftover format escaping
        assert not re.search(r"\(\d+, \d+\)", r.pattern), r.name                 # tuple repr = the rf-string quantifier trap


def test_overlap_resolution():
    a = Rule("date", "a", r"(?P<val>1950)")
    b = Rule("identified_number", "b", r"(?P<val>1950-01)")
    text = "x 1950-01 y"
    spans = find(text, rules=[a, b], cutoff_year=1900)
    assert [(s.label, s.text) for s in spans] == [("identified_number", "1950-01")]   # equal start: longest wins
    c = Rule("phone", "c", r"(?P<val>1950 y)")
    spans = find(text, rules=[c, b], cutoff_year=1900)
    assert [s.text for s in spans] == ["1950-01"]                                     # earlier start wins over a later overlap
    adjacent = find("AB", rules=[Rule("date", "l", r"(?P<val>A)"), Rule("date", "r", r"(?P<val>B)")], cutoff_year=1900)
    assert [s.text for s in adjacent] == ["A", "B"]                                   # adjacent spans both kept, sorted


def test_cutoff_year():
    assert find("DOB: 1936")[0].label == "age_90_plus"
    assert find("DOB: 1937")[0].label == "date"
    assert find("DOB: 1937", cutoff_year=1940)[0].label == "age_90_plus"
    assert CUTOFF_YEAR == 1936


def test_skipping():
    assert find('PharmacyCity="((PATIENT_CITY))"') == []
    assert find('CreatedUserName="Admin"') == []
    assert find('IsActive="true" PharmacyZip="0"') == []


def test_redact_round_trip():
    text = "Patient Name: Mary Ann Jones, DOB: 04/06/1959, Ph: (555) 123-4567."
    spans = find(text)
    out = redact(text, spans=spans)
    assert "Mary Ann Jones" not in out and "04/06/1959" not in out and "555" not in out
    assert out == "Patient Name: ((person_name)), DOB: ((date)), Ph: ((phone))."
    assert redact(text, "[{label}]", spans=spans).count("[") == 3
    for s in spans:
        assert s.text == text[s.start:s.end]
        assert isinstance(s, Span)


def test_label_for_key():
    assert label_for_key("CreatedBy", "3") == "identified_number"
    assert label_for_key("CreatedUserName", "asample") == "signature_block"
    assert label_for_key("FlowsheetID", "12") is None
    assert label_for_key("class", "item") is None
    assert label_for_key("age", "92") == "age_90_plus" and label_for_key("age", "61") is None
    assert label_for_key("PharmacyZip", "48000") == "zip_code" and label_for_key("PharmacyZip", "n/a") is None
    assert label_for_key("orderingmdid", "4471") == "identified_number"


def test_ip_octets():
    assert [s.text for s in find("from 192.168.10.44 at")] == ["192.168.10.44"]
    assert find("root 2.16.840.1 code") == []


def test_candidates_exposes_every_value_group():
    labs = [l for l, n, a, b in candidates("Sample Hills, MI 48000", RULES)]
    assert labs.count("address") >= 2 and "zip_code" in labs


if __name__ == "__main__":
    for k, v in list(globals().items()):
        if k.startswith("test_") and callable(v):
            v()
    print("ok")

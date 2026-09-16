"""phi_rules -- deterministic regex rules for the 19 PHI labels of the Biogen de-identification deliverable.

    from phi_rules import find, redact
    spans = find(text)                 # [Span(label, rule, start, end, text), ...] non-overlapping
    clean = redact(text)               # text with each span replaced by ((label))

RULES is ordered exactly as the evaluated rule set (ties at equal start and length resolve to the earlier
rule); GROUPS organises the same rules by PHI-type module for documentation.
"""
from . import amount, contact, dates, identifiers, markup, names, orgs, places
from .engine import CUTOFF_YEAR, LABELS, SKIP_VALUES, Rule, Span, find, redact
from .markup import KEY_RULES, PRESENTATIONAL, STRUCTURAL_KEYS, label_for_key

__version__ = "1.0.0"

GROUPS = [
    ("Dates and ages", "dates", dates.RULES),
    ("Identifiers, devices and studies", "identifiers", identifiers.RULES),
    ("Phone, fax, e-mail, URL, IP", "contact", contact.RULES),
    ("Amounts", "amount", amount.RULES),
    ("Addresses, ZIP codes and locations", "places", places.RULES),
    ("Hospitals and organizations", "orgs", orgs.RULES),
    ("Names: person, doctor, signature", "names", names.RULES),
    ("Structured markup (key decides the label)", "markup", markup.RULES),
]

# Evaluation order of the rule set (phi_rules.py in the pipeline, 2026-09-16). Kept verbatim so spans are identical.
RULE_ORDER = [
    "dob_labelled", "dob_after_guarantor_tokens", "age_labelled_90plus", "age_suffix_90plus", "id_labelled",
    "json_by_name", "after_final_column", "phone_after_zip_or_comma", "attr_by_name", "elem_by_name",
    "elem_v_attribute", "addr_v_attribute", "birth_v_attribute", "id_attribute", "xml_id_extension", "ssn_shape",
    "fax_labelled", "phone_labelled", "phone_formatted_unlabelled", "tel_href", "email_shape", "url_scheme",
    "url_bare_domain", "ip_shape", "dollar_amount", "amount_labelled", "city_state_zip", "upstream_city_then_state",
    "street_line", "po_box", "address_labelled", "zip_labelled", "zip_after_state", "location_labelled",
    "org_with_suffix", "hospital_labelled", "employer_labelled", "dr_prefix", "name_with_credential",
    "provider_labelled", "by_verb_name", "signature_labelled", "usersig_login", "patient_labelled", "relative_named",
    "honorific", "salutation", "after_upstream_name_tokens", "xml_name_parts", "device_labelled", "study_labelled",
    "nct_shape",
]

_by_name = {r.name: r for _, _, rs in GROUPS for r in rs}
assert len(_by_name) == sum(len(rs) for _, _, rs in GROUPS) == 52, "rule names must be unique and number 52"
assert set(_by_name) == set(RULE_ORDER), sorted(set(_by_name) ^ set(RULE_ORDER))
RULES = [_by_name[n] for n in RULE_ORDER]
for _r in RULES:
    assert _r.label in LABELS, _r.name
    assert "val" in _r.compiled().groupindex, _r.name

__all__ = ["RULES", "GROUPS", "RULE_ORDER", "LABELS", "Rule", "Span", "find", "redact", "label_for_key", "KEY_RULES",
           "PRESENTATIONAL", "STRUCTURAL_KEYS", "SKIP_VALUES", "CUTOFF_YEAR", "__version__"]

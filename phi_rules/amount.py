"""amount -- financial values only (never doses, lab values, vitals or scores)."""
import re

from ._blocks import labelled
from .engine import Rule

RULES = [
    Rule("amount", "dollar_amount",
         r"(?P<val>\$\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?)(?![\d])", re.I,
         doc="A currency amount with $ (optional thousands separators and cents). 91% recall; 42% precision against the "
             "reference because the model left most fee-schedule tables alone -- a policy call for DE (see docs/policy.md).",
         examples=("a fee of $25.00 applies", "balance $1,250")),
    Rule("amount", "amount_labelled",
         labelled(r"(?:balance|copay|co-pay|coinsurance|deductible|fee|charge|amount\s+due|payment|cost|total|owed)", r"\$?\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})"),
         doc="Balance / Copay / Deductible / Fee / Charge / Amount due / Payment / Cost / Total label followed by a decimal amount "
             "with or without $. 12% precision in the sample (n=86): 'Total' also labels counts.",
         examples=("Copay: 40.00 due",)),
]

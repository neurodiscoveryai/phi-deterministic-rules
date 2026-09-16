"""Rule / Span data types and the matching engine.

``find(text)`` runs every rule, keeps each ``val*`` group as a candidate span, applies the value skips and the
rule's ``relabel`` hook, promotes a ``date`` whose year is at or below the cut-off to ``age_90_plus``, then
resolves overlaps: candidates are sorted by (start, longest first) and swept greedily, so at equal starts the
longer span wins and nothing overlaps. Over-redaction is the safe side for PHI.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional, Sequence

LABELS = frozenset("""person_name doctor_name signature_block date age_90_plus address zip_code location
hospital_name organization email phone fax ip_address url identified_number device_id study_id amount""".split())

# A birth year at or below this implies age >= 90 (2026 - 90). Fixed so re-runs are reproducible; pass
# ``cutoff_year`` to find()/redact() to move it.
CUTOFF_YEAR = 1936

# Attribute / element values that are enums, booleans or system accounts, never PHI.
SKIP_VALUES = frozenset({"", "true", "false", "yes", "no", "null", "none", "n/a", "na", "unknown", "y", "n", "-", "--", "0",
                         "admin", "administrator", "system", "default", "user", "interface", "auto", "import", "backfill",
                         "conversion", "test"})

_YEAR_IN = re.compile(r"(?:18|19|20)\d{2}")

# relabel(match, group_name, value) -> new label, or None to drop the candidate
Relabel = Callable[[re.Match, str, str], Optional[str]]


@dataclass(frozen=True)
class Rule:
    label: str            # the PHI label the rule emits (a relabel hook may change it per match)
    name: str             # unique rule id, used in spans and docs
    pattern: str          # the regex source; must define a named group ``val`` (``val2``, ``val3`` allowed)
    flags: int = 0
    doc: str = ""         # what it matches and the evidence behind it (rendered into the README)
    examples: tuple = ()  # synthetic example strings (rendered with their find() output)
    relabel: Optional[Relabel] = field(default=None, compare=False, repr=False)

    def compiled(self) -> re.Pattern:
        return _compile(self.pattern, self.flags)

    @property
    def value_groups(self) -> list:
        return [g for g in self.compiled().groupindex if g.startswith("val")]


_cache: dict = {}


def _compile(pattern: str, flags: int) -> re.Pattern:
    key = (pattern, flags)
    p = _cache.get(key)
    if p is None:
        p = _cache[key] = re.compile(pattern, flags)
    return p


@dataclass(frozen=True)
class Span:
    label: str
    rule: str
    start: int
    end: int
    text: str


def candidates(text: str, rules: Iterable[Rule], cutoff_year: int = CUTOFF_YEAR):
    """Yield every (label, rule, start, end) before overlap resolution."""
    for rule in rules:
        pat = rule.compiled()
        groups = [g for g in pat.groupindex if g.startswith("val")]
        for m in pat.finditer(text):
            for g in groups:
                a, b = m.start(g), m.end(g)
                if a < 0 or b <= a:
                    continue
                value = text[a:b]
                if "((" in value or value.strip().lower() in SKIP_VALUES:
                    continue                                   # upstream placeholder / enum, not PHI
                label = rule.label
                if rule.relabel is not None:
                    label = rule.relabel(m, g, value)
                    if label is None:
                        continue
                if label == "date":                            # the birth year decides date vs age_90_plus
                    y = _YEAR_IN.search(value)
                    if y and int(y.group()) <= cutoff_year:
                        label = "age_90_plus"
                yield label, rule.name, a, b


def find(text: str, rules: Optional[Sequence[Rule]] = None, cutoff_year: int = CUTOFF_YEAR) -> list:
    """Non-overlapping spans, sorted by position. At equal starts the longer span wins."""
    if rules is None:
        from . import RULES as rules  # noqa: PLC0415 -- avoids a circular import at module load
    found = sorted(candidates(text, rules, cutoff_year), key=lambda t: (t[2], -(t[3] - t[2])))
    out, last_end = [], -1
    for label, name, a, b in found:
        if a >= last_end:
            out.append(Span(label, name, a, b, text[a:b]))
            last_end = b
    return out


def redact(text: str, placeholder: str = "(({label}))", rules: Optional[Sequence[Rule]] = None,
           cutoff_year: int = CUTOFF_YEAR, spans: Optional[list] = None) -> str:
    """Replace every found span with ``placeholder.format(label=...)``; pass ``spans`` to reuse a find() result."""
    if spans is None:
        spans = find(text, rules, cutoff_year)
    out, pos = [], 0
    for s in spans:
        out.append(text[pos:s.start])
        out.append(placeholder.format(label=s.label, rule=s.rule))
        pos = s.end
    out.append(text[pos:])
    return "".join(out)

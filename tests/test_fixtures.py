"""Every synthetic fixture (positives and the negative control) must produce exactly the expected spans."""
from phi_rules.selftest import CASES, outcome


def test_fixtures():
    failing = [(name, outcome(text), want) for name, text, want in CASES if outcome(text) != want]
    assert not failing, "\n".join(f"{n}: got {g!r} want {w!r}" for n, g, w in failing)


def test_half_of_the_suite_is_negative():
    negatives = sum(1 for _, _, want in CASES if not want)
    assert negatives >= len(CASES) // 3, f"{negatives} negatives of {len(CASES)}: the control is too thin"


if __name__ == "__main__":
    test_fixtures(); test_half_of_the_suite_is_negative(); print("ok")

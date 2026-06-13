from datetime import date
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT = (
    Path(__file__).parents[1]
    / "skills"
    / "mindfeast-weekly-slides"
    / "scripts"
    / "collect_week.py"
)
SPEC = spec_from_file_location("mindfeast_collect_week", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_rolling_week_start_includes_today_and_previous_six_days():
    assert MODULE.rolling_week_start(date(2026, 6, 12)) == date(2026, 6, 6)


def test_rolling_week_start_respects_custom_window_length():
    assert MODULE.rolling_week_start(date(2026, 6, 12), 3) == date(2026, 6, 10)

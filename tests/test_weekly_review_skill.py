from pathlib import Path

SKILL = (
    Path(__file__).resolve().parents[1] / "skills" / "weekly-review" / "SKILL.md"
)


def test_digest_is_a_few_bullets():
    skill = SKILL.read_text(encoding="utf-8")
    contract = skill.split("## Editorial contract", 1)[1]
    assert "A bullet is one sentence." in contract
    assert "at most 3 bullets" in contract
    assert "at most 2 bullets per student" in contract
    assert "Most of what you read stays out of the message." in contract
    assert "Do not list every" in contract
    assert "not a reconstruction of the pages" in skill


def test_digest_does_not_hardcode_students():
    text = SKILL.read_text(encoding="utf-8").lower()
    assert "isamaya" not in text
    assert "eliana" not in text

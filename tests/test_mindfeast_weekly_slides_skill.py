from pathlib import Path

SKILL = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "mindfeast-weekly-slides"
    / "SKILL.md"
)


def test_named_student_still_generates_without_remote():
    skill = SKILL.read_text(encoding="utf-8")
    assert (
        "If a student is named and MindFeast remote config is missing, still generate slides"
        in skill
    )


def test_unnamed_run_requires_complete_remote():
    skill = SKILL.read_text(encoding="utf-8")
    assert (
        "If no student is named, generate only for students with both `mindfeast.remote_url` and `mindfeast.remote_token` configured"
        in skill
    )
    assert 'Phrases such as "all students" do not name a student' in skill
    assert "Treat blank or whitespace-only values as missing." in skill

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


def test_selection_is_driven_by_week_content():
    skill = SKILL.read_text(encoding="utf-8")
    heuristics = skill.split("## Selection Heuristics", 1)[1].split("## Slide Type Rules", 1)[0]
    assert "The content that was taught decides what is worth a slide." in heuristics
    assert "Main ideas are the body of the set." in heuristics
    assert "This is one reason to choose a slide, not the filter for the set." in heuristics
    assert "no note of trouble does not mean the student holds it" in heuristics
    assert "single best signal" not in heuristics.lower()


def test_unnamed_run_requires_complete_remote():
    skill = SKILL.read_text(encoding="utf-8")
    assert (
        "If no student is named, generate only for students with both `mindfeast.remote_url` and `mindfeast.remote_token` configured"
        in skill
    )
    assert 'Phrases such as "all students" do not name a student' in skill
    assert "Treat blank or whitespace-only values as missing." in skill

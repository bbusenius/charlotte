from pathlib import Path

SKILL = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "mindfeast-morning-note"
    / "SKILL.md"
)


def test_morning_note_does_not_hardcode_students():
    text = SKILL.read_text(encoding="utf-8").lower()
    assert "isamaya" not in text
    assert "eliana" not in text


def test_morning_note_is_an_idea_not_a_recap():
    skill = SKILL.read_text(encoding="utf-8")
    assert "The students already know what they did." in skill
    assert "Do not narrate the session" in skill
    assert "Do not name the students." in skill
    assert "Nature study is allowed" in skill
    assert "It is not the default." in skill
    assert "does not need to understand every word" in skill
    assert "No scene-painting" in skill
    assert "students.yaml" in skill
    assert "Any subject in the logs is eligible." in skill
    assert "or an inspirational thought" in skill
    assert "It is not the only kind." in skill
    assert "good morning" not in skill.lower()


def test_morning_note_caps_length():
    skill = SKILL.read_text(encoding="utf-8")
    assert "At most 3 sentences, and at most 250 characters." in skill
    assert "Push only a note that is within both limits." in skill
    assert "2000" not in skill

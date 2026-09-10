from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_push_module():
    module_path = ROOT / "skills" / "mindfeast-agent-alarm" / "scripts" / "push.py"
    spec = importlib.util.spec_from_file_location("mindfeast_agent_alarm", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self.ok = 200 <= status_code < 300
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


def write_registry(path: Path, data: dict) -> Path:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def two_student_registry(
    *,
    alice_alarm: bool = True,
    charlie_alarm: bool = False,
    alice_url: str = "http://alice-alarm.local:8787/",
    charlie_url: str = "http://charlie-alarm.local:8787/",
) -> dict:
    alice: dict = {
        "display_name": "Alice",
        "aliases": ["alice"],
        "mindfeast": {
            "remote_url": "http://lockscreen.local:8787",
            "remote_token": "lockscreen-secret",
        },
    }
    if alice_alarm:
        alice["agent_alarm"] = {
            "remote_url": alice_url,
            "remote_token": "alice-secret",
        }
    charlie: dict = {
        "display_name": "Charlie",
        "aliases": ["cj"],
        "mindfeast": {
            "remote_url": "http://lockscreen.local:8787",
            "remote_token": "lockscreen-secret",
        },
    }
    if charlie_alarm:
        charlie["agent_alarm"] = {
            "remote_url": charlie_url,
            "remote_token": "charlie-secret",
        }
    return {
        "agent_alarm": {
            "remote_url": "http://household.local:8787",
            "remote_token": "household-secret",
        },
        "students": {"alice": alice, "charlie": charlie},
    }


def test_configured_students_ignores_household_and_lockscreen(tmp_path):
    push = load_push_module()
    registry = write_registry(tmp_path / "students.yaml", two_student_registry())
    students = push.load_students(registry)

    selected = push.configured_students(students, None)

    assert [slug for slug, _ in selected] == ["alice"]
    url, token = push.alarm_config(selected[0][1])
    assert url == "http://alice-alarm.local:8787"
    assert token == "alice-secret"


def test_named_student_without_alarm_reports_missing_config(tmp_path, capsys):
    push = load_push_module()
    registry = write_registry(tmp_path / "students.yaml", two_student_registry())

    code = push.main(["--status", "--student", "charlie", "--students-file", str(registry)])
    payload = json.loads(capsys.readouterr().out)

    assert code == 1
    assert payload["results"] == [
        {
            "student": "charlie",
            "display_name": "Charlie",
            "ok": False,
            "status": "missing_config",
            "error": "agent_alarm.remote_url is missing",
        }
    ]


def test_no_configured_students_exits(tmp_path):
    push = load_push_module()
    registry = write_registry(tmp_path / "students.yaml", two_student_registry(alice_alarm=False))

    with pytest.raises(SystemExit, match="No students have complete Agent Alarm config"):
        push.main(["--status", "--students-file", str(registry)])


def test_status_posts_to_named_student_without_leaking_token(tmp_path, monkeypatch, capsys):
    push = load_push_module()
    registry = write_registry(tmp_path / "students.yaml", two_student_registry())
    calls = []

    def fake_request(method, url, headers, json, data, timeout):
        calls.append(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "json": json,
                "data": data,
                "timeout": timeout,
            }
        )
        return FakeResponse({"ok": True, "audioPresent": False})

    monkeypatch.setattr(push.requests, "request", fake_request)

    code = push.main(
        ["--status", "--student", "Alice", "--students-file", str(registry), "--timeout", "12"]
    )
    output = capsys.readouterr().out

    assert code == 0
    assert calls == [
        {
            "method": "GET",
            "url": "http://alice-alarm.local:8787/api/status",
            "headers": {"Authorization": "Bearer alice-secret"},
            "json": None,
            "data": None,
            "timeout": 12.0,
        }
    ]
    assert "alice-secret" not in output
    assert "lockscreen-secret" not in output
    assert "household-secret" not in output
    payload = json.loads(output)
    assert payload["results"][0]["student"] == "alice"
    assert payload["results"][0]["base"] == "alice-alarm.local:8787"
    assert payload["results"][0]["operations"][0]["endpoint"] == "alice-alarm.local:8787/api/status"


def test_all_pushes_each_configured_student(tmp_path, monkeypatch, capsys):
    push = load_push_module()
    registry = write_registry(
        tmp_path / "students.yaml",
        two_student_registry(charlie_alarm=True),
    )
    urls = []

    def fake_request(method, url, headers, json, data, timeout):
        urls.append(url)
        return FakeResponse({"ok": True})

    monkeypatch.setattr(push.requests, "request", fake_request)

    code = push.main(["--all", "--enable", "--students-file", str(registry)])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert urls == [
        "http://alice-alarm.local:8787/api/alarm/enable",
        "http://alice-alarm.local:8787/api/status",
        "http://charlie-alarm.local:8787/api/alarm/enable",
        "http://charlie-alarm.local:8787/api/status",
    ]
    assert [row["student"] for row in payload["results"]] == ["alice", "charlie"]
    assert "alice-secret" not in str(payload)
    assert "charlie-secret" not in str(payload)


def test_unnamed_selects_all_configured(tmp_path, monkeypatch):
    push = load_push_module()
    registry = write_registry(tmp_path / "students.yaml", two_student_registry())
    urls = []

    def fake_request(method, url, headers, json, data, timeout):
        urls.append(url)
        return FakeResponse({"ok": True})

    monkeypatch.setattr(push.requests, "request", fake_request)

    code = push.main(["--status", "--students-file", str(registry)])

    assert code == 0
    assert urls == ["http://alice-alarm.local:8787/api/status"]


def test_dry_run_does_not_request(tmp_path, monkeypatch):
    push = load_push_module()
    registry = write_registry(tmp_path / "students.yaml", two_student_registry())

    def fake_request(*args, **kwargs):
        raise AssertionError("dry-run should not request")

    monkeypatch.setattr(push.requests, "request", fake_request)

    code = push.main(["--dry-run", "--enable", "--student", "alice", "--students-file", str(registry)])

    assert code == 0


def test_student_and_all_conflict():
    push = load_push_module()
    with pytest.raises(SystemExit) as exc:
        push.main(["--all", "--student", "alice", "--status"])
    assert exc.value.code == 2


def test_conflicting_enable_flags():
    push = load_push_module()
    with pytest.raises(SystemExit, match="--enable / --disable"):
        push.main(["--enable", "--disable"])


def test_conflicting_theme_flags():
    push = load_push_module()
    with pytest.raises(SystemExit, match="--theme / --theme-restore-default"):
        push.main(["--theme", "{}", "--theme-restore-default"])


def test_picture_requires_theme():
    push = load_push_module()
    with pytest.raises(SystemExit, match="--picture requires --theme"):
        push.main(["--picture", "morning.jpg"])


def test_picture_rejects_theme_restore():
    push = load_push_module()
    with pytest.raises(SystemExit, match="--picture requires --theme"):
        push.main(["--picture", "morning.jpg", "--theme-restore-default"])


def test_invalid_time():
    push = load_push_module()
    with pytest.raises(SystemExit, match="HH:MM"):
        push.main(["--time", "25:00"])


def test_nothing_to_do():
    push = load_push_module()
    with pytest.raises(SystemExit, match="Nothing to do"):
        push.main([])

def test_audio_meta_dry_run_posts_composer_and_title(tmp_path, monkeypatch, capsys):
    push = load_push_module()
    registry = write_registry(tmp_path / "students.yaml", two_student_registry())
    monkeypatch.setattr(push.requests, "request", lambda *a, **k: (_ for _ in ()).throw(AssertionError("dry-run should not request")))
    code = push.main([
        "--dry-run",
        "--composer", "J.S. Bach",
        "--audio-title", "Air on the G String",
        "--student", "alice",
        "--students-file", str(registry),
    ])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    ops = payload["results"][0]["operations"]
    assert any(op.get("method") == "POST" and "/api/audio/meta" in op.get("endpoint", "") for op in ops)


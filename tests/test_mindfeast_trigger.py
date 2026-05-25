from __future__ import annotations

import importlib.util
from pathlib import Path


def load_trigger_module():
    module_path = (
        Path(__file__).resolve().parents[1]
        / "skills"
        / "mindfeast-slide-trigger"
        / "scripts"
        / "trigger.py"
    )
    spec = importlib.util.spec_from_file_location("mindfeast_trigger", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    ok = True
    status_code = 200
    text = '{"ok":true,"message":"Triggered owl-facts","slideId":"owl-facts"}'

    def json(self):
        return {
            "ok": True,
            "message": "Triggered owl-facts",
            "slideId": "owl-facts",
        }


def test_trigger_one_posts_to_trigger_endpoint_without_leaking_token(monkeypatch):
    trigger = load_trigger_module()
    calls = []

    def fake_post(url, headers, timeout):
        calls.append({"url": url, "headers": headers, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(trigger.requests, "post", fake_post)

    result = trigger.trigger_one(
        "student",
        {
            "display_name": "Student",
            "mindfeast": {
                "remote_url": "http://tablet.local:8787/",
                "remote_token": "secret-token",
            },
        },
        timeout=12,
        dry_run=False,
    )

    assert calls == [
        {
            "url": "http://tablet.local:8787/api/trigger",
            "headers": {"Authorization": "Bearer secret-token"},
            "timeout": 12,
        }
    ]
    assert result["ok"] is True
    assert result["status"] == "completed"
    assert result["endpoint"] == "tablet.local:8787/api/trigger"
    assert result["slide_id"] == "owl-facts"
    assert "secret-token" not in str(result)


def test_trigger_one_dry_run_does_not_post(monkeypatch):
    trigger = load_trigger_module()

    def fake_post(*args, **kwargs):
        raise AssertionError("dry-run should not post")

    monkeypatch.setattr(trigger.requests, "post", fake_post)

    result = trigger.trigger_one(
        "student",
        {
            "mindfeast": {
                "remote_url": "http://tablet.local:8787",
                "remote_token": "secret-token",
            },
        },
        timeout=12,
        dry_run=True,
    )

    assert result["ok"] is True
    assert result["status"] == "dry_run"
    assert result["endpoint"] == "tablet.local:8787/api/trigger"

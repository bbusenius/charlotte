from __future__ import annotations

import importlib.util
from pathlib import Path


def load_select_module():
    module_path = (
        Path(__file__).resolve().parents[1]
        / "skills"
        / "ao-picture-study"
        / "scripts"
        / "select_slide.py"
    )
    spec = importlib.util.spec_from_file_location("ao_picture_select", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    ok = True
    status_code = 200
    text = '{"ok":true,"message":"Selected ao-work","activeSlideId":"ao-work"}'

    def json(self):
        return {
            "ok": True,
            "message": "Selected ao-work",
            "activeSlideId": "ao-work",
        }


def test_select_posts_exact_id_without_leaking_token(monkeypatch):
    select = load_select_module()
    calls = []

    def fake_post(url, headers, json, timeout):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(select.requests, "post", fake_post)
    result = select.select_one(
        "student",
        {
            "display_name": "Student",
            "mindfeast": {
                "remote_url": "http://tablet.local:8787/",
                "remote_token": "secret-token",
            },
        },
        "ao-work",
        timeout=12,
        dry_run=False,
    )

    assert calls == [
        {
            "url": "http://tablet.local:8787/api/slides/select",
            "headers": {"Authorization": "Bearer secret-token"},
            "json": {"id": "ao-work"},
            "timeout": 12,
        }
    ]
    assert result["ok"] is True
    assert result["active_slide_id"] == "ao-work"
    assert result["endpoint"] == "tablet.local:8787/api/slides/select"
    assert "secret-token" not in str(result)


def test_select_dry_run_does_not_post(monkeypatch):
    select = load_select_module()

    def fake_post(*args, **kwargs):
        raise AssertionError("dry-run should not post")

    monkeypatch.setattr(select.requests, "post", fake_post)
    result = select.select_one(
        "student",
        {
            "mindfeast": {
                "remote_url": "http://tablet.local:8787",
                "remote_token": "secret-token",
            },
        },
        "ao-work",
        timeout=12,
        dry_run=True,
    )
    assert result["ok"] is True
    assert result["status"] == "dry_run"

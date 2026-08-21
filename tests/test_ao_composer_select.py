from __future__ import annotations

import importlib.util
from pathlib import Path


def load_module():
    path = Path(__file__).resolve().parents[1] / "skills/ao-composer-study/scripts/select_slide.py"
    spec = importlib.util.spec_from_file_location("ao_composer_select", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    ok = True
    status_code = 200
    text = '{"ok":true,"message":"Selected work","activeSlideId":"work"}'

    def json(self):
        return {"ok": True, "message": "Selected work", "activeSlideId": "work"}


def test_select_posts_only_exact_primary_id_without_leaking_token(monkeypatch):
    mod = load_module()
    calls = []

    def fake_post(url, headers, json, timeout):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(mod.requests, "post", fake_post)
    result = mod.select_one(
        "student",
        {"mindfeast": {"remote_url": "http://tablet.local:8787/", "remote_token": "secret-token"}},
        "work",
        timeout=12,
        dry_run=False,
    )

    assert calls[0]["json"] == {"id": "work"}
    assert result["active_slide_id"] == "work"
    assert result["endpoint"] == "tablet.local:8787/api/slides/select"
    assert "secret-token" not in str(result)

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_script(relative_path: str, module_name: str):
    module_path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeSyncResponse:
    ok = True
    status_code = 200
    text = '{"ok":true,"message":"Sync complete"}'


class FakeSettingsResponse:
    ok = True
    status_code = 200
    text = '{"ok":true,"message":"Saved","slidesRequiredPerUnlock":2}'

    def json(self):
        return {
            "ok": True,
            "message": "Saved",
            "slidesRequiredPerUnlock": 2,
        }


def configured_student():
    return {
        "display_name": "Student",
        "mindfeast": {
            "remote_url": "http://tablet.local:8787/",
            "remote_token": "secret-token",
            "unlock_requirement": {"default": 2},
        },
    }


def test_sync_posts_to_current_mindfeast_endpoint_without_leaking_token(monkeypatch):
    sync = load_script(
        "skills/mindfeast-slide-sync/scripts/sync.py", "mindfeast_sync"
    )
    calls = []

    def fake_post(url, headers, timeout):
        calls.append({"url": url, "headers": headers, "timeout": timeout})
        return FakeSyncResponse()

    monkeypatch.setattr(sync.requests, "post", fake_post)

    result = sync.sync_one(
        "student", configured_student(), timeout=30, dry_run=False
    )

    assert calls == [
        {
            "url": "http://tablet.local:8787/api/sync",
            "headers": {"Authorization": "Bearer secret-token"},
            "timeout": 30,
        }
    ]
    assert result["ok"] is True
    assert result["endpoint"] == "tablet.local:8787/api/sync"
    assert "secret-token" not in str(result)


def test_unlock_requirement_posts_count_to_current_mindfeast_endpoint(monkeypatch):
    settings = load_script(
        "skills/mindfeast-unlock-requirement/scripts/set_requirement.py",
        "mindfeast_unlock_requirement",
    )
    calls = []

    def fake_post(url, headers, json, timeout):
        calls.append(
            {"url": url, "headers": headers, "json": json, "timeout": timeout}
        )
        return FakeSettingsResponse()

    monkeypatch.setattr(settings.requests, "post", fake_post)
    args = argparse.Namespace(
        count=None,
        use_default=True,
        no_tablet=False,
        today_policy=False,
        dry_run=False,
        timeout=12,
    )

    result = settings.set_one("student", configured_student(), args)

    assert calls == [
        {
            "url": "http://tablet.local:8787/api/settings/unlock-requirement",
            "headers": {"Authorization": "Bearer secret-token"},
            "json": {"count": 2},
            "timeout": 12,
        }
    ]
    assert result["ok"] is True
    assert result["slides_required_per_unlock"] == 2
    assert result["endpoint"] == "tablet.local:8787/api/settings/unlock-requirement"
    assert "secret-token" not in str(result)

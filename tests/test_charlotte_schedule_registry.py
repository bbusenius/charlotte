"""Tests for family schedule discovery on the Charlotte LAN page."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace


def load_module():
    path = Path(__file__).resolve().parents[1] / "apps/charlotte/server.py"
    spec = importlib.util.spec_from_file_location("charlotte_info_server", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_configured_schedule_uses_title_and_path(tmp_path):
    module = load_module()
    schedule_root = tmp_path / "schedules"
    schedule = schedule_root / "2026-2027" / "family-weekly-rhythm.html"
    schedule.parent.mkdir(parents=True)
    schedule.write_text("<h1>Family Weekly Rhythm</h1>", encoding="utf-8")
    registry = tmp_path / "students.yaml"
    registry.write_text(
        """schedules:
  Family Weekly Rhythm:
    description: Shared plan
    school_year: 2026-2027
    students: [alice, charlie]
    path: schedules/2026-2027/family-weekly-rhythm.html
""",
        encoding="utf-8",
    )

    entries = module.configured_schedules(registry, schedule_root)

    assert entries == [
        {
            "title": "Family Weekly Rhythm",
            "description": "Shared plan",
            "path": str(schedule.resolve()),
            "route": "/schedules/2026-2027/family-weekly-rhythm.html",
        }
    ]


def test_unconfigured_or_outside_schedule_is_not_listed(tmp_path):
    module = load_module()
    schedule_root = tmp_path / "schedules"
    schedule_root.mkdir()
    (schedule_root / "unconfigured.html").write_text("<h1>Private</h1>", encoding="utf-8")
    outside = tmp_path / "outside.html"
    outside.write_text("<h1>Outside</h1>", encoding="utf-8")
    registry = tmp_path / "students.yaml"
    registry.write_text(
        """schedules:
  Outside schedule:
    path: ../outside.html
""",
        encoding="utf-8",
    )

    assert module.configured_schedules(registry, schedule_root) == []


def test_schedule_list_html_uses_only_configured_entries():
    module = load_module()
    handler = object.__new__(module.CharlotteInfoHandler)
    handler.server = SimpleNamespace(
        schedules=[
            {
                "title": "Family Weekly Rhythm",
                "description": "Shared plan",
                "path": "/not/used/here.html",
                "route": "/schedules/2026-2027/family-weekly-rhythm.html",
            }
        ]
    )

    page_fragment = handler.schedule_list_html()

    assert 'href="/schedules/2026-2027/family-weekly-rhythm.html"' in page_fragment
    assert "Family Weekly Rhythm" in page_fragment
    assert "Shared plan" in page_fragment

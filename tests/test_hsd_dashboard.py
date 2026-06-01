from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_hsd_dashboard_module():
    repo = Path(__file__).resolve().parents[1]
    scripts_dir = repo / "scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        spec = importlib.util.spec_from_file_location(
            "hsd_dashboard", scripts_dir / "hsd_dashboard.py"
        )
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(scripts_dir))


def load_hsd_provision_dashboards_module():
    repo = Path(__file__).resolve().parents[1]
    scripts_dir = repo / "scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        spec = importlib.util.spec_from_file_location(
            "hsd_provision_dashboards", scripts_dir / "hsd_provision_dashboards.py"
        )
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(scripts_dir))


def test_save_dashboard_html_replaces_existing_output(tmp_path):
    hsd_dashboard = load_hsd_dashboard_module()
    workbook = tmp_path / "time.xlsx"
    workbook.write_text("workbook placeholder", encoding="utf-8")
    output = tmp_path / "eliana.html"
    output.write_text("old dashboard", encoding="utf-8")

    def save_html(files: list[str], output_path: str) -> None:
        assert files == [str(workbook)]
        Path(output_path).write_text("new dashboard", encoding="utf-8")

    hsd_dashboard.save_dashboard_html(save_html, workbook, output)

    assert output.read_text(encoding="utf-8") == "new dashboard"


def test_provision_student_logs_missing_workbook_and_continues(tmp_path):
    provision = load_hsd_provision_dashboards_module()
    log_dir = tmp_path / "logs"

    ok, slug = provision.provision_student(
        "eliana",
        {"time_tracking_spreadsheet": tmp_path / "missing.xlsx"},
        log_dir,
    )

    assert ok is False
    assert slug == "eliana"
    assert "time_tracking_spreadsheet not found" in (
        log_dir / "eliana.log"
    ).read_text(encoding="utf-8")

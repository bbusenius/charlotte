from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import openpyxl


def load_hsd_read_module():
    repo = Path(__file__).resolve().parents[1]
    scripts_dir = repo / "scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        spec = importlib.util.spec_from_file_location(
            "hsd_read", scripts_dir / "hsd_read.py"
        )
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(scripts_dir))


def save_workbook(path: Path, sheets: dict[str, list[tuple[object, ...]]]) -> None:
    wb = openpyxl.Workbook()
    first = True
    for name, rows in sheets.items():
        ws = wb.active if first else wb.create_sheet(name)
        ws.title = name
        first = False
        for row in rows:
            ws.append(row)
    wb.save(path)


def test_collect_time_rows_sorts_and_calculates_duration(tmp_path):
    hsd_read = load_hsd_read_module()
    workbook = tmp_path / "time.xlsx"
    save_workbook(
        workbook,
        {
            "Math": [
                ("Date", "Start Time", "End Time", "Description", "Teacher", "Notes"),
                ("5/2/2026", "10:00 AM", "10:45 AM", "Lesson 2", "Parent", ""),
                ("5/1/2026", "9:00 AM", "9:30 AM", "Lesson 1", "Parent", "review"),
            ],
            "Science": [
                ("Date", "Start Time", "End Time", "Description", "Teacher"),
                ("5/1/2026", "11:00 AM", "11:20 AM", "Nature walk", "Parent"),
            ],
        },
    )

    rows = hsd_read.collect_time_rows(workbook, ["Math", "Science"], "Math")

    assert [row["description"] for row in rows] == ["Lesson 1", "Lesson 2"]
    assert rows[0]["duration_minutes"] == 30
    assert rows[0]["notes"] == "review"
    assert rows[1]["duration_minutes"] == 45


def test_collect_book_rows_uses_configured_sheet_roles(tmp_path):
    hsd_read = load_hsd_read_module()
    workbook = tmp_path / "reading.xlsx"
    save_workbook(
        workbook,
        {
            "Books read by Student": [
                (
                    "Title",
                    "Author",
                    "Language",
                    "ISBN",
                    "SKU",
                    "Level",
                    "Audiobook",
                    "Part of coursework?",
                ),
                ("Book One", "Author A", "English", "123", "", "400L", "", "Yes"),
            ],
            "Books read to Student": [
                ("Title", "Author", "Language", "ISBN"),
                ("Book Two", "Author B", "English", "456"),
            ],
        },
    )

    rows = hsd_read.collect_book_rows(
        workbook,
        {"read_by_self_sheet_index": 0, "read_to_sheet_index": 1},
    )

    assert [row["title"] for row in rows] == ["Book One", "Book Two"]
    assert [row["list_type"] for row in rows] == ["read_by_self", "read_to"]
    assert rows[0]["coursework"] == "Yes"
    assert rows[1]["isbn"] == "456"

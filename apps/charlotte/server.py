#!/usr/bin/env python3
"""Serve the Charlotte LAN info page and generated dashboard HTML."""

from __future__ import annotations

import argparse
import html
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

import yaml


def configured_schedules(registry_path: Path, schedule_root: Path) -> list[dict[str, str]]:
    """Return safely serveable schedule entries from the household registry."""
    if not registry_path.is_file():
        return []
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    configured = registry.get("schedules") or {}
    if not isinstance(configured, dict):
        return []

    root = schedule_root.resolve()
    entries = []
    for title, entry in configured.items():
        if not isinstance(entry, dict):
            continue
        raw_path = entry.get("path")
        if not isinstance(raw_path, str):
            continue
        relative = Path(raw_path)
        if relative.parts[:1] == ("schedules",):
            relative = Path(*relative.parts[1:])
        candidate = (root / relative).resolve()
        if (
            candidate.suffix != ".html"
            or candidate == root
            or root not in candidate.parents
            or not candidate.is_file()
        ):
            continue
        entries.append(
            {
                "title": str(title).strip(),
                "description": str(entry.get("description") or "").strip(),
                "path": str(candidate),
                "route": "/schedules/" + relative.as_posix(),
            }
        )
    return sorted(entries, key=lambda item: item["title"].lower())


class CharlotteInfoHandler(SimpleHTTPRequestHandler):
    """Serve static info assets plus generated dashboard files."""

    def safe_path(self, root: Path, request_path: str) -> Path:
        """Resolve a request path under a root, rejecting path traversal."""
        rel = request_path.lstrip("/")
        candidate = (root / rel).resolve()
        if candidate == root or root in candidate.parents:
            return candidate
        return root / "__not_found__"

    def translate_path(self, path: str) -> str:
        parsed = urlparse(path)
        request_path = unquote(parsed.path)
        if request_path.startswith("/dashboards/"):
            rel = request_path.removeprefix("/dashboards/").lstrip("/")
            return str(self.safe_path(self.server.dashboard_root, rel))
        if request_path == "/dashboards":
            return str(self.server.dashboard_root)
        return str(self.safe_path(self.server.static_root, request_path))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        request_path = unquote(parsed.path)

        if request_path in {"/", "/index.html"}:
            self.send_index_page()
            return

        if request_path in {"/dashboards", "/dashboards/"}:
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header("Location", "/#dashboards")
            self.end_headers()
            return

        if request_path.startswith("/dashboards/"):
            dashboard_path = Path(self.translate_path(self.path))
            if (
                dashboard_path.suffix == ".html"
                and dashboard_path.parent == self.server.dashboard_root
                and dashboard_path.is_file()
            ):
                super().do_GET()
                return
            self.send_missing_dashboard()
            return

        schedule_path = self.server.schedule_routes.get(request_path)
        if schedule_path is not None:
            if schedule_path.is_file():
                self.send_html(schedule_path.read_text(encoding="utf-8"), HTTPStatus.OK)
            else:
                self.send_missing_schedule()
            return

        super().do_GET()

    def dashboard_list_html(self) -> str:
        """Return inline dashboard links for the main page."""
        dashboards = sorted(self.server.dashboard_root.glob("*.html"))
        if dashboards:
            items = "\n".join(
                "<li><a href=\"/dashboards/{name}\">{label}</a></li>".format(
                    name=html.escape(path.name, quote=True),
                    label=html.escape(path.stem.replace("-", " ").title()),
                )
                for path in dashboards
            )
            return f"<ul class=\"dashboard-links\">{items}</ul>"
        return (
            "<p>No dashboards have been generated yet. Ask Charlotte to show a "
            "student's homeschool dashboard and it will appear here when ready.</p>"
        )

    def schedule_list_html(self) -> str:
        """Return inline links for schedules configured in students.yaml."""
        schedules = self.server.schedules
        if schedules:
            items = "\n".join(
                "<li><a href=\"{route}\">{title}</a>{description}</li>".format(
                    route=html.escape(item["route"], quote=True),
                    title=html.escape(item["title"]),
                    description=(
                        " — " + html.escape(item["description"])
                        if item["description"]
                        else ""
                    ),
                )
                for item in schedules
            )
            return f"<ul class=\"dashboard-links\">{items}</ul>"
        return "<p>No family schedules have been configured yet.</p>"

    def send_index_page(self) -> None:
        """Render the main info page with the current dashboard list."""
        index_path = self.server.static_root / "index.html"
        page = index_path.read_text(encoding="utf-8").replace(
            "<!-- DASHBOARD_LIST -->",
            self.dashboard_list_html(),
        ).replace("<!-- SCHEDULE_LIST -->", self.schedule_list_html())
        self.send_html(page, HTTPStatus.OK)

    def send_missing_dashboard(self) -> None:
        body = (
            "<h1>Dashboard Not Found</h1>"
            "<p>That dashboard has not been generated yet. Ask Charlotte to show "
            "the student's homeschool dashboard and try again.</p>"
        )
        self.send_html_page(body, HTTPStatus.NOT_FOUND)

    def send_missing_schedule(self) -> None:
        body = (
            "<h1>Schedule Not Found</h1>"
            "<p>That schedule is not available on this Charlotte page.</p>"
        )
        self.send_html_page(body, HTTPStatus.NOT_FOUND)

    def send_html_page(self, body: str, status: HTTPStatus) -> None:
        page = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Charlotte</title>
    <link rel="stylesheet" href="/style.css">
  </head>
  <body>
    <main class="page">
      <section class="about">
        {body}
        <p><a href="/">Back to Charlotte</a></p>
      </section>
    </main>
  </body>
</html>
"""
        self.send_html(page, status)

    def send_html(self, page: str, status: HTTPStatus) -> None:
        encoded = page.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


class CharlotteInfoServer(ThreadingHTTPServer):
    """HTTP server with static and dashboard roots."""

    def __init__(
        self,
        address: tuple[str, int],
        static_root: Path,
        dashboard_root: Path,
        schedule_root: Path,
        schedules: list[dict[str, str]],
    ):
        self.static_root = static_root.resolve()
        self.dashboard_root = dashboard_root.resolve()
        self.schedule_root = schedule_root.resolve()
        self.schedules = schedules
        self.schedule_routes = {
            schedule["route"]: Path(schedule["path"]) for schedule in schedules
        }
        super().__init__(address, CharlotteInfoHandler)


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve Charlotte's LAN info page.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8788)
    parser.add_argument("--static-root", type=Path, default=Path("apps/charlotte/static"))
    parser.add_argument("--dashboard-root", type=Path, default=Path("dashboards"))
    parser.add_argument("--schedule-root", type=Path, default=Path("schedules"))
    parser.add_argument("--registry", type=Path, default=Path("students.yaml"))
    args = parser.parse_args()

    server = CharlotteInfoServer(
        (args.host, args.port),
        args.static_root,
        args.dashboard_root,
        args.schedule_root,
        configured_schedules(args.registry, args.schedule_root),
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

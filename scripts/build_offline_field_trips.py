#!/usr/bin/env python3
"""Build self-contained, phone-friendly HTML copies of field-trip plans.

Examples:
    python3 scripts/build_offline_field_trips.py field-trips/history-center-of-olmsted-county.md

    python3 scripts/build_offline_field_trips.py \\
      field-trips/hoover-dam-and-route-66.md \\
      field-trips/grand-canyon-south-rim.md \\
      --combined-out field-trips/offline/colorado-river-two-day-excursion.html \\
      --combined-title "The Colorado River: A Two-Day Excursion"
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRIPS_DIR = ROOT / "field-trips"
DEFAULT_CSS = DEFAULT_TRIPS_DIR / "offline-mobile.css"
DEFAULT_OUT_DIR = DEFAULT_TRIPS_DIR / "offline"
DEFAULT_PEDAGOGY_WIKI_URL = (
    "https://github.com/bbusenius/charlotte/blob/master/pedagogies/charlotte-mason/wiki/"
)
LOCAL_PEDAGOGY_LINK_RE = re.compile(
    r"(?P<prefix>(?:\.\./)+(?:pedagogy|pedagogies/charlotte-mason)/wiki/)"
)
IMAGE_LINK_RE = re.compile(r"!\[(?P<alt>[^\]]*)]\((?P<target>[^)]+)\)")


@dataclass(frozen=True)
class PreparedTrip:
    source: Path
    title: str
    markdown: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "sources",
        nargs="+",
        type=Path,
        help="Field-trip markdown files to render.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=f"Directory for individual HTML files. Default: {DEFAULT_OUT_DIR}",
    )
    parser.add_argument(
        "--css",
        type=Path,
        default=DEFAULT_CSS,
        help=f"CSS file to embed. Default: {DEFAULT_CSS}",
    )
    parser.add_argument(
        "--combined-out",
        type=Path,
        help="Optional output path for a combined single-page HTML file.",
    )
    parser.add_argument(
        "--combined-title",
        help="Title for --combined-out. Default: derived from the output filename.",
    )
    parser.add_argument(
        "--overview",
        type=Path,
        help="Optional markdown file to prepend to --combined-out instead of the generated overview.",
    )
    parser.add_argument(
        "--no-individual",
        action="store_true",
        help="Only write --combined-out; do not write one HTML file per source.",
    )
    parser.add_argument(
        "--pedagogy-wiki-url",
        default=DEFAULT_PEDAGOGY_WIKI_URL,
        help="Base URL for local pedagogy wiki links in offline HTML.",
    )
    parser.add_argument(
        "--preserve-local-pedagogy-links",
        action="store_true",
        help="Do not rewrite local pedagogy wiki links to GitHub URLs.",
    )
    parser.add_argument(
        "--image-max-pixels",
        default="1400x1400>",
        help="ImageMagick resize geometry for embedded images. Default: 1400x1400>",
    )
    parser.add_argument(
        "--jpeg-quality",
        default="78",
        help="JPEG quality for embedded images. Default: 78",
    )
    args = parser.parse_args()
    if args.no_individual and not args.combined_out:
        parser.error("--no-individual requires --combined-out")
    return args


def split_frontmatter(markdown: str) -> tuple[dict, str]:
    match = re.match(r"\A---\n(?P<frontmatter>.*?)\n---\n+", markdown, flags=re.DOTALL)
    if not match:
        return {}, markdown
    try:
        frontmatter = yaml.safe_load(match.group("frontmatter")) or {}
    except Exception:
        frontmatter = {}
    return frontmatter, markdown[match.end() :]


def rewrite_pedagogy_links(markdown: str, base_url: str) -> str:
    normalized_base = base_url.rstrip("/") + "/"
    return LOCAL_PEDAGOGY_LINK_RE.sub(normalized_base, markdown)


def markdown_title(markdown: str, frontmatter: dict, fallback: str) -> str:
    heading = re.search(r"^#\s+(.+?)\s*$", markdown, flags=re.MULTILINE)
    if heading:
        return heading.group(1).strip()
    for key in ("title", "theme", "venue"):
        value = frontmatter.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return fallback


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "field-trip"


def is_local_image_target(target: str) -> bool:
    target = target.strip()
    if not target or target.startswith("#"):
        return False
    parsed = urlparse(target)
    return not parsed.scheme and not parsed.netloc


def parse_markdown_image_target(target: str) -> tuple[str, str]:
    cleaned = target.strip()
    match = re.match(
        r"^(?P<path><[^>]+>|[^\s]+)"
        r"(?P<title>\s+(?:\"[^\"]*\"|'[^']*'|\([^)]+\)))?\s*$",
        cleaned,
    )
    if not match:
        raise ValueError(f"Unsupported image link target: {target}")
    path = match.group("path")
    if path.startswith("<") and path.endswith(">"):
        path = path[1:-1]
    return unquote(path), match.group("title") or ""


def image_converter_command() -> list[str]:
    if shutil.which("magick"):
        return ["magick"]
    if shutil.which("convert"):
        return ["convert"]
    raise SystemExit(
        "This builder requires ImageMagick: install `magick` or `convert`."
    )


def render_image(
    *,
    source_image: Path,
    destination: Path,
    image_command: list[str],
    image_max_pixels: str,
    jpeg_quality: str,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        *image_command,
        str(source_image),
        "-auto-orient",
        "-strip",
        "-resize",
        image_max_pixels,
    ]
    if source_image.suffix.lower() in {".jpg", ".jpeg"}:
        command.extend(["-quality", jpeg_quality])
    command.append(str(destination))
    subprocess.run(command, check=True)


def rewrite_images(
    markdown: str,
    *,
    source: Path,
    workspace: Path,
    image_command: list[str],
    image_max_pixels: str,
    jpeg_quality: str,
) -> str:
    source_slug = slugify(source.stem)
    image_dir = workspace / "images" / source_slug
    image_map: dict[str, str] = {}

    def replace(match: re.Match[str]) -> str:
        target = match.group("target")
        if not is_local_image_target(target):
            return match.group(0)
        try:
            relative_image, title = parse_markdown_image_target(target)
        except ValueError:
            return match.group(0)
        source_image = (source.parent / relative_image).resolve()
        if not source_image.exists():
            raise FileNotFoundError(
                f"{display_path(source)} references missing image: {relative_image}"
            )
        rewritten = image_map.get(relative_image)
        if rewritten is None:
            suffix = source_image.suffix.lower()
            digest = hashlib.sha1(relative_image.encode("utf-8")).hexdigest()[:8]
            destination_name = f"{source_image.stem}-{digest}{suffix}"
            destination = image_dir / destination_name
            render_image(
                source_image=source_image,
                destination=destination,
                image_command=image_command,
                image_max_pixels=image_max_pixels,
                jpeg_quality=jpeg_quality,
            )
            rewritten = f"images/{source_slug}/{destination.name}"
            image_map[relative_image] = rewritten
        return f"![{match.group('alt')}]({rewritten}{title})"

    return IMAGE_LINK_RE.sub(replace, markdown)


def assert_no_code_blocks(source: Path, markdown: str) -> None:
    parsed = subprocess.run(
        ["pandoc", "--from=gfm", "--to=native"],
        input=markdown,
        text=True,
        capture_output=True,
        check=True,
    ).stdout
    if "CodeBlock" in parsed:
        raise ValueError(
            f"{display_path(source)} contains an unexpected Markdown code block"
        )


def prepare_trip(
    source: Path,
    *,
    workspace: Path,
    image_command: list[str],
    rewrite_wiki_links: bool,
    pedagogy_wiki_url: str,
    image_max_pixels: str,
    jpeg_quality: str,
) -> PreparedTrip:
    source = source.expanduser().resolve()
    frontmatter, markdown = split_frontmatter(source.read_text(encoding="utf-8"))
    title = markdown_title(
        markdown,
        frontmatter,
        source.stem.replace("-", " ").title(),
    )
    if rewrite_wiki_links:
        markdown = rewrite_pedagogy_links(markdown, pedagogy_wiki_url)
    markdown = rewrite_images(
        markdown,
        source=source,
        workspace=workspace,
        image_command=image_command,
        image_max_pixels=image_max_pixels,
        jpeg_quality=jpeg_quality,
    )
    assert_no_code_blocks(source, markdown)
    return PreparedTrip(source=source, title=title, markdown=markdown)


def render(markdown: str, title: str, output: Path, workspace: Path, css: Path) -> None:
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    source = workspace / f"{output.stem}.md"
    source.write_text(markdown, encoding="utf-8")
    subprocess.run(
        [
            "pandoc",
            "--from=gfm",
            "--to=html5",
            "--standalone",
            "--embed-resources",
            "--resource-path",
            str(workspace),
            "--css",
            str(css.expanduser().resolve()),
            "--metadata",
            f"pagetitle={title}",
            "--output",
            str(output),
            str(source),
        ],
        check=True,
    )


def combined_title(args: argparse.Namespace) -> str:
    if args.combined_title:
        return args.combined_title
    if args.combined_out:
        return args.combined_out.stem.replace("-", " ").title()
    return "Offline Field Trips"


def generated_overview(title: str, trips: list[PreparedTrip]) -> str:
    lines = [
        f"# {title}",
        "",
        '<div class="trip-overview">',
        "",
        "## At a glance",
        "",
    ]
    for index, trip in enumerate(trips, start=1):
        lines.append(f"{index}. **{trip.title}**")
    lines.extend(["", "</div>", ""])
    return "\n".join(lines)


def combined_markdown(
    *,
    title: str,
    trips: list[PreparedTrip],
    overview: Path | None,
) -> str:
    if overview:
        prefix = overview.expanduser().read_text(encoding="utf-8").rstrip() + "\n\n"
    else:
        prefix = generated_overview(title, trips)
    body = "\n\n---\n\n".join(trip.markdown.strip() for trip in trips)
    return prefix + body + "\n"


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def main() -> None:
    args = parse_args()
    if not shutil.which("pandoc"):
        raise SystemExit("This builder requires pandoc.")
    image_command = image_converter_command()

    with tempfile.TemporaryDirectory(prefix="charlotte-field-trips-") as temp:
        workspace = Path(temp)
        trips = [
            prepare_trip(
                source,
                workspace=workspace,
                image_command=image_command,
                rewrite_wiki_links=not args.preserve_local_pedagogy_links,
                pedagogy_wiki_url=args.pedagogy_wiki_url,
                image_max_pixels=args.image_max_pixels,
                jpeg_quality=args.jpeg_quality,
            )
            for source in args.sources
        ]

        outputs: list[Path] = []
        if not args.no_individual:
            for trip in trips:
                output = args.out_dir / f"{slugify(trip.source.stem)}.html"
                render(trip.markdown, trip.title, output, workspace, args.css)
                outputs.append(output.expanduser().resolve())

        if args.combined_out:
            title = combined_title(args)
            render(
                combined_markdown(title=title, trips=trips, overview=args.overview),
                title,
                args.combined_out,
                workspace,
                args.css,
            )
            outputs.append(args.combined_out.expanduser().resolve())

    for output in outputs:
        print(f"{display_path(output)}\t{output.stat().st_size}")


if __name__ == "__main__":
    main()

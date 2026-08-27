from pathlib import Path
import re

import pytest


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_lesson_logs_are_excluded_from_the_docker_build_context():
    entries = {
        line.strip()
        for line in read(".dockerignore").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    assert "lesson-logs/" in entries


@pytest.mark.parametrize(
    "wrapper",
    [
        "runtime/hermes/run.sh",
        "runtime/openclaw/run.sh",
    ],
)
def test_container_wrappers_persist_lesson_logs(wrapper):
    text = read(wrapper)
    assert '"$repo_root/lesson-logs"' in text
    assert '-v "$repo_root/lesson-logs:/workspace/lesson-logs"' in text


@pytest.mark.parametrize(
    "dockerfile",
    [
        "runtime/hermes/Dockerfile",
        "runtime/openclaw/Dockerfile",
    ],
)
def test_container_images_provision_the_lesson_log_mountpoint(dockerfile):
    assert "/workspace/lesson-logs" in read(dockerfile)


@pytest.mark.parametrize(
    "dockerfile",
    [
        "runtime/hermes/Dockerfile",
        "runtime/openclaw/Dockerfile",
    ],
)
def test_container_images_install_native_pdf_reader(dockerfile):
    assert "poppler-utils" in read(dockerfile)


def test_hermes_native_writer_allows_each_writable_content_root():
    text = read("runtime/hermes/run.sh")
    match = re.search(r'^hermes_write_safe_root="([^"]+)"$', text, re.MULTILINE)
    assert match is not None

    safe_roots = set(match.group(1).split(":"))
    writable_mounts = set(
        re.findall(r'-v "\$repo_root/[^:"]+:(/workspace/[^":]+)"', text)
    )

    assert "/opt/data" in safe_roots
    assert "/workspace/.state" in safe_roots
    assert "/workspace/.scratch" in safe_roots
    assert "/workspace" not in safe_roots
    assert writable_mounts <= safe_roots
    assert '-e "HERMES_WRITE_SAFE_ROOT=$hermes_write_safe_root"' in text
    assert "/workspace/.scratch" in read("runtime/hermes/Dockerfile")
    assert "/workspace/.state" in read("runtime/hermes/Dockerfile")


def test_hermes_persists_workflow_state_and_scratch():
    text = read("runtime/hermes/run.sh")

    for name in (".state", ".scratch"):
        assert f'"$repo_root/{name}"' in text
        assert f'-v "$repo_root/{name}:/workspace/{name}"' in text

    assert ".state/" in read(".dockerignore").splitlines()


def test_openclaw_persists_workflow_state_and_scratch():
    text = read("runtime/openclaw/run.sh")

    for name in (".state", ".scratch"):
        assert f'"$repo_root/{name}"' in text
        assert f'-v "$repo_root/{name}:/workspace/{name}"' in text
        assert f"/workspace/{name}" in read("runtime/openclaw/Dockerfile")


def test_hermes_bakes_and_enables_direct_gemini_image_provider():
    dockerfile = read("runtime/hermes/Dockerfile")
    config = read("runtime/hermes/config.yaml.example")

    assert "runtime/hermes/plugins/image_gen/gemini" in dockerfile
    assert 'provider: "gemini"' in config
    assert 'model: "quality"' in config
    assert "image_gen" in config
    assert "NANOGPT" not in config
    terminal = config.split("terminal:", 1)[1].split("web:", 1)[0]
    assert "GEMINI_API_KEY" not in terminal


def test_hermes_enables_browser_for_keyless_page_retrieval():
    config = read("runtime/hermes/config.yaml.example")

    assert "search_backend: ddgs" in config
    for platform in ("cli", "telegram", "discord"):
        line = next(
            line
            for line in config.splitlines()
            if line.strip().startswith(f"{platform}:")
        )
        assert "browser" in line


def test_hermes_disables_autonomous_skill_rewrites():
    config = read("runtime/hermes/config.yaml.example")

    assert "creation_nudge_interval: 0" in config
    assert re.search(r"^curator:\n  enabled: false$", config, re.MULTILINE)


def test_hermes_provisions_file_utility_for_media_qc():
    dockerfile = read("runtime/hermes/Dockerfile")

    assert re.search(r"^        file \\$", dockerfile, re.MULTILINE)

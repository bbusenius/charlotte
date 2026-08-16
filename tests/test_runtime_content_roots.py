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

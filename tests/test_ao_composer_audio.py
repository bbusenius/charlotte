from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def load_module():
    path = Path(__file__).resolve().parents[1] / "skills/ao-composer-study/scripts/download_audio.py"
    spec = importlib.util.spec_from_file_location("ao_composer_audio", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeDownloader:
    def __init__(self, options):
        self.options = options

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def extract_info(self, url, download):
        assert download is True
        assert self.options["noplaylist"] is True
        assert self.options["ignoreconfig"] is True
        Path(self.options["outtmpl"].replace("%(ext)s", "mp3")).write_bytes(b"audio")
        return {
            "webpage_url": url,
            "title": "Example Work",
            "uploader": "Example Orchestra",
            "duration": 180,
            "extractor_key": "Youtube",
            "id": "abc",
        }


def test_download_returns_file_and_source_metadata(tmp_path):
    mod = load_module()
    result = mod.download_audio(
        url="https://youtu.be/example",
        output_dir=tmp_path,
        stem="work-recording",
        ydl_factory=FakeDownloader,
    )
    assert Path(result["path"]).read_bytes() == b"audio"
    assert result["performer"] == "Example Orchestra"
    assert result["duration"] == 180
    assert result["source_url"] == "https://youtu.be/example"


@pytest.mark.parametrize("url", ["file:///tmp/a", "not-a-url"])
def test_rejects_non_web_urls(tmp_path, url):
    mod = load_module()
    with pytest.raises(ValueError, match="HTTP or HTTPS"):
        mod.download_audio(url=url, output_dir=tmp_path, stem="work-recording", ydl_factory=FakeDownloader)


def test_rejects_unsafe_output_stems(tmp_path):
    mod = load_module()
    with pytest.raises(ValueError, match="output stem"):
        mod.download_audio(url="https://example.test/audio", output_dir=tmp_path, stem="../escape", ydl_factory=FakeDownloader)


def test_youtube_retries_with_player_clients_after_default_failure(tmp_path):
    mod = load_module()
    calls = []

    class RetryDownloader(FakeDownloader):
        def extract_info(self, url, download):
            calls.append(self.options)
            if len(calls) == 1:
                raise RuntimeError("HTTP Error 403: Forbidden")
            return super().extract_info(url, download)

    result = mod.download_audio(
        url="https://www.youtube.com/watch?v=example",
        output_dir=tmp_path,
        stem="work-recording",
        ydl_factory=RetryDownloader,
    )

    assert len(calls) == 2
    assert calls[1]["format"] == "18/bestaudio/best"
    assert calls[1]["extractor_args"] == {
        "youtube": {"player_client": ["android", "web"]}
    }
    assert result["download_strategy"] == "youtube-player-client-fallback"


def test_non_youtube_download_failure_is_not_retried(tmp_path):
    mod = load_module()
    calls = []

    class FailingDownloader(FakeDownloader):
        def extract_info(self, url, download):
            calls.append(self.options)
            raise RuntimeError("download failed")

    with pytest.raises(RuntimeError, match="download failed"):
        mod.download_audio(
            url="https://example.test/audio",
            output_dir=tmp_path,
            stem="work-recording",
            ydl_factory=FailingDownloader,
        )

    assert len(calls) == 1

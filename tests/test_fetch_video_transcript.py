from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def load_module():
    path = Path(__file__).resolve().parents[1] / "scripts/fetch_video_transcript.py"
    spec = importlib.util.spec_from_file_location("fetch_video_transcript", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


WEBVTT = """WEBVTT
Kind: captions
Language: en

00:00:00.000 --> 00:00:02.000
hello <c>world</c>

00:00:02.000 --> 00:00:02.010
hello world

00:00:02.010 --> 00:00:04.000
Bees collect nectar from flowers.
"""

JSON3 = """
{
  "events": [
    {"tStartMs": 0, "dDurationMs": 2000, "segs": [{"utf8": "hello "}, {"utf8": "world"}]},
    {"tStartMs": 1500, "dDurationMs": 2000, "segs": [{"utf8": "hello world"}]},
    {"tStartMs": 2000, "dDurationMs": 2000, "segs": [{"utf8": "Bees collect nectar from flowers."}]}
  ]
}
"""

SRT = """1
00:00:00,000 --> 00:00:02,000
hello world

2
00:00:02,000 --> 00:00:04,000
Bees collect nectar from flowers.
"""


class FakeDownloader:
    def __init__(self, options):
        self.options = options
        self.opened = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def extract_info(self, url, download):
        assert download is False
        assert self.options["skip_download"] is True
        assert self.options["noplaylist"] is True
        assert self.options["ignoreconfig"] is True
        return {
            "webpage_url": url,
            "title": "How Bees Make Honey",
            "uploader": "SciShow Kids",
            "duration": 252,
            "description": "A kids science video about honeybees.",
            "extractor_key": "Youtube",
            "id": "abc",
            "subtitles": {
                "en": [{"ext": "vtt", "data": WEBVTT}],
            },
        }

    def urlopen(self, url):
        self.opened.append(url)

        class Response:
            def read(self):
                return WEBVTT.encode()

        return Response()


def test_rejects_non_web_urls():
    mod = load_module()
    with pytest.raises(ValueError, match="HTTP or HTTPS"):
        mod.fetch_video_transcript("file:///tmp/video.mp4", ydl_factory=FakeDownloader)


def test_vtt_strips_cues_tags_and_rolling_duplicates():
    mod = load_module()
    text = mod.caption_payload_to_text(WEBVTT, "vtt")
    assert text == "hello world Bees collect nectar from flowers."


def test_json3_and_srt_yield_the_spoken_words():
    mod = load_module()
    assert "Bees collect nectar from flowers." in mod.caption_payload_to_text(JSON3, "json3")
    assert "hello world" in mod.caption_payload_to_text(SRT, "srt")


def test_xml_captions_keep_cue_text():
    mod = load_module()
    xml = (
        '<transcript><text start="0" dur="2">hello world</text>'
        '<text start="2" dur="2">Bees collect nectar from flowers.</text></transcript>'
    )
    assert mod.caption_payload_to_text(xml, "srv1") == (
        "hello world Bees collect nectar from flowers."
    )


def test_fetch_returns_canonical_url_title_and_transcript():
    mod = load_module()
    result = mod.fetch_video_transcript(
        "https://youtu.be/example",
        ydl_factory=FakeDownloader,
    )
    assert result["ok"] is True
    assert result["source_url"] == "https://youtu.be/example"
    assert result["title"] == "How Bees Make Honey"
    assert result["channel"] == "SciShow Kids"
    assert result["duration"] == 252
    assert result["transcript_kind"] == "captions"
    assert result["transcript"] == "hello world Bees collect nectar from flowers."
    assert result["download_strategy"] == "default"


def test_prefers_human_captions_over_auto_captions():
    mod = load_module()

    class AutoAndManual(FakeDownloader):
        def extract_info(self, url, download):
            info = super().extract_info(url, download)
            info["automatic_captions"] = {
                "en": [{"ext": "vtt", "data": "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nauto only\n"}]
            }
            return info

    result = mod.fetch_video_transcript(
        "https://www.youtube.com/watch?v=example",
        ydl_factory=AutoAndManual,
    )
    assert result["transcript_kind"] == "captions"
    assert "auto only" not in result["transcript"]


def test_falls_back_to_auto_captions_and_can_fetch_by_url():
    mod = load_module()

    class AutoOnly(FakeDownloader):
        def extract_info(self, url, download):
            info = super().extract_info(url, download)
            info.pop("subtitles")
            info["automatic_captions"] = {
                "en": [{"ext": "vtt", "url": "https://example.test/captions.vtt"}]
            }
            return info

    result = mod.fetch_video_transcript(
        "https://www.youtube.com/watch?v=example",
        ydl_factory=AutoOnly,
    )
    assert result["transcript_kind"] == "auto-captions"
    assert "Bees collect nectar from flowers." in result["transcript"]


def test_missing_captions_still_return_metadata():
    mod = load_module()

    class NoCaptions(FakeDownloader):
        def extract_info(self, url, download):
            info = super().extract_info(url, download)
            info.pop("subtitles")
            return info

    result = mod.fetch_video_transcript(
        "https://vimeo.com/123",
        ydl_factory=NoCaptions,
    )
    assert result["ok"] is True
    assert result["title"] == "How Bees Make Honey"
    assert result["transcript"] == ""
    assert result["transcript_kind"] is None


def test_youtube_retries_with_player_clients_after_default_failure():
    mod = load_module()
    calls = []

    class RetryDownloader(FakeDownloader):
        def extract_info(self, url, download):
            calls.append(self.options)
            if len(calls) == 1:
                raise RuntimeError("HTTP Error 403: Forbidden")
            return super().extract_info(url, download)

    result = mod.fetch_video_transcript(
        "https://www.youtube.com/watch?v=example",
        ydl_factory=RetryDownloader,
    )
    assert len(calls) == 2
    assert calls[1]["extractor_args"] == {
        "youtube": {"player_client": ["android", "web"]}
    }
    assert result["download_strategy"] == "youtube-player-client-fallback"
    assert result["transcript"]


def test_non_youtube_failure_is_not_retried():
    mod = load_module()
    calls = []

    class FailingDownloader(FakeDownloader):
        def extract_info(self, url, download):
            calls.append(self.options)
            raise RuntimeError("extractor failed")

    with pytest.raises(RuntimeError, match="extractor failed"):
        mod.fetch_video_transcript(
            "https://vimeo.com/123",
            ydl_factory=FailingDownloader,
        )
    assert len(calls) == 1

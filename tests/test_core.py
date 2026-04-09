"""
Tests for ff-kit core operations.

These tests mock subprocess.run so they work without FFmpeg installed.
"""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch, ANY

import pytest

from ff_kit.executor import Executor, FFmpegExecutionError, FFmpegNotFoundError


# ── Executor tests ────────────────────────────────────────────────


@patch("shutil.which", return_value=None)
def test_executor_raises_if_ffmpeg_not_found(mock_which):
    with pytest.raises(FFmpegNotFoundError):
        Executor()


@patch("shutil.which", return_value="/usr/bin/ffmpeg")
@patch("subprocess.run")
def test_executor_run_success(mock_run, mock_which):
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    exe = Executor()
    result = exe.run(["-i", "in.mp4", "out.mp4"], output_path="out.mp4")
    assert result.returncode == 0
    assert result.output_path == "out.mp4"


@patch("shutil.which", return_value="/usr/bin/ffmpeg")
@patch("subprocess.run")
def test_executor_run_failure(mock_run, mock_which):
    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Error!")
    exe = Executor()
    with pytest.raises(FFmpegExecutionError) as exc_info:
        exe.run(["-i", "bad.mp4", "out.mp4"])
    assert exc_info.value.returncode == 1
    assert "Error!" in exc_info.value.stderr


@patch("shutil.which", return_value="/usr/bin/ffmpeg")
@patch("subprocess.run")
def test_executor_probe(mock_run, mock_which):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout='{"format": {"duration": "120.5"}, "streams": []}',
        stderr="",
    )
    exe = Executor()
    info = exe.probe("video.mp4")
    assert info["format"]["duration"] == "120.5"


# ── Clip tests ────────────────────────────────────────────────────


@patch("shutil.which", return_value="/usr/bin/ffmpeg")
@patch("subprocess.run")
def test_clip_with_duration(mock_run, mock_which):
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    from ff_kit.core.clip import clip

    result = clip("in.mp4", "out.mp4", start="00:01:00", duration="30")
    assert result.output_path == "out.mp4"

    cmd = mock_run.call_args[0][0]
    assert "-ss" in cmd
    assert "-t" in cmd
    assert "30" in cmd


@patch("shutil.which", return_value="/usr/bin/ffmpeg")
@patch("subprocess.run")
def test_clip_with_end(mock_run, mock_which):
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    from ff_kit.core.clip import clip

    result = clip("in.mp4", "out.mp4", start="00:01:00", end="00:02:00")
    cmd = mock_run.call_args[0][0]
    assert "-to" in cmd


def test_clip_requires_end_or_duration():
    from ff_kit.core.clip import clip

    with pytest.raises(ValueError, match="Either"):
        clip("in.mp4", "out.mp4", start="0")


def test_clip_rejects_both_end_and_duration():
    from ff_kit.core.clip import clip

    with pytest.raises(ValueError, match="not both"):
        clip("in.mp4", "out.mp4", start="0", end="10", duration="10")


# ── Merge tests ───────────────────────────────────────────────────


def test_merge_requires_two_files():
    from ff_kit.core.merge import merge

    with pytest.raises(ValueError, match="at least 2"):
        merge(["only_one.mp4"], "out.mp4")


@patch("shutil.which", return_value="/usr/bin/ffmpeg")
@patch("subprocess.run")
def test_merge_demuxer(mock_run, mock_which):
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    from ff_kit.core.merge import merge

    result = merge(["a.mp4", "b.mp4"], "merged.mp4")
    cmd = mock_run.call_args[0][0]
    assert "-f" in cmd
    assert "concat" in cmd


@patch("shutil.which", return_value="/usr/bin/ffmpeg")
@patch("subprocess.run")
def test_merge_filter(mock_run, mock_which):
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    from ff_kit.core.merge import merge

    result = merge(["a.mp4", "b.mp4"], "merged.mp4", method="concat_filter")
    cmd = mock_run.call_args[0][0]
    assert "-filter_complex" in cmd


# ── Extract audio tests ──────────────────────────────────────────


@patch("shutil.which", return_value="/usr/bin/ffmpeg")
@patch("subprocess.run")
def test_extract_audio_defaults(mock_run, mock_which):
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    from ff_kit.core.extract_audio import extract_audio

    result = extract_audio("video.mp4", "audio.aac")
    cmd = mock_run.call_args[0][0]
    assert "-vn" in cmd
    assert "-acodec" in cmd


@patch("shutil.which", return_value="/usr/bin/ffmpeg")
@patch("subprocess.run")
def test_extract_audio_with_options(mock_run, mock_which):
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    from ff_kit.core.extract_audio import extract_audio

    result = extract_audio(
        "video.mp4", "audio.wav",
        codec="pcm_s16le", sample_rate=16000, channels=1,
    )
    cmd = mock_run.call_args[0][0]
    assert "pcm_s16le" in cmd
    assert "16000" in cmd
    assert "-ac" in cmd


# ── Add subtitles tests ─────────────────────────────────────────


@patch("shutil.which", return_value="/usr/bin/ffmpeg")
@patch("subprocess.run")
def test_add_subtitles_burn(mock_run, mock_which):
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    from ff_kit.core.add_subtitles import add_subtitles

    result = add_subtitles("video.mp4", "out.mp4", "subs.srt", mode="burn")
    cmd = mock_run.call_args[0][0]
    assert any("subtitles=" in arg for arg in cmd)


@patch("shutil.which", return_value="/usr/bin/ffmpeg")
@patch("subprocess.run")
def test_add_subtitles_embed(mock_run, mock_which):
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    from ff_kit.core.add_subtitles import add_subtitles

    result = add_subtitles("video.mp4", "out.mkv", "subs.srt", mode="embed")
    cmd = mock_run.call_args[0][0]
    assert "mov_text" in cmd


def test_add_subtitles_invalid_mode():
    from ff_kit.core.add_subtitles import add_subtitles

    with pytest.raises(ValueError, match="mode"):
        add_subtitles("video.mp4", "out.mp4", "subs.srt", mode="invalid")


# ── Transcode tests ──────────────────────────────────────────────


@patch("shutil.which", return_value="/usr/bin/ffmpeg")
@patch("subprocess.run")
def test_transcode_basic(mock_run, mock_which):
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    from ff_kit.core.transcode import transcode

    result = transcode("in.mp4", "out.webm", video_codec="libvpx-vp9")
    cmd = mock_run.call_args[0][0]
    assert "-c:v" in cmd
    assert "libvpx-vp9" in cmd


@patch("shutil.which", return_value="/usr/bin/ffmpeg")
@patch("subprocess.run")
def test_transcode_full_options(mock_run, mock_which):
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    from ff_kit.core.transcode import transcode

    result = transcode(
        "in.mp4", "out.mp4",
        video_codec="libx264", audio_codec="aac",
        resolution="1280x720", bitrate="2M",
        fps=30, preset="fast", crf=23,
    )
    cmd = mock_run.call_args[0][0]
    assert "1280x720" in cmd
    assert "2M" in cmd
    assert "30" in cmd
    assert "fast" in cmd
    assert "23" in cmd

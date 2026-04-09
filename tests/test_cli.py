"""Tests for the CLI entry point."""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

from ff_kit.cli import main


def test_no_args_prints_help(capsys):
    ret = main([])
    assert ret == 0


def test_list_tools_openai(capsys):
    ret = main(["list-tools", "--format", "openai"])
    assert ret == 0
    out = capsys.readouterr().out
    tools = json.loads(out)
    assert len(tools) == 5
    assert tools[0]["type"] == "function"


def test_list_tools_anthropic(capsys):
    ret = main(["list-tools", "--format", "anthropic"])
    assert ret == 0
    out = capsys.readouterr().out
    tools = json.loads(out)
    assert len(tools) == 5
    assert "input_schema" in tools[0]


@patch("shutil.which", return_value="/usr/bin/ffmpeg")
@patch("subprocess.run")
def test_clip_command(mock_run, mock_which, capsys):
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    ret = main(["clip", "in.mp4", "out.mp4", "--start", "0", "--duration", "30"])
    assert ret == 0
    assert "Done:" in capsys.readouterr().out


@patch("shutil.which", return_value="/usr/bin/ffmpeg")
@patch("subprocess.run")
def test_extract_audio_command(mock_run, mock_which, capsys):
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    ret = main(["extract-audio", "in.mp4", "out.wav", "--codec", "pcm_s16le", "--sample-rate", "16000"])
    assert ret == 0
    assert "Done:" in capsys.readouterr().out


@patch("shutil.which", return_value="/usr/bin/ffmpeg")
@patch("subprocess.run")
def test_probe_command(mock_run, mock_which, capsys):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout='{"format": {"duration": "60"}, "streams": []}',
        stderr="",
    )
    ret = main(["probe", "video.mp4"])
    assert ret == 0
    out = capsys.readouterr().out
    info = json.loads(out)
    assert "format" in info


def test_clip_missing_required_args():
    """Clip without --start should raise SystemExit(2) from argparse."""
    import pytest

    with pytest.raises(SystemExit) as exc_info:
        main(["clip", "in.mp4", "out.mp4"])
    assert exc_info.value.code == 2

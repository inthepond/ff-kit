"""Tests for the one-shot JSON bridge."""

from __future__ import annotations

import io
import json

import pytest

import ff_kit.bridge as bridge
from ff_kit.bridge import BridgeProtocolError, run_request


# ---------------------------------------------------------------------------
# run_request — protocol validation
# ---------------------------------------------------------------------------

def test_rejects_non_object_request():
    with pytest.raises(BridgeProtocolError):
        run_request(["not", "an", "object"])


def test_rejects_missing_tool():
    with pytest.raises(BridgeProtocolError):
        run_request({"arguments": {}})


def test_rejects_non_dict_arguments():
    with pytest.raises(BridgeProtocolError):
        run_request({"tool": "ffkit_clip", "arguments": "nope"})


def test_rejects_non_dict_executor():
    with pytest.raises(BridgeProtocolError):
        run_request({"tool": "ffkit_clip", "arguments": {}, "executor": "nope"})


# ---------------------------------------------------------------------------
# run_request — dispatch integration (in-band errors, no FFmpeg needed)
# ---------------------------------------------------------------------------

def test_unknown_tool_is_in_band_error():
    resp = run_request({"tool": "ffkit_nonexistent", "arguments": {}})
    assert resp["status"] == "error"
    assert "Unknown tool" in resp["error"]


def test_validation_error_is_in_band():
    """clip without end/duration fails validation before touching FFmpeg."""
    resp = run_request({
        "tool": "ffkit_clip",
        "arguments": {"input_path": "in.mp4", "output_path": "out.mp4", "start": "0"},
    })
    assert resp["status"] == "error"
    assert "ValueError" in resp["error"]


def test_bad_executor_binary_is_in_band_error():
    resp = run_request({
        "tool": "ffkit_clip",
        "arguments": {},
        "executor": {"ffmpeg_bin": "definitely-not-a-real-binary-xyz"},
    })
    assert resp["status"] == "error"
    assert "FFmpegNotFoundError" in resp["error"]


def test_executor_config_is_forwarded(monkeypatch):
    seen = {}

    def fake_dispatch(tool, arguments, *, executor=None):
        seen["executor"] = executor
        return {"status": "ok"}

    monkeypatch.setattr(bridge, "dispatch", fake_dispatch)
    monkeypatch.setattr(
        bridge, "Executor", lambda **kwargs: kwargs  # avoid FFmpeg lookup
    )
    resp = run_request({
        "tool": "ffkit_clip",
        "arguments": {},
        "executor": {"timeout": 60, "unknown_key": "dropped"},
    })
    assert resp == {"status": "ok"}
    assert seen["executor"] == {"timeout": 60}


# ---------------------------------------------------------------------------
# main — stdin/stdout plumbing
# ---------------------------------------------------------------------------

def test_main_ok_roundtrip(monkeypatch, capsys):
    monkeypatch.setattr(
        bridge, "dispatch", lambda tool, arguments, *, executor=None: {"status": "ok"}
    )
    monkeypatch.setattr("sys.stdin", io.StringIO('{"tool": "ffkit_clip", "arguments": {}}'))
    monkeypatch.setattr("sys.argv", ["ff_kit.bridge"])
    assert bridge.main() == 0
    out = capsys.readouterr().out
    assert json.loads(out) == {"status": "ok"}


def test_main_invalid_json_exits_2(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("{not json"))
    monkeypatch.setattr("sys.argv", ["ff_kit.bridge"])
    assert bridge.main() == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "invalid JSON" in captured.err


def test_main_protocol_error_exits_2(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO('{"arguments": {}}'))
    monkeypatch.setattr("sys.argv", ["ff_kit.bridge"])
    assert bridge.main() == 2
    assert "'tool'" in capsys.readouterr().err


def test_main_version(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["ff_kit.bridge", "--version"])
    assert bridge.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["name"] == "ff-toolkit"
    assert payload["version"]

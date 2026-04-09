"""Tests for schema generation and dispatch."""

from __future__ import annotations

from ff_kit.schemas.openai import openai_tools
from ff_kit.schemas.anthropic import anthropic_tools
from ff_kit.dispatch import dispatch, list_tools


# ── Schema structure tests ────────────────────────────────────────


def test_openai_tools_returns_five():
    tools = openai_tools()
    assert len(tools) == 5
    for t in tools:
        assert t["type"] == "function"
        assert "name" in t["function"]
        assert "parameters" in t["function"]
        assert t["function"]["name"].startswith("ffkit_")


def test_anthropic_tools_returns_five():
    tools = anthropic_tools()
    assert len(tools) == 5
    for t in tools:
        assert "name" in t
        assert "input_schema" in t
        assert t["name"].startswith("ffkit_")


def test_tool_names_match_across_formats():
    oa_names = {t["function"]["name"] for t in openai_tools()}
    an_names = {t["name"] for t in anthropic_tools()}
    assert oa_names == an_names


def test_all_tools_have_required_fields():
    for t in openai_tools():
        params = t["function"]["parameters"]
        assert "required" in params
        assert len(params["required"]) >= 1


# ── Dispatch tests ────────────────────────────────────────────────


def test_list_tools_returns_all_five():
    names = list_tools()
    assert len(names) == 5
    assert "ffkit_clip" in names


def test_dispatch_unknown_tool():
    result = dispatch("ffkit_nonexistent", {})
    assert result["status"] == "error"
    assert "Unknown tool" in result["error"]


def test_dispatch_clip_missing_args():
    """Dispatch should catch errors from the underlying function."""
    result = dispatch("ffkit_clip", {
        "input_path": "in.mp4",
        "output_path": "out.mp4",
        "start": "0",
        # Missing both end and duration → ValueError
    })
    assert result["status"] == "error"
    assert "ValueError" in result["error"]

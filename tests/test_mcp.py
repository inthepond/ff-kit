"""Tests for the MCP server request handling."""

from __future__ import annotations

import json

from ff_kit.mcp.server import _handle_request


def test_initialize():
    resp = _handle_request({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {},
    })
    assert resp["id"] == 1
    result = resp["result"]
    assert result["serverInfo"]["name"] == "ff-kit"
    assert "tools" in result["capabilities"]


def test_tools_list():
    resp = _handle_request({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {},
    })
    tools = resp["result"]["tools"]
    assert len(tools) == 5
    names = {t["name"] for t in tools}
    assert "ffkit_clip" in names
    assert "ffkit_merge" in names


def test_tools_call_unknown():
    resp = _handle_request({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "ffkit_nonexistent", "arguments": {}},
    })
    content = json.loads(resp["result"]["content"][0]["text"])
    assert content["status"] == "error"
    assert resp["result"]["isError"] is True


def test_tools_call_validation_error():
    """Calling clip without end/duration should return an error, not crash."""
    resp = _handle_request({
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "ffkit_clip",
            "arguments": {
                "input_path": "in.mp4",
                "output_path": "out.mp4",
                "start": "0",
            },
        },
    })
    content = json.loads(resp["result"]["content"][0]["text"])
    assert content["status"] == "error"
    assert resp["result"]["isError"] is True


def test_method_not_found():
    resp = _handle_request({
        "jsonrpc": "2.0",
        "id": 99,
        "method": "unknown/method",
    })
    assert "error" in resp
    assert resp["error"]["code"] == -32601

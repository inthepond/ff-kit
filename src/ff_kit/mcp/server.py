"""
ff-kit MCP server — expose FFmpeg operations over the Model Context Protocol.

Run standalone::

    python -m ff_kit.mcp.server

Or add to your Claude Desktop / Cursor config::

    {
      "mcpServers": {
        "ff-kit": {
          "command": "python",
          "args": ["-m", "ff_kit.mcp.server"]
        }
      }
    }
"""

from __future__ import annotations

import json
import sys
from typing import Any

from ff_kit.dispatch import dispatch, list_tools
from ff_kit.schemas.openai import openai_tools

# ---------------------------------------------------------------------------
# MCP protocol helpers (JSON-RPC over stdio)
# ---------------------------------------------------------------------------

_TOOL_DEFS = openai_tools()

# Build a lookup: tool name -> description + input schema
_TOOL_META: dict[str, dict[str, Any]] = {}
for t in _TOOL_DEFS:
    fn = t["function"]
    _TOOL_META[fn["name"]] = {
        "description": fn["description"],
        "inputSchema": fn["parameters"],
    }


def _make_response(id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": id, "result": result}


def _make_error(id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}


def _handle_request(req: dict) -> dict:
    """Route a single JSON-RPC request to the appropriate handler."""
    method = req.get("method", "")
    id_ = req.get("id")
    params = req.get("params", {})

    if method == "initialize":
        return _make_response(id_, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "ff-kit", "version": "0.1.0"},
        })

    if method == "notifications/initialized":
        # Client acknowledgement — no response needed, but we return None
        return None  # type: ignore[return-value]

    if method == "tools/list":
        tools = []
        for name in list_tools():
            meta = _TOOL_META[name]
            tools.append({
                "name": name,
                "description": meta["description"],
                "inputSchema": meta["inputSchema"],
            })
        return _make_response(id_, {"tools": tools})

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        result = dispatch(tool_name, arguments)

        is_error = result.get("status") == "error"
        return _make_response(id_, {
            "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
            "isError": is_error,
        })

    return _make_error(id_, -32601, f"Method not found: {method}")


def run_stdio() -> None:
    """Run the MCP server on stdin/stdout (JSON-RPC over stdio)."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            resp = _make_error(None, -32700, "Parse error")
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
            continue

        resp = _handle_request(req)
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    run_stdio()

"""
ff-kit one-shot JSON bridge — spawn-per-call entry point for host runtimes.

Reads a single JSON request object from stdin, executes the tool, writes a
single JSON response to stdout, and exits.  Used by the DeepSeek Harness
plugin (``integrations/deepseek-harness``), and suitable for any host that
prefers spawn-per-call over a long-lived server.

Request::

    {
      "tool": "ffkit_clip",
      "arguments": {"input_path": "in.mp4", ...},
      "executor": {"ffmpeg_bin": "ffmpeg", "ffprobe_bin": "ffprobe",
                   "timeout": 300, "overwrite": true}
    }

``executor`` is optional; omitted fields fall back to `Executor` defaults.

Response (mirrors :func:`ff_kit.dispatch.dispatch`)::

    {"status": "ok", ...}  |  {"status": "error", "error": "..."}

Exit codes: ``0`` — a JSON response was written (tool-level failures are
reported in-band via ``status``); ``2`` — the request itself was malformed
and nothing was dispatched (details on stderr).

Run standalone::

    echo '{"tool": "ffkit_clip", "arguments": {...}}' | python -m ff_kit.bridge
"""

from __future__ import annotations

import json
import sys
from typing import Any

from ff_kit.dispatch import dispatch
from ff_kit.executor import Executor

_EXECUTOR_KEYS = {"ffmpeg_bin", "ffprobe_bin", "timeout", "overwrite"}

PROTOCOL_ERROR_EXIT = 2


class BridgeProtocolError(ValueError):
    """Raised when the request is not a well-formed bridge request."""


def run_request(req: Any) -> dict[str, Any]:
    """
    Execute a parsed bridge request and return the response dict.

    Raises
    ------
    BridgeProtocolError
        If the request is structurally invalid (not dispatched).
    """
    if not isinstance(req, dict):
        raise BridgeProtocolError("Request must be a JSON object.")

    tool = req.get("tool")
    if not isinstance(tool, str) or not tool:
        raise BridgeProtocolError("Request field 'tool' must be a non-empty string.")

    arguments = req.get("arguments", {})
    if not isinstance(arguments, dict):
        raise BridgeProtocolError("Request field 'arguments' must be an object.")

    executor_cfg = req.get("executor")
    executor = None
    if executor_cfg is not None:
        if not isinstance(executor_cfg, dict):
            raise BridgeProtocolError("Request field 'executor' must be an object.")
        kwargs = {k: v for k, v in executor_cfg.items() if k in _EXECUTOR_KEYS}
        try:
            executor = Executor(**kwargs)
        except Exception as exc:
            return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}

    return dispatch(tool, arguments, executor=executor)


def main() -> int:
    """Read one request from stdin, write one response to stdout."""
    if "--version" in sys.argv[1:]:
        from ff_kit import __version__

        sys.stdout.write(json.dumps({"name": "ff-toolkit", "version": __version__}) + "\n")
        return 0

    raw = sys.stdin.read()
    try:
        req = json.loads(raw)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"ff-kit bridge: invalid JSON on stdin: {exc}\n")
        return PROTOCOL_ERROR_EXIT

    try:
        resp = run_request(req)
    except BridgeProtocolError as exc:
        sys.stderr.write(f"ff-kit bridge: {exc}\n")
        return PROTOCOL_ERROR_EXIT

    sys.stdout.write(json.dumps(resp) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

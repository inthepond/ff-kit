"""
Tool-call dispatcher — routes LLM tool calls to ff-kit functions.

Usage::

    from ff_kit.dispatch import dispatch

    # Given a tool call from any LLM provider:
    result = dispatch("ffkit_clip", {
        "input_path": "in.mp4",
        "output_path": "out.mp4",
        "start": "00:01:00",
        "duration": "30",
    })
"""

from __future__ import annotations

from typing import Any

from ff_kit.core import clip, merge, extract_audio, add_subtitles, transcode
from ff_kit.executor import Executor, FFmpegResult

# Map of tool name → (function, set of valid kwargs)
_REGISTRY: dict[str, tuple[Any, set[str]]] = {
    "ffkit_clip": (clip, {"input_path", "output_path", "start", "end", "duration"}),
    "ffkit_merge": (merge, {"input_paths", "output_path", "method"}),
    "ffkit_extract_audio": (
        extract_audio,
        {"input_path", "output_path", "codec", "sample_rate", "channels"},
    ),
    "ffkit_add_subtitles": (
        add_subtitles,
        {"input_path", "output_path", "subtitle_path", "mode"},
    ),
    "ffkit_transcode": (
        transcode,
        {
            "input_path", "output_path", "video_codec", "audio_codec",
            "resolution", "bitrate", "fps", "preset", "crf", "extra_args",
        },
    ),
}


def dispatch(
    tool_name: str,
    arguments: dict[str, Any],
    *,
    executor: Executor | None = None,
) -> dict[str, Any]:
    """
    Execute an ff-kit tool by name and return a JSON-serialisable result.

    Parameters
    ----------
    tool_name : str
        One of the registered tool names (e.g. ``"ffkit_clip"``).
    arguments : dict
        The arguments dict as parsed from the LLM's tool call.
    executor : Executor, optional
        Shared executor instance (reuses ffmpeg path / timeout settings).

    Returns
    -------
    dict
        ``{"status": "ok", ...result_fields}`` on success, or
        ``{"status": "error", "error": "..."}`` on failure.
    """
    if tool_name not in _REGISTRY:
        return {
            "status": "error",
            "error": f"Unknown tool: {tool_name!r}. Available: {sorted(_REGISTRY)}",
        }

    fn, valid_keys = _REGISTRY[tool_name]

    # Filter out any unexpected keys the LLM might hallucinate
    kwargs = {k: v for k, v in arguments.items() if k in valid_keys}

    if executor is not None:
        kwargs["executor"] = executor

    try:
        result: FFmpegResult = fn(**kwargs)
        return {"status": "ok", **result.to_dict()}
    except Exception as exc:
        return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}


def list_tools() -> list[str]:
    """Return the names of all registered tools."""
    return sorted(_REGISTRY)

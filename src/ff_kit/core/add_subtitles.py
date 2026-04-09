"""Burn or embed subtitles into a video file."""

from __future__ import annotations

from pathlib import Path

from ff_kit.executor import Executor, FFmpegResult


def add_subtitles(
    input_path: str,
    output_path: str,
    subtitle_path: str,
    *,
    mode: str = "burn",
    executor: Executor | None = None,
) -> FFmpegResult:
    """
    Add subtitles to a video.

    Parameters
    ----------
    input_path : str
        Source video file.
    output_path : str
        Output video file.
    subtitle_path : str
        Path to subtitle file (``.srt``, ``.ass``, ``.vtt``).
    mode : str
        ``"burn"`` (default) — hard-code subtitles into the video pixels
        (uses the ``subtitles`` filter; universal playback).
        ``"embed"`` — add as a soft subtitle stream (requires
        a container that supports subtitle tracks, e.g. MKV/MP4).
    executor : Executor, optional
        Custom executor.

    Returns
    -------
    FFmpegResult
    """
    if mode not in ("burn", "embed"):
        raise ValueError(f"mode must be 'burn' or 'embed', got {mode!r}")

    exe = executor or Executor()

    if mode == "burn":
        # Escape path for the subtitles filter (colons, backslashes)
        safe_sub = str(Path(subtitle_path).resolve()).replace("\\", "/").replace(":", "\\:")
        args = [
            "-i", input_path,
            "-vf", f"subtitles={safe_sub}",
            "-c:a", "copy",
            output_path,
        ]
    else:  # embed
        args = [
            "-i", input_path,
            "-i", subtitle_path,
            "-c", "copy",
            "-c:s", "mov_text",
            output_path,
        ]

    return exe.run(args, output_path=output_path)

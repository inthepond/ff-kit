"""Merge (concatenate) multiple media files."""

from __future__ import annotations

import tempfile
from pathlib import Path

from ff_kit.executor import Executor, FFmpegResult


def merge(
    input_paths: list[str],
    output_path: str,
    *,
    method: str = "concat_demuxer",
    executor: Executor | None = None,
) -> FFmpegResult:
    """
    Concatenate multiple media files into one.

    Parameters
    ----------
    input_paths : list[str]
        Ordered list of files to concatenate.
    output_path : str
        Destination path for the merged file.
    method : str
        ``"concat_demuxer"`` (default, fast, same-codec) or
        ``"concat_filter"`` (re-encodes, works across formats).
    executor : Executor, optional
        Custom executor.

    Returns
    -------
    FFmpegResult
    """
    if len(input_paths) < 2:
        raise ValueError("Need at least 2 input files to merge.")

    exe = executor or Executor()

    if method == "concat_demuxer":
        return _merge_demuxer(exe, input_paths, output_path)
    elif method == "concat_filter":
        return _merge_filter(exe, input_paths, output_path)
    else:
        raise ValueError(f"Unknown merge method: {method!r}")


def _merge_demuxer(
    exe: Executor, input_paths: list[str], output_path: str
) -> FFmpegResult:
    """Fast concat via the concat demuxer (same codec required)."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False
    ) as f:
        for p in input_paths:
            f.write(f"file '{Path(p).resolve()}'\n")
        list_file = f.name

    args = [
        "-f", "concat",
        "-safe", "0",
        "-i", list_file,
        "-c", "copy",
        output_path,
    ]
    return exe.run(args, output_path=output_path)


def _merge_filter(
    exe: Executor, input_paths: list[str], output_path: str
) -> FFmpegResult:
    """Re-encoding concat via the concat filter (cross-format)."""
    args: list[str] = []
    for p in input_paths:
        args.extend(["-i", p])

    n = len(input_paths)
    filter_str = "".join(f"[{i}:v][{i}:a]" for i in range(n))
    filter_str += f"concat=n={n}:v=1:a=1[outv][outa]"

    args.extend([
        "-filter_complex", filter_str,
        "-map", "[outv]",
        "-map", "[outa]",
        output_path,
    ])
    return exe.run(args, output_path=output_path)

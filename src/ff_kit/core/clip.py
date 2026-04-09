"""Clip (trim) a segment from a media file."""

from __future__ import annotations

from ff_kit.executor import Executor, FFmpegResult


def clip(
    input_path: str,
    output_path: str,
    start: str,
    end: str | None = None,
    duration: str | None = None,
    *,
    executor: Executor | None = None,
) -> FFmpegResult:
    """
    Extract a segment from *input_path* and write it to *output_path*.

    Specify the segment with *start* + either *end* or *duration*.
    Time format: ``HH:MM:SS.ms`` or seconds (e.g. ``"90"``).

    Parameters
    ----------
    input_path : str
        Path to the source media file.
    output_path : str
        Path for the trimmed output file.
    start : str
        Start timestamp (e.g. ``"00:01:30"`` or ``"90"``).
    end : str, optional
        End timestamp.  Mutually exclusive with *duration*.
    duration : str, optional
        Duration of the clip.  Mutually exclusive with *end*.
    executor : Executor, optional
        Custom executor; a default one is created if omitted.

    Returns
    -------
    FFmpegResult
    """
    if not end and not duration:
        raise ValueError("Either 'end' or 'duration' must be provided.")
    if end and duration:
        raise ValueError("Provide either 'end' or 'duration', not both.")

    exe = executor or Executor()
    args = ["-i", input_path, "-ss", start]

    if end:
        args.extend(["-to", end])
    else:
        args.extend(["-t", duration])  # type: ignore[arg-type]

    args.extend(["-c", "copy", output_path])
    return exe.run(args, output_path=output_path)

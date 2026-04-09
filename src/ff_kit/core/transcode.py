"""Transcode a media file to a different format / codec / resolution."""

from __future__ import annotations

from ff_kit.executor import Executor, FFmpegResult


def transcode(
    input_path: str,
    output_path: str,
    *,
    video_codec: str | None = None,
    audio_codec: str | None = None,
    resolution: str | None = None,
    bitrate: str | None = None,
    fps: int | None = None,
    preset: str | None = None,
    crf: int | None = None,
    extra_args: list[str] | None = None,
    executor: Executor | None = None,
) -> FFmpegResult:
    """
    Transcode a media file with full control over codecs and quality.

    Parameters
    ----------
    input_path : str
        Source file.
    output_path : str
        Destination file — the container format is inferred from the
        extension (e.g. ``.mp4``, ``.webm``, ``.mkv``).
    video_codec : str, optional
        Video codec (e.g. ``"libx264"``, ``"libx265"``, ``"libvpx-vp9"``).
    audio_codec : str, optional
        Audio codec (e.g. ``"aac"``, ``"libopus"``).
    resolution : str, optional
        Output resolution as ``"WxH"`` (e.g. ``"1280x720"``).
    bitrate : str, optional
        Target bitrate (e.g. ``"2M"``, ``"500k"``).
    fps : int, optional
        Output frame rate.
    preset : str, optional
        Encoder preset (e.g. ``"fast"``, ``"medium"``, ``"slow"``).
    crf : int, optional
        Constant Rate Factor for quality-based encoding (lower = better).
    extra_args : list[str], optional
        Any additional ffmpeg arguments.
    executor : Executor, optional
        Custom executor.

    Returns
    -------
    FFmpegResult
    """
    exe = executor or Executor()
    args = ["-i", input_path]

    if video_codec:
        args.extend(["-c:v", video_codec])
    if audio_codec:
        args.extend(["-c:a", audio_codec])
    if resolution:
        args.extend(["-s", resolution])
    if bitrate:
        args.extend(["-b:v", bitrate])
    if fps:
        args.extend(["-r", str(fps)])
    if preset:
        args.extend(["-preset", preset])
    if crf is not None:
        args.extend(["-crf", str(crf)])
    if extra_args:
        args.extend(extra_args)

    args.append(output_path)
    return exe.run(args, output_path=output_path)

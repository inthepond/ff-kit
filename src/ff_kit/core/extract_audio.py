"""Extract audio track from a media file."""

from __future__ import annotations

from ff_kit.executor import Executor, FFmpegResult


def extract_audio(
    input_path: str,
    output_path: str,
    *,
    codec: str = "copy",
    sample_rate: int | None = None,
    channels: int | None = None,
    executor: Executor | None = None,
) -> FFmpegResult:
    """
    Extract the audio stream from a video/audio file.

    Parameters
    ----------
    input_path : str
        Source media file.
    output_path : str
        Destination audio file (e.g. ``"out.mp3"``, ``"out.wav"``).
    codec : str
        Audio codec.  ``"copy"`` (default) keeps the original codec;
        use ``"libmp3lame"``, ``"aac"``, ``"pcm_s16le"``, etc. to re-encode.
    sample_rate : int, optional
        Output sample rate in Hz (e.g. ``16000`` for ASR pipelines).
    channels : int, optional
        Number of audio channels (``1`` = mono, ``2`` = stereo).
    executor : Executor, optional
        Custom executor.

    Returns
    -------
    FFmpegResult
    """
    exe = executor or Executor()
    args = ["-i", input_path, "-vn"]

    if codec != "copy":
        args.extend(["-acodec", codec])
    else:
        args.extend(["-acodec", "copy"])

    if sample_rate is not None:
        args.extend(["-ar", str(sample_rate)])
    if channels is not None:
        args.extend(["-ac", str(channels)])

    args.append(output_path)
    return exe.run(args, output_path=output_path)

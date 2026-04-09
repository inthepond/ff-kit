"""
ff-kit — FFmpeg operations as LLM-callable tools.

Quick start::

    from ff_kit import clip, merge, extract_audio, add_subtitles, transcode

    result = clip("in.mp4", "out.mp4", start="00:01:00", duration="30")
"""

from __future__ import annotations

from ff_kit.core.clip import clip
from ff_kit.core.merge import merge
from ff_kit.core.extract_audio import extract_audio
from ff_kit.core.add_subtitles import add_subtitles
from ff_kit.core.transcode import transcode
from ff_kit.executor import Executor, FFmpegResult

__version__ = "0.1.0"

__all__ = [
    "clip",
    "merge",
    "extract_audio",
    "add_subtitles",
    "transcode",
    "Executor",
    "FFmpegResult",
]

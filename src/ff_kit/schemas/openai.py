"""
OpenAI function-calling / tool-use schema definitions.

Usage with the OpenAI SDK::

    from openai import OpenAI
    from ff_kit.schemas.openai import openai_tools

    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=openai_tools(),
    )
"""

from __future__ import annotations

from typing import Any


def openai_tools() -> list[dict[str, Any]]:
    """Return all ff-kit operations as OpenAI-compatible tool definitions."""
    return [
        _clip_tool(),
        _merge_tool(),
        _extract_audio_tool(),
        _add_subtitles_tool(),
        _transcode_tool(),
    ]


def _clip_tool() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "ffkit_clip",
            "description": (
                "Trim a segment from a media file. Specify start + end or "
                "start + duration. Time format: HH:MM:SS.ms or seconds."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "input_path": {
                        "type": "string",
                        "description": "Path to the source media file.",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Path for the trimmed output file.",
                    },
                    "start": {
                        "type": "string",
                        "description": "Start timestamp (e.g. '00:01:30' or '90').",
                    },
                    "end": {
                        "type": "string",
                        "description": "End timestamp. Mutually exclusive with duration.",
                    },
                    "duration": {
                        "type": "string",
                        "description": "Duration of the clip. Mutually exclusive with end.",
                    },
                },
                "required": ["input_path", "output_path", "start"],
                "additionalProperties": False,
            },
        },
    }


def _merge_tool() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "ffkit_merge",
            "description": (
                "Concatenate multiple media files into one. "
                "Use concat_demuxer (fast, same codec) or concat_filter (re-encodes, cross-format)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "input_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 2,
                        "description": "Ordered list of file paths to concatenate.",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Destination path for the merged file.",
                    },
                    "method": {
                        "type": "string",
                        "enum": ["concat_demuxer", "concat_filter"],
                        "description": "Merge strategy. Default: concat_demuxer.",
                    },
                },
                "required": ["input_paths", "output_path"],
                "additionalProperties": False,
            },
        },
    }


def _extract_audio_tool() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "ffkit_extract_audio",
            "description": (
                "Extract the audio stream from a video/audio file. "
                "Can re-encode to a different codec or keep original."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "input_path": {
                        "type": "string",
                        "description": "Source media file.",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Destination audio file (e.g. 'out.mp3', 'out.wav').",
                    },
                    "codec": {
                        "type": "string",
                        "description": "Audio codec. 'copy' keeps original; or 'libmp3lame', 'aac', 'pcm_s16le'.",
                    },
                    "sample_rate": {
                        "type": "integer",
                        "description": "Output sample rate in Hz (e.g. 16000 for ASR).",
                    },
                    "channels": {
                        "type": "integer",
                        "description": "Number of audio channels (1=mono, 2=stereo).",
                    },
                },
                "required": ["input_path", "output_path"],
                "additionalProperties": False,
            },
        },
    }


def _add_subtitles_tool() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "ffkit_add_subtitles",
            "description": (
                "Add subtitles to a video. 'burn' hard-codes into pixels; "
                "'embed' adds as a soft subtitle track."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "input_path": {
                        "type": "string",
                        "description": "Source video file.",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Output video file.",
                    },
                    "subtitle_path": {
                        "type": "string",
                        "description": "Path to subtitle file (.srt, .ass, .vtt).",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["burn", "embed"],
                        "description": "Subtitle mode. Default: burn.",
                    },
                },
                "required": ["input_path", "output_path", "subtitle_path"],
                "additionalProperties": False,
            },
        },
    }


def _transcode_tool() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "ffkit_transcode",
            "description": (
                "Transcode a media file to a different format, codec, or resolution. "
                "The output container is inferred from the file extension."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "input_path": {
                        "type": "string",
                        "description": "Source file path.",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Destination file path (.mp4, .webm, .mkv, etc.).",
                    },
                    "video_codec": {
                        "type": "string",
                        "description": "Video codec (e.g. 'libx264', 'libx265', 'libvpx-vp9').",
                    },
                    "audio_codec": {
                        "type": "string",
                        "description": "Audio codec (e.g. 'aac', 'libopus').",
                    },
                    "resolution": {
                        "type": "string",
                        "description": "Output resolution as WxH (e.g. '1280x720').",
                    },
                    "bitrate": {
                        "type": "string",
                        "description": "Target bitrate (e.g. '2M', '500k').",
                    },
                    "fps": {
                        "type": "integer",
                        "description": "Output frame rate.",
                    },
                    "preset": {
                        "type": "string",
                        "description": "Encoder preset (e.g. 'fast', 'medium', 'slow').",
                    },
                    "crf": {
                        "type": "integer",
                        "description": "Constant Rate Factor (lower = higher quality).",
                    },
                },
                "required": ["input_path", "output_path"],
                "additionalProperties": False,
            },
        },
    }

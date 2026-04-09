"""
ff-kit CLI — use FFmpeg tools directly from the command line.

Usage::

    ffkit clip input.mp4 output.mp4 --start 00:01:00 --duration 30
    ffkit merge a.mp4 b.mp4 -o merged.mp4
    ffkit extract-audio video.mp4 audio.wav --sample-rate 16000 --channels 1
    ffkit add-subtitles video.mp4 output.mp4 --subtitle subs.srt --mode burn
    ffkit transcode input.mp4 output.webm --video-codec libvpx-vp9 --crf 30
    ffkit probe video.mp4
    ffkit list-tools --format openai
"""

from __future__ import annotations

import argparse
import json
import sys

from ff_kit.executor import Executor


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ffkit",
        description="ff-kit: FFmpeg operations as LLM-callable tools.",
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # ── clip ──────────────────────────────────────────────────────
    p_clip = sub.add_parser("clip", help="Trim a segment from a media file")
    p_clip.add_argument("input", help="Source media file")
    p_clip.add_argument("output", help="Output file")
    p_clip.add_argument("--start", "-s", required=True, help="Start time (HH:MM:SS or seconds)")
    p_clip.add_argument("--end", "-e", help="End time")
    p_clip.add_argument("--duration", "-d", help="Duration")

    # ── merge ─────────────────────────────────────────────────────
    p_merge = sub.add_parser("merge", help="Concatenate multiple files")
    p_merge.add_argument("inputs", nargs="+", help="Files to merge (at least 2)")
    p_merge.add_argument("--output", "-o", required=True, help="Output file")
    p_merge.add_argument("--method", "-m", default="concat_demuxer",
                         choices=["concat_demuxer", "concat_filter"])

    # ── extract-audio ─────────────────────────────────────────────
    p_audio = sub.add_parser("extract-audio", help="Extract audio from a media file")
    p_audio.add_argument("input", help="Source media file")
    p_audio.add_argument("output", help="Output audio file (.mp3, .wav, .aac, etc.)")
    p_audio.add_argument("--codec", "-c", default="copy", help="Audio codec (default: copy)")
    p_audio.add_argument("--sample-rate", "-r", type=int, help="Sample rate in Hz (e.g. 16000)")
    p_audio.add_argument("--channels", type=int, help="Channels (1=mono, 2=stereo)")

    # ── add-subtitles ─────────────────────────────────────────────
    p_subs = sub.add_parser("add-subtitles", help="Add subtitles to a video")
    p_subs.add_argument("input", help="Source video file")
    p_subs.add_argument("output", help="Output video file")
    p_subs.add_argument("--subtitle", required=True, help="Subtitle file (.srt, .ass, .vtt)")
    p_subs.add_argument("--mode", default="burn", choices=["burn", "embed"])

    # ── transcode ─────────────────────────────────────────────────
    p_trans = sub.add_parser("transcode", help="Convert format/codec/resolution")
    p_trans.add_argument("input", help="Source file")
    p_trans.add_argument("output", help="Destination file")
    p_trans.add_argument("--video-codec", help="Video codec (e.g. libx264)")
    p_trans.add_argument("--audio-codec", help="Audio codec (e.g. aac)")
    p_trans.add_argument("--resolution", help="Resolution as WxH (e.g. 1280x720)")
    p_trans.add_argument("--bitrate", help="Target bitrate (e.g. 2M)")
    p_trans.add_argument("--fps", type=int, help="Frame rate")
    p_trans.add_argument("--preset", help="Encoder preset (e.g. fast, medium, slow)")
    p_trans.add_argument("--crf", type=int, help="Constant Rate Factor")

    # ── probe ─────────────────────────────────────────────────────
    p_probe = sub.add_parser("probe", help="Show media file info (ffprobe)")
    p_probe.add_argument("input", help="Media file to inspect")

    # ── list-tools ────────────────────────────────────────────────
    p_list = sub.add_parser("list-tools", help="Print tool schemas for LLM integration")
    p_list.add_argument("--format", "-f", default="openai",
                        choices=["openai", "anthropic"],
                        help="Schema format (default: openai)")

    # ── parse ─────────────────────────────────────────────────────
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    try:
        return _run(args)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _run(args: argparse.Namespace) -> int:
    if args.command == "list-tools":
        if args.format == "openai":
            from ff_kit.schemas.openai import openai_tools
            print(json.dumps(openai_tools(), indent=2))
        else:
            from ff_kit.schemas.anthropic import anthropic_tools
            print(json.dumps(anthropic_tools(), indent=2))
        return 0

    if args.command == "probe":
        exe = Executor()
        info = exe.probe(args.input)
        print(json.dumps(info, indent=2))
        return 0

    # All other commands need the core functions
    from ff_kit.core import clip, merge, extract_audio, add_subtitles, transcode

    if args.command == "clip":
        result = clip(
            args.input, args.output,
            start=args.start, end=args.end, duration=args.duration,
        )

    elif args.command == "merge":
        result = merge(args.inputs, args.output, method=args.method)

    elif args.command == "extract-audio":
        result = extract_audio(
            args.input, args.output,
            codec=args.codec,
            sample_rate=args.sample_rate,
            channels=args.channels,
        )

    elif args.command == "add-subtitles":
        result = add_subtitles(
            args.input, args.output,
            subtitle_path=args.subtitle,
            mode=args.mode,
        )

    elif args.command == "transcode":
        result = transcode(
            args.input, args.output,
            video_codec=args.video_codec,
            audio_codec=args.audio_codec,
            resolution=args.resolution,
            bitrate=args.bitrate,
            fps=args.fps,
            preset=args.preset,
            crf=args.crf,
        )
    else:
        return 1

    print(f"Done: {result.output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
FFmpeg command executor — the single point where shell commands are built and run.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class FFmpegNotFoundError(RuntimeError):
    """Raised when the ffmpeg / ffprobe binary cannot be located."""


class FFmpegExecutionError(RuntimeError):
    """Raised when an ffmpeg command exits with a non-zero code."""

    def __init__(self, cmd: list[str], returncode: int, stderr: str) -> None:
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(
            f"ffmpeg exited with code {returncode}.\n"
            f"Command: {' '.join(cmd)}\n"
            f"Stderr:  {stderr[:2000]}"
        )


@dataclass
class FFmpegResult:
    """Result of an FFmpeg operation."""

    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    output_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": " ".join(self.command),
            "returncode": self.returncode,
            "stdout": self.stdout[:500],
            "stderr": self.stderr[:500],
            "output_path": self.output_path,
        }


@dataclass
class Executor:
    """Thin wrapper around subprocess for running ffmpeg/ffprobe."""

    ffmpeg_bin: str = "ffmpeg"
    ffprobe_bin: str = "ffprobe"
    timeout: int = 300  # seconds
    overwrite: bool = True

    def __post_init__(self) -> None:
        if not shutil.which(self.ffmpeg_bin):
            raise FFmpegNotFoundError(
                f"Could not find '{self.ffmpeg_bin}' on PATH. "
                "Install FFmpeg: https://ffmpeg.org/download.html"
            )

    # ── public API ────────────────────────────────────────────────

    def run(
        self,
        args: list[str],
        output_path: str | None = None,
    ) -> FFmpegResult:
        """Run an ffmpeg command and return the result."""
        cmd = [self.ffmpeg_bin]
        if self.overwrite:
            cmd.append("-y")
        cmd.extend(args)

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )

        result = FFmpegResult(
            command=cmd,
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            output_path=output_path,
        )

        if proc.returncode != 0:
            raise FFmpegExecutionError(cmd, proc.returncode, proc.stderr)

        return result

    def probe(self, input_path: str) -> dict[str, Any]:
        """Run ffprobe and return parsed JSON metadata."""
        cmd = [
            self.ffprobe_bin,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            input_path,
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )
        if proc.returncode != 0:
            raise FFmpegExecutionError(cmd, proc.returncode, proc.stderr)
        return json.loads(proc.stdout)

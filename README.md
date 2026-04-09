# ff-toolkit

FFmpeg operations as LLM-callable tools.

<p align="center">
  <img src="https://raw.githubusercontent.com/inthepond/ff-toolkit/main/docs/demo.svg" alt="ff-toolkit demo" width="720">
</p>

> **Stop hand-writing FFmpeg subprocess calls and JSON tool schemas.**
> `ff-toolkit` gives you 5 production-ready media operations, dual-format LLM schemas (OpenAI + Anthropic), and an MCP server — all in one `pip install`.

## Real-World Use Cases

**"My agent pipeline needs to process uploaded videos"** — Give your agent `openai_tools()` or `anthropic_tools()` and let it decide how to clip, transcode, or extract audio. The `dispatch()` function handles execution.

**"I need to batch-extract 16kHz WAV for ASR"** — One line: `extract_audio("video.mp4", "out.wav", codec="pcm_s16le", sample_rate=16000, channels=1)`

**"I want FFmpeg tools in Claude Desktop / Cursor"** — Add the MCP server config (3 lines of JSON) and Claude can edit your videos directly.

**"I'm tired of writing the same FFmpeg commands"** — Use the CLI: `ffkit clip input.mp4 output.mp4 --start 00:01:00 --duration 30`

## 60-Second Quick Start

```bash
# Install (requires FFmpeg on PATH)
pip install ff-toolkit

# Verify it works — no API keys needed
ffkit probe some_video.mp4

# Or run the full demo with a generated test video
python -m ff_kit.examples.local
```

### Python API

```python
from ff_kit import clip, extract_audio, merge, transcode

# Trim seconds 60-90
clip("raw.mp4", "highlight.mp4", start="00:01:00", duration="30")

# Extract 16kHz mono audio for Whisper/Paraformer
extract_audio("raw.mp4", "speech.wav", codec="pcm_s16le", sample_rate=16000, channels=1)

# Concatenate intro + main + outro
merge(["intro.mp4", "main.mp4", "outro.mp4"], "final.mp4")

# Compress to 720p WebM for web delivery
transcode("raw.mp4", "web.webm", video_codec="libvpx-vp9", resolution="1280x720", crf=30)
```

### CLI

```bash
ffkit clip raw.mp4 highlight.mp4 --start 00:01:00 --duration 30
ffkit extract-audio raw.mp4 speech.wav --codec pcm_s16le --sample-rate 16000 --channels 1
ffkit merge intro.mp4 main.mp4 outro.mp4 -o final.mp4
ffkit transcode raw.mp4 web.webm --video-codec libvpx-vp9 --resolution 1280x720 --crf 30
ffkit probe video.mp4
```

### With OpenAI (3 lines to integrate)

```python
from ff_kit.schemas.openai import openai_tools
from ff_kit.dispatch import dispatch

# 1. Pass tools to the model
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    tools=openai_tools(),       # ← that's it
)

# 2. Execute whatever the model calls
tc = response.choices[0].message.tool_calls[0]
result = dispatch(tc.function.name, json.loads(tc.function.arguments))
```

### With Anthropic (3 lines to integrate)

```python
from ff_kit.schemas.anthropic import anthropic_tools
from ff_kit.dispatch import dispatch

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    tools=anthropic_tools(),    # ← that's it
    messages=messages,
)

for block in response.content:
    if block.type == "tool_use":
        result = dispatch(block.name, block.input)
```

### As an MCP Server (Claude Desktop / Cursor)

Add to your config (`claude_desktop_config.json` or Cursor settings):

```json
{
  "mcpServers": {
    "ff-toolkit": {
      "command": "ffkit-mcp",
      "args": []
    }
  }
}
```

That's it. Claude can now clip, merge, extract audio, add subtitles, and transcode your files.

## Operations

| Tool | What it does | Example |
|------|-------------|---------|
| `ffkit_clip` | Trim a segment by start + end/duration | Cut highlight reel from raw footage |
| `ffkit_merge` | Concatenate multiple files | Join intro + content + outro |
| `ffkit_extract_audio` | Extract audio, optionally re-encode | Get 16kHz WAV for speech recognition |
| `ffkit_add_subtitles` | Burn or embed subtitles (.srt/.ass/.vtt) | Hard-sub a translated SRT into video |
| `ffkit_transcode` | Convert format, codec, resolution, bitrate | Compress 4K MP4 to 720p WebM for web |

## How It Works

```
Your Agent                    ff-toolkit                         FFmpeg
    │                           │                              │
    ├─ openai_tools() ──────────┤                              │
    │  or anthropic_tools()     │                              │
    │                           │                              │
    ├─ LLM returns tool call ──►│                              │
    │                           │                              │
    ├─ dispatch(name, args) ───►├─ validates & builds cmd ────►│
    │                           │                              │
    │◄── FFmpegResult ─────────┤◄── subprocess result ────────┤
    │                           │                              │
```

## Project Structure

```
ff-toolkit/
├── src/ff_kit/
│   ├── __init__.py          # Public API: clip, merge, extract_audio, ...
│   ├── cli.py               # CLI entry point (ffkit command)
│   ├── executor.py          # FFmpeg subprocess runner + probe
│   ├── dispatch.py          # Tool name → function router
│   ├── core/                # One module per operation
│   │   ├── clip.py
│   │   ├── merge.py
│   │   ├── extract_audio.py
│   │   ├── add_subtitles.py
│   │   └── transcode.py
│   ├── schemas/             # LLM tool definitions
│   │   ├── openai.py        # OpenAI function-calling format
│   │   └── anthropic.py     # Anthropic tool-use format
│   └── mcp/                 # MCP server (stdio JSON-RPC)
│       └── server.py
├── examples/
│   ├── local_example.py     # ← Run this first! No API key needed
│   ├── openai_example.py
│   ├── anthropic_example.py
│   └── agent_loop_example.py
└── tests/                   # 30 tests, all mocked (no FFmpeg needed)
```

## Development

```bash
git clone https://github.com/inthepond/ff-toolkit.git
cd ff-toolkit
pip install -e ".[dev]"
pytest -v                    # 30 tests, runs in <1s
```

## FAQ

**Q: Do I need FFmpeg installed?**
Yes, for actual media operations. Tests are fully mocked and don't need FFmpeg. Install it from [ffmpeg.org/download](https://ffmpeg.org/download.html) or `brew install ffmpeg` / `apt install ffmpeg`.

**Q: Can I add custom operations?**
Yes — add a function in `core/`, register it in `dispatch.py`'s `_REGISTRY`, and add schema entries in `schemas/openai.py` and `schemas/anthropic.py`. See any existing operation as a template.

**Q: Why not just use LangChain / CrewAI tools?**
Those frameworks are great, but they're heavy dependencies. ff-toolkit is zero-dependency (beyond Python stdlib) and works with any LLM provider. You can use it inside LangChain if you want, or standalone.

**Q: What about streaming / progress callbacks?**
Not in v0.1. FFmpeg progress parsing is planned for v0.2.

## License

MIT

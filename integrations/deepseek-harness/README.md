# dsh-ffkit — ff-toolkit as a DeepSeek Harness plugin

A [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) (dsh) plugin that registers [ff-toolkit](https://github.com/inthepond/ff-toolkit)'s five FFmpeg operations as native harness tools:

`ffkit_clip` · `ffkit_merge` · `ffkit_extract_audio` · `ffkit_add_subtitles` · `ffkit_transcode`

Each tool call spawns the one-shot `ff_kit.bridge` Python entry point (JSON request on stdin, JSON response on stdout). FFmpeg failures come back as in-band `status: "error"` values the model can react to; only a broken bridge (missing Python or ff-toolkit) throws.

## Requirements

- DeepSeek Harness (`@deepseek-ai/dsh`), currently tracked against `0.1.0-rc.6` — the harness is in developer preview and breaks compatibility between RCs
- Python 3.10+ with `ff-toolkit` installed (`pip install ff-toolkit`)
- FFmpeg on `PATH` (or set `ffmpegBin`)

## Install

```sh
dsh plugin --profile <name> add dsh-ffkit
```

The package declares a `dsh.bundle` manifest, so the install auto-activates its patch layer; the five tools are available on the next launch. Verify with:

```sh
dsh --profile <name> --dump-config   # look for the "ffkit" row
```

## Configuration

Override the inserted row in your profile's `cordis.patch.yml`:

```yaml
- id: ffkit
  config:
    # Argv that starts the bridge; the default requires `python3` with
    # ff-toolkit importable. Point it at a venv or pinned interpreter as
    # needed, or at the `ffkit-bridge` console script a pip/pipx install puts
    # on PATH: bridgeCommand: ['ffkit-bridge']
    bridgeCommand: ['python3', '-m', 'ff_kit.bridge']
    cwd: ''                    # working directory for the bridge (empty = inherit)
    env: {}                    # extra environment variables for the bridge
    ffmpegBin: ''              # FFmpeg binary name/path ('' = ffmpeg on PATH)
    ffprobeBin: ''             # FFprobe binary name/path
    ffmpegTimeoutSeconds: 300  # per-operation FFmpeg timeout (bridge default)
    overwrite: true            # whether FFmpeg overwrites existing outputs
    timeoutMs: 600000          # cooperative tool-call timeout budget
```

## Canonical output

Every tool resolves to the bridge response, so Code Mode scripts can branch on it:

```js
const result = await tools.ffkit_transcode({ input_path: 'raw.mp4', output_path: 'web.webm' })
if (result.status === 'ok') console.log(result.output_path)
```

Fields on success: `command`, `returncode`, `stdout`, `stderr` (both truncated to 500 chars by the bridge), `output_path`. On failure: `error`.

## Sandboxing note

The bridge and FFmpeg run as ordinary child processes of the harness, outside the harness's opt-in file sandbox seam. FFmpeg writes wherever the model points it. Review tool calls accordingly, or gate them with a `tools/pre-execute` policy plugin.

## Alternative: MCP

If you prefer no Node package at all, ff-toolkit also ships an MCP stdio server (`ffkit-mcp`), and the harness ships `@deepseek-ai/dsh-mcp-client`:

```yaml
- insert:
    - id: mcp-ffkit
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        serverName: ffkit
        transport: stdio
        command: ffkit-mcp
        args: []
```

Trade-offs vs. this plugin: tool names become `mcp__ffkit__*`, results flatten to text (no canonical value for Code Mode), and there are no presentation cards.

## Development

```sh
npm install
npm test        # builds, then runs the node:test suite against a stub bridge
```

The test suite is hermetic (a Node stub stands in for the Python bridge). For a real round-trip, see `tests/` and the repository root's Python test suite for `ff_kit.bridge`.

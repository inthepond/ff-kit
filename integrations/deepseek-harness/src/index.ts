/**
 * DeepSeek Harness plugin exposing ff-toolkit's FFmpeg operations as
 * model-facing tools. Each call spawns the one-shot `ff_kit.bridge` Python
 * entry point (JSON request on stdin, JSON response on stdout); tool-level
 * FFmpeg failures are reported in-band via the canonical `status` field,
 * while a broken bridge (missing Python, missing ff-toolkit) throws.
 * @module dsh-ffkit
 */

import { spawn } from 'node:child_process'
import type { Context } from '@deepseek-ai/cordis'
import z from '@deepseek-ai/schemastery'
import {
  defineTool,
  type FileLocation,
  type InferArgs,
  type InferValue,
  type ParameterSchemaSpec,
  type ToolDefinition,
} from '@deepseek-ai/dsh-tools'

/** Cordis plugin name used by loader diagnostics. */
export const name = 'ffkit'

/** Services required by the plugin. */
export const inject = ['tools']

/** Plugin configuration. */
export interface Config {
  /** Argv that starts the one-shot bridge; the JSON request is written to its stdin. */
  bridgeCommand: string[]
  /** Working directory for the bridge process; relative media paths resolve against it. Empty = inherit. */
  cwd?: string
  /** Extra environment variables merged over the harness process environment. */
  env: Record<string, string>
  /** FFmpeg binary name or path forwarded to the bridge. Empty = the bridge's default (`ffmpeg` on PATH). */
  ffmpegBin?: string
  /** FFprobe binary name or path forwarded to the bridge. Empty = the bridge's default. */
  ffprobeBin?: string
  /** Per-operation FFmpeg timeout in seconds, enforced inside the bridge. Unset = the bridge's default (300). */
  ffmpegTimeoutSeconds?: number
  /** Whether FFmpeg overwrites existing output files. Unset = the bridge's default (true). */
  overwrite?: boolean
  /** Cooperative tool-call timeout budget in milliseconds, enforced by the harness timeout policy. */
  timeoutMs: number
}

export const Config: z<Config> = z.object({
  bridgeCommand: z
    .array(String)
    .default(['python3', '-m', 'ff_kit.bridge'])
    .description('Argv that starts the ff-kit bridge (requires Python with ff-toolkit installed).'),
  cwd: z.string().description('Working directory for the bridge process.'),
  env: z.dict(String).default({}).description('Extra environment variables for the bridge process.'),
  ffmpegBin: z.string().description('FFmpeg binary name or path.'),
  ffprobeBin: z.string().description('FFprobe binary name or path.'),
  ffmpegTimeoutSeconds: z.number().description('Per-operation FFmpeg timeout in seconds.'),
  overwrite: z.boolean().description('Whether FFmpeg overwrites existing output files.'),
  timeoutMs: z.number().default(600_000).description('Cooperative tool-call timeout budget in milliseconds.'),
})

/**
 * Canonical output of every ffkit tool: the bridge response as produced by
 * `ff_kit.dispatch.dispatch` — `status: "ok"` plus the FFmpeg result fields,
 * or `status: "error"` plus a message. FFmpeg failures are domain outcomes,
 * not throws, so agents and Code Mode scripts can branch on `status`.
 */
const RESULT_SCHEMA = {
  type: 'object',
  additionalProperties: true,
  properties: {
    status: {
      type: 'string',
      enum: ['ok', 'error'],
      required: true,
      description: 'Whether the FFmpeg operation succeeded.',
    },
    command: { type: 'string', description: 'The FFmpeg command line that ran.' },
    returncode: { type: 'integer', description: 'FFmpeg process exit code.' },
    stdout: { type: 'string', description: 'Captured stdout (truncated).' },
    stderr: { type: 'string', description: 'Captured stderr (truncated).' },
    output_path: {
      oneOf: [{ type: 'string' }, { type: 'null' }],
      description: 'Path of the produced file, when the operation writes one.',
    },
    error: { type: 'string', description: 'Failure message when status is "error".' },
  },
} as const

/** Bridge response value, as declared by {@link RESULT_SCHEMA}. */
export type BridgeResult = InferValue<typeof RESULT_SCHEMA>

/** Model-facing rendering of one bridge response. */
function renderResult(value: BridgeResult): { type: 'text'; text: string }[] {
  if (value.status === 'ok') {
    const lines = ['FFmpeg operation succeeded.']
    if (typeof value.output_path === 'string') lines.push(`Output file: ${value.output_path}`)
    if (typeof value.command === 'string') lines.push(`Command: ${value.command}`)
    return [{ type: 'text', text: lines.join('\n') }]
  }
  const message = typeof value.error === 'string' ? value.error : 'unknown error'
  return [{ type: 'text', text: `FFmpeg operation failed: ${message}` }]
}

/** Executor overrides forwarded in the bridge request, or undefined when all defaults apply. */
function executorConfig(config: Config): Record<string, string | number | boolean> | undefined {
  const executor: Record<string, string | number | boolean> = {}
  if (config.ffmpegBin) executor['ffmpeg_bin'] = config.ffmpegBin
  if (config.ffprobeBin) executor['ffprobe_bin'] = config.ffprobeBin
  if (config.ffmpegTimeoutSeconds !== undefined) executor['timeout'] = config.ffmpegTimeoutSeconds
  if (config.overwrite !== undefined) executor['overwrite'] = config.overwrite
  return Object.keys(executor).length > 0 ? executor : undefined
}

/**
 * Run one tool call through the bridge process.
 * @param config - plugin configuration.
 * @param tool - ff-kit tool name (e.g. `ffkit_clip`).
 * @param args - validated tool arguments, forwarded verbatim.
 * @param signal - cooperative cancellation; kills the bridge process.
 * @returns The bridge response.
 */
export async function runBridge(
  config: Config,
  tool: string,
  args: unknown,
  signal: AbortSignal,
): Promise<BridgeResult> {
  signal.throwIfAborted()
  const [command, ...baseArgs] = config.bridgeCommand
  if (!command) throw new Error('dsh-ffkit: bridgeCommand must not be empty')

  const executor = executorConfig(config)
  const request = JSON.stringify({ tool, arguments: args, ...(executor ? { executor } : {}) })

  const child = spawn(command, baseArgs, {
    cwd: config.cwd || undefined,
    env: { ...process.env, ...config.env },
    stdio: ['pipe', 'pipe', 'pipe'],
    signal,
  })

  const stdoutChunks: Buffer[] = []
  const stderrChunks: Buffer[] = []
  child.stdout.on('data', (chunk: Buffer) => stdoutChunks.push(chunk))
  child.stderr.on('data', (chunk: Buffer) => stderrChunks.push(chunk))
  child.stdin.on('error', () => {}) /* EPIPE when the process never started; surfaced via 'error'/'close' */
  child.stdin.end(request)

  const exitCode = await new Promise<number | null>((resolve, reject) => {
    child.on('error', (err: NodeJS.ErrnoException) => {
      if (err.name === 'AbortError' || signal.aborted) {
        reject(err)
        return
      }
      reject(
        new Error(
          `dsh-ffkit: failed to start the ff-kit bridge (${config.bridgeCommand.join(' ')}): ${err.message}. ` +
            'Requires Python 3.10+ with the ff-toolkit package installed (pip install ff-toolkit).',
        ),
      )
    })
    child.on('close', code => resolve(code))
  })
  signal.throwIfAborted()

  const stderrText = Buffer.concat(stderrChunks).toString('utf8')
  if (exitCode !== 0) {
    throw new Error(`dsh-ffkit: bridge exited with code ${exitCode}: ${stderrText.trim()}`)
  }

  const stdoutText = Buffer.concat(stdoutChunks).toString('utf8').trim()
  let parsed: unknown
  try {
    parsed = JSON.parse(stdoutText)
  } catch {
    throw new Error(`dsh-ffkit: bridge returned invalid JSON: ${stdoutText.slice(0, 500)}`)
  }
  if (
    typeof parsed !== 'object' ||
    parsed === null ||
    !('status' in parsed) ||
    ((parsed as { status: unknown }).status !== 'ok' && (parsed as { status: unknown }).status !== 'error')
  ) {
    throw new Error(`dsh-ffkit: bridge response has no valid status field: ${stdoutText.slice(0, 500)}`)
  }
  return parsed as BridgeResult
}

/** Per-tool schema and presentation, shared plumbing supplied by {@link ffkitTool}. */
interface FfkitToolSpec<S extends ParameterSchemaSpec> {
  name: string
  description: string
  parameters: S
  /** Pending-card title for one call. */
  title(args: InferArgs<S>): string
  /** Files the call reads and writes, for editor follow-along. */
  locations(args: InferArgs<S>): FileLocation[]
}

/** Define one ffkit tool that executes through the bridge. */
function ffkitTool<const S extends ParameterSchemaSpec>(config: Config, spec: FfkitToolSpec<S>): ToolDefinition {
  return defineTool({
    name: spec.name,
    description: spec.description,
    parameters: spec.parameters,
    timeoutMs: config.timeoutMs,
    output: {
      schema: RESULT_SCHEMA,
      render: (_args, value) => renderResult(value),
    },
    execute(args, exec) {
      return runBridge(config, spec.name, args, exec.signal)
    },
    presentCall: args => ({
      card: 'generic',
      kind: 'execute',
      title: spec.title(args),
      locations: spec.locations(args),
    }),
  })
}

/**
 * Build the five ffkit tool definitions for one plugin configuration.
 * Schemas mirror `ff_kit.schemas` in the ff-toolkit Python package.
 * @param config - plugin configuration.
 * @returns Registry-ready definitions.
 */
export function ffkitToolDefinitions(config: Config): ToolDefinition[] {
  return [
    ffkitTool(config, {
      name: 'ffkit_clip',
      description:
        'Trim a segment from a media file. Specify start + end or start + duration. ' +
        'Time format: HH:MM:SS.ms or seconds.',
      parameters: {
        input_path: { type: 'string', required: true, description: 'Path to the source media file.' },
        output_path: { type: 'string', required: true, description: 'Path for the trimmed output file.' },
        start: { type: 'string', required: true, description: "Start timestamp (e.g. '00:01:30' or '90')." },
        end: { type: 'string', description: 'End timestamp. Mutually exclusive with duration.' },
        duration: { type: 'string', description: 'Duration of the clip. Mutually exclusive with end.' },
      },
      title: args => `Clip ${args.input_path} → ${args.output_path}`,
      locations: args => [{ path: args.input_path }, { path: args.output_path }],
    }),
    ffkitTool(config, {
      name: 'ffkit_merge',
      description:
        'Concatenate multiple media files into one. ' +
        'Use concat_demuxer (fast, same codec) or concat_filter (re-encodes, cross-format).',
      parameters: {
        input_paths: {
          type: 'array',
          items: { type: 'string' },
          required: true,
          description: 'Ordered list of file paths to concatenate.',
        },
        output_path: { type: 'string', required: true, description: 'Destination path for the merged file.' },
        method: {
          type: 'string',
          enum: ['concat_demuxer', 'concat_filter'],
          description: 'Merge strategy. Default: concat_demuxer.',
        },
      },
      title: args => `Merge ${args.input_paths.length} files → ${args.output_path}`,
      locations: args => [...args.input_paths.map(path => ({ path })), { path: args.output_path }],
    }),
    ffkitTool(config, {
      name: 'ffkit_extract_audio',
      description:
        'Extract the audio stream from a video/audio file. Can re-encode to a different codec or keep original.',
      parameters: {
        input_path: { type: 'string', required: true, description: 'Source media file.' },
        output_path: {
          type: 'string',
          required: true,
          description: "Destination audio file (e.g. 'out.mp3', 'out.wav').",
        },
        codec: {
          type: 'string',
          description: "Audio codec. 'copy' keeps original; or 'libmp3lame', 'aac', 'pcm_s16le'.",
        },
        sample_rate: { type: 'integer', description: 'Output sample rate in Hz (e.g. 16000 for ASR).' },
        channels: { type: 'integer', description: 'Number of audio channels (1=mono, 2=stereo).' },
      },
      title: args => `Extract audio ${args.input_path} → ${args.output_path}`,
      locations: args => [{ path: args.input_path }, { path: args.output_path }],
    }),
    ffkitTool(config, {
      name: 'ffkit_add_subtitles',
      description:
        "Add subtitles to a video. 'burn' hard-codes into pixels; 'embed' adds as a soft subtitle track.",
      parameters: {
        input_path: { type: 'string', required: true, description: 'Source video file.' },
        output_path: { type: 'string', required: true, description: 'Output video file.' },
        subtitle_path: { type: 'string', required: true, description: 'Path to subtitle file (.srt, .ass, .vtt).' },
        mode: { type: 'string', enum: ['burn', 'embed'], description: 'Subtitle mode. Default: burn.' },
      },
      title: args => `Add subtitles ${args.subtitle_path} → ${args.output_path}`,
      locations: args => [{ path: args.input_path }, { path: args.subtitle_path }, { path: args.output_path }],
    }),
    ffkitTool(config, {
      name: 'ffkit_transcode',
      description:
        'Transcode a media file to a different format, codec, or resolution. ' +
        'The output container is inferred from the file extension.',
      parameters: {
        input_path: { type: 'string', required: true, description: 'Source file path.' },
        output_path: {
          type: 'string',
          required: true,
          description: 'Destination file path (.mp4, .webm, .mkv, etc.).',
        },
        video_codec: { type: 'string', description: "Video codec (e.g. 'libx264', 'libx265', 'libvpx-vp9')." },
        audio_codec: { type: 'string', description: "Audio codec (e.g. 'aac', 'libopus')." },
        resolution: { type: 'string', description: "Output resolution as WxH (e.g. '1280x720')." },
        bitrate: { type: 'string', description: "Target bitrate (e.g. '2M', '500k')." },
        fps: { type: 'integer', description: 'Output frame rate.' },
        preset: { type: 'string', description: "Encoder preset (e.g. 'fast', 'medium', 'slow')." },
        crf: { type: 'integer', description: 'Constant Rate Factor (lower = higher quality).' },
      },
      title: args => `Transcode ${args.input_path} → ${args.output_path}`,
      locations: args => [{ path: args.input_path }, { path: args.output_path }],
    }),
  ]
}

/**
 * Register the ffkit tools; disposal unregisters them with the plugin fiber.
 * @param ctx - plugin context providing `ctx.tools`.
 * @param config - validated plugin configuration.
 */
export function apply(ctx: Context, config: Config): void {
  for (const definition of ffkitToolDefinitions(config)) {
    ctx.tools.register(definition)
  }
}

import assert from 'node:assert/strict'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'
import process from 'node:process'
import { apply, Config, ffkitToolDefinitions, runBridge } from '../lib/index.js'
import type { ToolDefinition } from '@deepseek-ai/dsh-tools'

const STUB = fileURLToPath(new URL('../tests/stub-bridge.mjs', import.meta.url))

function stubConfig(mode: string, extra: Partial<Config> = {}): Config {
  return {
    ...(Config as unknown as (input: unknown) => Config)({ bridgeCommand: [process.execPath, STUB] }),
    env: { FFKIT_STUB_MODE: mode },
    ...extra,
  }
}

function fakeExec(signal?: AbortSignal) {
  return { signal: signal ?? new AbortController().signal } as never
}

const CLIP_ARGS = { input_path: 'a.mp4', output_path: 'b.mp4', start: '0', duration: '1' }

test('Config applies documented defaults', () => {
  const config = (Config as unknown as (input: unknown) => Config)({})
  assert.deepEqual(config.bridgeCommand, ['python3', '-m', 'ff_kit.bridge'])
  assert.equal(config.timeoutMs, 600_000)
  assert.deepEqual(config.env, {})
})

test('apply registers the five ffkit tools', () => {
  const registered: string[] = []
  const ctx = {
    tools: {
      register(definition: ToolDefinition) {
        registered.push(definition.name)
        return () => {}
      },
    },
  }
  apply(ctx as never, stubConfig('ok'))
  assert.deepEqual(registered, [
    'ffkit_clip',
    'ffkit_merge',
    'ffkit_extract_audio',
    'ffkit_add_subtitles',
    'ffkit_transcode',
  ])
})

test('parameter schemas compile to JSON Schema with required fields', () => {
  const clip = ffkitToolDefinitions(stubConfig('ok')).find(d => d.name === 'ffkit_clip')!
  const parameters = clip.parameters as { type: string; required?: string[] }
  assert.equal(parameters.type, 'object')
  assert.deepEqual([...(parameters.required ?? [])].sort(), ['input_path', 'output_path', 'start'])
})

test('execute round-trips through the bridge and returns the canonical value', async () => {
  const clip = ffkitToolDefinitions(stubConfig('ok')).find(d => d.name === 'ffkit_clip')!
  const value = (await clip.execute(CLIP_ARGS, fakeExec())) as Record<string, unknown>
  assert.equal(value.status, 'ok')
  assert.equal(value.echo_tool, 'ffkit_clip')
  assert.equal(value.output_path, 'b.mp4')
})

test('executor overrides are forwarded in the bridge request', async () => {
  const config = stubConfig('ok', { ffmpegBin: '/opt/ffmpeg', ffmpegTimeoutSeconds: 60 })
  const clip = ffkitToolDefinitions(config).find(d => d.name === 'ffkit_clip')!
  const value = (await clip.execute(CLIP_ARGS, fakeExec())) as Record<string, unknown>
  assert.deepEqual(value.echo_executor, { ffmpeg_bin: '/opt/ffmpeg', timeout: 60 })
})

test('invalid arguments are rejected before the bridge is spawned', async () => {
  const clip = ffkitToolDefinitions(stubConfig('ok')).find(d => d.name === 'ffkit_clip')!
  await assert.rejects(clip.execute({ input_path: 'a.mp4' }, fakeExec()))
})

test('FFmpeg failure is an in-band status:error value, not a throw', async () => {
  const clip = ffkitToolDefinitions(stubConfig('ffmpeg-error')).find(d => d.name === 'ffkit_clip')!
  const value = (await clip.execute(CLIP_ARGS, fakeExec())) as Record<string, unknown>
  assert.equal(value.status, 'error')
  assert.match(String(value.error), /FFmpegExecutionError/)
})

test('a crashing bridge throws with its stderr', async () => {
  const clip = ffkitToolDefinitions(stubConfig('crash')).find(d => d.name === 'ffkit_clip')!
  await assert.rejects(clip.execute(CLIP_ARGS, fakeExec()), /bridge exited with code 2.*stub bridge crashed/s)
})

test('non-JSON bridge output throws', async () => {
  const clip = ffkitToolDefinitions(stubConfig('garbage')).find(d => d.name === 'ffkit_clip')!
  await assert.rejects(clip.execute(CLIP_ARGS, fakeExec()), /invalid JSON/)
})

test('a missing bridge executable throws an actionable error', async () => {
  const config = { ...stubConfig('ok'), bridgeCommand: ['definitely-not-a-real-binary-xyz'] }
  await assert.rejects(runBridge(config, 'ffkit_clip', CLIP_ARGS, new AbortController().signal), /failed to start the ff-kit bridge/)
})

test('aborting the signal kills a hanging bridge', async () => {
  const controller = new AbortController()
  const clip = ffkitToolDefinitions(stubConfig('hang')).find(d => d.name === 'ffkit_clip')!
  const pending = clip.execute(CLIP_ARGS, fakeExec(controller.signal))
  setTimeout(() => controller.abort(), 100)
  await assert.rejects(pending, (err: Error) => err.name === 'AbortError')
})

test('render summarizes success and failure for the model', () => {
  const clip = ffkitToolDefinitions(stubConfig('ok')).find(d => d.name === 'ffkit_clip')!
  const ok = clip.output.render(CLIP_ARGS, { status: 'ok', output_path: 'b.mp4', command: 'ffmpeg -y ...' })
  assert.match((ok[0] as { text: string }).text, /succeeded[\s\S]*Output file: b\.mp4/)
  const failed = clip.output.render(CLIP_ARGS, { status: 'error', error: 'boom' })
  assert.match((failed[0] as { text: string }).text, /failed: boom/)
})

test('presentCall yields a generic execute card with file locations', () => {
  const clip = ffkitToolDefinitions(stubConfig('ok')).find(d => d.name === 'ffkit_clip')!
  const view = clip.presentCall?.(CLIP_ARGS)
  assert.deepEqual(view, {
    card: 'generic',
    kind: 'execute',
    title: 'Clip a.mp4 → b.mp4',
    locations: [{ path: 'a.mp4' }, { path: 'b.mp4' }],
  })
})

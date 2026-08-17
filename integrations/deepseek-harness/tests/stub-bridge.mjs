// Test stand-in for `python -m ff_kit.bridge`: validates the request protocol
// and answers with a canned response chosen by FFKIT_STUB_MODE.
import { stdin, stdout, stderr, exit, env } from 'node:process'

let raw = ''
for await (const chunk of stdin) raw += chunk

const mode = env.FFKIT_STUB_MODE ?? 'ok'

if (mode === 'crash') {
  stderr.write('stub bridge crashed\n')
  exit(2)
}
if (mode === 'garbage') {
  stdout.write('not json\n')
  exit(0)
}
if (mode === 'hang') {
  setTimeout(() => exit(0), 60_000)
} else {
  const req = JSON.parse(raw)
  if (typeof req.tool !== 'string' || typeof req.arguments !== 'object') {
    stderr.write('stub bridge: malformed request\n')
    exit(2)
  }
  const resp =
    mode === 'ffmpeg-error'
      ? { status: 'error', error: 'FFmpegExecutionError: ffmpeg exited with code 1.' }
      : {
          status: 'ok',
          command: `ffmpeg -y -i ${req.arguments.input_path ?? '?'}`,
          returncode: 0,
          stdout: '',
          stderr: '',
          output_path: req.arguments.output_path ?? null,
          echo_tool: req.tool,
          echo_executor: req.executor ?? null,
        }
  stdout.write(JSON.stringify(resp) + '\n')
  exit(0)
}

// /identity — the expanded form of the prompt's `@bot(PM) id v1 5/6` segment.
//
//   /identity             every agent the repo you are in declares (.project.json): the PM in full, the rest one line each
//   /identity <employee>  any employee flume knows, by post (33god-pm) or person (grolf)
//
// A thin adapter: the view is `flume identity manifest [employee] --markdown`, the one renderer every agent CLI's
// /identity shares (Codex and OpenCode run the same command). Change the view in flume, never here.
// Pattern and the other CLIs' adapters: 33god-hub sub-skill `agent-cli-extensions`.
//
// The answer is display-only: drawn in the transcript, never sent to the model, so it costs no turn.
import type { Register } from 'claude-code'

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'identity',
      description: "Expand the prompt's PM identity segment: manifest version and each identity point, for this repo's agents or a named employee",
      argumentHint: '[employee]',
    })
    return next(e)
  })

  on('command.run', { command: 'identity' }, async ($, e) => {
    const cwd = await $.session.cwd()
    const employee = (e.args ?? '').trim()
    const argv = ['flume', 'identity', 'manifest', ...(employee ? [employee] : []), '--markdown']
    try {
      const run = await $.process.run(argv, { cwd, timeoutMs: 30000 })
      const text = (run.stdout || run.stderr || `flume exited ${run.exitCode} with no output`).trimEnd()
      return { text, isTextDisplayOnly: true }
    } catch (error) {
      return { text: `✗ flume not runnable: ${(error as Error).message}`, isTextDisplayOnly: true }
    }
  })
}

// 33GOD commands for Claude Code. The procedure for adding one (to this CLI,
// Codex and OpenCode at once) is the 33god-hub sub-skill `agent-cli-extensions`.
//
// /identity [employee]: the shell prompt's PM identity segment expanded. Every
// word shown comes from `flume identity manifest`; this module only runs flume
// and places what it prints.
//   - with an employee: flume's markdown, in the transcript, display-only
//   - bare: a pane holding a menu of the repo's agents, each labelled with its
//     prompt form (`id v1 5/6`); a pick shows that agent's identity points.
//     Where no pane can be placed (`claude -p`), flume's markdown instead.
import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { IdentityAgent, IdentityMenu } from '../types'

const PANE = 'identity'
const menu = atom({ plugin: '33god', key: 'identityMenu' } as const, { project: '', agents: [], detail: {} } as IdentityMenu, {
  shape: 'identity-menu-1',
})

type Run = { exitCode: number; stdout: string; stderr: string }
type Engine = { process: { run(argv: string[], init: { cwd?: string; timeoutMs?: number }): Promise<Run> }; session: { cwd(): Promise<string> } }

async function flume($: Engine, args: string[]): Promise<{ ok: boolean; text: string }> {
  try {
    const run = await $.process.run(['flume', 'identity', 'manifest', ...args], { cwd: await $.session.cwd(), timeoutMs: 30000 })
    return { ok: run.exitCode === 0, text: (run.stdout || run.stderr || `flume exited ${run.exitCode} with no output`).trimEnd() }
  } catch (error) {
    return { ok: false, text: `✗ flume not runnable: ${(error as Error).message}` }
  }
}

// flume's project-mode JSON, cut to what the menu draws.
function agentsOf(json: string): { project: string; agents: IdentityAgent[] } | undefined {
  try {
    const data = JSON.parse(json)
    if (!data?.ok || !Array.isArray(data.agents) || data.agents.length === 0) return undefined
    return {
      project: String(data.project?.slug ?? ''),
      agents: data.agents.map((a: any) => ({ employee: String(a.employee), role: String(a.role ?? ''), prompt: String(a.prompt ?? '') })),
    }
  } catch {
    return undefined
  }
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'identity',
      description: "Expand the prompt's PM identity segment: a menu of this repo's agents, or one named employee's identity points",
      argumentHint: '[employee]',
    })
    return next(e)
  })

  on('command.run', { command: 'identity' }, async ($, e) => {
    const employee = (e.args ?? '').trim()
    if (employee) return { text: (await flume($, [employee, '--markdown'])).text, isTextDisplayOnly: true }

    const listed = await flume($, ['--json'])
    const project = listed.ok ? agentsOf(listed.text) : undefined
    if (!project) return { text: (await flume($, ['--markdown'])).text, isTextDisplayOnly: true }

    const first = project.agents[0]!.employee
    const detail = (await flume($, [first])).text
    await update($, menu, () => ({ ...project, selected: first, detail: { [first]: detail } }))
    const opened = await $.ui.open({ id: PANE, title: `Identity · ${project.project}`, focus: true, closeOnEscape: true })
    if (!opened.isPlaced) return { text: (await flume($, ['--markdown'])).text, isTextDisplayOnly: true }
    return { text: `${project.agents.length} agents in the Identity pane: pick one to see its points (Esc closes).`, isTextDisplayOnly: true }
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Select } = $.ui.resolve(e)
    const state = await read($, menu)
    if (state.agents.length === 0) return <Text dimColor>Run /identity in a repo with a .project.json.</Text>

    const selected = state.selected ?? state.agents[0]!.employee
    const lines = (state.detail[selected] ?? 'Asking flume…').split('\n')
    const room = Math.max(3, (e.viewport?.rows ?? 24) - state.agents.length - 4)
    const pick = async (value: string) => {
      await update($, menu, s => ({ ...s, selected: value }))
      if ((await read($, menu)).detail[value] !== undefined) return
      const text = (await flume($, [value])).text
      await update($, menu, s => ({ ...s, detail: { ...s.detail, [value]: text } }))
    }

    return (
      <Box flexDirection="column">
        <Select
          key="agent"
          options={state.agents.map(a => ({ value: a.employee, label: `${a.employee} · ${a.role} · ${a.prompt}` }))}
          value={selected}
          autoFocus
          onSelect={value => void pick(value)}
        />
        <Text> </Text>
        {lines.slice(0, room).map(line => (
          <Text dimColor={line.trimStart().startsWith('✗')}>{line}</Text>
        ))}
      </Box>
    )
  })
}

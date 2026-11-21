import { expect, test } from 'claude-code/testing'

type Ran = Array<{ argv: string[]; cwd?: string }>

const PROJECT = JSON.stringify({
  ok: true,
  project: { slug: '33god' },
  pm: '33god-pm',
  agents: [
    { employee: '33god-pm', role: 'pm', prompt: 'id v1 5/6' },
    { employee: '33god-art-director', role: 'art-director', prompt: 'id v1 4/6' },
  ],
})

// Stands for flume: answers each argv from `replies` (by its last word), else `fallback`.
function flume(on: any, ran: Ran, replies: Record<string, { stdout: string; exitCode?: number }>, fallback = { stdout: '**33god** · bound PM\n', exitCode: 0 }) {
  on('session.cwd', () => ({ value: '/repo/sub' }))
  on('process.run', (_: unknown, e: any) => {
    ran.push({ argv: [...e.argv], cwd: e.init?.cwd })
    const reply = replies[e.argv.slice(3).join(' ')] ?? fallback
    return { value: { exitCode: reply.exitCode ?? 0, stdout: reply.stdout, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
  })
}

const PANE = {
  plugin: '33god',
  component: 'Pane',
  requestId: 'identity',
  surface: 'terminal',
  props: { title: 'Identity · 33god', isFocused: true, bodyColumns: 80, placement: 'dock', scroll: { offset: 0, bodyRows: 20 }, view: {} },
} as const

test('/identity <employee> prints flume markdown display-only; a failure shows flume\'s own words', async ($, on) => {
  const ran: Ran = []
  flume(on, ran, { 'nobody --markdown': { stdout: '✗ Employee not found: nobody\n', exitCode: 1 } })
  const out = await $.command.run({ command: 'identity', args: ' nobody ' })
  expect(ran).toEqual([{ argv: ['flume', 'identity', 'manifest', 'nobody', '--markdown'], cwd: '/repo/sub' }])
  expect(out.text).toBe('✗ Employee not found: nobody')
  expect(out.isTextDisplayOnly).toBe(true)
})

test('bare /identity outside a project falls back to flume\'s markdown', async ($, on) => {
  const ran: Ran = []
  flume(on, ran, { '--json': { stdout: '{"ok":false}', exitCode: 1 }, '--markdown': { stdout: '✗ No .project.json\n', exitCode: 1 } })
  const out = await $.command.run({ command: 'identity' })
  expect(out.text).toBe('✗ No .project.json')
  expect(out.isTextDisplayOnly).toBe(true)
})

test('bare /identity with no pane surface (claude -p) prints the markdown', async ($, on) => {
  const ran: Ran = []
  flume(on, ran, { '--json': { stdout: PROJECT }, '33god-pm': { stdout: 'pm text' } })
  on('ui.open', () => ({ value: { isPlaced: false } }))
  const out = await $.command.run({ command: 'identity' })
  expect(out.text).toBe('**33god** · bound PM')
})

test('bare /identity opens the agent menu; a pick shows that agent\'s points', async ($, on) => {
  const ran: Ran = []
  flume(on, ran, {
    '--json': { stdout: PROJECT },
    '33god-pm': { stdout: '33god-pm: grolf (active) · identity manifest v1 · 5/6 required\n  ✓ 1Password Identity: vault item\n' },
    '33god-art-director': { stdout: '33god-art-director (active) · identity manifest v1 · 4/6 required\n  ✗ avatar: no avatar file\n' },
  })
  const opened: any[] = []
  on('ui.open', (_: unknown, e: any) => {
    opened.push(e)
    return { value: { isPlaced: true } }
  })

  const out = await $.command.run({ command: 'identity' })
  expect(opened[0]).toMatchObject({ id: 'identity', title: 'Identity · 33god', focus: true, closeOnEscape: true })
  expect(out.isTextDisplayOnly).toBe(true)

  const ui = await $.ui.mount(PANE)
  expect((await ui.find({ type: 'Text', text: /1Password Identity/ }))?.text).toBe('  ✓ 1Password Identity: vault item')
  const select = await ui.find({ type: 'Select' })
  expect(select?.props.options.map((o: any) => o.label)).toEqual([
    '33god-pm · pm · id v1 5/6',
    '33god-art-director · art-director · id v1 4/6',
  ])

  await ui.select({ key: 'agent', value: '33god-art-director' })
  expect((await ui.find({ type: 'Text', text: /avatar/ }))?.text).toBe('  ✗ avatar: no avatar file')
  expect(ran.map(r => r.argv.slice(3).join(' '))).toEqual(['--json', '33god-pm', '33god-art-director'])
  await ui.unmount()
})

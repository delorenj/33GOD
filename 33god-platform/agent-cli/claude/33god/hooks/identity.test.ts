import { expect, test } from 'claude-code/testing'

function flume(on: any, ran: Array<{ argv: string[]; cwd?: string }>, stdout = '**33god** · bound PM\n', exitCode = 0) {
  on('session.cwd', () => ({ value: '/repo/sub' }))
  on('process.run', (_: unknown, e: any) => {
    ran.push({ argv: [...e.argv], cwd: e.init?.cwd })
    return { value: { exitCode, stdout, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
  })
}

test('bare /identity asks flume for the project at the session cwd, display-only', async ($, on) => {
  const ran: Array<{ argv: string[]; cwd?: string }> = []
  flume(on, ran)
  const out = await $.command.run({ command: 'identity' })
  expect(ran).toEqual([{ argv: ['flume', 'identity', 'manifest', '--markdown'], cwd: '/repo/sub' }])
  expect(out.text).toBe('**33god** · bound PM')
  expect(out.isTextDisplayOnly).toBe(true)
})

test('/identity <employee> passes the employee through; a failure shows flume\'s own words', async ($, on) => {
  const ran: Array<{ argv: string[]; cwd?: string }> = []
  flume(on, ran, '✗ Employee not found: nobody\n', 1)
  const out = await $.command.run({ command: 'identity', args: ' nobody ' })
  expect(ran[0]!.argv).toEqual(['flume', 'identity', 'manifest', 'nobody', '--markdown'])
  expect(out.text).toBe('✗ Employee not found: nobody')
})

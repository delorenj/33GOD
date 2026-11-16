// Node loader for the self-check: the sandbox imports without extensions (Vite style), node wants them.
import { register } from 'node:module'
register('data:text/javascript,' + encodeURIComponent(`
import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
export async function resolve(specifier, context, next) {
  if ((specifier.startsWith('.') || specifier.startsWith('/')) && !/\\.[a-z]+$/.test(specifier) && context.parentURL) {
    for (const ext of ['.ts', '/index.ts']) {
      const u = new URL(specifier + ext, context.parentURL)
      if (existsSync(fileURLToPath(u))) return next(u.href, context)
    }
  }
  return next(specifier, context)
}
`))

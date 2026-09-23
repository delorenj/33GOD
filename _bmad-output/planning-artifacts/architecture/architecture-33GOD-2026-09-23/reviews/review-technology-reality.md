# Architecture Spine Review — Technology Reality

## Scope

Checked every named technology, version, and brownfield runtime claim against
the current repository, package manifests, service state, and Compose source.

## Confirmed

- Holocene web package manifests declare Next.js 15.0.0 and React 18.3.1.
- Holocene API declares Fastify 5.1.x and TypeScript 5.6.x; the architecture
  document records the current major/minor rather than inventing a new stack.
- The live host reports Node.js 26.5.0, and `holocene-api.service` is active
  with the built Holocene API. The Compose web target is `node:22`.
- `holocene/package.json` declares pnpm 10.0.0 and Turbo 2.0.x; the stack row
  matches the repository declaration.
- Flume's handbook and TypeScript contract agree on schema version 5 and
  contract version 1.4.0.
- `/hq` currently loads the official versionless Telegram WebApp SDK URL and
  validates `initData` in the repository's server-side route helper.
- `33god-platform/compose.yaml` owns `holocene-web`; the API remains the
  existing `holocene-api.service`, matching the spine.

## Finding

- **Medium — host package-manager invocation is not currently executable.**
  `pnpm --version` fails under the live Node 26.5 host with
  `ERR_VM_DYNAMIC_IMPORT_CALLBACK_MISSING` from the cached Corepack pnpm 11.5.0
  shim, even though the repository declares pnpm 10.0.0. This does not change
  the DeloHQ boundary, but it must be resolved before using the documented
  package-manager stack as implementation evidence.

## Verdict

The named architecture technologies are current or directly reality-checked.
No new framework or starter is introduced. The pnpm/Node invocation mismatch is
the only technology-reality issue found and is appropriately deferred to the
platform/toolchain handoff.

# CLI hook migration and observability — 2026-09-13

The migration replaces native behavioral registrations with one `bb-hook`
entry per native lifecycle hook. Bloodbank's host hub normalizes the invocation,
selects its applicable concerns from one registry, and publishes its canonical
event once. Holocene exposes installed wiring and actual execution receipts at
[holocene.delo.sh/hooks](https://holocene.delo.sh/hooks).

This follows [the original audit](cli-hook-audit-2026-09-13.md). The detailed
runtime contract is in [Bloodbank's hub README](../bloodbank/services/hook-hub/README.md).

## Installed coverage

Live inspection on September 13 found no remaining direct managed calls in any
of the inspected native configurations. All eight adapter executables resolve,
including binaries installed under mise that are absent from the daemon PATH.

| CLI | Native bindings | Installed hub calls | Configuration scope |
| --- | ---: | ---: | --- |
| Claude | 13 | 13 | Global native settings |
| Codex | 10 | 20 | User home and Orca runtime home |
| Copilot | 12 | 12 | Bloodbank projection; old Orca entries removed |
| Hermes | 12 | 492 | Default, 38 profiles, and two active legacy homes |
| Antigravity | 4 | 4 | Native hook configuration |
| Gemini | 7 | 7 | Valid native settings; installed CLI 0.41.2 |
| Kimi | 13 | 13 | Native TOML configuration |
| OpenCode | 8 | 8 | Canonical native plugin bridge |
| OpenClaw | 0 | 0 | Explicitly unsupported; no adapter claimed |

There are 79 distinct supported native bindings and 569 installed hub entries.
The original cutover changed 92 targets and removed 120 known legacy entries
across 12 paths. Foreign hooks and unrelated preferences were preserved. Codex's
native loader verified all 20 new managed hooks enabled and trusted, including
the alternate Orca home. The retained foreign reaper kept its existing trust.

Native coverage and concern applicability are separate. The registry declares
which concerns apply to which CLI. For example, Project Notebook's native engine
supports Claude, while Orca requires its launch context. A non-applicable concern
is skipped rather than reported as successful work. Hermes lifecycle signals
without a Bloodbank contract are marked Local in Holocene.

## Repairs

- Central publication and behavioral dispatch now share one invocation owner.
  Cached legacy publisher commands forward into that owner after activation.
- Codex uses native timeout units, preserves payloads, runs Bash post-tool hooks,
  and separates turn completion from actual session end. The old notify path no
  longer duplicates the Stop path.
- Hermes uses its actual installed hook surfaces: turn-end and final session
  teardown are different signals. Discovery includes live profiles and runtime
  homes.
- Copilot, Gemini, Kimi, and OpenCode projections use their native schemas and
  preserve their own CLI identity. Opaque session IDs remain intact in payloads;
  schema-required correlation UUIDs use deterministic conversion.
- Behavioral children are supervised. Completion, explicit skips, missing
  dependencies, timeout, interruption, and duplicate suppression have receipts.
  Session-end retention waits for pending candidate writes from that session.
- The missing merge-forward worker was restored. Legacy launchers, scaffold
  fallbacks, Project Notebook, CodeGraph, Nanoleaf, and Orca installers honor the
  central ownership manifest instead of recreating direct registrations.
- Python 3.13's inherited Unix-socket cleanup was fixed. It had removed systemd's
  pathname while leaving the daemon's HTTP API healthy. An actual service-only
  restart retained socket inode 9259765, and an automated regression runs the
  real daemon twice against the same activated socket. Missing ingress now
  degrades status and produces a Holocene alert.

## Native and durable-delivery evidence

A fresh Codex session (`01a09bd1-a110-7081-bb99-94c5b8df1d2f`) ran one harmless
Bash printf in a disposable `/tmp` directory with a read-only sandbox. It exited
successfully and created no files. Exactly one receipt each was recorded for
SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Stop, and SessionEnd.
Each of its six publisher event IDs appeared exactly once in Candystore.

The PostToolUse receipt `c40bb29e-951f-586f-8748-45b5d80215fd` published event
`f0ab6cbb-2541-42d2-8eda-0327ff6cd878`. Pre/post-tool shared their native tool-call
ID; prompt/Stop shared their native turn ID.

A real Claude session (`37a37ec6-37a9-48a4-a57c-ba1a54e22117`) likewise ran one
Bash printf, created no files, and produced six native receipts and six unique
Candystore events. These first probes exposed notebook applicability and recall handling. Notebook
now declares its supported Claude scope and skips non-repositories. The corrected
non-repository recall fallback returned context in follow-up probes. Historical
failure receipts remain in the journal rather than being erased.

A publisher receipt marked `sent` proves NATS transport. The separate event-ID
lookups above provide the durable Candystore evidence. Stable native IDs permit
duplicate suppression; a native retry without a stable identity cannot have an
exactly-once guarantee.

## Holocene

The direct proxy and polling path described below is the initial delivery.
The [Bloodbank event collection follow-up](hooks-event-collection-2026-09-13.md)
supersedes that integration boundary: Hooks is now a filtered view of
Holocene's shared event collection.

The implementation preserves the drawing's stacked Bloodbank/native panels,
explorer, explicit mapping, and attached-handler badges. Its UX was refined in
[Google Stitch project 16143358374491232683](https://stitch.withgoogle.com/projects/16143358374491232683),
screen `919e509947ca4713abcbfbdc39c1e8cf`. Generated sample telemetry was not
included in the product.

The live page provides CLI and event selection, installed-source inspection,
handler/outcome filters, pagination, pause/refresh, and expandable receipts with
lifecycle timelines. Polling updates active receipts. Configured-but-quiet,
unsupported, local-only, skipped, failed, and duplicate-suppressed states remain
distinct. Receipt data contains execution metadata, not prompts or transcripts.

The API runs through `holocene-api.service`; the web service is owned by
`33god-platform/compose.yaml`. The API proxy tests, TypeScript checks, and
production web build pass. The independent visual review and browser checks passed at desktop and mobile
sizes. Mobile document width equals viewport content width; tables scroll inside
their containers. Verified interactions include CLI selection, local-only and
unsupported mappings, search, receipt expansion, lifecycle details, follow-
selection filtering, pause/resume, outcome filtering, empty results, pagination,
and recovery from a simulated status-feed failure. An unsupported-inventory
selection crash found during these checks was corrected and re-tested live.


## Final acceptance and deployed state

- **218 hook tests passed** in the combined hub and adapter run. This includes
  the 80-test hub suite, native envelope contracts, duplicate identities,
  supervised outcomes, socket activation, and graceful shutdown.
- Eight adapter replays each produced one successful receipt, one publication,
  and one matching Candystore event. Actual native execution was additionally
  proved for Claude, Codex, and OpenCode; Gemini loaded its native settings.
  The exact evidence and all 22 publication IDs are in
  [the native acceptance report](../bloodbank/docs/hooks-native-acceptance-2026-09-13.md).
- OpenCode's actual loader is repaired through a deterministic native agent
  projection. Shared definitions retain their content; its Momo tool allowlist
  is translated to equivalent native permissions.
- Orca 1.4.180 was updated on disk and in running PID 6414. Existing terminal
  processes stayed alive. Seven managed installers report central ownership;
  its generated OpenCode plugin produced zero direct status callbacks.
- Code Review Graph's installed `install` and `init` entry points now use a
  persistent ownership-aware wrapper. Ordinary native-hook reinstalls are
  suppressed while the hub owns the concerns; other commands remain available.
- The final hub service uses `KillMode=mixed`, a five-second stop limit, and a
  two-second graceful drain. Two reserved publisher slots prevent starvation by
  long behavioral jobs. Accepted publication completes before exit where it
  fits that budget; remaining work is recorded as interrupted, with unknown
  publication outcome rather than a fabricated result. The in-flight restart
  regression passed. A live restart retained the socket inode and added no
  failed receipts. Historical rows were preserved.
- The API proxy has three passing tests; TypeScript and production web build
  passed. Holocene `/hooks` is deployed from source revision `2bfcf5b` through
  the root Compose service; the API runs its built service artifact.

Existing CLI processes may cache native registrations. Their registered legacy
publisher commands now forward safely to the hub, and guarded legacy behavior
entrypoints defer to central ownership. Start a fresh CLI session to load newly
added native hook types.
The final process check found two running Claude and four Codex processes with
no Orca launch environment, and no Copilot/Kimi processes. Their cached Orca
registrations reference mutable shell scripts, which exit without that launch
context. No current Orca double-posting path was demonstrated, and these observed
processes do not require a restart to prevent it. Fresh sessions use the new
central registrations.

Actual cached Hermes fleet emission has not yet been observed; compatibility is
covered by executable forwarding/identity tests, while its installed wiring and
adapter replay are verified. OpenClaw remains explicitly unsupported.

The task's source changes and native projections are committed and pushed in
their owning repositories. The workspace-wide `git unpushed` scan also reports
pre-existing and concurrent work; that unrelated work was not folded into this
migration. In particular, the existing James Brennan audio commit exceeds
GitHub's file-size limit; the hook guard itself was published separately.

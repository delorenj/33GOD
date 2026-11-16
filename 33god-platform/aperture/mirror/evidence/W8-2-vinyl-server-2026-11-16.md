# W8-2 (Vinyl server half): the Mac runs its own `vinyl-server`, 2026-11-16

Executor: Claude Code on big-chungus over `ssh -o BatchMode=yes hellosubconscious@100.117.109.60` (no sudo), Vinyl story 2.5. Source of record: `~/HeyMa/components/vinyl`, commits `d2f7b54` and `c77ad76` (tools, tests, notes) on top of the story 2.4 formula.

## Verdict

**Agent-verifiable part: PASS. Operator part (TCC, typed sentence, HeyMa.app status): OWED.** big-chungus is not needed for Mac dictation, and the tailnet-share blocker in the W8 block no longer applies to voice typing: the server, the token and the audio all stay on this Mac (loopback only).

## What was installed (real HOME, once)

`brew tap delorenj/tap` + `brew trust delorenj/tap` (Homebrew 7.0.14 asked), `brew install delorenj/tap/vinyl-server` (0.5.0, python@3.13 keg venv, transcribe-cpp 0.4.2), `vinyl-server setup` (downloaded and sha256-verified both GGUFs into `~/audio/models`, minted `server.token`, paired the client to 127.0.0.1:7733, replaced the old `damian-studio` big-chungus token in `~/.config/vinyl/token` as designed; big-chungus's `clients.d` copy untouched), `brew services start delorenj/tap/vinyl-server`, `brew install delorenj/tap/vinyl-client` (0.4.3), `brew install --cask delorenj/tap/heyma` (0.4.4, `/Applications/HeyMa.app`), `vinyl setup --server 127.0.0.1:7733`, `brew services start delorenj/tap/vinyl-client`. No pre-existing vinyl client, LaunchAgent or `~/.local/share/vinyl` was on the Mac. No tokens were printed or copied off it.

## Proof

| Check | Result |
|---|---|
| `brew list` | `vinyl-server`, `vinyl-client`, cask `heyma` present |
| `brew services list` | `vinyl-server` and `vinyl-client` `started` (LaunchAgents `sh.delo.vinyl.server`, `sh.delo.vinyl.client`) |
| `vinyl-server doctor` | all clear: `backend metal (devices: cpu, metal)`, models ok, `serve listening 127.0.0.1:7733` |
| `vinyl doctor` (client) | all clear: server `127.0.0.1:7733`, pairing token, osascript + pbcopy |
| `vinyl status` | answered over the client RPC, `idle` |
| Metal | service log `ggml_metal_device_init: GPU name: MTL0 (Apple M3 Ultra)`; server trace `recognizer.config` `backend: metal`, `fallbacks: 0` |
| Live wire, `tests/e2e/mac_server_acceptance.sh ... 10` | 10 of 10 sessions returned a non-empty final (the probe asserts only that; the printed finals matched the `say` sentences in this run); stop to last final p50 91.6 / p95 97.7 / max 97.7 ms; stop to `stopped` p50 92.4 / p95 98.7 / max 98.7 ms |
| Corpus replay through the keg (59 traces, 8.44 h) | 1409 finals, 5 empty (0.35%), stop-to-text p50/p95/max 43/81/87 ms, all-finals 40/83/155 ms, RTF 0.0207, 0 decodes over 1 s, `fallbacks` 0; within 8% of the story 1.4 uv-venv Metal run (RTF 0.0192) |
| Cleanup | no `/tmp/vinyl-accept.*` or `/tmp/vinyl-parity.*` left on the Mac |

The live probe used macOS `say` speech only, so the server traces now on the Mac (two driver runs of 10 sessions each, pruned after 7 days) hold synthetic text. The replay copied Jarad's corpus audio only into a `/tmp` directory removed by a trap.

## Owed (operator, at the Mac's GUI)

1. First dictation raises the Microphone and Accessibility prompts for the Vinyl client: grant both (no ssh path exists).
2. Speak a sentence into a text field through the hotkey or HeyMa toggle and confirm it types. The agent never ran `vinyl toggle`/`start` and never launched HeyMa.app.
3. Open `/Applications/HeyMa.app` once and confirm its status reads `idle` with endpoint `127.0.0.1:7733`.

## Findings

- The Mac has `~/HeyMa` with a wax checkout and a 118-term `Dictionary.yaml`, so the server's dictionary corrector is on (auto mode), unlike the "no wax checkout" case the epic assumed. Under launchd `op` is not on PATH, so the Jev key does not resolve and finals use policy P3; nothing is sent to Jev. `vinyl dictionary off` disables it.
- Still one dictation session at a time on the server (`session_lock`); the one-user-per-Mac case is unaffected.
- W8-2's Wax half (waxd, transcribe, enrichment) is untouched and still Linux-only.

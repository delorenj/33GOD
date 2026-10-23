# folder-curator — documented deferral (not a shipped service)

No curator container or pretend health stub is supplied in v0.1. This is an
explicit scope option in the G2 handoff, not a claim of complete curator support.

## Read-only host crib (2026-10-23)

These lines are recorded verbatim from user units; they are NOT executed by G2:

```ini
# curator-serve.service
Environment=PATH=%h/.local/share/mise/shims:%h/.local/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=%h/.local/bin/folder-curator serve --host 127.0.0.1 --port 8787
# curator-drain.service
Environment=CURATOR_WEBHOOK=http://127.0.0.1:5678/webhook/folder-curator-intake
ExecStart=%h/.local/bin/curator-drain
# pdf2md-serve.service
ExecStart=%h/.local/bin/pdf2md serve --host 127.0.0.1 --port 8788
```

The launcher targets a DeLoDocs vault-local Python script, not a redistributable
package. Source inspection (no invocation) found a personal vault-root default,
implicit `.env` lookup, a 1Password subprocess lookup and fixed provider URLs.
Copying it as-is would violate the charter's portable endpoint / isolated-state
requirements. A new no-op server would misrepresent the delivered capability.
The drain depends on a host custom node intake; custom nodes are excluded here.
PDF conversion belongs with that later document-enrichment slice.

## Follow-up contract proposal (not adopted/implemented)

Extract and version an owned curator package first; explicit `GOD_LLM_BASE_URL`,
`GOD_LLM_MODEL`, deployment-supplied credential, and `/work`-confined file access.
Use `serve --host 0.0.0.0 --port 8787` in-network, owned `god-g2-curator-data`,
no host/vault mounts, health/readiness plus dry-run routing evidence. Target
256 MiB; reallocate the current 2016 MiB steady-state cap to keep the full
bundle below 2560 MiB. Prove arm64 image manifests/dependencies and routing on
synthetic files before including the service. No LLM key is requested now.

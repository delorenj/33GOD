# Changed-behavior gates

Select checks that demonstrate the slice's actual behavior:

- Live routing failures: check the public response, backend, and affected data endpoint; an authentication redirect alone does not prove backend health. Correlate Traefik DNS/health errors with container recreation timestamps and the configured health-check interval. If service recovers without intervention, verify current route health and endpoint responses, then stop without a speculative restart or patch. Distinguish the observed failure and recovery from any unproven recreation trigger.
- Hook changes: native loader registration, one event to one handler receipt, payload and context output, hub-down behavior, and concurrent session identity.
- Event changes: contract validation, broker delivery, and durable Candystore arrival.
- Holocene changes: typecheck, build, browser interaction, and live route verification.
- Compose or systemd changes: resolve the effective configuration, restart only affected units, and verify the running artifact.
- Template or generator changes: render into an isolated temporary directory and compare the intended owned projection while preserving foreign settings.

Run the affected tests and direct boundary checks. A config file, selected handler, or zero exit status alone is not proof that its downstream work succeeded. Treat idle clients as unobserved until exercised.

Preserve unrelated WIP. Land coherent units promptly on component main and root main. Do not add speculative review layers or repeat unchanged checks.

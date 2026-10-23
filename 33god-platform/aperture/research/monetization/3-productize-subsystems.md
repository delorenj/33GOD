# Monetization avenue 3 — Productize subsystems (HeyMa first)

**Model.** Extract one domain, harden it as a standalone product, sell that.
The operator's own candidate: **HeyMa = Wax + Vinyl** — a local-first voice
memo → transcript → enriched document pipeline.

**Why HeyMa is the right first product**
- Smallest external-dependency surface of the 8 groups (no Plane, no fleet,
  no personal memory; LLM endpoints are config)
- Solves a legible, everyday problem (voice notes → structured docs) that
  buyers understand in one sentence
- The Wax pipeline engine (11 passes, pipelines.d composition) is genuinely
  differentiated: deterministic passes + LLM passes, pluggable per deployment
- Vinyl gives it a hardware/edge story (dictation thin clients, warm recognizer)
- Already has packaging instincts: deploy/ dir, systemd units, homebrew tap
  formula (vinyl-client.rb exists)

**Product shape (draft)**
- `heyma` image: wax daemon + passes + API + web UI (transcript inbox)
- Bring your own LLM key (OpenAI-compatible base_url) — passes that call LLMs
  degrade gracefully without one
- Transports: file drop, syncthing folder, or Telnyx/S3 intake (config)
- Vinyl client optional (dictation endpoint for phone/desktop thin clients)

**Gaps to close**
- Strip Bloodbank hard-dep to optional (pipeline completes locally; bus events
  become an optional adapter)
- Branding/naming separate from 33GOD internals
- Install story for non-technical buyers (single binary or DMG for client,
  one container for server)
- Licensing per install or per seat

**Fit with the moat.** Medium-high — sells one slice of the moat, keeps the
rest. Good first revenue while avenue 2 matures.

**Risk.** Scope creep back into the full stack; support for GPU transcription
(variants: CPU-only build for the product).

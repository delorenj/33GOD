# G5 — explicit non-deliveries and extraction contracts

The three tool images build and execute on the build host. This is artifact
acceptance, **not** the broader [G5 real-project gate](../../ACCEPTANCE.md#g5--project-tooling-a-real-project-born-on-the-stack).

| Deferred | Why it is not proven | Extraction / next acceptance contract |
|---|---|---|
| Python/uv PJangler recipe | Current PJangler is Node >=24, not pip-installable; the named sibling checkout does not exist | Use the real Node source image now. A Python image requires an owning-project product change and genuine Python packaging, not a wrapper pretending otherwise |
| Node 20 CLI images | Both source packages require Node >=24 | Node 24.6.0 is used and executed; do not downgrade without upstream support |
| Image publication (all three), multi-platform build/runtime | No registry destination/publication authority or target execution supplied | Owner chooses registry/tags/auth; build and push both Bake platforms, record immutable application-image digests; recipient reruns native smoke |
| npm Trusted Publishing for Skillex | Installing public 0.3.1 proves package availability, not its release provenance or publishing workflow | Owning Skillex PM verifies OIDC workflow/package provenance and reruns release gates in its repo; no host npm token/config enters this bundle |
| Full PJangler/CommonProject project creation | Thin CLI image does not contain Git, trusted Copier's canonical managed-Python installation, template checkout or ancillary CLIs; source lifecycle preflight explicitly validates these | Extend a reviewed build recipe to supply actual prerequisites; mount a pinned recipient-owned template read-only and a fresh project/registry writable; run `pj init` with recipient answers, commit/read back its real manifest without host config |
| CommonProject template execution | Only its real read-only mount is proved; its existing tasks may call shell/Python and generated setup can reference deployment state | Consumer reviews/sanitizes source and answers, executes Copier in an isolated fresh output, validates no global-config side effects; do not claim a generic synthetic template is CommonProject |
| Skillex catalog shipment / installed skill execution | npm CLI is not a catalog; no operator skill selection or payload was exported | Recipient pins its own canonical catalog, supplies explicit set/pack selection and writable output, installs and executes one real skill with captured output; current source uses `sets/`/`packs/`, not the historical layout |
| MCP semantic tool execution | Real stdio initialize/list succeeded; no project DB/module/dependency or model-provider state was exported | Recipient mounts its own CodeGraph project/module and supplies required libraries/credentials at runtime, then proves a real semantic tool result. Initialization is not semantic-search proof |
| Notebook + attached bus roundtrip, recipient dogfood | This build changes no service or production registry and has no bus attachment | Recipient performs all four G5 acceptance criteria with a fresh real evidence repo; retain its manifest, skill result, notebook readback, and downstream bus record |
| Independent review | Implementer cannot self-certify the merge gate | PM reruns `smoke/smoke.sh`, source-preservation and artifact review on the pushed branch before merge |

## Operational findings kept out of this bundle

- The root CodeGraph sidecar reports thousands of test vectors mixed with a
  small real group. It was inspected only; no purge/reindex occurred. Do not
  treat that existing index as semantic retrieval evidence.
- The supplied root “no fake server” directive was not found verbatim in the
  current checkout's tracked Markdown. It is binding task context; the existing
  platform runtime README corroborates the no-listener/run-only PJangler model.
  No architecture file was invented or amended to make the citation look real.
- Source checkouts had pre-existing unrelated changes. Their exact initial and
  final statuses are recorded in PROOF.md; unchanged means preserved, not
  falsely reported as clean.

## Reusable review question

How can a Docker artifact look healthy while misrepresenting the component?
Check the real package metadata before selecting the language/runtime, distinguish
an executable image from a service, and separate protocol startup from domain
work. A passing CLI help or MCP initialize is narrowly useful evidence, not proof
that a real project, provider, notebook, or event route works.

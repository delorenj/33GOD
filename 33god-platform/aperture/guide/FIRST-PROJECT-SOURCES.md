# Your first PJangler project — source and review record

Verified against the local checkout on **27 October 2026**. This is a static educational artifact, not execution evidence for a learner’s Mac. Expected outcomes describe what to look for; no terminal output is fabricated. Spotlight and the operations panel are explicitly labeled illustrative; file panels are pointers/field maps, not invented file contents.

## Scope and delivery

New files only: `first-project.html`, `first-project.css`, `first-project-mascot.css`, `first-project.js`, `FIRST-PROJECT-TESTS.json`, this record and the seven local files under `first-project-assets/`. Existing conceptual guide, design system, logo assets and published URL are preserved. The companion references the existing local `33god-mark.svg` and `favicon.svg`; publish with those assets and the existing `pjangler.html` if retaining the masthead’s local link. The conceptual-guide link in the article is the existing published URL.

The browser performs clipboard, reading-position and optional local checklist operations only. No commands execute. No analytics, remote images, fonts, CDNs or API calls. Installation, credentials, provider configuration, hiring, service/board changes and real Studio acceptance are outside this artifact. Rererere owns Studio readiness and deployment acceptance. The worker does not commit, publish, change application source or run project initialization.

## Primary authority

- `33god-platform/aperture/CHARTER.md` §§2–3: Rererere alone owns Damian’s environment; independent review precedes merge; evidence is not a status label.
- `guide/DESIGN.md`, `guide/PRODUCT.md`, `guide/style.css`: incumbent cobalt `#163fc5`, deep blue `#102d8b`, ink `#14234a`, ice `#eaf1ff`, system sans typography. The companion extends this world with one-task scroll stops. Min-height is used, never height clipping or forced scroll snapping.
- `guide/33god-mark.svg`: existing two-path split-circle mark, identical geometry to `holocene/design/project/assets/Logos/33god-mark.svg` and the live Holocene `hub-brand`. Existing inverse off-white/coral color adaptation retained, not a new identity.
- `pjangler/docs/project-registry.md`: `.project.json` canonical; registry indexes known locations; `agents` is Flume’s projection; `pj list`/`pj info` do not constitute full bootstrap/provider acceptance.

## Version distinction

The checked source HEAD was `aa93868de6700298ab4350a2a3173ce661980577`; `pjangler/dist/index.js --version` reports **1.5.18**. The checkout is newer than the published npm 1.5.18 package despite sharing that number. The existing verified npm tarball `@delorenj/pjangler@1.5.18` was separately inspected; matching version strings alone are not behavioral parity proof. `pj skills --version` from both the local pass-through and the pre-existing isolated npm prefix reports **0.3.0**, its own Skillex version, not PJangler’s. The isolated npm 1.5.18 prefix also executed `skills status --help`, `skills skill list --help` and `skills sync --help`; the documented scopes/flags match the checked checkout.

Both the local source and npm compiled `runProjectInit` compute apply as `!options.dryRun && (options.yes || options.apply || interactive)`. Therefore **plain interactive `pj init studio-notes` is not a guaranteed preview**, even though help calls dry-run the default. The guide intentionally uses `pj init studio-notes --dry-run` followed by `pj init studio-notes --apply`. No `--yes` or `--no-tui` bypass is taught.

## Wizard verification (source, not an executed bootstrap)

- `pjangler/src/index.ts:178–193`: interactive requires a real stdin/stdout TTY, no JSON, no yes, no disabled TUI. Text inputs validate nonempty strings; cancellation says `project init cancelled` and exits.
- `src/index.ts:273–317`: operation rows derive from the actual plan plus any fixable sync findings. Prompt text is **“Select project init operations to run:”**. All offered values start selected. Non-TTY `--apply` selects all without this UI; a beginner should use Terminal, not a pipe.
- `src/index.ts:236–250`: verified source row labels: “Refresh the project registry index”; “Render CommonProject scaffold”; “Write authoritative repo-local .project.json”; “Create/link ticket provider project”. Their presence/order can depend on plan and version; the guide labels the depiction illustrative.
- `src/index.ts:320–425`: a positional name resolves `./name` first. The exact named sample does not ask for project name/directory. The alternate no-name/no-adoption route can ask **“Project name”** and **“Project directory”**. Existing targets may enter sync and add audit/migration rows. These are branches, not a promised sequential wizard.
- `@clack/core`/`@clack/prompts` dependency: arrow navigation, Space toggling, Return submission and cancellation handling support the explained keys. Ctrl+C at the selection prompt is cancellation, not universal rollback after execution begins.
- `src/index.ts:734–858`, `src/recipes/ProjectRecipe.ts`: applied transaction orchestrates scaffold/dependencies/BMAD, audits, Git, ticket-provider phase and registry finalizer. External effects may survive a failure. No guarantee of universal rollback, idempotent bootstrap or safe blind retry is made.
- `src/parity/rules.ts:1896–1914`: internal BMAD installer is driven with supplied arguments/`--yes`; no invented learner-facing BMAD questionnaire is shown.
- `src/project/index.ts:1587–1637`: Copier runs as a captured child process. Its internal template behavior is not presented as a separate interactive learner wizard.
- Board creation/linking is default and can affect the configured workspace without `--live`. The guide gates it on Rererere’s preapproval and delegates provider/identifier choices to the operator.

## Verified CLI surfaces

Help was executed using `node pjangler/dist/index.js … --help`, without performing the operations:

| Learner command | Verification |
|---|---|
| `pj init studio-notes --dry-run` / `--apply` | `init --help`, target resolver + apply logic; npm bundle inspected separately |
| `pj list`, optional `pj info` | `list --help`, `info --help`, registry documentation |
| `pj skills status --scope both --project "$PWD" --json` | `skills status --help` confirms `auto/global/project/both`, `--project`, JSON; status is read-only and drift exit is 6 |
| optional `pj skills status --scope global --json` | same status help, explicit global scope |
| `pj skills skill list` | `skills skill list --help` confirms catalog names/descriptions/provenance; **not** the unsupported shortcut `pj skills list` |
| optional `pj skills explain NAME --scope both --project "$PWD" --json` | `skills explain --help`; NAME is deliberately uncopiable notation, must come from actual catalog/report |
| `pj skills sync --scope project --project "$PWD" --dry-run --json` | `skills sync --help`, project-only preview; default sync may touch both scopes, hence explicit scope |
| optional skill enable preview/apply notation | `skills enable --help`: skill/set/pack, explicit project scope, `--dry-run`; enable without dry-run immediately reconciles; no fabricated canonical skill name |
| `pj audit --rules bmad.version`, optional `pj audit` | `audit --help`, `--rules` exists; read-only audit |
| `pj migrate bmad.version --dry-run` | `migrate --help`, explicit preview |
| optional `pj migrate bmad.version` then same audit again | apply has **no `--apply` flag**; saved/committed work and Rererere agreement are required; no `--all` shortcut |

The standalone `skillex` executable is not assumed on PATH; this learner uses the bundled `pj skills` pass-through consistently. Actual catalog names, selection content and terminal success output are never fabricated.

## Skill ownership and scope

Product semantics checked against `.agents/skills/skillex-skill-registry/SKILL.md` and explicit user corrections:

- Project selection: `<project>/.agents/skills.json`; project activated root: `<project>/.agents/skills/`.
- Global selection: `~/.agents/skills.json`; global activated root: `~/.agents/skills/`.
- Canonical definition catalog is separately configured/owned. Studio is not assumed to contain another developer’s checkout path.
- Sets replace a scope-owned root; packs add members. Effective discovery remains the deduplicated union of global + project-specific skills. Older help headings that reverse set/pack descriptions are not taught as authority.
- Finder inspections and global status are read-only. A missing activation root/manifest is an operator setup finding, not an instruction to mkdir or hand-copy payloads.

## macOS command basis and limits

- Apple Terminal documentation: https://support.apple.com/guide/terminal/ — Terminal, shell commands and path concepts; opening via Spotlight uses macOS Command+Space, typing Terminal, Return.
- macOS `open` reference fetched during implementation: https://ss64.com/mac/open.html — `-e` opens files with TextEdit, unflagged folder paths open Finder. Thus `open -e AGENTS.md`, `open -e .project.json`, `open .agents`, `open ~/.agents`, `open _bmad` are native macOS syntax, not Linux commands.
- This implementation host is Linux. macOS TextEdit/Finder actions were **not executed**. File presence is conditional on successful, accepted setup; guide provides missing-file recovery and does not invent generated content.
- `cd` is a shell builtin; `~/` expands to home; `pwd` prints the working directory. A child process cannot change the launching shell’s working directory, hence explicit post-init `cd ~/code/studio-notes`.

## Operating status boundary

Dated 27 October 2026: the existing registry diagnosis record reports clean Linux acceptance for npm 1.5.18 registry-only use. Full Studio/macOS bootstrap, BMAD create and repeat-create acceptance remain pending. These are instructor readiness gates, not a claim that the current source fixes or accepts the full workflow. The artifact was tested as static UI only.

## UI test results

Local headless Chromium tests executed successfully after implementation (Playwright; no real Studio action):

- **18 slides**, **16 copy buttons**, **10 internal links**, all anchors resolve.
- Clipboard success copies the exact one-line command. Denial selects the command and announces manual-copy recovery. No shell prompt markers are copied.
- Reading next-link, sticky rail, keyboard skip-link, manual checkmarks/localStorage persistence work; upgrade Copy is gated and approval does not persist across reload.
- No-JavaScript text/disclosures/anchors remain usable; Copy is hidden without script.
- **No horizontal page overflow or out-of-bounds elements** at 1440×900, 1024×768, 768×1024, 760×900, 390×844 and 320×740.
- **0 JavaScript/console errors**, no remote asset requests.
- Mobile Next/Pause touch targets are at least 44px high. At the bottom of the 390px page, final stage bottom was 730.61px and sticky rail top was 781.41px: final content scrolls fully clear of navigation.
- **0 axe-core WCAG A/AA/2.1 AA violations** in the checked desktop DOM (not a claim of universal accessibility certification).
- Print PDF rendered; rail and mascots hidden. Reduced-motion has no mascot animations.
- **18 actual-artwork mascot stages and 18 distinct scenes**, every cutout image decodes. All scene-specific animations run only when their stage is observed onscreen, with 4.0–5.8 second durations. Offscreen animations are paused. Global Pause produces a stable computed transform; Resume restarts motion. No command panel overlaps a stage.
- Desktop/mobile viewport screenshots and all 18 stage screenshots were generated and visually inspected via contact sheets. Larger Copy/Next/Pause targets and the compact wizard keep instructional content primary.

Sanitized machine-readable test receipts are bundled in [`FIRST-PROJECT-TESTS.json`](FIRST-PROJECT-TESTS.json). Screenshots, print PDF and reproducible test/extraction scripts remain in the worker’s local scratch directory; the parent’s handoff supplies their location. They are review evidence, not a claim that the learner executed any command.

The mechanical Impeccable detector was run once. Its advisory findings included `--` CLI flags counted as em dashes, the inherited Arial/system typography, and literal operational contrast language. Those do not justify corrupting command syntax, changing the established brand or removing needed authority distinctions. A separate parent review remains required; this worker did not spawn its own finish-review worker. The `html-artifact-delivery` skill was quarantined by the runtime; no quarantine or global skill configuration was changed.

## Chocolate Man artwork and motion

The user supplied the drawing and explicitly authorized its incorporation and loops. `first-project-assets/chocolate-man-original.jpg` is an exact copy of the supplied image (SHA-256 `16c43472325e8d4c8663fdae0ca62b258ac8a984914a60d83ba94647af86416c`), retained locally with an expandable original/credit on the final slide. The source was inspected visually before extraction. `body.png`, `rocket.png`, `brimley-foot.png`, `bare-foot.png`, `dog-tail.png` and `speech.png` are polygon-masked crops of the actual artwork. A follow-up alpha cleanup removed only edge-connected near-neutral notebook paper; colored drawing, ink contours and enclosed white features (teeth and speech burst) remain. The cutouts were re-inspected on a contrasting contact sheet and at desktop display size. There are no generated eyes, normal arms or substitute generic mascot. All four sad dogs remain in the tail cutout. Shapes used for small instructional gag props are CSS, not replacement anatomy.

`first-project-mascot.css` keeps the playful stage secondary to the instructions and uses unique props/keyframes per slide: Terminal collision, folder shoe, backward rocket, Brimley Return tap, door squeeze, registry photocopier, AGENTS hat, mistaken ID, skill bookshelf, globe shoe, reachability scanner, failed skill juggle, dog conveyor, BMAD toolkit, butt audit, ruler launch, wrong-foot rocket launch and POOP encore. An IntersectionObserver enables visible-stage motion only. Pause/Resume, reduced-motion, static no-JS and print fallback are all bounded; no audio, flashing or inference dependency is present.

Parent PM performs independent factual/visual review, commit and canonical publication afterward. No source application, live board, service, global activation root or Studio environment was changed.

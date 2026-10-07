---
title: 'iOS release standard across 33GOD projects (plan)'
status: 'proposed'
created: '2026-10-07'
owner: '33god'
governed_by: 'director-rule-plan.md'
proposed_initiative: 'I-5'
---

# iOS release standard across 33GOD projects

> Proposed. Nothing in this document is implemented outside `tower-of-dumb-things`,
> where the reference pipeline shipped TestFlight build 0.2.1 (7) on 2026-10-07.

## Outcome

Any pjangler project whose manifest declares iOS ships to TestFlight with one
command, through the same two self-hosted runners and the same App Store Connect
key, with the same agent skills active, whether it was created yesterday or is a
legacy project being migrated.

## What exists (verified 2026-10-07)

| Piece | State |
| --- | --- |
| Reference pipeline | `tower-of-dumb-things`: `tools/testflight.mjs`, `.github/workflows/testflight.yml`, `docs/testflight.md`, `mise run testflight`. Build 7 is in Owner Testing. |
| Mac runner | `carries-macbook-air`, labels `macOS,xcode,ios-signing`, LaunchAgent in the GUI session without `SessionCreate`, so `codesign` reaches the login keychain. Registered to one repo. |
| Linux runner | `big-chungus`, labels `linux,godot`, systemd unit plus `op.conf` drop-in. Registered to one repo. |
| Credentials | `op://DeLoSecrets/App Store Connect API Key/{key_id,issuer_id,credential}` (Admin key `5MRHBR4678`). |
| Apple team | `YJ7W7Z36FP`; certificates Apple Distribution, Apple Development, Developer ID Application, all in the Mac login keychain. |
| pjangler | `.project.json` is the source of truth; the Postgres index stores unknown top-level manifest keys in `pjangler_extensions` and returns them on read. No platform field exists. 12 projects indexed. |
| Skillex | `all-skills/` catalog (419), reference-only `sets/` and exclusive `packs/`. No iOS release skill. Related: `expo`, `tauri`, `clerk-swift`, `android-kotlin`. |
| Gruvato | Tauri 2.11. iOS is planned (epics NFR8, sprint change 2026-09-26) and unimplemented: no `src-tauri/gen/apple`, no App Store app record. Mac DMG uses its own notarize script. |
| Green in Between | Godot 4.7.2 plus a Rust GDExtension (`gib_godot` framework). `native/tools/render/ios-build.py` (1,123 lines) builds, signs with a development profile and installs to the iPad on the Mac. Bundle `io.lasertoast.greeninbetween.spike`, empty `app_store_team_id`. No App Store app record. |

## Decisions this plan proposes

1. **One shared engine, thin project adapters.** The App Store half (number the
   build, archive, sign, validate, upload, wait, assign testers) is identical for
   every engine. The export half differs. Godot (Tower, Green in Between),
   Tauri (Gruvato), Expo/React Native and native Xcode each get an adapter that
   produces the same artifact: an Xcode project tarball plus `testflight-export.json`.
2. **The engine lives in a new `ios-release` package** consumed as a pinned tool
   (an npm package `@delorenj/ios-release`, installed through mise like Skillex).
   Projects keep only `ios-release.toml` and a 10-line workflow. Tower's
   `tools/testflight.mjs` becomes the package's first code and its own copy is
   retired.
3. **The workflow is a reusable GitHub workflow** in that package's repo,
   `uses: delorenj/ios-release/.github/workflows/testflight.yml@v1`.
4. **Runners move from per-repo to account-level sharing.** A personal account
   cannot host an organization runner group, so either create a `delorenj-mobile`
   organization and transfer the mobile repos (one runner pair for all) or
   register one runner instance per repo on each host (`~/actions-runner/<repo>`,
   same labels). The plan defaults to per-repo instances because it needs no repo
   transfers; the bootstrap script makes adding one a single command.
5. **The manifest declares platforms; everything else is derived.**

## Manifest contract (pjangler owns)

New top-level `.project.json` key, validated by `manifestIndex.ts`:

```json
"platforms": {
  "ios": {
    "engine": "godot",
    "bundle_id": "io.automaticai.towerofdumbthings",
    "app_store_app_id": "6819943259",
    "team_id": "YJ7W7Z36FP",
    "release": "testflight",
    "state": "shipping"
  },
  "android": { "engine": "godot", "package": "io.automaticai.towerofdumbthings" }
}
```

- `engine`: `godot | tauri | expo | xcode`.
- `state`: `planned | bootstrapped | shipping | blocked`, with `blocked_reason`.
- `pj list --platform ios` and `pj info` show the row. The key rides in
  `pjangler_extensions` today; promote it to an indexed column only if queries
  need it (a migration adding `platforms jsonb` plus a GIN index).
- Project-specific build facts that change often (profile name, minimum OS,
  build floor, beta group id) live in the repo's `ios-release.toml`, not in the
  manifest, so the registry does not churn on every signing change.

## Skills (Skillex owns)

| Canonical skill | Contents |
| --- | --- |
| `ios-release` | The standard: architecture, `ios-release.toml` contract, commands, the keychain/`SessionCreate` rule, `errSecInternalComponent` diagnosis, build-number rules, tester groups, App Store Connect API limits. |
| `ios-release-godot` | Godot iOS preset rules (`app_store_team_id`, project-only export, icon alpha, GDExtension xcframework embedding). |
| `ios-release-tauri` | `tauri ios init`, `gen/apple`, signing settings for the generated project. |
| `apple-signing-ops` | Profile/certificate inventory and repair through the API, runner maintenance. |

Set `sets/mobile-ios` = `ios-release` plus the engine skill plus `antislop-layoutmobile`.
It is a **set**, not a pack: packs are exclusive and would replace each project's
existing selection (Gruvato already uses the `product-manager` set).

Selection is derived: pjangler's skills rule adds
`{ "name": "mobile-ios", "include": [...engine members] }` to `.agents/skills.json`
when `platforms.ios` exists, then runs `pj skills sync`. Existing selections and
`inherit_global` are preserved, matching `skills.project-manifest` behavior.

## pjangler surfaces

| Surface | Behavior |
| --- | --- |
| `pj init --platform ios[,android] --engine godot` | Writes `platforms`, renders the `ios-release` subsystem (config, workflow, mise tasks), adds the set, registers runners, records `state: planned` until the app record exists. |
| `pj add ios-release` | Same subsystem for an adopted repo. |
| `pj audit` rule `platform.ios-release` | Fails when `platforms.ios` exists but config, workflow, mise task, skill set, runner registration or 1Password references are missing or drifted. Host checks (runner online, keychain unlocked) are `scope: host` and never gate. |
| `pj migrate platform.ios-release` | Idempotent repair of the project-scoped findings. Never edits signing assets, never creates App Store records, never deletes a project's legacy build script. |
| `pj ios doctor` (via the package) | Live checks: API key, app record, profile, certificate in keychain, runner online, last TestFlight build. |

## Apple automation boundary

Verified against the API on 2026-10-07: `POST /v1/apps` is forbidden
("Allowed operations are: GET_COLLECTION, GET_INSTANCE, UPDATE"). Bundle IDs,
App Store profiles, certificates and beta groups can be created with the key.

So new-app bootstrap is automated except one step: **creating the App Store
Connect app record is a one-time click in the web UI** (name, SKU, bundle ID).
`pj ios doctor` detects the missing record and prints the exact values to enter,
then `pj migrate` finishes the rest (bundle ID, App Store profile, Owner Testing
group, `app_store_app_id` in the manifest).

## Migration of the two legacy projects

**Green in Between** (Godot plus Rust GDExtension):

1. Add `platforms.ios` with `engine: godot`, `state: planned`.
2. Decide the store bundle id. `io.lasertoast.greeninbetween.spike` is a spike id;
   a store id should be final because changing it later orphans installs and saves.
3. Create the app record (one click), then let migrate create the App Store
   profile and group.
4. The Godot adapter needs a pre-export hook: build the Rust framework for
   `aarch64-apple-ios` on the Mac before archive (Linux cannot produce it).
   `ios-build.py` already contains this step; lift it into
   `ios-release.toml` as `[mac].pre_archive`.
5. Keep `ios-build.py` as the development/iPad lane until TestFlight is proven,
   then decide whether to retire it.

**Gruvato** (Tauri 2):

1. iOS does not exist yet, so this is a bootstrap rather than a migration.
   `tauri ios init` on the Mac creates `src-tauri/gen/apple` (commit it).
2. The Tauri adapter runs on the Mac entirely (Rust iOS targets and the Xcode
   project both need macOS); the Linux job only runs tests.
3. Bundle id: desktop is `sh.delo.gruvato`; Android is still the legacy
   `sh.delo.drumjangler`. Pick the iOS id before the first upload
   (recommendation: `sh.delo.gruvato`, matching the accepted desktop decision).
4. Create the app record, then migrate.

## Delivery sequence

| Step | Owner | Proof |
| --- | --- | --- |
| 1. Extract `@delorenj/ios-release` from Tower (engine plus Godot adapter, reusable workflow, runner bootstrap script) | new repo | Tower ships build 8 through the package with its local copy deleted |
| 2. Skills `ios-release`, `ios-release-godot` and set `mobile-ios` | skillex | `skillex topology check` clean; Tower's project sync activates them |
| 3. Manifest `platforms` field, `pj list --platform`, `pj info` row | pjangler | Tower and the two legacy repos show correct rows; reindex is a no-op on rerun |
| 4. `platform.ios-release` audit/migrate rule and `ios-release` subsystem | pjangler | Tower audits clean; a scratch project goes from `pj init --platform ios` to a TestFlight build after one app-record click |
| 5. Green in Between migration | green-in-between | First TestFlight build in Owner Testing; iPad lane still works |
| 6. Tauri adapter plus `ios-release-tauri` skill | ios-release, skillex | Gruvato's first TestFlight build |
| 7. Fleet doctor | pjangler | `pj audit --rules platform.ios-release` across all `platforms.ios` projects returns pass |

Steps 1 to 3 are independent and can run in parallel. Step 5 needs 1 to 4.
Step 6 needs 1 and Gruvato's iOS client work (its own epics).

## Open questions

1. Runner sharing: per-repo runner instances (default here) or a `delorenj-mobile`
   organization with one shared runner pair?
2. Bundle ids for Green in Between and Gruvato iOS.
3. Should Expo/React Native (`intelliforia-mobile`) be in scope now or later?
4. Package home: a new `ios-release` repo, or a directory inside `33GOD`?

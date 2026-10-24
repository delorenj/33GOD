# G5 — build-host proof

**Date:** 2026-10-24. **Host:** Docker Engine 29.2.1, Linux amd64.
**Branch:** `aperture/g5-tooling`. Implementer evidence; independent PM review
and merge are pending. No target-host/arm64 runtime or full project lifecycle
acceptance is claimed. See [DEFERRED.md](DEFERRED.md).

All blocks below are trimmed from actual execution. Source paths are represented
by `GOD_*` variables to keep this artifact portable. Commands were invoked from
the worker checkout, with read-only source checkouts selected by explicit env
vars. The standard shell tool returned empty output (and once reported a wedged
pre-execution guard); actual execution used Python subprocess capture. No
synthetic output or substitute component was used.

## 1. Source discovery / package contracts

Commands: directory enumeration, reads of each package manifest, `npm view
@delorenj/skillex version engines --json`, and Git source receipts.

```text
PJangler sibling checkout: absent
PJangler monorepo child: @delorenj/pjangler 1.5.18, node >=24
PJangler pyproject.toml: absent
Skillex package.json: @delorenj/skillex 0.3.1, node >=24
npm registry: {"version":"0.3.1","engines":{"node":">=24"}}
Skillex mcp-servers directory entries: ["codegraph-voyage-mcp"]
MCP servers present: 1
MCP project script: codegraph-voyage-mcp = codegraph_voyage_mcp.server:main
Skillex historical skill-sets/global: absent
Current registry directories: all-skills, sets, packs
```

Node 24 images deliberately replace impossible Python-PJangler / Node-20 recipes.
The cited “no fake server” directive is supplied binding context; its exact
sentence is absent from current tracked Markdown. The platform runtime README
and PJangler component YAML independently describe run-only tools/no listener.

## 2. Bake config and cold build

Commands (both exit 0):

```sh
docker buildx bake --print
docker buildx bake --allow="fs.read=$GOD_PJANGLER_CONTEXT" \
  --allow="fs.read=$GOD_MCP_CONTEXT" --no-cache \
  --set '*.platform=linux/amd64' --load --progress=plain
```

Rendered plan (context paths omitted; targets/tags/platforms retained):

```json
{
  "targets": {
    "mcp-codegraph": {
      "dockerfile": "Dockerfile.mcp-codegraph",
      "tags": [
        "god-g5-mcp-codegraph:0.1"
      ],
      "platforms": [
        "linux/amd64",
        "linux/arm64"
      ]
    },
    "pjangler": {
      "dockerfile": "Dockerfile.pjangler",
      "tags": [
        "god-g5-pjangler:0.1"
      ],
      "platforms": [
        "linux/amd64",
        "linux/arm64"
      ]
    },
    "skillex": {
      "dockerfile": "Dockerfile.skillex",
      "tags": [
        "god-g5-skillex:0.1"
      ],
      "platforms": [
        "linux/amd64",
        "linux/arm64"
      ]
    }
  }
}
```

Real no-cache build output (trimmed):

```text
#24 writing image sha256:cce162e939966750386fd797a02d4548eea3f9744ff58fc4574da13664168d76 done
#24 naming to docker.io/library/god-g5-skillex:0.1 done
#28 0.172 ⚡ Done in 20ms
#26 2.586 Successfully installed uv-0.13.5
#34 writing image sha256:4cc1fb7b5dd65028f88ce3379624e5af1d82cb08944bb79a8208e3828d70ce84 done
#34 naming to docker.io/library/god-g5-pjangler:0.1 done
#39 writing image sha256:966630ed4d95c1a97afb67c828a8ccd8718e211b312dee4c924cee9d0e95ba6a done
#39 naming to docker.io/library/god-g5-mcp-codegraph:0.1 done
build exit: 0
```

Local image IDs after that build, from `docker image inspect` (not registry
publication digests):

```json
[
  {
    "image": "god-g5-pjangler:0.1",
    "id": "sha256:4cc1fb7b5dd65028f88ce3379624e5af1d82cb08944bb79a8208e3828d70ce84",
    "arch": "amd64",
    "user": "node",
    "entrypoint": [
      "pj"
    ],
    "size_bytes": 265361160
  },
  {
    "image": "god-g5-skillex:0.1",
    "id": "sha256:cce162e939966750386fd797a02d4548eea3f9744ff58fc4574da13664168d76",
    "arch": "amd64",
    "user": "node",
    "entrypoint": [
      "skillex"
    ],
    "size_bytes": 238011870
  },
  {
    "image": "god-g5-mcp-codegraph:0.1",
    "id": "sha256:966630ed4d95c1a97afb67c828a8ccd8718e211b312dee4c924cee9d0e95ba6a",
    "arch": "amd64",
    "user": "tool",
    "entrypoint": [
      "codegraph-voyage-mcp"
    ],
    "size_bytes": 192826182
  }
]
```

## 3. Complete smoke / CLI + stdio + template roundtrip

Command: `./smoke/smoke.sh`; **exit 0**. Rebuilds all three tool images before
checking execution. Containers have no external network during runtime checks.

```text
Build: 3 tool images loaded
Bake plan: 3 targets, each linux/amd64 + linux/arm64
god-g5-pjangler:0.1 --help: exit 0
Container: published host ports=0, network=none
Image: user=node entrypoint=["pj"] exposed=0 published=0
god-g5-skillex:0.1 --help: exit 0
Container: published host ports=0, network=none
Image: user=node entrypoint=["skillex"] exposed=0 published=0
god-g5-mcp-codegraph:0.1 --help: exit 0
Container: published host ports=0, network=none
Image: user=tool entrypoint=["codegraph-voyage-mcp"] exposed=0 published=0
1.5.18
0.3.1
MCP initialize: {"name": "codegraph-voyage", "version": "0.1.0"}
MCP tools/list: explore, index, search, semantic_candidates, status
MCP EOF: exit 0
CommonProject: copier.yml + project template present; mount is read-only
artifact scan: 15 files, zero forbidden-marker hits
artifact taxonomy: 3 real tool entrypoints, no Compose, no daemon command, no port instruction
PASS: G5 smoke; run-only artifacts, zero published host ports
smoke exit: 0
```

The executable really answers initialize with `serverInfo`, then tools/list
with the five tools, and exits at stdin EOF. This is **a real MCP handshake**,
using the installed SDK's newline-delimited JSON-RPC (not legacy Content-Length
framing). It is not an import-only check and does not claim actual embeddings,
index/search results, or any deployed agent-host attachment.

The CommonProject mount uses the real source at the exact in-image location
PJangler expects. The check reads `copier.yml`, the project template, and kernel
mount flags. It does not execute template tasks or write output/source state.

## 4. All external base manifests

Command for each exact ref: `docker buildx imagetools inspect "$ref" --raw`.
The smoke parses the manifest index, separately asserts each platform and its
recorded digest, ignoring unknown/unknown attestations. **Both checks exit 0.**
Every Dockerfile `FROM` reference equals an entry in `base-images.json`.

```text
node:24.6.0-bookworm-slim@sha256:9b741b28148b0195d62fa456ed84dd6c953c1f17a3761f3e6e6797a754d9edff
  linux/amd64 sha256:527e3f1e925c5727a98b17575e68d0bb0b577965bf3b60330790bfcf8a0b3035
  linux/arm64 sha256:798837daa2a12bab9cdf53cf8779a05256c2ce08176f449e239e7577d26225e8
python:3.12.12-slim-bookworm@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c
  linux/amd64 sha256:2986c55feb36e6cae00fa1fefb454283e4b33f35e75ff8bdd123b134130be301
  linux/arm64 sha256:228390eced221ad2986a3dd77e10b1accca6ba8ceb36f1572de1b346a337cc1a
```

amd64 images were built/executed; arm64 **manifest support only** was verified.

## 5. Zero ports, no pretend service, artifact scan

The smoke creates then inspects one disposable container per tool. Each has
`HostConfig.PortBindings` empty, `PublishAllPorts=false`, and no bound runtime
ports; each is removed. Image configs expose no ports and select a non-root
user. All runtime commands omit publication and detachment flags. Bake has no
service/port schema. `smoke/audit.py` checks all group files, no exclusions,
for seven forbidden credential/host markers; it also checks exact real tool
entrypoints, no Compose document, no listener/keepalive command or port
instruction in any Dockerfile. Expected taxonomy language is asserted too.
The successful scan above covers this proof and the review handoff as well.

Additional image-content checks (each exit 0):

```text
PJangler: no source Git, env, templates or user config copied
Skillex: CLI only, no host config or registry payload
MCP: no source Git, host venv, project DB or user config copied
```

Negative checks (not in the real bundle):

```text
GOD_PLATFORM=linux/notreal ./smoke/smoke.sh
unsupported smoke platform
exit: 1

Injected forbidden credential-prefix marker into a disposable scratch copy:
AssertionError: [('injected.txt', 2)]
exit: 1
```

The audit intentionally constructs marker strings from fragments, so its own
source does not contain a forbidden literal. All actual group bytes are scanned,
including README/PROOF and the scanner. The failed negative copy was not shipped.

## 6. Upstream MCP unit tests

Executed the existing tests against the **image-installed** server package;
read-only source-test bind, disposable tmpfs venv, no source writes. Command:

```sh
docker run --rm --tmpfs /work:rw,uid=10001,gid=10001,mode=700 -e TMPDIR=/work \
  --mount "type=bind,src=$GOD_MCP_CONTEXT/tests,dst=/upstream-tests,readonly" \
  --entrypoint sh god-g5-mcp-codegraph:0.1 -ec '
python -m venv --system-site-packages /work/tests-env
uv pip install --python /work/tests-env/bin/python pytest==8.4.2 pytest-asyncio==1.2.0
/work/tests-env/bin/python -m pytest -q -p no:cacheprovider --basetemp=/work/pytest /upstream-tests'
```

```text
.........                                                                [100%]
9 passed in 0.62s
exit: 0
```

These tests include real validation/rejection paths and mocked semantic
subprocesses. No claim is made that the two upstream Node projects' entire test
suites were executed; their source is unchanged and this artifact proof covers
in-image execution only. PM may run their broader suites independently.

## 7. No production harm / exact source preservation

Commands before **and** after all builds/tests:
`git rev-parse HEAD` and `git status --porcelain=v1 --untracked-files=all`
in each actual source checkout. Literal JSON strings preserve whitespace.
No source installation/build/test wrote into those checkouts; existing ignored
host state was not mounted into the tool images. No stack was stopped/started.

```text
pjangler: HEAD aa93868de6700298ab4350a2a3173ce661980577
  before status: ""
  after status:  ""
  unchanged: true
skillex: HEAD 05209a23163e9ef7c8ad2dc98144d94aacbf7a5f
  before status: " M all-skills\n"
  after status:  " M all-skills\n"
  unchanged: true
CommonProject: HEAD de7a78b242d7ba16bbcb65789032c111f6b31d71
  before status: "?? template/mise.toml\n"
  after status:  "?? template/mise.toml\n"
  unchanged: true
```

Thus “untouched” is accurate; “all source repos clean” would not be. Existing
Skillex catalog dirt and CommonProject's untracked file predate this work.
The tool images and BuildKit cache are the only retained Docker artifacts;
no G5 runtime container, named volume, or network is left behind.

## 8. Independent review boundary

[REVIEW.md](REVIEW.md) gives the PM a bounded review prompt. Worker branch is
pushed, not merged. Publication, native arm64 execution, real project creation,
skill execution, notebook readback, and attached bus/recipient gates remain
unproven as listed in DEFERRED.md. Artifact smoke must not turn those into green
ship-board claims.

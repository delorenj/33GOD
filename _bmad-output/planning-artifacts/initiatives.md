---
title: '33GOD initiatives (integration work that spans children)'
governed_by: 'director-rule-plan.md'
created: '2026-09-29'
---

<!-- The parent holds outcomes that span children, never work inside one.
     NOT epics.md: keys here are I-n / I-n.m on purpose. bmad-loop only parses
     `epic-<digits>` and `<digits>-<digits>-<slug>`, so nothing in this file can be
     dispatched as code. Do not paste these into a sprint-status.yaml.
     Refer to child work only as `<project>:<key>` or a ticket ref (FLUME-12).
     Status is derived from the boards and events, never typed here. -->

# Initiatives

## I-1 Flume agent rollout throughout the system

**Outcome.** Every pjangler-registered project has a declared post held by a named
agent, the workforce is visible on the bus and in `/hq`, and a named specialist can be
invoked with no repo present.
**Owner:** `33god` (Grolf). Implementation is owned by the children named in each
story's delegations. The full story list (I-1.1 to I-1.8) is in
`director-rule-plan.md`; only the two below are authored so far.

### I-1.1 Flume and PJangler seam

```yaml
owner_project: 33god
delegations:
  - owner_project: pjangler
    request: pj audit and flume review agree on the same repo
  - owner_project: flume
    request: roster derives every PM post from the pjangler registry
depends_on: []
```

**Seam acceptance criteria**

- For any project registered in pjangler, `flume roster` shows its PM post with zero
  hand-maintained fields.
- `pj audit` and `flume review` agree on the same repo.
- The two binaries share only the handbook contract; neither imports the other.

**Seam evidence (executable).** Run `pj list` and `flume roster --json`; diff the
project ids and post states. Run `pj audit <repo>` and `flume review <repo>` for one
repo and compare findings on the fields both report.

### I-1.6 Company projection sourced from Flume

```yaml
owner_project: 33god
delegations:
  - owner_project: flume
    request: expose one company snapshot with a freshness envelope
  - owner_project: holocene
    request: build the /hq company view from that snapshot
depends_on: [I-1.1]
```

Resolves the transport decision deferred in the architecture spine (AD-5): how Flume
publishes the company projection, and retiring `org.yaml` as the hierarchy source. It
is the seam half of the former Story 1.3.

**Seam acceptance criteria**

- The `/hq` company view is built from one Flume snapshot carrying a freshness
  envelope.
- Hierarchy is no longer read from `org.yaml`.
- A change in Flume appears in `/hq` within the declared maximum age.

**Seam evidence (executable).** Change a post in Flume; measure the time until the
`/hq` API reflects it; assert it is under the declared maximum age and that
`org.yaml` is not opened during the request.

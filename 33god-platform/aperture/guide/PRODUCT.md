# 33GOD Field Guide — product record

<!-- impeccable:product-schema 1 -->

## Platform
web

## Users
Damian, a non-engineer cofounder and dogfood partner, reads a standalone static guide to understand the stack before hands-on setup. Other future readers may use its modular chapters. No assumption that the reader has command-line access.

## Product Purpose
Explain 33GOD's components as an approachable, accurate sequence of field-guide modules. This first module teaches the project identity and registry layer through PJangler, rather than claiming to operate the reader's environment. A successful reader can distinguish a project's source identity from its index, explain what CommonProject prepares, and see where fleet tools take over.

## Positioning
The guide uses a clearly synthetic project dossier to trace one stable project identity from its manifest through an indexed directory into several consumers. It separates ownership boundaries instead of flattening the stack into one platform switch.

## Operating Context
Standalone HTML, no backend, no external assets or network calls. The canonical eight Aperture domains organize future coverage, but the learning sequence begins at project tooling (G5), not installation order. Commands are illustrative and never execute from the page. Rererere alone acts on Damian's machine.

## Capabilities and Constraints
This release is one PJangler page with local CSS and optional enhancement JS, reusable tokens and shell for later modules. The registry index is rebuildable from registered manifests, not automatic filesystem discovery. Agent staffing is Flume's authority, not PJangler's. Do not expose real private manifests, identifiers, secrets, client data, or deployment instructions. No live status inference from an educational static page. Commercial choices belong to Jarad. A public guide must distinguish historical acceptance evidence from live acceptance.

## Brand Commitments
33GOD and PJangler names; plain-spoken, peer-to-peer voice. The guide now uses the same split-circle geometry as the live Holocene top-left 33GOD mark, bundled locally in inverse-header off-white/coral colors for contrast on cobalt. Its accompanying "33GOD FIELD GUIDE" text identifies this standalone chapter series, not the Holocene app. The operator explicitly authorized a new 33GOD guide design system rather than copying existing dashboard styling. Avoid stock SaaS cards, dark neon, or cream-serif editorial defaults.

## Evidence on Hand
Verified local sources: `pjangler/docs/project-registry.md`, PJangler CLI help from `pjangler/dist/index.js`, `.agents/skills/projects/SKILL.md`, `.agents/skills/project-jangler/SKILL.md`, and Aperture README's canonical group taxonomy. Registry clean Linux acceptance was reported for published npm 1.5.18 as of 2026-10-27; Studio/macOS and repeated-create acceptance remain pending. This is a dated report, not a service query.

## Product Principles
- Show a project before explaining architecture.
- Make every boundary legible: manifest / index, template / generated files, project tooling / fleet.
- Keep operations optional, explicit, and non-executing.
- Teach through the canonical eight domains without conflating learning order and deployment order.

## Accessibility & Inclusion
Semantic reading order and navigation, visible keyboard focus, readable contrast, responsive layout at 390px and zoom, print access, reduced-motion support. Core explanation works without JavaScript.

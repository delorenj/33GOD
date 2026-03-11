# CRANK_ENGINE Pickup: OWRLD-35 (Map Export PNG/SVG with Watermark)

**Date:** 2026-03-10 23:45 EDT  
**Assignee:** Grolf (eng) - IC fallback due to session locks  
**Ticket:** OWRLD-35

## Pickup Reason
CRANK_ENGINE dispatch at 23:39 ET requested highest-leverage unblocked lasertoast ticket. All ICs (bub, family, har, etc.) have session locks (pid=206865). Per directive fallback: assign to self if no IC free.

## Ticket Details
- **ID:** OWRLD-35
- **Name:** Map Export (PNG/SVG with Watermark)
- **Project:** Overworld (lasertoast/33god)
- **State:** Todo (unassigned)

## First Concrete Action
Research canvas/SVG export libraries for Next.js (html2canvas, dom-to-image, svg2png). Document technical approach in GOD-13-tech-spec.md.

## ETA
30 minutes (by 00:15 ET)

## Related
- Overworld repo: implementation target
- Watermark: overlay on exported images
- Formats: PNG (raster) + SVG (vector)

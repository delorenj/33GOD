#!/bin/sh
# One-shot first boot only. Never import/export credentials or overwrite user work.
set -eu
marker=/home/node/.n8n/.g2-workflows-v1-imported
if [ -f "$marker" ]; then
  printf '%s\n' 'G2 workflows already imported; skipping (no workflow overwrites)'
  exit 0
fi
n8n import:workflow --separate --input=/bundle/workflows
# Imports are inactive. Activate ONLY the synthetic smoke endpoint before start.
n8n update:workflow --id=apertureG2Smoke01 --active=true
touch "$marker"
printf '%s\n' 'G2 fresh workflows imported; smoke only active, templates inactive'

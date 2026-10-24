# G2 acceptance gate — "the client ships his first workflow"

Run this on the DEPLOYED system (Damian's Studio or the build host).
Everything is client-executable: no upstream repo, no host tools.

## The task (the client does this)

1. **Import the template** (if not already there):
   `docker compose exec n8n n8n import:workflow --separate --input=/bundle/accept`
   — the file is also at `accept/04-client-form-template.json` in the bundle.
   Note: import DEACTIVATES workflows on n8n 1.120.4 (verified) — that's fine,
   the client activates next.
2. **Open the n8n UI** (the deployed instance). Find "Aperture G2 — client
   form note (ACCEPTANCE TEMPLATE)".
3. **Make it YOURS**: rename the form title, edit the dropdown options (add
   your own moods), change the note field label — anything. The template's
   code requires only that a `note` (text) and `mood` (dropdown) field exist.
4. **Activate it.**
5. **Open the form URL n8n shows**, fill in a real note (your own words),
   pick a mood, submit.

## The checks (run from g2/ in a terminal — or let the form's response page be step 1 evidence)

- [ ] **Your values arrive in the bus**: `GET /latest` on the outbox shows a
      `bloodbank.studio.note.recorded` event whose `data.note` and `data.mood`
      are EXACTLY what you typed (in attached mode: query the G1 candystore
      `/events/<id>/raw` for the id in the publish response).
- [ ] **The workflow is real n8n state**: `docker compose exec n8n n8n
      export:workflow --id=apertureG2ClientForm01` returns your edited graph.
- [ ] **The rejection path still holds on YOUR deployment**:
      `curl -s -o /dev/null -w '%{http_code}' -X POST
      http://localhost:<n8n>/webhook/<your-form-path> -d '{}'` → **401**
      (missing demo header). And with the header but junk body → the code
      node throws (400/500) — errors are visible, not silent.
- [ ] **No ghost deliveries**: deactivate the workflow, submit the form
      again → no new event in `/latest` (sequence unchanged). Reactivate.
- [ ] **Execution history**: n8n UI shows your submission as a succeeded
      execution of YOUR workflow.

## PASS

All five checks green = G2 client gate PASSED. File the trimmed outputs
(the `/latest` JSON, the 401 curl, the unchanged sequence) under
`aperture/acceptance/g2/` with a screenshot of your edited workflow.

## Build-host note (PM) — allowlist implemented

The outbox now carries an explicit two-entry allowlist (smoke +
studio-note, both canonical 4/5-token pairs); anything else is rejected
with 400. Publish path routes to the event's own subject (was: hardcoded
smoke subject — caught and fixed during gate proving). `/latest?subject=`
serves either allowlisted subject. Verified: 8/8 unit tests, standalone
smoke PASS, note → own subject seq ack, non-allowlisted subject → 400,
no-header → 401. Still NOT a general ingress — widening further is a
reviewable change.

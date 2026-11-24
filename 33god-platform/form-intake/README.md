# form-intake

One form backend for every page we host. Any page on a `*.delo.sh` site can `POST /_forms/<form>`
to its own origin; a site we host somewhere else posts cross-origin to
`https://forms.delo.sh/_forms/<form>` (see "Sites off delo.sh"). There is no per-site backend and
no third-party form service.

```
page ──POST /_forms/briefing──▶ Traefik (form-intake.yml, every *.delo.sh host, priority 1100)
                                   │
                                   ▼
                     form-intake (systemd user service, 172.17.0.1:18811)
                       1. store   → ~/.local/state/form-intake/forms.db  (SQLite)
                       2. publish → bloodbank.messaging.webform.received  (bb emit --strict)
                                       ├─▶ Candystore (durable audit)
                                       └─▶ ntfy router (a push to the phone)
```

The row is written before the event is published, so a bus outage loses nothing: the row stays
`emitted = 0` with the error, and `form_intake.py replay` re-emits it.

## Use it from a page

Load `33god-platform/overnight/site/forms.js` (copy it, or serve it), then:

```js
G33Forms.submit('briefing', { email: 'a@b.co' }).then(function (r) {
  if (r.ok) { /* thanks */ } else { show(r.error); }   // r.error is written for a person
});
```

Or post a plain HTML form (urlencoded works too):

```html
<form method="post" action="/_forms/contact">
  <input name="email" type="email" required> <textarea name="message"></textarea>
  <input name="_hp" tabindex="-1" autocomplete="off" style="position:absolute;left:-9999px">
</form>
```

Rules: field values are strings, up to 40 fields of 4000 chars, body up to 16 KiB; `email` must
look like an address when present; names starting with `_` are not stored (`_hp` is the honeypot:
filled in, the request gets a fake 201 and nothing is kept); 8 submissions per IP per 10 minutes
(the IP is Cloudflare's `CF-Connecting-IP`). The site is the `X-Forwarded-Host`; only hosts
matching `FORM_INTAKE_SITES` (default `*.delo.sh`) are accepted.

## Sites off delo.sh (CORS)

A site we host outside `*.delo.sh` (the AutomaticAI store on Cloudflare Pages is the first) posts
JSON to `https://forms.delo.sh/_forms/<form>`. `forms.delo.sh` is a dedicated host: the `forms`
router in `form-intake.yml` sends the whole host here, and it reaches us like every `*.delo.sh`
name (Cloudflare wildcard DNS, the tunnel, Traefik).

- `FORM_INTAKE_CORS_ORIGINS` (set in `form-intake.service`) lists the exact origins allowed, e.g.
  `https://store.automaticai.io`. Add a site there, `systemctl --user daemon-reload`, restart.
- `OPTIONS /_forms/<form>` from a listed origin answers `204` with
  `Access-Control-Allow-Origin: <that origin>`, `Allow-Methods: POST`, `Allow-Headers: content-type`,
  `Max-Age: 86400`; every POST answer to it (errors too) carries `Access-Control-Allow-Origin`, so
  the page can show the error. Any other origin gets `403` and no CORS headers.
- The row's `site` is the listed Origin's host (`store.automaticai.io`), never the endpoint host.
- A POST whose Origin is another host and is not listed is refused with `403`, preflight or not
  (a plain `<form>` post skips the preflight). That includes one `*.delo.sh` page posting to another.
- `Origin: null` is refused with `403` on every host. It is an opaque origin (a sandboxed iframe, a
  `file:` or `data:` page), which any third-party page can make; none of our pages ever sends it.
- No `Origin` or an Origin on the request's own host is same-origin: unchanged on every `*.delo.sh`
  site. The exception is the hosts in `FORM_INTAKE_CORS_HOSTS` (default `forms.delo.sh`): they serve
  no pages, so they take only a listed Origin, and no row is ever stored under their own name.
- The Bloodbank event for a row from such a site carries **no address**: only field values that look
  like an id (`product=heyma`) are published, and every other field is named in `withheld`
  (`sender.handle` is `anonymous`). Candystore keeps every event and ntfy caches the push, and those
  sites promise deletion on request, so the SQLite row is the only copy and `delete` really removes it.
  `*.delo.sh` rows publish every field, as before.
- **No JavaScript:** a plain HTML form post (urlencoded, `Sec-Fetch-Mode: navigate`) from a listed
  Origin is answered `303` back to that origin, never JSON: `Location: <origin><_back>#<form>-saved`
  (or `#<form>-error`). `_back` is an optional hidden field holding the page path (`/heyma/`); under
  the default referrer policy the browser's Referer is only the origin. A `_back` that is not a plain
  path falls back to the Referer's path on that origin, then to `/`. Script callers (JSON, or
  `Sec-Fetch-Mode: cors`) get JSON as before.

```bash
curl -si -X OPTIONS https://forms.delo.sh/_forms/store-notify -H 'Origin: https://store.automaticai.io' \
  -H 'Access-Control-Request-Method: POST' -H 'Access-Control-Request-Headers: content-type'
```

## Read and delete what came in

```bash
FI=~/code/33GOD/33god-platform/form-intake/form_intake.py
python3 $FI list                                    # newest first, with each row's id
python3 $FI list --form briefing --json
python3 $FI list --site store.automaticai.io --form store-notify --field product=heyma --emails   # each address once, oldest first
python3 $FI delete --email someone@example.com      # a deletion request: every row with that address
python3 $FI delete --site store.automaticai.io --form store-notify --field product=heyma   # a list that has been used
python3 $FI delete --id <id>                        # one row (a test)
python3 $FI replay                                  # re-emit rows the bus missed
```

Always pass `--site` for a send list: a row posted to `/_forms/store-notify` on some other host is
stored under that host, and `--site store.automaticai.io` keeps it off the list. The store's
`mise run deploy` runs `notify-guard`, which refuses a deploy while a product that is already on sale
still has sign-ups waiting (see the store README). `delete` refuses to run without a filter. Each row holds the fields, the time, the page address
(`Referer`), the IP and the browser's user-agent; the store's privacy page says so.

## Run it

```bash
systemctl --user link ~/code/33GOD/33god-platform/form-intake/form-intake.service
systemctl --user enable --now form-intake
curl -s https://33god.delo.sh/_forms/health
```

The Traefik route lives in DeLoContainers: `~/docker/core/traefik/traefik-data/dynamic/form-intake.yml`.
Tests: `pytest tests/test_form_intake.py` (real handler, temp DB, stub `bb`; CORS allowlist,
preflight, cross-origin and `null` refusals, the endpoint-only host, same-origin unchanged, no address
on the bus for off-site rows, the no-JS `303`, list/delete).

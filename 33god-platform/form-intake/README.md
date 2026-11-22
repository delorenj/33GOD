# form-intake

One form backend for every page we host. Any page on a `*.delo.sh` site can `POST /_forms/<form>`
to its own origin; there is no CORS, no per-site backend and no third-party form service.

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

## Read what came in

```bash
python3 ~/code/33GOD/33god-platform/form-intake/form_intake.py list               # newest first
python3 ~/code/33GOD/33god-platform/form-intake/form_intake.py list --form briefing --json
python3 ~/code/33GOD/33god-platform/form-intake/form_intake.py replay             # re-emit rows the bus missed
```

## Run it

```bash
systemctl --user link ~/code/33GOD/33god-platform/form-intake/form-intake.service
systemctl --user enable --now form-intake
curl -s https://33god.delo.sh/_forms/health
```

The Traefik route lives in DeLoContainers: `~/docker/core/traefik/traefik-data/dynamic/form-intake.yml`.
Tests: `pytest tests/test_form_intake.py` (real handler, temp DB, stub `bb`).

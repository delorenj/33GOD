/* forms.js: the client half of form-intake (33god-platform/form-intake).
 *
 * Every *.delo.sh site has POST /_forms/<form> on its own origin (Traefik routes it to the one
 * form-intake service, which stores the submission and announces it on Bloodbank). Any page can
 * load this file and call:
 *
 *   G33Forms.submit('briefing', { email: 'a@b.co' }).then(function (r) { ... })
 *
 * The promise always resolves to { ok: true, id } or { ok: false, error } with an error a person
 * can read; it never rejects. Fields are strings; names starting with '_' are page metadata and
 * are not stored, and '_hp' is the honeypot (leave it empty).
 */
(function (root) {
  'use strict';
  function submit(form, fields) {
    var body = {};
    Object.keys(fields || {}).forEach(function (k) { if (fields[k] != null) body[k] = String(fields[k]); });
    body._page = root.location ? root.location.pathname : '';
    return fetch('/_forms/' + encodeURIComponent(form), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      credentials: 'same-origin'
    }).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (j) {
        if (res.ok && j.ok) return { ok: true, id: j.id };
        return { ok: false, error: j.error || ('That did not go through (' + res.status + '). Try again in a minute.') };
      });
    }, function () {
      return { ok: false, error: 'Could not reach the server. Check your connection and try again.' };
    });
  }
  root.G33Forms = { submit: submit };
})(typeof window !== 'undefined' ? window : this);

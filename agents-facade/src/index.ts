/**
 * agents-facade — edge identity facade (FLUME-48) + employee mailbox ingress (FLUME-49).
 *
 * FLUME-48: identity.delo.sh sits behind Cloudflare Access. The authoritative
 * verifier is `flume access serve` (flume-hr, workforce/access.ts) — this Worker
 * is the edge seam. It refuses direct-origin calls on the access path with the
 * same refusal codes the facade uses, and proxies to the facade origin once one
 * is provisioned (ACCESS_FACADE_ORIGIN). Until then the access path answers 501:
 * honest about what is not live yet.
 *
 * FLUME-49: mail to an enrolled <handle>@agents.delo.sh address is stored RAW in
 * the MAILBOX R2 bucket. Per the story, "raw-mail content is mailbox storage,
 * not a second event ledger" — nothing here parses for action, forwards to the
 * agent bus, or lets mail content trigger grants, links or tasks. Dedupe is by
 * content hash (Message-ID is attacker-controlled); unknown recipients and
 * oversize mail are rejected at SMTP time with setReject, so no false
 * "accepted" receipt exists. A failed store throws (transient) so delivery is
 * retried rather than lost or falsely acknowledged.
 */

// Optional provisioning seam, set when the live facade origin exists.
// (declare global: merges with the cf-typegen Env instead of shadowing it.)
declare global {
	interface Env {
		ACCESS_FACADE_ORIGIN?: string;
	}
}

const ACCESS_REQUEST_PATH = '/v1/access/requests'; // flume-hr ACCESS_REQUEST_PATH
// FLUME-53: employee-authenticated mail read. The Worker owns the R2 binding; the
// flume access facade (the origin) owns identity and employment status. The Worker
// asks the origin who the verified employee is and whether they are active, and
// reads ONLY that employee's prefix. Nothing in the request selects a mailbox.
const MAIL_MESSAGES_PATH = '/v1/mail/messages';
const MAIL_AUTHORIZE_PATH = '/v1/mail/authorize'; // flume-hr MAIL_AUTHORIZE_PATH
const MAIL_DOMAIN = 'agents.delo.sh';
const HANDLE = /^[a-z0-9][a-z0-9_-]{0,57}$/u;
const MESSAGE_ID = /^[0-9a-f]{64}$/u;
const MAX_MAIL_REQUEST_BYTES = 1024;
const MAIL_LIST_LIMIT = 100;
const DEFAULT_MAX_MESSAGE_BYTES = 10 * 1024 * 1024;

function refusal(status: number, code: string, detail: string): Response {
	return Response.json(
		{ ok: false, status: 'error', code, detail },
		{ status, headers: { 'cache-control': 'no-store' } },
	);
}

async function sha256Hex(data: ArrayBuffer): Promise<string> {
	const digest = await crypto.subtle.digest('SHA-256', data);
	return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

/**
 * The routing projection lives in KV as `allowlist/<address>` keys written by
 * `flume identity provision` (FLUME-56): hiring never redeploys this worker.
 * A KV failure throws — transient, so delivery is retried rather than a mail
 * being falsely accepted or silently dropped on an infrastructure hiccup.
 */
async function allowlisted(env: Env, address: string): Promise<boolean> {
	const entry = await env.MAILBOX_ALLOWLIST.get<{ handle: string }>(`allowlist/${address.trim().toLowerCase()}`, 'json');
	return entry !== null && typeof entry.handle === 'string';
}

function logMail(event: string, fields: Record<string, unknown>): void {
	// Receipt lines for `wrangler tail` / Workers Logs: IDs and outcomes, never content.
	console.log(JSON.stringify({ event, at: new Date().toISOString(), ...fields }));
}

interface MailAuthorization { ok?: boolean; status?: string; handle?: string; subject?: string; run_id?: string; harness?: string }

/**
 * FLUME-53 mail read. Order matters and nothing is read before step 4:
 * 1. POST only, an Access assertion present (the origin re-verifies it), origin provisioned.
 * 2. Bounded, closed request body: {operation: list|read, message_id?: sha256 hex}.
 * 3. The origin decides identity and employment status. Any non-authorized answer
 *    (suspended, retired, unknown client, bad run) is returned to the caller unchanged and
 *    NOTHING is read from storage.
 * 4. The allowlist projection must still hold the employee's address: suspension removes
 *    that key, so a mailbox whose projection is gone is closed even if the origin were stale.
 * 5. Only `mail/<handle>/` of the AUTHENTICATED handle is listed or read.
 * Mail is data: it is returned, never parsed, followed or acted on, and never logged.
 */
async function readMail(request: Request, env: Env): Promise<Response> {
	if (request.method !== 'POST') return refusal(405, 'method-not-allowed', 'POST only');
	if (!request.headers.get('cf-access-jwt-assertion')) {
		return refusal(401, 'missing-assertion', 'no Cloudflare Access assertion; mail is readable only through Access');
	}
	if (!env.ACCESS_FACADE_ORIGIN) {
		return refusal(501, 'facade-not-provisioned', 'the access facade origin is not provisioned');
	}
	const text = await request.text();
	if (new TextEncoder().encode(text).byteLength > MAX_MAIL_REQUEST_BYTES) return refusal(413, 'request-too-large', 'mail request body exceeds the limit');
	let parsed: { operation?: unknown; message_id?: unknown };
	try { parsed = JSON.parse(text); } catch { return refusal(400, 'invalid-request', 'body must be JSON'); }
	if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) return refusal(400, 'invalid-request', 'body must be an object');
	const extra = Object.keys(parsed).filter((k) => k !== 'operation' && k !== 'message_id');
	if (extra.length) return refusal(400, 'invalid-request', `unknown field: ${extra[0]}`);
	if (parsed.operation !== 'list' && parsed.operation !== 'read') return refusal(400, 'invalid-request', 'operation must be list or read');
	if (parsed.operation === 'read' && !(typeof parsed.message_id === 'string' && MESSAGE_ID.test(parsed.message_id))) {
		return refusal(400, 'invalid-request', 'read requires message_id: a 64-hex content hash');
	}
	if (parsed.operation === 'list' && parsed.message_id !== undefined) return refusal(400, 'invalid-request', 'list takes no message_id');

	const upstream = new URL(MAIL_AUTHORIZE_PATH, env.ACCESS_FACADE_ORIGIN);
	const authorize = await fetch(new Request(upstream, { method: 'POST', headers: request.headers, body: text }));
	let auth: MailAuthorization;
	try { auth = (await authorize.json()) as MailAuthorization; } catch {
		return refusal(502, 'bad-origin-response', `the access facade answered HTTP ${authorize.status} without JSON`);
	}
	if (authorize.status !== 200 || auth.status !== 'authorized') {
		// Pass the facade's own refusal through unchanged; storage was never touched.
		return Response.json(auth, { status: authorize.status === 200 ? 403 : authorize.status, headers: { 'cache-control': 'no-store' } });
	}
	const handle = auth.handle;
	if (typeof handle !== 'string' || !HANDLE.test(handle)) return refusal(502, 'bad-origin-response', 'the access facade returned no valid handle');

	if (!(await allowlisted(env, `${handle}@${MAIL_DOMAIN}`))) {
		logMail('mail.read.denied', { handle, reason: 'mailbox-closed', run_id: auth.run_id ?? null });
		return Response.json({ ok: false, status: 'denied', code: 'mailbox-closed', detail: 'the mailbox allowlist entry is absent; the mailbox is closed to reads until the employee is restored' }, { status: 403, headers: { 'cache-control': 'no-store' } });
	}

	const prefix = `mail/${handle}/`;
	const correlation = { handle, subject: auth.subject ?? null, run_id: auth.run_id ?? null, harness: auth.harness ?? null };
	if (parsed.operation === 'list') {
		const messages: Array<Record<string, unknown>> = [];
		let cursor: string | undefined;
		do {
			const page = await env.MAILBOX.list({ prefix, limit: MAIL_LIST_LIMIT, cursor, include: ['customMetadata'] });
			for (const object of page.objects) {
				messages.push({
					id: object.key.slice(object.key.lastIndexOf('/') + 1).replace(/\.eml$/u, ''),
					size: object.size,
					received_at: object.customMetadata?.['received-at'] ?? object.uploaded.toISOString(),
					from: object.customMetadata?.from ?? null,
					subject: object.customMetadata?.subject ?? null,
				});
			}
			cursor = page.truncated ? page.cursor : undefined;
		} while (cursor && messages.length < 1000);
		logMail('mail.read', { operation: 'list', count: messages.length, ...correlation });
		return Response.json({ ok: true, status: 'listed', ...correlation, count: messages.length, messages }, { headers: { 'cache-control': 'no-store' } });
	}

	const wanted = parsed.message_id as string;
	let found: string | null = null;
	let cursor: string | undefined;
	do {
		const page = await env.MAILBOX.list({ prefix, limit: MAIL_LIST_LIMIT, cursor });
		found = page.objects.find((o) => o.key.endsWith(`/${wanted}.eml`))?.key ?? null;
		cursor = found || !page.truncated ? undefined : page.cursor;
	} while (cursor);
	const object = found ? await env.MAILBOX.get(found) : null;
	if (!object) {
		logMail('mail.read.denied', { reason: 'not-found', ...correlation });
		// Another employee's message id and a nonexistent one are indistinguishable.
		return Response.json({ ok: false, status: 'error', code: 'message-not-found', detail: 'no such message in this mailbox' }, { status: 404, headers: { 'cache-control': 'no-store' } });
	}
	const raw = await object.text();
	logMail('mail.read', { operation: 'read', id: wanted, bytes: object.size, ...correlation });
	return Response.json({
		ok: true, status: 'read', ...correlation, id: wanted, size: object.size,
		received_at: object.customMetadata?.['received-at'] ?? object.uploaded.toISOString(),
		from: object.customMetadata?.from ?? null, subject: object.customMetadata?.subject ?? null, raw,
	}, { headers: { 'cache-control': 'no-store' } });
}

export default {
	// FLUME-48: HTTP Access Facade
	async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
		const url = new URL(request.url);

		if (url.pathname === ACCESS_REQUEST_PATH) {
			if (request.method !== 'POST') return refusal(405, 'method-not-allowed', 'POST only');
			// No assertion means the request never came through Access — refuse the
			// direct-origin call the same way the facade does.
			if (!request.headers.get('cf-access-jwt-assertion')) {
				return refusal(401, 'missing-assertion', 'no Cloudflare Access assertion; the origin accepts only requests that came through Access');
			}
			if (!env.ACCESS_FACADE_ORIGIN) {
				return refusal(501, 'facade-not-provisioned', 'the access facade origin is not provisioned; see flume docs/employee-access.md "Pending live proof"');
			}
			// Proxy untouched: assertion, run assertion and body are the facade's to
			// verify, not the edge's.
			const upstream = new URL(url.pathname + url.search, env.ACCESS_FACADE_ORIGIN);
			return fetch(new Request(upstream, request));
		}

		if (url.pathname === MAIL_MESSAGES_PATH) return readMail(request, env);

		if (url.pathname === '/' || url.pathname === '/health') {
			return Response.json({
				ok: true,
				service: 'agents-facade',
				status: 'Facade active',
				access: env.ACCESS_FACADE_ORIGIN ? 'proxied' : 'not-provisioned',
			});
		}

		return refusal(404, 'not-found', 'unknown path');
	},

	// FLUME-49: Email Routing Engine — mailbox storage, not the agent bus.
	async email(message: ForwardableEmailMessage, env: Env, ctx: ExecutionContext): Promise<void> {
		const to = message.to.toLowerCase();

		if (!(await allowlisted(env, to))) {
			logMail('mail.rejected', { reason: 'unknown-recipient', to });
			message.setReject('Unknown recipient');
			return;
		}

		const maxBytes = Number(env.MAX_MESSAGE_BYTES ?? DEFAULT_MAX_MESSAGE_BYTES);
		if (message.rawSize > maxBytes) {
			logMail('mail.rejected', { reason: 'oversize', to, bytes: message.rawSize, max: maxBytes });
			message.setReject('Message too large');
			return;
		}

		// Bounded by rawSize check above; hash the content for the dedupe key.
		const raw = await new Response(message.raw).arrayBuffer();
		const hash = await sha256Hex(raw);
		const day = new Date().toISOString().slice(0, 10);
		const key = `mail/${to.split('@')[0]}/${day}/${hash}.eml`;

		// Duplicate delivery (or retry of an identical body) is acknowledged
		// without a second stored copy — and never triggers anything downstream.
		if (await env.MAILBOX.head(key)) {
			logMail('mail.duplicate', { to, key });
			return;
		}

		// A throw here is deliberate: transient failure = delivery retried, so no
		// false accepted/delivered receipt is ever produced by an interrupted write.
		await env.MAILBOX.put(key, raw, {
			customMetadata: {
				from: message.from,
				to: message.to,
				// Message-ID and Subject are attacker-controlled: metadata only,
				// never identity, never dedupe.
				'message-id': (message.headers.get('message-id') ?? '').slice(0, 256),
				subject: (message.headers.get('subject') ?? '').slice(0, 256),
				'received-at': new Date().toISOString(),
				'raw-size': String(message.rawSize),
				sha256: hash,
			},
		});
		logMail('mail.stored', { to, key, bytes: message.rawSize });
	},
} satisfies ExportedHandler<Env>;

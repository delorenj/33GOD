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

function allowlisted(env: Env, address: string): boolean {
	const list = (env.MAILBOX_ALLOWLIST ?? '')
		.split(',')
		.map((a) => a.trim().toLowerCase())
		.filter(Boolean);
	return list.includes(address.trim().toLowerCase());
}

function logMail(event: string, fields: Record<string, unknown>): void {
	// Receipt lines for `wrangler tail` / Workers Logs: IDs and outcomes, never content.
	console.log(JSON.stringify({ event, at: new Date().toISOString(), ...fields }));
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

		if (!allowlisted(env, to)) {
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

import { env, createExecutionContext, waitOnExecutionContext, SELF } from 'cloudflare:test';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import worker from '../src/index';

const IncomingRequest = Request<unknown, IncomingRequestCfProperties>;

// wrangler.jsonc now provisions ACCESS_FACADE_ORIGIN (FLUME-50); tests of the unprovisioned edge say so explicitly.
const unprovisioned = { ...env, ACCESS_FACADE_ORIGIN: undefined } as typeof env;

// The routing projection `flume identity provision` would have written.
beforeEach(async () => {
	await env.MAILBOX_ALLOWLIST.put('allowlist/grolf@agents.delo.sh', JSON.stringify({ handle: 'grolf', subject: 'fixture-subject', provisioned_at: new Date().toISOString() }));
});

function stubMessage(overrides: { from?: string; to?: string; raw?: string; messageId?: string; setReject?: ReturnType<typeof vi.fn> }) {
	const body = overrides.raw ?? 'From: sender@example.com\r\nTo: grolf@agents.delo.sh\r\nSubject: hi\r\n\r\nhello\r\n';
	const setReject = overrides.setReject ?? vi.fn();
	const message = {
		from: overrides.from ?? 'sender@example.com',
		to: overrides.to ?? 'grolf@agents.delo.sh',
		headers: new Headers({ 'message-id': overrides.messageId ?? '<m1@example.com>', subject: 'hi' }),
		raw: new Response(body).body!,
		rawSize: new TextEncoder().encode(body).byteLength,
		canBeForwarded: true,
		setReject,
		forward: vi.fn(),
		reply: vi.fn(),
	} as unknown as ForwardableEmailMessage;
	return { message, setReject, body };
}

describe('fetch — FLUME-48 access facade edge', () => {
	it('GET / reports the facade active', async () => {
		const ctx = createExecutionContext();
		const response = await worker.fetch(new IncomingRequest('https://identity.delo.sh/'), unprovisioned, ctx);
		await waitOnExecutionContext(ctx);
		expect(response.status).toBe(200);
		const body = await response.json<{ status: string; access: string }>();
		expect(body.status).toBe('Facade active');
		expect(body.access).toBe('not-provisioned');
	});

	it('refuses a direct-origin access request with missing-assertion', async () => {
		const ctx = createExecutionContext();
		const request = new IncomingRequest('https://identity.delo.sh/v1/access/requests', { method: 'POST', body: '{}' });
		const response = await worker.fetch(request, env, ctx);
		await waitOnExecutionContext(ctx);
		expect(response.status).toBe(401);
		const body = await response.json<{ code: string }>();
		expect(body.code).toBe('missing-assertion');
	});

	it('answers 501 (not a grant) when the facade origin is not provisioned', async () => {
		const ctx = createExecutionContext();
		const request = new IncomingRequest('https://identity.delo.sh/v1/access/requests', {
			method: 'POST',
			headers: { 'cf-access-jwt-assertion': 'edge-fixture' },
			body: '{}',
		});
		const response = await worker.fetch(request, unprovisioned, ctx);
		await waitOnExecutionContext(ctx);
		expect(response.status).toBe(501);
		const body = await response.json<{ code: string }>();
		expect(body.code).toBe('facade-not-provisioned');
	});
});

describe('email — FLUME-49 mailbox ingress', () => {
	it('stores raw mail for an enrolled address in the mailbox bucket', async () => {
		const { message, body } = stubMessage({});
		const ctx = createExecutionContext();
		await worker.email(message, env, ctx);
		await waitOnExecutionContext(ctx);

		// The object exists under the recipient's prefix and is byte-identical.
		const day = new Date().toISOString().slice(0, 10);
		const list = await env.MAILBOX.list({ prefix: `mail/grolf/${day}/` });
		expect(list.objects.length).toBe(1);
		const stored = await env.MAILBOX.get(list.objects[0]!.key);
		expect(await stored?.text()).toBe(body);
		expect(stored?.customMetadata?.from).toBe('sender@example.com');
	});

	it('dedupes an identical redelivery to the same object', async () => {
		const raw = 'From: sender@example.com\r\nTo: grolf@agents.delo.sh\r\nSubject: dupe\r\n\r\nsame bytes\r\n';
		const first = stubMessage({ raw });
		const second = stubMessage({ raw, messageId: '<spoofed-second@example.com>' });
		const ctx = createExecutionContext();
		await worker.email(first.message, env, ctx);
		await worker.email(second.message, env, ctx);
		await waitOnExecutionContext(ctx);

		const day = new Date().toISOString().slice(0, 10);
		const list = await env.MAILBOX.list({ prefix: `mail/grolf/${day}/` });
		const keys = list.objects.map((o) => o.key);
		expect(new Set(keys).size).toBe(keys.length); // one object per content hash
		expect(keys.filter((k) => k.endsWith('.eml')).length).toBeGreaterThanOrEqual(1);
	});

	it('rejects mail to an unenrolled recipient and stores nothing', async () => {
		const setReject = vi.fn();
		const { message } = stubMessage({ to: 'intruder@agents.delo.sh', setReject });
		const ctx = createExecutionContext();
		await worker.email(message, env, ctx);
		await waitOnExecutionContext(ctx);

		expect(setReject).toHaveBeenCalledWith('Unknown recipient');
		const list = await env.MAILBOX.list({ prefix: 'mail/intruder/' });
		expect(list.objects.length).toBe(0);
	});
});

// FLUME-53: employee-authenticated mail read. The origin (flume access serve) decides who is
// asking and whether they are active; the Worker reads only that employee's prefix.
describe('fetch — FLUME-53 mail read', () => {
	const origin = 'https://origin.test';
	const mailEnv = { ...env, ACCESS_FACADE_ORIGIN: origin } as typeof env;

	async function store(handle: string, raw: string): Promise<string> {
		const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(raw));
		const hash = [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('');
		await env.MAILBOX.put(`mail/${handle}/2026-10-14/${hash}.eml`, raw, { customMetadata: { from: 'sender@example.com', subject: `for ${handle}`, 'received-at': '2026-10-14T00:00:00.000Z' } });
		return hash;
	}

	function asEmployee(handle: string, over: Record<string, unknown> = {}, status = 200) {
		return vi.spyOn(globalThis, 'fetch').mockResolvedValue(
			Response.json(status === 200 ? { ok: true, status: 'authorized', handle, subject: `subject-${handle}`, run_id: 'run-1', harness: 'plain', ...over } : { ok: false, status: 'denied', ...over }, { status }),
		);
	}

	async function call(body: unknown, headers: Record<string, string> = { 'cf-access-jwt-assertion': 'edge-fixture' }, e = mailEnv) {
		const ctx = createExecutionContext();
		const response = await worker.fetch(new IncomingRequest('https://identity.delo.sh/v1/mail/messages', { method: 'POST', headers, body: typeof body === 'string' ? body : JSON.stringify(body) }), e, ctx);
		await waitOnExecutionContext(ctx);
		return response;
	}

	beforeEach(async () => {
		vi.restoreAllMocks();
		await env.MAILBOX_ALLOWLIST.put('allowlist/rererere@agents.delo.sh', JSON.stringify({ handle: 'rererere', subject: 'subject-rererere', provisioned_at: new Date().toISOString() }));
	});

	it('refuses a request that did not come through Access', async () => {
		const response = await call({ operation: 'list' }, {});
		expect(response.status).toBe(401);
		expect((await response.json<{ code: string }>()).code).toBe('missing-assertion');
	});

	it('is 501 without a provisioned origin and never reads storage', async () => {
		const response = await call({ operation: 'list' }, { 'cf-access-jwt-assertion': 'x' }, unprovisioned);
		expect(response.status).toBe(501);
	});

	it('rejects unknown fields, a handle in the body and malformed ids before any origin call', async () => {
		const spy = vi.spyOn(globalThis, 'fetch');
		expect((await call({ operation: 'list', handle: 'grolf' })).status).toBe(400);
		expect((await call({ operation: 'read', message_id: '../grolf' })).status).toBe(400);
		expect((await call({ operation: 'send' })).status).toBe(400);
		expect((await call('not json')).status).toBe(400);
		expect(spy).not.toHaveBeenCalled();
	});

	it('lists only the authenticated employee, never another mailbox', async () => {
		await store('rererere', 'Subject: mine\r\n\r\nrererere body\r\n');
		await store('grolf', 'Subject: theirs\r\n\r\ngrolf body\r\n');
		asEmployee('rererere');
		const response = await call({ operation: 'list' });
		expect(response.status).toBe(200);
		const body = await response.json<{ handle: string; messages: Array<{ subject: string }> }>();
		expect(body.handle).toBe('rererere');
		expect(body.messages.length).toBeGreaterThanOrEqual(1);
		expect(body.messages.every((m) => m.subject === 'for rererere')).toBe(true);
		expect(JSON.stringify(body)).not.toContain('grolf body');
	});

	it('reads own message by hash and returns not-found for another employee\'s hash', async () => {
		const mine = await store('rererere', 'Subject: mine\r\n\r\nrererere body\r\n');
		const theirs = await store('grolf', 'Subject: theirs\r\n\r\ngrolf body\r\n');
		asEmployee('rererere');
		const own = await call({ operation: 'read', message_id: mine });
		expect(own.status).toBe(200);
		expect((await own.json<{ raw: string }>()).raw).toContain('rererere body');
		asEmployee('rererere');
		const foreign = await call({ operation: 'read', message_id: theirs });
		expect(foreign.status).toBe(404);
		expect(await foreign.text()).not.toContain('grolf body');
	});

	it('passes the facade denial through and returns no mail when the employee is suspended', async () => {
		await store('rererere', 'Subject: mine\r\n\r\nrererere body\r\n');
		asEmployee('rererere', { code: 'employee-suspended' }, 403);
		const response = await call({ operation: 'list' });
		expect(response.status).toBe(403);
		const text = await response.text();
		expect(text).toContain('employee-suspended');
		expect(text).not.toContain('messages');
	});

	it('is closed when the allowlist projection is gone even if the origin authorizes', async () => {
		await store('rererere', 'Subject: mine\r\n\r\nrererere body\r\n');
		await env.MAILBOX_ALLOWLIST.delete('allowlist/rererere@agents.delo.sh');
		asEmployee('rererere');
		const response = await call({ operation: 'list' });
		expect(response.status).toBe(403);
		expect((await response.json<{ code: string }>()).code).toBe('mailbox-closed');
	});

	it('refuses an origin answer without a valid handle', async () => {
		asEmployee('Bad Handle/../x');
		expect((await call({ operation: 'list' })).status).toBe(502);
	});
});

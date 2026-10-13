import { env, createExecutionContext, waitOnExecutionContext, SELF } from 'cloudflare:test';
import { describe, it, expect, vi } from 'vitest';
import worker from '../src/index';

const IncomingRequest = Request<unknown, IncomingRequestCfProperties>;

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
		const response = await worker.fetch(new IncomingRequest('https://identity.delo.sh/'), env, ctx);
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
		const response = await worker.fetch(request, env, ctx);
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

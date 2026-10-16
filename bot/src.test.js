import test from 'node:test';
import assert from 'node:assert/strict';
import worker, { authorized, route } from './src.js';

const env = { TELEGRAM_CHAT_ID: '42', WEBHOOK_SECRET: 's', GH_DISPATCH_TOKEN: 'g', TELEGRAM_BOT_TOKEN: 't', GITHUB_REPO: 'me/repo' };

test('plain text is a lesson', () => {
  assert.deepEqual(route('गुस्से में फैसले मत लो').inputs, { topic: 'गुस्से में फैसले मत लो' });
  assert.equal(route('गुस्से').workflow, 'make-reel.yml');
});

test('commands', () => {
  assert.deepEqual(route('/reel').inputs, {});
  assert.deepEqual(route('/reel@StickBot समय की कीमत').inputs, { topic: 'समय की कीमत' });
  assert.deepEqual(route('🎬 New Reel').inputs, {});
  assert.deepEqual(route('/batch 5').inputs, { count: '5' });
  assert.deepEqual(route('/batch').inputs, { count: '3' });
  assert.deepEqual(route('/series दोस्ती').inputs, { series: 'true', topic: 'दोस्ती' });
  assert.equal(route('/report').workflow, 'weekly-report.yml');
  assert.ok(route('/status').status);
  assert.ok(route('/start').menu);
  assert.ok(route('/unknown').menu);
});

test('ideas, compilation and media', async () => {
  assert.deepEqual(route('', 'idea:55:2').inputs, { idea_of: '55:2' });
  assert.deepEqual(route('', 'comp:77').inputs, { from_run: '77' });
  assert.deepEqual(route('/ideas').inputs, { part: 'ideas' });
  assert.deepEqual(route('/report').inputs, { part: 'report' });
  const key = 'a'.repeat(32) + '.jpg';
  const store = { MEDIA: { get: async (k) => (k === key ? new Uint8Array([1, 2]).buffer : null) } };
  const hit = await worker.fetch(new Request('https://x/m/' + key), { ...env, ...store });
  assert.equal(hit.headers.get('Content-Type'), 'image/jpeg');
  assert.equal((await worker.fetch(new Request('https://x/m/' + 'b'.repeat(32) + '.jpg'), { ...env, ...store })).status, 404);
  assert.equal((await worker.fetch(new Request('https://x/m/../secret'), env)).status, 404);
});

test('buttons', () => {
  assert.deepEqual(route('', 'post:123:2'), { workflow: 'publish.yml', inputs: { source_run: '123', reel: '2' }, reply: route('', 'post:123:2').reply, clear: true });
  assert.deepEqual(route('', 'again:123:1').inputs, { remake_of: '123:1' });
  assert.ok(route('', 'skip:9:1').skip);
  assert.match(route('', 'post:abc:1').reply, /expired/);
});

test('only the owner chat is served', () => {
  assert.ok(authorized({ message: { chat: { id: 42 } } }, env));
  assert.ok(!authorized({ message: { chat: { id: 7 } } }, env));
  assert.ok(authorized({ callback_query: { message: { chat: { id: 42 } } } }, env));
});

test('webhook rejects a wrong secret and serves health', async () => {
  const bad = await worker.fetch(new Request('https://x/webhook', { method: 'POST', headers: { 'X-Telegram-Bot-Api-Secret-Token': 'no' }, body: '{}' }), env);
  assert.equal(bad.status, 403);
  assert.equal(await (await worker.fetch(new Request('https://x/health'), env)).text(), 'ok');
  const other = await worker.fetch(new Request('https://x/webhook', { method: 'POST', headers: { 'X-Telegram-Bot-Api-Secret-Token': 's' },
    body: JSON.stringify({ message: { chat: { id: 7 }, text: 'hi' } }) }), env);
  assert.equal(await other.text(), 'Ignored');
});

test('a lesson dispatches the workflow and replies', async () => {
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push([String(url), options?.body ? JSON.parse(options.body) : null]);
    return String(url).includes('dispatches') ? new Response(null, { status: 204 }) : new Response('{"ok":true,"result":{}}');
  };
  const response = await worker.fetch(new Request('https://x/webhook', { method: 'POST', headers: { 'X-Telegram-Bot-Api-Secret-Token': 's' },
    body: JSON.stringify({ message: { chat: { id: 42 }, text: 'समय' } }) }), env);
  assert.equal(await response.text(), 'ok');
  assert.equal(calls[0][0], 'https://api.github.com/repos/me/repo/actions/workflows/make-reel.yml/dispatches');
  assert.deepEqual(calls[0][1], { ref: 'main', inputs: { topic: 'समय' } });
  assert.match(calls[1][1].text, /समय/);
});

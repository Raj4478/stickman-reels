import test from 'node:test';
import assert from 'node:assert/strict';
import worker, { authorized, route, screen, encode, decode, makeInputs, summary, SETTINGS, isOn, flipped, settingsKeys, THEMES } from './src.js';

const env = { TELEGRAM_CHAT_ID: '42', WEBHOOK_SECRET: 's', GH_DISPATCH_TOKEN: 'g', TELEGRAM_BOT_TOKEN: 't', GITHUB_REPO: 'me/repo' };

// Fake Telegram + GitHub: records every call; GitHub variables live in `vars`
function fakeFetch(vars = {}) {
  const calls = [];
  globalThis.fetch = async (url, options = {}) => {
    const u = String(url);
    const body = options.body ? JSON.parse(options.body) : null;
    calls.push([u, options.method || 'GET', body]);
    if (u.includes('api.telegram.org')) return new Response('{"ok":true,"result":{}}');
    if (u.includes('/dispatches')) return new Response(null, { status: 204 });
    const v = /actions\/variables\/?(\w*)$/.exec(u);
    if (v) {
      const name = v[1] || body?.name;
      if ((options.method || 'GET') === 'GET') return name in vars ? new Response(JSON.stringify({ name, value: vars[name] })) : new Response('', { status: 404 });
      if (options.method === 'PATCH' && !(name in vars)) return new Response('', { status: 404 });
      vars[name] = body.value;
      return new Response(null, { status: 204 });
    }
    return new Response('{}');
  };
  return calls;
}
const post = (update, e = env) => worker.fetch(new Request('https://x/webhook', { method: 'POST', headers: { 'X-Telegram-Bot-Api-Secret-Token': 's' },
  body: JSON.stringify(update) }), e);
const tap = (data, id = 7) => ({ callback_query: { id: 'q', data, message: { message_id: id, chat: { id: 42 } } } });
const say = (text) => ({ message: { chat: { id: 42 }, text } });

test('commands', () => {
  assert.deepEqual(route('/reel'), { menu: 's', st: {} });
  assert.deepEqual(route('🎬 New Reel'), { menu: 's', st: {} });
  assert.deepEqual(route('/reel@StickBot समय की कीमत').inputs, { topic: 'समय की कीमत' });
  assert.deepEqual(route('/batch 5').inputs, { count: '5' });
  assert.deepEqual(route('/batch').inputs, { count: '3' });
  assert.deepEqual(route('/series दोस्ती').inputs, { series: 'true', topic: 'दोस्ती' });
  assert.equal(route('/report').workflow, 'weekly-report.yml');
  assert.ok(route('/status').status);
  assert.ok(route('/settings').settings && route('⚙️ Settings').settings);
  assert.ok(route('/start').menu_keyboard);
  assert.ok(route('/unknown').menu_keyboard);
  assert.deepEqual(route('गुस्से में फैसले मत लो'), { lesson: 'गुस्से में फैसले मत लो' });
});

test('every menu button fits Telegram and decodes back', () => {
  const states = [{}, { src: 't', theme: 9 }, { src: 't', theme: 3, voice: 'f' }, { src: 'l', voice: 'm', music: 'o' },
    { src: 'o', voice: 'f', music: 't', count: 's' }];
  for (const st of states) {
    for (const stage of ['s', 'h', 'v', 'm', 'c', 'k']) {
      for (const row of screen(stage, st).keys) {
        for (const b of row) {
          assert.ok(Buffer.byteLength(b.callback_data) <= 64, b.callback_data);
          const r = route('', b.callback_data);
          assert.ok(r.menu || r.go || r.cancel || r.edit, `${b.callback_data} -> ${JSON.stringify(r)}`);
        }
      }
    }
  }
  assert.deepEqual(decode(encode('m', { src: 't', theme: 4, voice: 'f' })), { stage: 'm', st: { src: 't', theme: 4, voice: 'f', music: undefined, count: undefined } });
});

test('menu walks topic → theme → voice → music → count → make', () => {
  let r = route('', screen('s').keys[1][1].callback_data); // 📚 Pick a theme
  assert.equal(r.menu, 'h');
  r = route('', screen('h', r.st).keys[0][1].callback_data); // 💰 पैसा
  assert.deepEqual([r.menu, r.st.theme], ['v', 1]);
  r = route('', screen('v', r.st).keys[0][1].callback_data); // 👩 Female
  r = route('', screen('m', r.st).keys[1][1].callback_data); // 🔇 No music
  r = route('', screen('c', r.st).keys[0][2].callback_data); // 3 Reels
  assert.equal(r.menu, 'k');
  r = route('', screen('k', r.st).keys[0][0].callback_data); // ✅ Make it
  assert.deepEqual(makeInputs(r.go), { options: 'theme=money voice=female music=off', count: '3' });
  assert.match(summary(r.go), /पैसा · 👩 Female voice · 🔇 No music · 3 Reels/);
});

test('inputs for each topic source', () => {
  assert.deepEqual(makeInputs({ src: 'r', voice: 'm', music: 'a', count: '1' }), { options: 'source=random voice=male' });
  assert.deepEqual(makeInputs({ src: 'o', voice: 'f', music: 'w', count: 's' }), { options: 'source=occasion voice=female music=warm', series: 'true' });
  assert.deepEqual(makeInputs({ src: 'l', voice: 'm', music: 't', count: '1' }, 'समय'), { options: 'voice=male music=tense', topic: 'समय' });
  assert.equal(THEMES.length, 10);
  assert.ok(route('', screen('s').keys[3][0].callback_data).go); // ⚡ Random Reel now
  assert.ok(route('', screen('s').keys[2][0].callback_data).edit); // ✍️ My own lesson
});

test('settings switches', () => {
  assert.ok(isOn('AUTO_POST', 'true') && !isOn('AUTO_POST', ''));
  assert.ok(isOn('OCCASIONS', '') && !isOn('OCCASIONS', 'off'));
  assert.equal(flipped('OCCASIONS', ''), 'off');
  assert.equal(flipped('CAROUSEL', 'true'), 'false');
  const keys = settingsKeys({ CAROUSEL: 'true' });
  assert.equal(keys.length, SETTINGS.length);
  assert.match(keys[2][0].text, /^✅/);
  assert.match(keys[0][0].text, /^⬜/);
  assert.deepEqual(route('', 'set:2'), { toggle: 'CAROUSEL' });
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
  assert.equal(await (await post({ message: { chat: { id: 7 }, text: 'hi' } })).text(), 'Ignored');
});

test('a typed lesson opens the menu, then makes the Reel with it', async () => {
  const kv = new Map();
  const store = { MEDIA: { put: async (k, v) => kv.set(k, v), get: async (k) => kv.get(k) ?? null } };
  const calls = fakeFetch();
  assert.equal(await (await post(say('समय'), { ...env, ...store })).text(), 'ok');
  assert.equal(kv.get('lesson:42'), 'समय');
  assert.match(calls.at(-1)[2].text, /समय[\s\S]*Which voice/);
  await post(tap(encode('k', { src: 'l', voice: 'f', music: 'a', count: '1' }).replace('w:k:', 'w:g:')), { ...env, ...store });
  const dispatched = calls.find(([u]) => u.includes('/dispatches'));
  assert.deepEqual(dispatched[2], { ref: 'main', inputs: { options: 'voice=female', topic: 'समय' } });
});

test('without storage a typed lesson is made straight away', async () => {
  const calls = fakeFetch();
  await post(say('समय'));
  assert.deepEqual(calls[0][2], { ref: 'main', inputs: { topic: 'समय' } });
});

test('settings tap flips the variable and redraws the switches', async () => {
  const vars = { CAROUSEL: 'false' };
  const calls = fakeFetch(vars);
  await post(tap('set:2'));
  assert.equal(vars.CAROUSEL, 'true');
  await post(tap('set:5')); // festivals: unset counts as on, so the tap turns it off (created with POST)
  assert.equal(vars.OCCASIONS, 'off');
  const edit = calls.filter(([u]) => u.includes('editMessageText')).at(-1)[2];
  assert.match(JSON.stringify(edit.reply_markup), /⬜ 🎉 Festival topics/);
});

test('post, again, skip, ideas and compilation buttons', () => {
  assert.deepEqual(route('', 'post:123:2').inputs, { source_run: '123', reel: '2' });
  assert.deepEqual(route('', 'again:123:1').inputs, { remake_of: '123:1' });
  assert.ok(route('', 'skip:9:1').skip);
  assert.deepEqual(route('', 'idea:55:2').inputs, { idea_of: '55:2' });
  assert.deepEqual(route('', 'comp:77').inputs, { from_run: '77' });
  assert.match(route('', 'post:abc:1').reply, /expired/);
});

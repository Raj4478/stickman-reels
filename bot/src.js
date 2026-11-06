// Stickman Reels Telegram bot (Cloudflare Worker). It only turns your messages and button taps into GitHub
// Actions runs of this repository; the Reels themselves are made by the workflows.
//   🎬 New Reel / /reel   a step-by-step menu: topic (random, ideas, festival, a theme, or your own lesson),
//                         voice, music, how many → Make it
//   any plain message     your own lesson: the menu continues with voice, music and how many
//   /reel <lesson>        make it straight away with the usual settings
//   /comic [situation]    a comic Reel: a cartoon kid's deadpan rant with a punchline (reel/comic.py)
//   /batch [n]  /series <lesson>  /status  /report  /ideas
//   ⚙️ Settings / /settings   on/off switches (auto-post, best time, carousel, hook test, daily Reel, festivals),
//                         saved as repository variables
// Buttons under each Reel: ✅ Post, 🔁 Make again, 🗑 Skip. Under the ideas: one per idea. Under the weekly
// compilation: ✅ Post to YouTube.
// GET /m/<key> serves carousel images stored in the MEDIA KV namespace (Instagram fetches them by URL); MEDIA also
// keeps a typed lesson for 30 minutes while the menu is open.
// Only TELEGRAM_CHAT_ID is served, and only requests carrying the webhook secret are accepted.

export const HELP = `🎬 Stickman Reels

Tap 🎬 New Reel and choose the topic, voice and music, or just send me a life lesson (for example "गुस्से में फैसले मत लो").

/reel <lesson> - make it straight away
/comic - a funny cartoon Reel (or /comic <situation>, e.g. /comic gym membership)
/batch 3 - three Reels on fresh lessons
/series <lesson> - a two-part story
/status - what is running
/report - this week's numbers
/ideas - next lessons from comments and trends
/settings - auto-post, best time, carousel and more

Under every Reel: ✅ Post, 🔁 Make again, 🗑 Skip.`;
export const MENU = { keyboard: [[{ text: '🎬 New Reel' }, { text: '⚙️ Settings' }], [{ text: '📊 Status' }, { text: '❓ Help' }]], resize_keyboard: true, is_persistent: true };
const RUNS = { 'Make a Reel': 'Making Reels', 'Post a Reel': 'Posting', 'Weekly report': 'Weekly report', 'Weekly compilation': 'Compilation',
  'Post queued Reels': 'Posting at the best time', 'Renew Instagram token': 'Instagram token', 'Check YouTube sign-in': 'YouTube sign-in' };

// ---- the New Reel menu -------------------------------------------------------------------------------
// Each button carries every choice made so far, so the bot needs no memory between taps:
//   w:<stage>:<source>:<theme>:<voice>:<music>:<count>:<style>
// source r random, i ideas, o festival, t theme, l your lesson · theme index · voice m/f · music a/w/t/o ·
// count 1/2/3/5 or s (two-part series) · style s story, c comic · "-" = not chosen yet (style "-" follows the
// usual style in Settings). Buttons sent before the style field existed still work.
export const THEMES = [['love', '💘 प्यार'], ['family', '👨‍👩‍👧 परिवार'], ['money', '💰 पैसा'], ['health', '💪 सेहत'], ['study', '📚 पढ़ाई'],
  ['friendship', '🤝 दोस्ती'], ['work', '💼 काम'], ['self_respect', '👑 आत्मसम्मान'], ['relationships', '❤️ रिश्ते'],
  ['habits', '🔁 आदतें'], ['time', '⏰ समय']];
const SOURCES = { r: '🎲 Fresh random lesson', i: '💡 From viewer ideas', o: '🎉 Upcoming festival', t: '📚 Pick a theme', l: '✍️ Your lesson' };
const VOICES = { m: '👨 Male voice', f: '👩 Female voice' };
const MUSIC = { a: '🤖 Music: auto', w: '🎵 Music: warm', t: '⚡ Music: tense', o: '🔇 No music' };
const COUNTS = { 1: '1 Reel', 2: '2 Reels', 3: '3 Reels', 5: '5 Reels', s: '📖 2-part story' };
const STYLES = { s: '📖 Story', c: '😂 Comic' };
const STAGES = ['s', 'h', 'v', 'm', 'c', 'k'];

export function encode(stage, st) {
  return `w:${stage}:${st.src || '-'}:${st.theme ?? '-'}:${st.voice || '-'}:${st.music || '-'}:${st.count || '-'}:${st.style || '-'}`;
}

export function decode(data) {
  const m = /^w:([shvmckx]):([-rioltc]):(-|\d{1,2}):([-mf]):([-awto]):([-1235s])(?::([-sc]))?$/.exec(data);
  if (!m) return null;
  const v = (x) => (x === '-' || x === undefined ? undefined : x);
  return { stage: m[1], st: { src: v(m[2]), theme: v(m[3]) === undefined ? undefined : Number(m[3]), voice: v(m[4]), music: v(m[5]), count: v(m[6]),
    style: v(m[7]) } };
}

const rowsOf = (items, per = 2) => items.reduce((rows, b, i) => (i % per ? rows[rows.length - 1].push(b) : rows.push([b]), rows), []);
const button = (text, data) => ({ text, callback_data: data });

export function summary(st) {
  const topic = st.src === 't' ? `📚 ${THEMES[st.theme]?.[1] || ''}` : SOURCES[st.src] || '';
  return [STYLES[st.style], topic, VOICES[st.voice], MUSIC[st.music], COUNTS[st.count]].filter(Boolean).join(' · ');
}

// The message and buttons for one stage of the menu
export function screen(stage, st = {}) {
  const back = (to) => button('⬅️ Back', encode(to, st));
  const cancel = button('✖ Cancel', 'w:x:-:-:-:-:-');
  if (stage === 's') {
    return { text: '🎬 New Reel\n\nWhat should it be about?', keys: [
      ...rowsOf(['r', 'i', 'o', 't'].map((s) => button(SOURCES[s], encode(s === 't' ? 'h' : 'v', { ...st, src: s })))),
      [button('✍️ My own lesson', 'w:type')],
      [button('⚡ Random Reel now, usual settings', encode('k', { src: 'r', voice: 'm', music: 'a', count: '1' }).replace('w:k:', 'w:g:'))],
      [button('😂 Comic Reel now', encode('k', { src: 'r', voice: 'm', music: 'a', count: '1', style: 'c' }).replace('w:k:', 'w:g:'))]] };
  }
  if (stage === 'h') {
    return { text: '📚 Pick a theme', keys: [...rowsOf(THEMES.map(([, label], i) => button(label, encode('v', { ...st, src: 't', theme: i })))), [back('s'), cancel]] };
  }
  if (stage === 'v') {
    return { text: `${summary(st)}\n\n🎙 Which voice tells the story?`, keys: [Object.entries(VOICES).map(([k, label]) => button(label, encode('m', { ...st, voice: k }))),
      [back(st.src === 't' ? 'h' : 's'), cancel]] };
  }
  if (stage === 'm') {
    return { text: `${summary(st)}\n\n🎵 Background music?`, keys: [...rowsOf(Object.entries(MUSIC).map(([k, label]) => button(label, encode('c', { ...st, music: k })))),
      [back('v'), cancel]] };
  }
  if (stage === 'c') {
    const counts = st.src === 'l' ? ['1', 's'] : ['1', '2', '3', '5', 's'];
    return { text: `${summary(st)}\n\n🔢 How many?`, keys: [...rowsOf(counts.map((k) => button(COUNTS[k], encode('k', { ...st, count: k }))), 3), [back('m'), cancel]] };
  }
  // a two-part series is always a story; anything else can switch between story and comic here
  const flip = st.count === 's' ? [] : [[button(st.style === 'c' ? '📖 Make it a story instead' : '😂 Make it comic instead', encode('k', { ...st, style: st.style === 'c' ? 's' : 'c' }))]];
  return { text: `Ready:\n${summary(st)}`, keys: [[button('✅ Make it', encode('k', st).replace('w:k:', 'w:g:'))], ...flip, [back('c'), cancel]] };
}

// The Make a Reel inputs for the final choices (`lesson` is the typed lesson, when the source is l)
export function makeInputs(st, lesson = '') {
  const options = [st.src === 't' && THEMES[st.theme] ? `theme=${THEMES[st.theme][0]}` : '',
    { r: 'source=random', i: 'source=ideas', o: 'source=occasion' }[st.src] || '',
    st.voice === 'f' ? 'voice=female' : st.voice === 'm' ? 'voice=male' : '',
    { w: 'music=warm', t: 'music=tense', o: 'music=off' }[st.music] || '',
    { c: 'style=comic', s: 'style=story' }[st.style] || ''].filter(Boolean).join(' ');
  const inputs = { ...(options ? { options } : {}), ...(lesson ? { topic: lesson.slice(0, 200) } : {}) };
  if (st.count === 's') inputs.series = 'true';
  else if (st.count && st.count !== '1') inputs.count = st.count;
  return inputs;
}

// ---- settings: on/off switches stored as repository variables ------------------------------------
export const SETTINGS = [
  ['AUTO_POST', '📤 Auto-post (no ✅ Post tap)', 'true'],
  ['POST_AT_PEAK', '⏰ Post at the best time', 'true'],
  ['CAROUSEL', '🖼 Also post a carousel', 'true'],
  ['HOOK_TEST', '🧪 Test a second hook', 'true'],
  ['DAILY_REEL', '📅 A Reel every day, 9 am', 'true'],
  ['OCCASIONS', '🎉 Festival topics', 'off'], // on unless set to "off"
  ['REEL_STYLE', '😂 Comic style by default', 'comic'], // "comic" or "story": the usual style of a Reel
  ['REEL_AUDIENCE', '👨‍👩‍👧 Family comedy (kid-friendly)', 'family'], // "family" or "adult" (kids = made for kids: set by hand)
];
export const isOn = (name, value) => {
  const v = String(value || '').toLowerCase();
  if (name === 'OCCASIONS') return v !== 'off';
  if (name === 'REEL_AUDIENCE') return v === 'family' || v === 'kids';
  return name === 'REEL_STYLE' ? v === 'comic' : v === 'true';
};
export const flipped = (name, value) => {
  if (name === 'OCCASIONS') return isOn(name, value) ? 'off' : 'on';
  if (name === 'REEL_STYLE') return isOn(name, value) ? 'story' : 'comic';
  if (name === 'REEL_AUDIENCE') return isOn(name, value) ? 'adult' : 'family';
  return isOn(name, value) ? 'false' : 'true';
};

export function settingsKeys(values) {
  return SETTINGS.map(([name, label], i) => [button(`${isOn(name, values[name]) ? '✅' : '⬜'} ${label}`, `set:${i}`)]);
}

export function authorized(update, env) {
  const chat = update.message?.chat?.id ?? update.callback_query?.message?.chat?.id;
  return chat !== undefined && String(chat) === String(env.TELEGRAM_CHAT_ID).trim();
}

// What a message or button asks for: { workflow, inputs, reply } · { menu: stage, st } · { lesson } ·
// { settings } · { toggle } · { status } · { reply }
export function route(text, data) {
  if (data) {
    if (data.startsWith('w:g:')) {
      const chosen = decode(data.replace('w:g:', 'w:k:'));
      return chosen ? { go: chosen.st } : { reply: 'That button has expired.' };
    }
    if (data.startsWith('w:x:')) return { cancel: true };
    if (data === 'w:type') return { edit: '✍️ Send me your lesson as a message (Hindi or English), for example:\nगुस्से में फैसले मत लो' };
    const w = decode(data);
    if (w) return { menu: w.stage, st: w.st };
    const toggle = /^set:(\d)$/.exec(data);
    if (toggle && SETTINGS[Number(toggle[1])]) return { toggle: SETTINGS[Number(toggle[1])][0] };
    const idea = /^idea:(\d+):(\d+)$/.exec(data);
    if (idea) return { workflow: 'make-reel.yml', inputs: { idea_of: `${idea[1]}:${idea[2]}` }, reply: `🎬 Making idea ${Number(idea[2]) + 1} (about 7 minutes)...` };
    const comp = /^comp:(\d+)$/.exec(data);
    if (comp) return { workflow: 'compile.yml', inputs: { from_run: comp[1] }, reply: '📺 Uploading the weekly compilation to YouTube...', clear: true };
    const m = /^(post|again|skip):(\d+):(\d+)$/.exec(data);
    if (!m) return data === 'status' ? { status: true } : { reply: 'That button has expired.' };
    const [, verb, run, reel] = m;
    if (verb === 'post') return { workflow: 'publish.yml', inputs: { source_run: run, reel }, reply: '📤 Posting it to Instagram and YouTube... I will send the links here.', clear: true };
    if (verb === 'again') return { workflow: 'make-reel.yml', inputs: { remake_of: `${run}:${reel}` }, reply: '🔁 Making a new version of this lesson (about 7 minutes)...' };
    return { skip: true, reply: '🗑 Skipped. Nothing was posted.', clear: true };
  }
  const t = (text || '').trim();
  if (!t || t === '❓ Help' || /^\/(start|help)\b/i.test(t)) return { reply: HELP, menu_keyboard: true };
  if (t === '📊 Status' || /^\/status\b/i.test(t)) return { status: true };
  if (t === '⚙️ Settings' || /^\/settings\b/i.test(t)) return { settings: true };
  if (/^\/report\b/i.test(t)) return { workflow: 'weekly-report.yml', inputs: { part: 'report' }, reply: '📊 Counting this week\'s numbers...' };
  if (/^\/ideas\b/i.test(t)) return { workflow: 'weekly-report.yml', inputs: { part: 'ideas' }, reply: '💡 Reading comments and trends for new lessons...' };
  if (t === '📚 Series') return { reply: 'Send /series followed by the lesson, for example:\n/series दोस्ती में भरोसा' };
  let m = /^\/batch(?:@\w+)?\s*(\d*)/i.exec(t);
  if (m) {
    const n = ['1', '2', '3', '5'].includes(m[1]) ? m[1] : '3';
    return { workflow: 'make-reel.yml', inputs: { count: n }, reply: `🎬 Making ${n} Reels on fresh lessons (about ${5 + 3 * Number(n)} minutes)...` };
  }
  m = /^\/series(?:@\w+)?\s*([\s\S]*)$/i.exec(t);
  if (m) return { workflow: 'make-reel.yml', inputs: { series: 'true', topic: m[1].trim().slice(0, 200) }, reply: '📚 Making a two-part story (about 12 minutes)...' };
  if (t === '🎬 New Reel' || /^\/(reel|new)(?:@\w+)?\s*$/i.test(t)) return { menu: 's', st: {} };
  m = /^\/comic(?:@\w+)?\s*([\s\S]*)$/i.exec(t);
  if (m) {
    const situation = m[1].trim().slice(0, 200);
    return { workflow: 'make-reel.yml', inputs: { options: 'style=comic', ...(situation ? { topic: situation } : {}) },
      reply: `😂 Making a comic Reel${situation ? ` about "${situation.slice(0, 80)}"` : ''} (about 6 minutes)...` };
  }
  m = /^\/reel(?:@\w+)?\s+([\s\S]+)$/i.exec(t);
  if (m) return { workflow: 'make-reel.yml', inputs: { topic: m[1].trim().slice(0, 200) }, reply: `🎬 Making a Reel about "${m[1].trim().slice(0, 80)}" (about 7 minutes)...` };
  if (t.startsWith('/')) return { reply: HELP, menu_keyboard: true };
  return { lesson: t.slice(0, 200) };
}

async function api(url, options) {
  return fetch(url, { ...options, signal: AbortSignal.timeout(20000) });
}

export class Bot {
  constructor(env) { this.env = env; }
  async telegram(method, body) {
    const r = await api(`https://api.telegram.org/bot${this.env.TELEGRAM_BOT_TOKEN}/${method}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const result = await r.json();
    if (!result.ok) throw new Error('Telegram rejected the request');
    return result.result;
  }
  send(text, markup) {
    return this.telegram('sendMessage', { chat_id: this.env.TELEGRAM_CHAT_ID, text, disable_web_page_preview: true, ...(markup ? { reply_markup: markup } : {}) });
  }
  // Show a menu screen: edit the tapped message in place, or send a new one
  show(text, keys, messageId) {
    const markup = { inline_keyboard: keys };
    if (messageId) return this.telegram('editMessageText', { chat_id: this.env.TELEGRAM_CHAT_ID, message_id: messageId, text, reply_markup: markup }).catch(() => this.send(text, markup));
    return this.send(text, markup);
  }
  github(path, body, method) {
    return api(`https://api.github.com/repos/${this.env.GITHUB_REPO}/${path}`, {
      method: method || (body ? 'POST' : 'GET'),
      headers: { Authorization: `Bearer ${this.env.GH_DISPATCH_TOKEN}`, Accept: 'application/vnd.github+json', 'Content-Type': 'application/json',
        'User-Agent': 'Stickman-Reels-Bot', 'X-GitHub-Api-Version': '2022-11-28' },
      ...(body ? { body: JSON.stringify(body) } : {}) });
  }
  async dispatch(workflow, inputs) {
    const r = await this.github(`actions/workflows/${workflow}/dispatches`, { ref: 'main', inputs });
    if (r.status === 401 || r.status === 403 || r.status === 404) {
      throw new Error('🔑 GitHub refused the bot (GH_DISPATCH_TOKEN). It needs a fine-grained token with Actions: Read and write on stickman-reels; save it as the GH_DISPATCH_TOKEN secret and run Deploy bot.');
    }
    if (!r.ok) throw new Error(`GitHub could not start ${workflow} (HTTP ${r.status}). Try again in a minute.`);
  }
  async status() {
    const r = await this.github('actions/runs?per_page=8');
    const runs = r.ok ? ((await r.json()).workflow_runs || []) : [];
    if (!runs.length) return this.send('Nothing has run yet. Tap 🎬 New Reel to make your first Reel.');
    const icon = (x) => (x.status !== 'completed' ? '⏳' : x.conclusion === 'success' ? '✅' : x.conclusion === 'cancelled' ? '🛑' : '❌');
    const lines = runs.slice(0, 6).map((x) => `${icon(x)} ${RUNS[x.name] || x.name}: ${x.display_title}`.slice(0, 120));
    return this.send('📊 Latest runs\n\n' + lines.join('\n'));
  }
  async variables() {
    const values = {};
    for (const [name] of SETTINGS) {
      const r = await this.github(`actions/variables/${name}`);
      if (r.status === 403) throw new Error('🔑 The bot cannot read settings: give GH_DISPATCH_TOKEN "Variables: Read and write" on stickman-reels.');
      values[name] = r.ok ? (await r.json()).value : '';
    }
    return values;
  }
  async setVariable(name, value) {
    let r = await this.github(`actions/variables/${name}`, { name, value }, 'PATCH');
    if (r.status === 404) r = await this.github('actions/variables', { name, value });
    if (r.status === 403) throw new Error('🔑 The bot cannot change settings: give GH_DISPATCH_TOKEN "Variables: Read and write" on stickman-reels.');
    if (!r.ok) throw new Error(`GitHub could not save ${name} (HTTP ${r.status}).`);
  }
  async settings(messageId) {
    const values = await this.variables();
    return this.show('⚙️ Settings\nTap to switch on or off.', settingsKeys(values), messageId);
  }
  async handle(update) {
    const query = update.callback_query;
    if (query) await this.telegram('answerCallbackQuery', { callback_query_id: query.id });
    const messageId = query?.message?.message_id;
    const step = route(update.message?.text, query?.data);
    if (step.status) return this.status();
    if (step.settings) return this.settings();
    if (step.toggle) {
      const values = await this.variables();
      await this.setVariable(step.toggle, flipped(step.toggle, values[step.toggle]));
      return this.settings(messageId);
    }
    if (step.menu) {
      const s = screen(step.menu, step.st);
      return this.show(s.text, s.keys, messageId);
    }
    if (step.cancel || step.edit) return this.show(step.edit || 'Cancelled.', [], messageId);
    if (step.lesson) {
      // keep the typed lesson while the menu asks for the rest; without storage, make it straight away
      if (!this.env.MEDIA) return this.make({ src: 'l', count: '1' }, step.lesson);
      await this.env.MEDIA.put(`lesson:${this.env.TELEGRAM_CHAT_ID}`, step.lesson, { expirationTtl: 1800 });
      const s = screen('v', { src: 'l' });
      return this.show(`✍️ "${step.lesson.slice(0, 80)}"\n\n${s.text}`, s.keys);
    }
    if (step.go) {
      const lesson = step.go.src === 'l' && this.env.MEDIA ? (await this.env.MEDIA.get(`lesson:${this.env.TELEGRAM_CHAT_ID}`)) || '' : '';
      if (step.go.src === 'l' && !lesson) return this.show('That lesson has expired. Send it again.', [], messageId);
      if (messageId) await this.telegram('editMessageReplyMarkup', { chat_id: this.env.TELEGRAM_CHAT_ID, message_id: messageId, reply_markup: { inline_keyboard: [] } }).catch(() => {});
      return this.make(step.go, lesson);
    }
    if (step.workflow) await this.dispatch(step.workflow, step.inputs);
    if (step.clear && query?.message) {
      // remove the buttons so the same Reel is not posted (or skipped) twice by accident
      await this.telegram('editMessageReplyMarkup', { chat_id: this.env.TELEGRAM_CHAT_ID, message_id: query.message.message_id, reply_markup: { inline_keyboard: [] } }).catch(() => {});
    }
    return this.send(step.reply, step.menu_keyboard ? MENU : undefined);
  }
  async make(st, lesson) {
    await this.dispatch('make-reel.yml', makeInputs(st, lesson));
    const n = st.count === 's' ? 2 : Number(st.count || 1);
    return this.send(`🎬 Making ${st.count === 's' ? 'a two-part story' : n > 1 ? `${n} Reels` : 'your Reel'} (about ${5 + 3 * n} minutes)\n${summary(st)}`);
  }
}

export default {
  async fetch(request, env) {
    const path = new URL(request.url).pathname;
    if (path === '/health') return new Response('ok');
    const media = /^\/m\/([a-f0-9]{32}\.jpg)$/.exec(path);
    if (media && request.method === 'GET') {
      const image = env.MEDIA ? await env.MEDIA.get(media[1], 'arrayBuffer') : null;
      return image ? new Response(image, { headers: { 'Content-Type': 'image/jpeg', 'Cache-Control': 'public, max-age=86400' } }) : new Response('Not found', { status: 404 });
    }
    if (path !== '/webhook' || request.method !== 'POST') return new Response('Not found', { status: 404 });
    if (!env.WEBHOOK_SECRET || !env.TELEGRAM_CHAT_ID || !env.GH_DISPATCH_TOKEN || !env.TELEGRAM_BOT_TOKEN) return new Response('Not configured', { status: 503 });
    if (request.headers.get('X-Telegram-Bot-Api-Secret-Token') !== env.WEBHOOK_SECRET) return new Response('Forbidden', { status: 403 });
    const text = await request.text();
    if (text.length > 32000) return new Response('Too large', { status: 413 });
    let update;
    try { update = JSON.parse(text); } catch { return new Response('Invalid JSON', { status: 400 }); }
    if (!authorized(update, env)) return new Response('Ignored');
    const bot = new Bot(env);
    try { await bot.handle(update); } catch (error) {
      // Never log the error itself: Telegram URLs carry the bot token.
      const message = String(error?.message || '');
      try { await bot.send(message.startsWith('🔑') || message.startsWith('GitHub') ? message : '❌ That did not work. Tap 📊 Status to check, then try again.'); } catch {}
      return new Response('handled_error');
    }
    return new Response('ok');
  },
};

// Stickman Reels Telegram bot (Cloudflare Worker). It only turns your messages and button taps into GitHub
// Actions runs of this repository; the Reels themselves are made by the workflows.
//   /reel [lesson]   make a Reel (any plain message also counts as a lesson)
//   /batch [n]       make n Reels on fresh random lessons (up to 5)
//   /series [lesson] make a two-part story
//   /status          what is running, and the last results
//   /report          the weekly numbers now
// Buttons under each Reel: ✅ Post (Instagram + YouTube), 🔁 Make again (same lesson), 🗑 Skip.
// Only TELEGRAM_CHAT_ID is served, and only requests carrying the webhook secret are accepted.

export const HELP = `🎬 Stickman Reels

Send me a life lesson (for example "गुस्से में फैसले मत लो") and I will make a Hindi stickman Reel about it in about 7 minutes.

/reel - a Reel on a fresh random lesson
/batch 3 - three Reels at once
/series <lesson> - a two-part story
/status - what is running
/report - this week's numbers

Under every Reel: ✅ Post, 🔁 Make again, 🗑 Skip.`;
export const MENU = { keyboard: [[{ text: '🎬 New Reel' }, { text: '📚 Series' }], [{ text: '📊 Status' }, { text: '❓ Help' }]], resize_keyboard: true, is_persistent: true };
const RUNS = { 'Make a Reel': 'Making Reels', 'Post a Reel': 'Posting', 'Weekly report': 'Weekly report' };

export function authorized(update, env) {
  const chat = update.message?.chat?.id ?? update.callback_query?.message?.chat?.id;
  return chat !== undefined && String(chat) === String(env.TELEGRAM_CHAT_ID).trim();
}

// What a message or button asks for: { workflow, inputs, reply } or { reply } or { status } / { skip }.
export function route(text, data) {
  if (data) {
    const m = /^(post|again|skip):(\d+):(\d+)$/.exec(data);
    if (!m) return data === 'status' ? { status: true } : { reply: 'That button has expired.' };
    const [, verb, run, reel] = m;
    if (verb === 'post') return { workflow: 'publish.yml', inputs: { source_run: run, reel }, reply: '📤 Posting it to Instagram and YouTube... I will send the links here.', clear: true };
    if (verb === 'again') return { workflow: 'make-reel.yml', inputs: { remake_of: `${run}:${reel}` }, reply: '🔁 Making a new version of this lesson (about 7 minutes)...' };
    return { skip: true, reply: '🗑 Skipped. Nothing was posted.', clear: true };
  }
  const t = (text || '').trim();
  if (!t || t === '❓ Help' || /^\/(start|help)\b/i.test(t)) return { reply: HELP, menu: true };
  if (t === '📊 Status' || /^\/status\b/i.test(t)) return { status: true };
  if (/^\/report\b/i.test(t)) return { workflow: 'weekly-report.yml', inputs: {}, reply: '📊 Counting this week\'s numbers...' };
  if (t === '📚 Series') return { reply: 'Send /series followed by the lesson, for example:\n/series दोस्ती में भरोसा' };
  let m = /^\/batch(?:@\w+)?\s*(\d*)/i.exec(t);
  if (m) {
    const n = ['1', '2', '3', '5'].includes(m[1]) ? m[1] : m[1] === '4' ? '3' : '3';
    return { workflow: 'make-reel.yml', inputs: { count: n }, reply: `🎬 Making ${n} Reels on fresh lessons (about ${5 + 3 * Number(n)} minutes)...` };
  }
  m = /^\/series(?:@\w+)?\s*([\s\S]*)$/i.exec(t);
  if (m) return { workflow: 'make-reel.yml', inputs: { series: 'true', topic: m[1].trim().slice(0, 200) }, reply: '📚 Making a two-part story (about 12 minutes)...' };
  m = /^\/reel(?:@\w+)?\s*([\s\S]*)$/i.exec(t);
  const topic = (m ? m[1] : t === '🎬 New Reel' ? '' : t).trim().slice(0, 200);
  if (t.startsWith('/') && !m) return { reply: HELP, menu: true };
  return { workflow: 'make-reel.yml', inputs: topic ? { topic } : {}, reply: topic ? `🎬 Making a Reel about "${topic}" (about 7 minutes)...` : '🎬 Making a Reel on a fresh lesson (about 7 minutes)...' };
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
  github(path, body) {
    return api(`https://api.github.com/repos/${this.env.GITHUB_REPO}/${path}`, {
      method: body ? 'POST' : 'GET',
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
    if (!runs.length) return this.send('Nothing has run yet. Send a lesson to make your first Reel.');
    const icon = (x) => (x.status !== 'completed' ? '⏳' : x.conclusion === 'success' ? '✅' : x.conclusion === 'cancelled' ? '🛑' : '❌');
    const lines = runs.slice(0, 6).map((x) => `${icon(x)} ${RUNS[x.name] || x.name}: ${x.display_title}`.slice(0, 120));
    return this.send('📊 Latest runs\n\n' + lines.join('\n'));
  }
  async handle(update) {
    const query = update.callback_query;
    if (query) await this.telegram('answerCallbackQuery', { callback_query_id: query.id });
    const step = route(update.message?.text, query?.data);
    if (step.status) return this.status();
    if (step.workflow) await this.dispatch(step.workflow, step.inputs);
    if (step.clear && query?.message) {
      // remove the buttons so the same Reel is not posted (or skipped) twice by accident
      await this.telegram('editMessageReplyMarkup', { chat_id: this.env.TELEGRAM_CHAT_ID, message_id: query.message.message_id, reply_markup: { inline_keyboard: [] } }).catch(() => {});
    }
    return this.send(step.reply, step.menu ? MENU : undefined);
  }
}

export default {
  async fetch(request, env) {
    const path = new URL(request.url).pathname;
    if (path === '/health') return new Response('ok');
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

// Deploys the bot Worker, stores its secrets, connects the Telegram webhook and checks it end to end.
// Adapted from the infographic repo's telegram-worker/deploy.mjs. Never prints a secret.
import { spawnSync } from 'node:child_process';
import { randomBytes } from 'node:crypto';

const required = ['CLOUDFLARE_API_TOKEN', 'CLOUDFLARE_ACCOUNT_ID', 'GH_DISPATCH_TOKEN', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID'];
const env = process.env;
const missing = required.filter((name) => !env[name]?.trim());
if (missing.length) throw new Error(`Missing GitHub Actions secrets: ${missing.join(', ')} (see README.md, "Telegram bot")`);
for (const name of required) env[name] = env[name].trim();
if (!/^[a-f0-9]{32}$/i.test(env.CLOUDFLARE_ACCOUNT_ID)) throw new Error('CLOUDFLARE_ACCOUNT_ID must be the 32-character Account ID');

const safe = (text) => {
  let result = String(text);
  for (const name of required) result = result.split(env[name]).join('[redacted]');
  return result.replace(/https?:\/\/\S+/g, '[URL hidden]').slice(0, 300);
};
async function call(url, options = {}) {
  let response;
  try { response = await fetch(url, { ...options, signal: AbortSignal.timeout(30000) }); } catch { throw new Error('Setup connection failed'); }
  const body = await response.json().catch(() => ({}));
  if (!response.ok || body.success === false || body.ok === false) {
    const details = (body.errors || []).map((e) => `${e.code}: ${e.message}`).join('; ') || body.description || 'Request rejected';
    throw new Error(`Setup API failed (${response.status}): ${safe(details)}`);
  }
  return body.result;
}
function wrangler(args, input) {
  const run = spawnSync(process.execPath, ['node_modules/wrangler/bin/wrangler.js', ...args], { input, encoding: 'utf8', env });
  if (run.status !== 0) throw new Error(`Cloudflare ${args[0]} failed. Check the Workers token permissions and account ID.`);
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const headers = { Authorization: `Bearer ${env.CLOUDFLARE_API_TOKEN}` };

// Explain a Cloudflare refusal plainly (never printing a secret): is the token active, and can it see this account?
async function cloudflareCheck() {
  let active = false;
  for (const endpoint of ['user/tokens/verify', `accounts/${env.CLOUDFLARE_ACCOUNT_ID}/tokens/verify`]) {
    try {
      if ((await call(`https://api.cloudflare.com/client/v4/${endpoint}`, { headers }))?.status === 'active') { active = true; break; }
    } catch {}
  }
  let visible = null, count = 0;
  try {
    const accounts = await call('https://api.cloudflare.com/client/v4/accounts?per_page=50', { headers });
    count = accounts?.length || 0;
    visible = accounts?.some((a) => a.id === env.CLOUDFLARE_ACCOUNT_ID) ?? null;
  } catch {}
  console.log(`Cloudflare token active: ${active}; accounts it can see: ${count}; CLOUDFLARE_ACCOUNT_ID among them: ${visible}`);
  if (!active) return 'CLOUDFLARE_API_TOKEN is not an active API token (copy it again, whole, or create a new one from the "Edit Cloudflare Workers" template).';
  if (visible === false) return `the token cannot see CLOUDFLARE_ACCOUNT_ID. It can see ${count} account(s): make sure the secret is the Account ID (Workers & Pages, right side; not a Zone ID) and that the token's Account Resources include that account.`;
  return 'the token is active but lacks Workers permissions for this account: create it from the "Edit Cloudflare Workers" template with Account Resources = your account.';
}

let subdomain;
try {
  subdomain = await call(`https://api.cloudflare.com/client/v4/accounts/${env.CLOUDFLARE_ACCOUNT_ID}/workers/subdomain`, { headers });
} catch {
  throw new Error(`Cloudflare refused the Workers account check: ${await cloudflareCheck()}`);
}
if (!subdomain?.subdomain) throw new Error('Enable a workers.dev subdomain in Cloudflare Workers & Pages first');

// The GitHub token must be able to start this repository's workflows, or every button would fail later.
const repo = /GITHUB_REPO = "([^"]+)"/.exec((await import('node:fs')).readFileSync('wrangler.toml', 'utf8'))[1];
const gh = await fetch(`https://api.github.com/repos/${repo}/actions/workflows`, { headers: { Authorization: `Bearer ${env.GH_DISPATCH_TOKEN}`,
  Accept: 'application/vnd.github+json', 'User-Agent': 'Stickman-Reels-Deploy' } });
if (!gh.ok) throw new Error(`GH_DISPATCH_TOKEN cannot read ${repo}'s workflows (HTTP ${gh.status}). Give it Actions: Read and write on ${repo}.`);

// Storage for carousel images (Workers KV, free tier): made once, then bound to the Worker as MEDIA.
const fs = await import('node:fs');
const namespaces = await call(`https://api.cloudflare.com/client/v4/accounts/${env.CLOUDFLARE_ACCOUNT_ID}/storage/kv/namespaces?per_page=100`, { headers });
let media = (namespaces || []).find((ns) => ns.title === 'stickman-media');
if (!media) {
  media = await call(`https://api.cloudflare.com/client/v4/accounts/${env.CLOUDFLARE_ACCOUNT_ID}/storage/kv/namespaces`, {
    method: 'POST', headers: { ...headers, 'Content-Type': 'application/json' }, body: JSON.stringify({ title: 'stickman-media' }) });
}
fs.appendFileSync('wrangler.toml', `\n[[kv_namespaces]]\nbinding = "MEDIA"\nid = "${media.id}"\n`);
wrangler(['deploy']);
const secret = randomBytes(32).toString('hex');
wrangler(['secret', 'bulk'], JSON.stringify({ WEBHOOK_SECRET: secret, GH_DISPATCH_TOKEN: env.GH_DISPATCH_TOKEN,
  TELEGRAM_BOT_TOKEN: env.TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID: env.TELEGRAM_CHAT_ID }));
const url = `https://stickman-reels-bot.${subdomain.subdomain}.workers.dev`;

let ready = false;
for (let attempt = 0; attempt < 10 && !ready; attempt++) {
  try {
    const probe = await fetch(url + '/webhook', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Telegram-Bot-Api-Secret-Token': secret }, body: '{}' });
    ready = probe.ok && (await probe.text()).trim() === 'Ignored';
  } catch {}
  if (!ready) await sleep(5000);
}
if (!ready) throw new Error('The deployed bot did not answer with its new secret; the webhook was not changed');

const tg = (method, body) => call(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/${method}`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
await tg('setWebhook', { url: url + '/webhook', secret_token: secret, allowed_updates: ['message', 'callback_query'], max_connections: 2 });
await tg('setMyCommands', { commands: [
  { command: 'reel', description: 'Make a Reel (add a lesson, or leave empty for a fresh one)' },
  { command: 'batch', description: 'Make several Reels at once, e.g. /batch 3' },
  { command: 'series', description: 'A two-part story, e.g. /series दोस्ती' },
  { command: 'status', description: 'What is running' },
  { command: 'report', description: "This week's numbers" },
  { command: 'ideas', description: 'Next lessons from comments and trends' },
  { command: 'help', description: 'How it works' }] });
const hook = await tg('getWebhookInfo', {});
if (hook.url !== url + '/webhook') throw new Error('Webhook verification failed');
await tg('sendMessage', { chat_id: env.TELEGRAM_CHAT_ID, text: '✅ Stickman bot is ready. Send me a life lesson, or tap 🎬 New Reel.',
  reply_markup: { keyboard: [[{ text: '🎬 New Reel' }, { text: '📚 Series' }], [{ text: '📊 Status' }, { text: '❓ Help' }]], resize_keyboard: true, is_persistent: true } });
console.log('Bot deployed and connected.');

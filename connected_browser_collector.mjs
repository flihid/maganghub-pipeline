// Companion for the connected Browser tool. The caller supplies its documented tab.
// Does not attach to browsers, read credentials, or call private X endpoints.
import fs from 'node:fs/promises';
import path from 'node:path';

export async function readPage(tab) {
  return tab.playwright.evaluate(() => {
    const render = n => !n ? '' : n.nodeType === 3 ? n.textContent :
      n.nodeType === 1 && n.tagName === 'IMG' ? (n.getAttribute('alt') || '') :
      Array.from(n.childNodes || []).map(render).join('');
    const main = document.querySelector('main');
    const text = main?.innerText || '';
    const articles = Array.from(document.querySelectorAll('article[data-testid="tweet"]'));
    const atBottom = window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 100;
    return {
      query: document.querySelector('input[role="combobox"]')?.value,
      empty: !articles.length && /No results for|Tidak ada hasil/i.test(text),
      error: !articles.length && /Something went wrong|Rate limit exceeded|Try reloading|Terjadi kesalahan/i.test(text),
      loading: !!main?.querySelector('[role="progressbar"]'),
      at_bottom: atBottom, scroll_y: window.scrollY, scroll_height: document.documentElement.scrollHeight,
      records: articles.map(a => ({
        href: a.querySelector('time')?.closest('a')?.getAttribute('href'),
        created_at: a.querySelector('time')?.getAttribute('datetime'),
        text: render(a.querySelector('[data-testid="tweetText"]')).replace(/\s+/g, ' ').trim(),
        post_lang: a.querySelector('[data-testid="tweetText"]')?.getAttribute('lang'),
        metrics: Array.from(a.querySelectorAll('button[aria-label]')).map(e => e.getAttribute('aria-label')),
        text_truncated: Array.from(a.querySelectorAll('button')).some(e => /Show more|Tampilkan lebih banyak/.test(e.innerText)),
      })),
    };
  });
}

export class Collector {
  constructor(root) { this.root = root; this.ids = new Set(); this.jobs = []; this.logs = []; this.active = null; }
  async init() {
    const source = JSON.parse(await fs.readFile(path.join(this.root, 'browser_jobs.json'), 'utf8'));
    const bounds = new Map();
    for (const j of source) {
      const b = bounds.get(j.fase) || {name:j.fase, since:j.since, until:j.until};
      if (j.since < b.since) b.since = j.since;
      if (j.until > b.until) b.until = j.until;
      bounds.set(j.fase, b);
    }
    this.phaseBounds = [...bounds.values()];
    const groups = new Map();
    for (const j of source) groups.set([j.fase, j.since, j.until].join('|'), {
      ...j, language_filter: 'in', kueri: '(maganghub OR "magang hub" OR "magang nasional" OR "magang kemnaker" OR "pemagangan nasional")',
    });
    this.jobs = [...groups.values()];
    for (const name of await fs.readdir(this.root)) {
      if (!/^x_.*\.jsonl$/.test(name)) continue;
      for (const line of (await fs.readFile(path.join(this.root, name), 'utf8')).split('\n').filter(Boolean))
        this.ids.add(JSON.parse(line).tweet_id);
    }
    try { this.logs = (await fs.readFile(path.join(this.root, 'browser_collection_log.jsonl'), 'utf8')).split('\n').filter(Boolean).map(JSON.parse); }
    catch (e) { if (e.code !== 'ENOENT') throw e; }
    return { jobs: this.jobs.length, stored: this.ids.size, checked: this.logs.length };
  }
  key(j) { return [j.fase, j.since, j.until, j.kueri, j.language_filter ?? 'id'].join('|'); }
  async start(tab) {
    const done = new Set(this.logs.filter(x => ['empty_search', 'exhausted_visible_results'].includes(x.status)).map(x => this.key(x)));
    const job = this.jobs.find(j => !done.has(this.key(j)));
    if (!job) return { status: 'all_intervals_checked', total: this.ids.size };
    this.active = { job, seen: new Set(), idle: 0, scrolls: 0, started: Date.now(), polls: 0 };
    const query = `${job.kueri} lang:${job.language_filter} since:${job.since} until:${job.until}`;
    const url = 'https://x.com/search?' + new URLSearchParams({ q: query, src: 'typed_query', f: 'live' });
    await tab.goto(url);
    return { status: 'search_opened', ...job };
  }
  async finish(status) {
    const a = this.active;
    const log = { ...a.job, status, seen: a.seen.size, scrolls: a.scrolls,
      duration_seconds: Math.round((Date.now()-a.started)/1000), total_unique: this.ids.size,
      finished_at: new Date().toISOString(), collector: 'connected_brave_dom_v2' };
    await fs.appendFile(path.join(this.root, 'browser_collection_log.jsonl'), JSON.stringify(log)+'\n', 'utf8');
    this.logs.push(log); this.active = null;
    return log;
  }
  async step(tab) {
    if (!this.active) return { status: 'no_active_interval' };
    const state = await readPage(tab);
    const a = this.active;
    const expected = `${a.job.kueri} lang:${a.job.language_filter} since:${a.job.since} until:${a.job.until}`;
    if (state.query && state.query !== expected) return this.finish('query_changed_stop');
    if (state.error) return this.finish('platform_error_stop');
    if (state.empty) return this.finish('empty_search');
    if (!state.records.length) {
      if (++a.polls > 8) return this.finish('loading_timeout');
      return { status: 'loading', polls: a.polls };
    }
    a.polls = 0;
    let newlySeen = 0;
    const added = [];
    for (const r of state.records) {
      const m = /^\/([^/]+)\/status\/(\d+)/.exec(r.href || '');
      if (!m || !r.text || !r.created_at) continue;
      const [, username, tweet_id] = m;
      if (!a.seen.has(tweet_id)) { a.seen.add(tweet_id); newlySeen++; }
      if (this.ids.has(tweet_id)) continue;
      const dateWib = new Date(Date.parse(r.created_at) + 7*3600000).toISOString().slice(0,10);
      const phase = this.phaseBounds.find(b => b.since <= dateWib && dateWib < b.until);
      if (!phase) continue;
      const metric = regex => {
        const label = r.metrics.find(x => regex.test(x));
        const value = label && /^([\d.,]+)\s/.exec(label);
        return value ? Number(value[1].replace(/,/g, '')) : null;
      };
      added.push({tweet_id, username, url:'https://x.com'+r.href, created_at:r.created_at,
        text:r.text, n_reply:metric(/\bRepl/i), n_repost:metric(/\brepost/i), n_like:metric(/\bLikes?\./i),
        ...a.job, retrieval_phase:a.job.fase, fase:phase.name,
        outside_query_window:dateWib < a.job.since || dateWib >= a.job.until,
        post_lang:r.post_lang, scraped_at:new Date().toISOString(), collector:'connected_brave_dom_v2', text_truncated:r.text_truncated});
    }
    for (const phase of new Set(added.map(r => r.fase))) {
      const batch = added.filter(r => r.fase === phase);
      await fs.appendFile(path.join(this.root, 'x_'+phase+'.jsonl'), batch.map(r => JSON.stringify(r)).join('\n')+'\n', 'utf8');
      for (const r of batch) this.ids.add(r.tweet_id);
    }
    a.idle = newlySeen ? 0 : a.idle + 1;
    if (a.idle >= 6 && !state.loading && state.at_bottom) return this.finish('exhausted_visible_results');
    if (a.idle >= 6 && !state.at_bottom) return this.finish('scroll_stalled_partial');
    if (a.seen.size >= (this.maxPosts || 400)) return this.finish('record_cap_partial');
    // Caller must supply a real scroll adapter; focusing body can reset position.
    if (!this.scroll) throw new Error('A verified native scroll adapter is required');
    await this.scroll();
    a.scrolls++;
    return { status:'scrolling', since:a.job.since, until:a.job.until, added:added.length,
      seen:a.seen.size, idle:a.idle, total:this.ids.size, scroll_y:state.scroll_y, at_bottom:state.at_bottom };
  }
}

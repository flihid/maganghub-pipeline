"""Local twscrape adapter: plan, private session setup, resumable daily collection."""
import argparse
import asyncio
from contextlib import aclosing
from datetime import date, datetime, timedelta
import getpass
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

# Set before importing the SDK. No analytics, browser-cookie extraction, or proxies.
os.environ['TWS_TELEMETRY'] = '0'

import config

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'data/raw'
SESSION = ROOT / '.twscrape/accounts.db'
WIB = ZoneInfo('Asia/Jakarta')


def write_json(file, value):
    file.parent.mkdir(parents=True, exist_ok=True)
    temp = file.with_suffix(file.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(file)


def make_jobs():
    """Interleave phases; walk backwards through days within each phase."""
    buckets = []
    for phase, (since, until) in config.JENDELA_WAKTU.items():
        d, first = date.fromisoformat(until) - timedelta(days=1), date.fromisoformat(since)
        bucket = []
        while d >= first:
            bucket.append(dict(fase=phase, since=d.isoformat(), until=(d+timedelta(days=1)).isoformat()))
            d -= timedelta(days=1)
        buckets.append(bucket)
    return [bucket[i] for i in range(max(map(len, buckets))) for bucket in buckets if i < len(bucket)]


def base_query():
    return '(' + ' OR '.join(config.KATA_KUNCI) + ')'


def collection_jobs(args, records):
    jobs = make_jobs()
    if args.mode == 'pilot':
        return jobs
    # Full pass: spread days over each phase, prioritizing untried days.
    # Previously attempted dates still remain in this pass; they are not lost.
    log_path = RAW / 'browser_collection_log.jsonl'
    logs = [json.loads(line) for line in log_path.read_text(encoding='utf-8').split('\n')
            if line.strip()] if log_path.exists() else []
    tried = {(r.get('fase'), r.get('since')) for r in logs
             if r.get('collector') == 'twscrape_0.20.1' and r.get('processed_once')}
    populated = {datetime.fromisoformat(r['created_at']).astimezone(WIB).date().isoformat()
                 for r in records}

    def spread(items):
        # Breadth-first midpoint selection covers beginning/middle/end early.
        result, queue = [], [items]
        while queue:
            part = queue.pop(0)
            if not part:
                continue
            mid = len(part)//2
            result.append(part[mid])
            queue.extend([part[:mid], part[mid+1:]])
        return result

    buckets = []
    for phase in config.JENDELA_WAKTU:
        bucket = spread(sorted((j for j in jobs if j['fase'] == phase), key=lambda j: j['since']))
        bucket.sort(key=lambda j: ((phase, j['since']) in tried, j['since'] in populated))
        buckets.append(bucket)
    return [bucket[i] for i in range(max(map(len, buckets))) for bucket in buckets if i < len(bucket)]


def search_query(job):
    # Date-only search boundaries may use UTC. Cover both UTC dates intersecting
    # the WIB day, then enforce the exact local interval in normalize().
    since = (date.fromisoformat(job['since']) - timedelta(days=1)).isoformat()
    return f"{base_query()} lang:{config.BAHASA} since:{since} until:{job['until']}"


def study_phase(dt):
    day = dt.astimezone(WIB).date().isoformat()
    return next((p for p, (s, u) in config.JENDELA_WAKTU.items() if s <= day < u), None)


def normalize(tweet, job, collected_at=None):
    if tweet.date.tzinfo is None:
        raise ValueError('Timestamp has no timezone')
    day = tweet.date.astimezone(WIB).date().isoformat()
    if not job['since'] <= day < job['until'] or not study_phase(tweet.date):
        return None
    if tweet.retweetedTweet is not None or not tweet.rawContent.strip():
        return None
    username = getattr(tweet.user, 'username', '') or ''
    return dict(tweet_id=str(tweet.id), username=username, url=tweet.url,
                text=tweet.rawContent, created_at=tweet.date.isoformat(), post_lang=tweet.lang,
                n_reply=tweet.replyCount, n_repost=tweet.retweetCount, n_like=tweet.likeCount,
                n_quote=tweet.quoteCount, conversation_id=str(tweet.conversationId),
                content_type='reply' if tweet.inReplyToTweetId else 'quote' if tweet.quotedTweet else 'original',
                author_missing=not username, fase=study_phase(tweet.date), kueri=base_query(),
                language_filter=config.BAHASA, since=job['since'], until=job['until'],
                scraped_at=collected_at or datetime.now(WIB).isoformat(),
                text_truncated=None, collector='twscrape_0.20.1')


def load_records(root):
    return [json.loads(line) for f in root.glob('x_*.jsonl')
            for line in f.read_text(encoding='utf-8').split('\n') if line.strip()]


def sdk():
    from twscrape import API
    from twscrape.logger import logger
    warnings = []
    def capture(message):
        # Only bounded categories are retained; SDK logs/headers are not printed.
        text = message.record['message'].lower()
        category = 'rate_limit' if 'rate' in text or 'limit' in text else (
            'access_error' if 'blocked' in text or 'auth' in text or 'cookie' in text else 'sdk_warning')
        warnings.append(category)
    logger.remove()
    logger.add(capture, level='WARNING')
    return API(str(SESSION), raise_when_no_account=True, wait_timeout=1, wait_interval=1), warnings


async def setup_session():
    if not sys.stdin.isatty():
        raise ValueError('Buka setup di terminal Windows interaktif agar input sesi dapat disembunyikan.')
    SESSION.parent.mkdir(parents=True, exist_ok=True)
    print('Masukkan nilai cookie akun X milikmu di terminal ini. Input disembunyikan.')
    print('Di Brave yang sudah login: F12 > Application > Cookies > https://x.com.')
    print('Salin Value untuk auth_token dan ct0. Jangan kirim ke chat atau Git.')
    auth = getpass.getpass('auth_token: ').strip()
    csrf = getpass.getpass('ct0: ').strip()
    if not auth or not csrf or any(c in auth+csrf for c in '\r\n;'):
        raise ValueError('Input cookie tidak valid')
    api, _ = sdk()
    accounts = await api.pool.get_all()
    if any(a.username != 'maganghub_local' for a in accounts):
        raise ValueError('Database harus khusus satu akun penelitian')
    await api.pool.add_account_cookies('maganghub_local', 'auth_token='+auth+'; ct0='+csrf)
    print('Sesi tersimpan lokal. Ini belum membuktikan akses pencarian berhasil.')


def settings(args):
    result = dict(query=base_query(), language=config.BAHASA, phases=config.JENDELA_WAKTU,
                mode=args.mode, per_phase=args.per_phase, per_day=args.per_day,
                max_raw=args.max_raw, sdk=version('twscrape'), adapter_version=2,
                query_window='previous_date_through_until_then_filter_WIB')
    if args.mode == 'full':
        result['schedule'] = 'untried_then_spread_days_v1'
    return result


async def collect(args):
    if not SESSION.exists():
        raise ValueError('Sesi belum ada. Jalankan setup terlebih dahulu.')
    api, warnings = sdk()
    accounts = await api.pool.get_all()
    if len(accounts) != 1 or not accounts[0].active:
        raise ValueError('Diperlukan tepat satu sesi aktif. Jalankan setup untuk memperbaruinya.')
    RAW.mkdir(parents=True, exist_ok=True)
    cfg = settings(args)
    fingerprint = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:16]
    checkpoint = RAW / ('twscrape_state_' + fingerprint + '.json')
    state = json.loads(checkpoint.read_text(encoding='utf-8')) if checkpoint.exists() else dict(settings=cfg, jobs={})
    state['status'] = 'running'
    records = load_records(RAW)
    known = {r['tweet_id'] for r in records}
    # Pilot quotas count this SDK's data, separately from earlier browser experiments.
    counts = {p: sum(r.get('collector') == 'twscrape_0.20.1' and r.get('fase') == p for r in records)
              for p in config.JENDELA_WAKTU}
    attempted = 0
    for job in collection_jobs(args, records):
        key = job['fase'] + '|' + job['since']
        if state['jobs'].get(key, {}).get('processed_once'):
            continue
        if args.mode == 'pilot' and counts[job['fase']] >= args.per_phase:
            continue
        if len(known) >= args.max_raw:
            state['status'] = 'raw_limit_partial'
            break
        if attempted >= args.max_jobs:
            state['status'] = 'run_job_limit_partial'
            break
        if attempted:
            await asyncio.sleep(args.query_delay)
        attempted += 1
        print(f"{job['fase']} | {job['since']} | total unik tersimpan {len(known)}", flush=True)
        log = dict(job, kueri=base_query(), language_filter=config.BAHASA,
                   search_query=search_query(job), started_at=datetime.now(WIB).isoformat(),
                   collector='twscrape_0.20.1', pages=0, seen=0, added=0, outside_or_excluded=0,
                   status='started', processed_once=False)
        warnings.clear()
        capped = False
        try:
            from twscrape.models import parse_tweets
            stream = api.search_raw(search_query(job), limit=args.per_day, kv={'product':'Latest'})
            async with asyncio.timeout(args.query_timeout), aclosing(stream) as responses:
                async for response in responses:
                    log['pages'] += 1
                    for tweet in parse_tweets(response.json()):
                        log['seen'] += 1
                        row = normalize(tweet, job)
                        if row is None:
                            log['outside_or_excluded'] += 1
                            continue
                        if row['tweet_id'] in known:
                            continue
                        if len(known) >= args.max_raw or (args.mode == 'pilot' and counts[job['fase']] >= args.per_phase):
                            capped = True
                            break
                        with (RAW / ('x_' + row['fase'] + '.jsonl')).open('a', encoding='utf-8') as out:
                            out.write(json.dumps(row, ensure_ascii=False)+'\n')
                            out.flush()
                        known.add(row['tweet_id']); counts[row['fase']] += 1; log['added'] += 1
                    if capped:
                        break
                    await asyncio.sleep(args.page_delay)
            log['status'] = ('sdk_warning_partial' if warnings else 'quota_partial' if capped else
                             'daily_limit_partial' if log['seen'] >= args.per_day else
                             'stream_ended_unverified' if log['pages'] else 'no_rows_unverified')
            log['processed_once'] = not warnings
        except asyncio.CancelledError:
            log['status'] = 'interrupted_partial'
            raise
        except TimeoutError:
            log['status'] = 'query_timeout_partial'
        except Exception as error:
            # Never print exception messages that might include session material.
            log['status'] = 'sdk_error_partial'
            log['error_type'] = type(error).__name__
            if log['error_type'] == 'NoAccountError':
                print('Sesi belum tersedia untuk pencarian. Bisa karena cooldown/limit sementara.', flush=True)
                print('Tunggu sebelum menjalankan ulang; jangan reset pembatasan akun.', flush=True)
        finally:
            log['warnings'] = sorted(set(warnings))
            log['finished_at'] = datetime.now(WIB).isoformat()
            state['jobs'][key] = log
            state['total_unique'] = len(known)
            state['sdk_counts_per_phase'] = counts
            write_json(checkpoint, state)
            with (RAW / 'browser_collection_log.jsonl').open('a', encoding='utf-8') as out:
                out.write(json.dumps(log, ensure_ascii=False)+'\n')
            print(f"  +{log['added']} post | {log['status']}", flush=True)
        if not log['processed_once']:
            state['status'] = 'stopped_for_review'
            write_json(checkpoint, state)
            return 2
    else:
        state['status'] = 'job_pass_finished_not_a_census'
    state['total_unique'] = len(known)
    state['sdk_counts_per_phase'] = counts
    write_json(checkpoint, state)
    print(json.dumps(dict(status=state['status'], total_unique=len(known), sdk_counts_per_phase=counts)))
    return 0


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['plan','setup','collect'])
    p.add_argument('--mode', choices=['pilot','full'], default='pilot')
    p.add_argument('--per-phase', type=int, default=50)
    p.add_argument('--per-day', type=int, default=60)
    p.add_argument('--max-raw', type=int, default=10000)
    p.add_argument('--max-jobs', type=int, default=117)
    p.add_argument('--page-delay', type=float, default=5)
    p.add_argument('--query-delay', type=float, default=35)
    p.add_argument('--query-timeout', type=float, default=120)
    return p


def main():
    args = parser().parse_args()
    if min(args.per_phase,args.per_day,args.max_raw,args.max_jobs) < 1 or args.page_delay < 5 or args.query_delay < 25 or args.query_timeout < 1:
        raise ValueError('Batas tidak valid; jeda minimum halaman 5 detik dan kueri 25 detik.')
    if args.command == 'plan':
        jobs = collection_jobs(args, load_records(RAW))
        print(json.dumps(dict(settings=settings(args), daily_jobs=len(jobs), first_jobs=jobs[:3],
                              pilot_target=args.per_phase*len(config.JENDELA_WAKTU)), indent=2))
        return 0
    if args.command == 'setup':
        asyncio.run(setup_session())
        return 0
    return asyncio.run(collect(args))


if __name__ == '__main__':
    os.chdir(ROOT)
    if hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('\nDihentikan. Data yang sudah ditulis tetap tersimpan; jalankan collect untuk melanjutkan.')
        raise SystemExit(130)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2)
    except Exception as error:
        print('Operasi dihentikan: '+type(error).__name__+'. Tidak ada kredensial yang ditampilkan.', file=sys.stderr)
        raise SystemExit(2)

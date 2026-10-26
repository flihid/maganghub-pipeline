"""Offline checks only: no credentials, X calls or live browser."""
import asyncio
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
from datetime import datetime, timezone

import twscrape_pipeline as pipeline


def tweet(identity='100', timestamp='2026-08-31T05:00:00+00:00', text='MagangHub gak adil 😭!!!'):
    return NS(id=identity, date=datetime.fromisoformat(timestamp), rawContent=text,
              user=NS(username='example'), url='https://x.com/example/status/'+identity,
              lang='in', replyCount=0, retweetCount=0, likeCount=2, quoteCount=0,
              conversationId=identity, inReplyToTweetId=None, quotedTweet=None, retweetedTweet=None)


class FakeAPI:
    def __init__(self, rows, error=False):
        self.rows, self.error, self.calls = rows, error, 0
        self.pool = NS(get_all=self.accounts)

    async def accounts(self):
        return [NS(active=True)]

    async def search_raw(self, query, limit, kv):
        self.calls += 1
        assert kv == {'product': 'Latest'}
        assert limit == -1
        yield NS(json=lambda: self.rows)
        if self.error:
            raise RuntimeError('Do not expose session-like exception text')


class CollectorTests(unittest.TestCase):
    def test_full_schedule_spreads_and_prioritizes_untried_days(self):
        args = pipeline.parser().parse_args(['plan', '--mode', 'full'])
        with tempfile.TemporaryDirectory() as folder, patch.object(pipeline, 'RAW', Path(folder)):
            first = pipeline.collection_jobs(args, [])
            self.assertEqual(len(first), 117)
            self.assertEqual(len({(j['fase'], j['since']) for j in first}), 117)
            self.assertEqual([j['fase'] for j in first[:3]], list(pipeline.config.JENDELA_WAKTU))
            already = dict(first[0], collector='twscrape_0.20.1', processed_once=True)
            (Path(folder)/'browser_collection_log.jsonl').write_text(json.dumps(already)+'\n')
            second = pipeline.collection_jobs(args, [])
            self.assertNotEqual(second[0], first[0])
            self.assertEqual([j for j in second if j['fase'] == first[0]['fase']][-1], first[0])

    def test_unicode_line_separators_are_not_jsonl_boundaries(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            row = {'tweet_id': '100', 'text': 'maganghub\u2028sedih\u2029😭'}
            (root/'x_test.jsonl').write_text(json.dumps(row, ensure_ascii=False)+'\n', encoding='utf-8')
            self.assertEqual(pipeline.load_records(root), [row])

    def test_plan_and_boundaries(self):
        jobs = pipeline.make_jobs()
        self.assertEqual(len(jobs), 117)
        self.assertEqual([x['fase'] for x in jobs[:3]], list(pipeline.config.JENDELA_WAKTU))
        start, end = pipeline.window_bounds(jobs[0])
        self.assertEqual(start.astimezone(timezone.utc).isoformat(), '2026-08-30T17:00:00+00:00')
        self.assertEqual(int(end.timestamp()-start.timestamp()),86400)
        self.assertIn(f'since_time:{int(start.timestamp())} until_time:{int(end.timestamp())}', pipeline.search_query(jobs[0]))
        # Aug 30 17:00 UTC is Aug 31 00:00 WIB, included in that local day.
        self.assertIsNotNone(pipeline.normalize(tweet(timestamp='2026-08-30T17:00:00+00:00'), jobs[0]))
        self.assertIsNone(pipeline.normalize(tweet(timestamp='2026-08-30T16:59:59+00:00'), jobs[0]))
        self.assertIsNone(pipeline.normalize(tweet(timestamp='2026-08-31T17:00:00+00:00'), jobs[0]))
        self.assertEqual(pipeline.os.environ['TWS_TELEMETRY'], '0')

    def test_text_reply_and_retweet(self):
        source = tweet(text='maganghub ' + 'panjang ' * 100 + '😭')
        source.inReplyToTweetId = '90'
        row = pipeline.normalize(source, pipeline.make_jobs()[0])
        self.assertEqual(row['text'], source.rawContent)
        self.assertEqual(row['content_type'], 'reply')
        source.retweetedTweet = NS()
        self.assertIsNone(pipeline.normalize(source, pipeline.make_jobs()[0]))

    def run_collection(self, root, api, **overrides):
        raw = root / 'raw'
        session = root / 'accounts.db'
        session.touch()
        args = pipeline.parser().parse_args(['collect'])
        args.max_jobs = 1
        args.page_delay = args.query_delay = 0
        for name, value in overrides.items():
            setattr(args, name, value)
        with patch.object(pipeline, 'RAW', raw), patch.object(pipeline, 'SESSION', session), \
             patch.object(pipeline, 'sdk', return_value=(api, [])), \
             patch('twscrape.models.parse_tweets', side_effect=lambda rows: iter(rows)):
            result = asyncio.run(pipeline.collect(args))
        checkpoint = next(raw.glob('twscrape_state_*.json'))
        return result, json.loads(checkpoint.read_text()), pipeline.load_records(raw)

    def test_save_deduplicate_resume(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            api = FakeAPI([tweet(), tweet()])
            result, state, rows = self.run_collection(root, api)
            self.assertEqual(result, 0)
            self.assertEqual(len(rows), 1)
            self.assertTrue(next(iter(state['jobs'].values()))['processed_once'])
            # Second invocation skips the processed day and tries the next phase.
            _, resumed, rows = self.run_collection(root, api)
            self.assertEqual(len(rows), 1)
            self.assertEqual(len(resumed['jobs']), 2)

    def test_error_preserves_partial_data_and_retries(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            result, state, rows = self.run_collection(root, FakeAPI([tweet()], error=True))
            self.assertEqual(result, 2)
            self.assertEqual(len(rows), 1)
            self.assertFalse(next(iter(state['jobs'].values()))['processed_once'])
            self.assertEqual(state['status'], 'stopped_for_review')
            _, state, rows = self.run_collection(root, FakeAPI([tweet(), tweet('101')]))
            self.assertEqual(len(rows), 2)

    def test_pilot_quota(self):
        with tempfile.TemporaryDirectory() as folder:
            _, state, rows = self.run_collection(Path(folder), FakeAPI([tweet(), tweet('101')]), per_phase=1)
            self.assertEqual(len(rows), 1)
            self.assertEqual(next(iter(state['jobs'].values()))['status'], 'quota_partial')

    def test_excluded_context_does_not_spend_day_quota(self):
        class PagesAPI(FakeAPI):
            async def search_raw(self, query, limit, kv):
                assert limit == -1
                yield NS(json=lambda:[tweet('90',timestamp='2026-08-30T05:00:00+00:00')])
                yield NS(json=lambda:[tweet('100'),tweet('101')])
        with tempfile.TemporaryDirectory() as folder:
            _,state,rows=self.run_collection(Path(folder),PagesAPI([]),per_day=2)
            self.assertEqual(len(rows),2)
            log=next(iter(state['jobs'].values()))
            self.assertEqual(log['excluded_outside_window'],1)
            self.assertEqual(log['eligible_unique'],2)
            self.assertEqual(log['pages'],2)
            self.assertEqual(log['status'],'eligible_day_limit_partial')

    def test_page_budget_marks_partial(self):
        with tempfile.TemporaryDirectory() as folder:
            _,state,_=self.run_collection(Path(folder),FakeAPI([tweet()]),max_pages=1)
            self.assertEqual(next(iter(state['jobs'].values()))['status'],'page_budget_partial')

    def test_missing_session_never_calls_sdk(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(pipeline, 'SESSION', Path(folder)/'absent.db'), \
             patch.object(pipeline, 'sdk') as sdk:
            with self.assertRaisesRegex(ValueError, 'Sesi belum ada'):
                asyncio.run(pipeline.collect(pipeline.parser().parse_args(['collect'])))
            sdk.assert_not_called()


class PreprocessingTests(unittest.TestCase):
    def test_distinct_ids_with_short_repeated_text_survive(self):
        spec = importlib.util.spec_from_file_location('preprocess', Path(__file__).with_name('03_preprocess.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            raw = root / 'raw'
            raw.mkdir()
            job = pipeline.make_jobs()[0]
            rows = [pipeline.normalize(tweet(str(i), text='MagangHub mengecewakan 😭'), job) for i in (100,101)]
            (raw / 'x_test.jsonl').write_text('\n'.join(json.dumps(row) for row in rows), encoding='utf-8')
            with patch.object(module, 'DIR_RAW', raw), patch.object(module, 'DIR_OUT', root/'out'), \
                 patch.object(module.config, 'FILE_SALT', str(root/'salt')):
                module.main()
            result = module.pd.read_csv(root/'out/maganghub_bersih.csv')
            self.assertEqual(len(result), 2)
            self.assertTrue(result['teks_berulang'].all())
            self.assertTrue(result['teks_pendek'].all())

    def test_minimal_text_preserves_sentiment(self):
        spec = importlib.util.spec_from_file_location('preprocess', Path(__file__).with_name('03_preprocess.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.bersih_minimal('@example MagangHub GAKKK adil 😭!!! https://example.com'),
                         '[USER] MagangHub GAKKK adil 😭!!! [URL]')


if __name__ == '__main__':
    unittest.main()

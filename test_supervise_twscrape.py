from datetime import datetime, timedelta, timezone
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch, Mock

import supervise_twscrape as supervisor


class SupervisorTests(unittest.TestCase):
    def test_retry_budget_stops_after_three_restarts(self):
        state=dict(status='stopped_for_review',jobs={'job':dict(error_type='NoAccountError',finished_at='2026-10-25')})
        child=Mock(returncode=2)
        with patch.object(supervisor,'read_state',return_value=state), \
             patch.object(supervisor,'alive',return_value=False), \
             patch.object(supervisor,'retry_time',return_value=datetime.now(timezone.utc)-timedelta(seconds=1)), \
             patch.object(supervisor,'report') as report, \
             patch.object(supervisor,'refresh_outputs',return_value=True), \
             patch.object(supervisor.subprocess,'Popen',return_value=child) as launch:
            self.assertEqual(supervisor.run(),2)
            self.assertEqual(launch.call_count,3)
            report.assert_called_with('retry_budget_exhausted',3)

    def test_adopting_existing_collector_does_not_launch_another(self):
        running=dict(status='running',process_id=123,run_started_at='2026-10-25T00:00:00+00:00')
        done=dict(running,status='job_pass_finished_not_a_census')
        with patch.object(supervisor,'read_state',side_effect=[running,done]), \
             patch.object(supervisor,'alive',side_effect=[True,False,False]), \
             patch.object(supervisor.time,'sleep'), patch.object(supervisor,'report'), \
             patch.object(supervisor.subprocess,'Popen') as launch:
            self.assertEqual(supervisor.run(),0)
            launch.assert_not_called()

    def test_only_known_account_or_rate_limit_errors_retry(self):
        def state(**details):
            return dict(status='stopped_for_review', jobs={'job':dict(finished_at='2026-10-25', **details)})
        self.assertTrue(supervisor.retry_allowed(state(error_type='NoAccountError')))
        self.assertTrue(supervisor.retry_allowed(state(status='sdk_warning_partial',warnings=['rate_limit'])))
        self.assertFalse(supervisor.retry_allowed(state(error_type='RuntimeError')))
        self.assertFalse(supervisor.retry_allowed(state(status='sdk_warning_partial',warnings=['access_error'])))
        self.assertFalse(supervisor.retry_allowed(dict(status='job_pass_finished_not_a_census')))

    def database(self, folder, active, locks):
        path=Path(folder)/'availability.db'
        with closing(sqlite3.connect(path)) as db:
            # There are deliberately no credential columns to read.
            db.execute('CREATE TABLE accounts (active INTEGER, locks TEXT)')
            db.execute('INSERT INTO accounts VALUES (?,?)', (active,json.dumps(locks)))
            db.commit()
        return path

    def test_waits_at_least_fifteen_minutes_without_mutation(self):
        now=datetime(2026,10,25,16,0,tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as folder:
            path=self.database(folder,1,{'SearchTimeline':(now+timedelta(minutes=20)).isoformat()})
            before=path.read_bytes()
            self.assertEqual(supervisor.retry_time(path,now),now+timedelta(minutes=20,seconds=15))
            self.assertEqual(path.read_bytes(),before)

    def test_inactive_session_and_long_locks_do_not_retry(self):
        now=datetime.now(timezone.utc)
        for active, locks in [(0,{}),(1,{'SearchTimeline':(now+timedelta(hours=2)).isoformat()})]:
            with self.subTest(active=active),tempfile.TemporaryDirectory() as folder:
                self.assertIsNone(supervisor.retry_time(self.database(folder,active,locks),now))

    @unittest.skipUnless(os.name=='nt','Windows process API')
    def test_read_only_process_check_rejects_reused_pid(self):
        self.assertTrue(supervisor.alive(os.getpid(),datetime.now(timezone.utc).isoformat()))
        self.assertFalse(supervisor.alive(os.getpid(),(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()))


if __name__=='__main__':
    unittest.main()

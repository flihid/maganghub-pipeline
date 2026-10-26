"""Local bounded supervisor; never clears account locks or reads cookie columns."""
from datetime import datetime, timedelta, timezone
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

import twscrape_pipeline as pipeline

ROOT = Path(__file__).resolve().parent
PRIVATE = ROOT / '.twscrape'
STATUS = PRIVATE / 'supervisor_status.json'
LOCK = PRIVATE / 'supervisor.lock'


def alive(pid, started_at):
    """Windows read-only process check, also rejecting reused PIDs. None=unknown."""
    if not pid or not started_at:
        return False
    if os.name != 'nt':
        return None
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel.GetProcessTimes.restype = wintypes.BOOL
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x100000 | 0x1000, False, int(pid))
    if not handle:
        return False if ctypes.get_last_error() == 87 else None
    try:
        created, exited, kernel_time, user_time = [wintypes.FILETIME() for _ in range(4)]
        if not kernel.GetProcessTimes(handle, *[ctypes.byref(x) for x in (created, exited, kernel_time, user_time)]):
            return None
        stamp = ((created.dwHighDateTime << 32) | created.dwLowDateTime) / 10_000_000 - 11644473600
        age = datetime.fromisoformat(started_at).timestamp() - stamp
        if not 0 <= age < 120:
            return False
        result = kernel.WaitForSingleObject(handle, 0)
        return True if result == 258 else False if result == 0 else None
    finally:
        kernel.CloseHandle(handle)


def read_state(path):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def retry_allowed(state):
    if state.get('status') != 'stopped_for_review' or not state.get('jobs'):
        return False
    last = max(state['jobs'].values(), key=lambda job: job.get('finished_at', ''))
    return (last.get('error_type') == 'NoAccountError' or
            (last.get('status') == 'sdk_warning_partial' and last.get('warnings') == ['rate_limit']))


def retry_time(database, now):
    # Read only availability metadata. Never SELECT cookies/headers/credentials.
    with closing(sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)) as db:
        accounts = db.execute('SELECT active, locks FROM accounts').fetchall()
    if len(accounts) != 1 or not accounts[0][0]:
        return None
    target = now + timedelta(minutes=15)
    for stamp in json.loads(accounts[0][1] or '{}').values():
        reset = datetime.fromisoformat(stamp)
        if reset.tzinfo is None:
            reset = reset.replace(tzinfo=timezone.utc)
        target = max(target, reset + timedelta(seconds=15))
    return target if target <= now + timedelta(hours=1) else None


def report(status, retries, **extra):
    record = dict(status=status, retries_done=retries, max_retries=3,
                  supervisor_pid=os.getpid(), updated_at=datetime.now(pipeline.WIB).isoformat(), **extra)
    pipeline.write_json(STATUS, record)
    print(json.dumps(record, ensure_ascii=False), flush=True)


def refresh_outputs():
    for script in ('03_preprocess.py', '04_audit_collection.py'):
        if subprocess.run([sys.executable, str(ROOT/script)], cwd=ROOT).returncode:
            return False
    return True


def run(max_retries=3):
    args = pipeline.parser().parse_args(['collect', '--mode', 'full', '--per-day', '300', '--max-raw', '10000'])
    checkpoint = pipeline.checkpoint_for(args)
    retries = 0
    while True:
        state = read_state(checkpoint)
        current = alive(state.get('process_id'), state.get('run_started_at'))
        if current is None:
            report('process_check_unknown_needs_review', retries)
            return 2
        if current:
            report('watching_existing_collector', retries, collector_pid=state['process_id'])
            while alive(state['process_id'], state['run_started_at']) is True:
                time.sleep(10)
            # Existing launcher already refreshes CSVs after its child exits.
            time.sleep(10)
            continue
        if state.get('status') in ('job_pass_finished_not_a_census', 'raw_limit_partial', 'run_job_limit_partial'):
            report('finished', retries, collection_status=state['status'])
            return 0
        if state and not retry_allowed(state):
            report('needs_review_no_automatic_restart', retries, collection_status=state.get('status'))
            return 2
        if state:
            if retries >= max_retries:
                report('retry_budget_exhausted', retries)
                return 2
            target = retry_time(pipeline.SESSION, datetime.now(timezone.utc))
            if target is None:
                report('session_or_cooldown_needs_review', retries)
                return 2
            report('cooldown', retries, next_retry_at=target.astimezone(pipeline.WIB).isoformat())
            while datetime.now(timezone.utc) < target:
                time.sleep(min(10, max(0.1, (target-datetime.now(timezone.utc)).total_seconds())))
            # Recheck before launch in case someone manually resumed during cooldown.
            latest = read_state(checkpoint)
            if latest != state:
                continue
            if alive(latest.get('process_id'), latest.get('run_started_at')) is not False:
                continue
            retries += 1
        report('launching_collector', retries)
        child = subprocess.Popen([sys.executable, str(ROOT/'twscrape_pipeline.py'),
                                  'collect', '--mode', 'full', '--per-day', '300', '--max-raw', '10000'], cwd=ROOT)
        child.wait()
        if not refresh_outputs():
            report('preprocessing_needs_review', retries)
            return 2
        if child.returncode == 0:
            report('finished', retries)
            return 0
        if not read_state(checkpoint) or not retry_allowed(read_state(checkpoint)):
            report('collector_error_needs_review', retries)
            return 2


def main():
    PRIVATE.mkdir(exist_ok=True)
    if LOCK.exists():
        lock = read_state(LOCK)
        if alive(lock.get('pid'), lock.get('started_at')) is not False:
            print('Pengawas lain masih aktif atau tidak dapat diperiksa. Tidak memulai salinan kedua.')
            return 2
        LOCK.unlink()
    with LOCK.open('x', encoding='utf-8') as stream:
        json.dump(dict(pid=os.getpid(), started_at=datetime.now(pipeline.WIB).isoformat()), stream)
    try:
        return run()
    except KeyboardInterrupt:
        report('supervisor_stopped_by_user', 0)
        return 130
    except Exception as error:
        report('supervisor_error_needs_review', 0, error_type=type(error).__name__)
        return 2
    finally:
        LOCK.unlink(missing_ok=True)


if __name__ == '__main__':
    os.chdir(ROOT)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    raise SystemExit(main())

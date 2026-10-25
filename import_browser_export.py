"""Import the local extension's JSON export; no network or credentials required."""
import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import config


def import_export(source, root=Path('data/raw')):
    source = Path(source)
    payload = source.read_bytes()
    data = json.loads(payload.decode('utf-8-sig'))
    if data.get('schema') != 'maganghub-x-export-v1':
        raise ValueError('Bukan ekspor MagangHub X Collector')
    state = data.get('state') or {}
    exported = (state.get('config') or {}).get('phases')
    expected = [dict(name=k, since=s, until=u) for k, (s, u) in config.JENDELA_WAKTU.items()]
    if exported != expected:
        raise ValueError('Fase ekspor berbeda dari config.py. Cocokkan konfigurasi sebelum menggabungkan data.')
    records = data.get('posts')
    if not isinstance(records, list):
        raise ValueError('Daftar posts tidak valid')
    normalized = []
    for row in records:
        if not isinstance(row.get('tweet_id'), str) or not row['tweet_id'].isdigit():
            raise ValueError('ID post harus string digit agar presisi tidak hilang')
        if not isinstance(row.get('text'), str) or not row['text'].strip():
            raise ValueError('Teks post kosong/tidak valid')
        dt = datetime.fromisoformat(row['created_at'].replace('Z', '+00:00'))
        if dt.tzinfo is None:
            raise ValueError('Timestamp harus memiliki zona waktu')
        day = dt.astimezone(ZoneInfo('Asia/Jakarta')).date().isoformat()
        phase = next((k for k, (s, u) in config.JENDELA_WAKTU.items() if s <= day < u), None)
        if phase:
            normalized.append(dict(row, fase=phase))
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    existing = set()
    for file in root.glob('x_*.jsonl'):
        for line in file.read_text(encoding='utf-8').split('\n'):
            if line.strip():
                existing.add(json.loads(line)['tweet_id'])
    added = 0
    for row in normalized:
        if row['tweet_id'] in existing:
            continue
        with (root / ('x_' + row['fase'] + '.jsonl')).open('a', encoding='utf-8') as out:
            out.write(json.dumps(row, ensure_ascii=False) + '\n')
        existing.add(row['tweet_id'])
        added += 1
    digest = hashlib.sha256(payload).hexdigest()
    marker = root / 'extension_imports.json'
    imports = json.loads(marker.read_text(encoding='utf-8')) if marker.exists() else {}
    if digest not in imports:
        with (root / 'browser_collection_log.jsonl').open('a', encoding='utf-8') as out:
            for log in state.get('logs', []):
                record = dict(log, finished_at=log.get('finishedAt'), collector='local_extension_v1', export_id=digest)
                out.write(json.dumps(record, ensure_ascii=False) + '\n')
        imports[digest] = {'exported_at': data.get('exportedAt'), 'posts_in_export': len(records), 'added': added}
        marker.write_text(json.dumps(imports, indent=2), encoding='utf-8')
        (root / ('extension_config_' + digest[:12] + '.json')).write_text(
            json.dumps(state.get('config'), ensure_ascii=False, indent=2), encoding='utf-8')
    return {'exported': len(records), 'added': added, 'total_unique': len(existing)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('export_file', type=Path)
    args = parser.parse_args()
    print(json.dumps(import_export(args.export_file)))

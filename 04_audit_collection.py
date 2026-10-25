"""Audit locally collected X data without network access; preserve manual reviews."""
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import config

RAW = Path('data/raw')
OUT = Path('data/processed')


def jsonl(file):
    return [json.loads(s) for s in file.read_text(encoding='utf-8').split('\n') if s.strip()]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = json.loads((RAW / 'browser_jobs.json').read_text(encoding='utf-8'))
    intervals = {(j['fase'], j['since'], j['until']) for j in jobs}
    logs = jsonl(RAW / 'browser_collection_log.jsonl')
    expected_query = '(' + ' OR '.join(config.KATA_KUNCI) + ')'
    valid_logs = [log for log in logs if log.get('language_filter', 'id') == config.BAHASA
                  and log.get('kueri') == expected_query]
    complete_statuses = ('empty_search', 'exhausted_visible_results')
    coverage = []
    for key in sorted(intervals, key=lambda x: x[1]):
        relevant = [log for log in valid_logs if log.get('fase') == key[0]
                    and log['since'] < key[2] and key[1] < log['until']]
        day = datetime.fromisoformat(key[1]).date()
        end = datetime.fromisoformat(key[2]).date()
        checked = 0
        while day < end:
            next_day = day + timedelta(days=1)
            if any(log['since'] <= day.isoformat() and next_day.isoformat() <= log['until']
                   and log.get('status') in complete_statuses for log in relevant):
                checked += 1
            day = next_day
        days = (end - datetime.fromisoformat(key[1]).date()).days
        status = ('all_daily_jobs_checked' if checked == days else 'partial' if relevant
                  else 'needs_recollection_language_filter')
        log = relevant[-1] if relevant else {}
        coverage.append(dict(fase=key[0], since=key[1], until=key[2],
                             status=status, checked_days=checked, total_days=days, seen=log.get('seen', ''),
                             finished_at=log.get('finished_at', '')))
    pd.DataFrame(coverage).to_csv(OUT / 'cakupan_interval_x.csv', index=False, encoding='utf-8-sig')

    rows = [r for f in RAW.glob('x_*.jsonl') for r in jsonl(f)]
    ids = [r['tweet_id'] for r in rows]
    assert len(ids) == len(set(ids)), 'Duplicate raw IDs require review'
    assert all(r.get('text') and r.get('created_at') for r in rows), 'Missing core fields'
    clean = pd.read_csv(OUT / 'maganghub_bersih.csv', dtype={'post_id': str})
    promo_review = pd.read_csv(OUT / 'review_promosi.csv') if (OUT / 'review_promosi.csv').exists() else pd.DataFrame()
    promo_audit = pd.read_csv(OUT / 'audit_penyaringan_promosi.csv') if (OUT / 'audit_penyaringan_promosi.csv').exists() else pd.DataFrame()
    excluded_promos = int((promo_audit['promosi_status'] == 'exclude').sum()) if len(promo_audit) else 0
    review_path = OUT / 'review_manual_x.csv'
    previous = {}
    if review_path.exists():
        with review_path.open(encoding='utf-8-sig', newline='') as stream:
            previous = {r['post_id']: r for r in csv.DictReader(stream)}
    fields = ['post_id', 'relevance_keep', 'privacy_checked', 'jenis_akun_manual', 'reason']
    with review_path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for post_id in clean['post_id']:
            writer.writerow(previous.get(post_id, dict.fromkeys(fields, '') ) | {'post_id': post_id})
    complete = sum(r['status'] == 'all_daily_jobs_checked' for r in coverage)
    truncated = sum(bool(r.get('text_truncated')) for r in rows)
    report = [
        '# Hasil pengambilan X',
        '',
        'Diperbarui: ' + datetime.now(ZoneInfo('Asia/Jakarta')).isoformat(timespec='seconds'),
        '',
        f'- Unggahan mentah unik: {len(rows)}.',
        f'- Kandidat sesudah pembersihan otomatis: {len(clean)}.',
        f'- Dikecualikan oleh aturan penawaran promosi: {excluded_promos}; ditahan untuk review promosi: {len(promo_review)}.',
        f'- Interval diperiksa sampai kondisi berhenti yang tercatat: {complete}/{len(coverage)}.',
        f'- Teks yang diketahui terpotong dalam data mentah: {truncated}.',
        '- Rentang penelitian: 1 Juli sampai 25 Oktober 2026; batas akhir eksklusif 26 Oktober.',
        '- Metode: lihat collector pada record; DOM browser dan/atau twscrape (pencarian internal X, bukan API resmi berbayar), tab Latest.',
        '- Lima kata kunci digabung dengan OR per interval; bukan lima pencarian terpisah.',
        '- Koreksi filter bahasa: lang:id pada pengambilan awal keliru; uji pembanding membuktikan lang:in mengembalikan unggahan Indonesia. Hasil kosong dengan filter lama tidak dihitung sebagai interval selesai.',
        '- Ada pengambilan tambahan kata kunci maganghub untuk seluruh periode. Parameter aktual tercatat di setiap record.',
        '',
        '## Batas interpretasi',
        '',
        '- empty_search berarti halaman pencarian menampilkan tidak ada hasil, bukan bukti tidak ada percakapan.',
        '- exhausted_visible_results berarti enam putaran tanpa ID baru pada hasil yang terlihat, bukan sensus X.',
        '- Semua kandidat masih memerlukan pemeriksaan relevansi, privasi, serta jenis akun secara manual.',
        '- maganghub_bersih.csv hanya memuat baris tanpa indikasi promosi menurut aturan; ini belum label kebenaran manual.',
        '- Kasus promosi ambigu ditahan di review_promosi.csv dan tetap ada di maganghub_kandidat.csv, termasuk kritik yang perlu konteks.',
        '- Penawaran yang dikecualikan dan alasan/sinyalnya tercatat di audit_penyaringan_promosi.csv; data mentah dipertahankan.',
        '- Daftar jenis akun bawaan tidak mencakup semua akun organisasi; label publik perlu diperiksa.',
        '- Sampel tidak dapat dipakai membandingkan fase yang tidak memiliki data.',
        '- Sesi twscrape dimasukkan pengguna secara lokal dan tidak dimasukkan ke dataset atau Git.',
        '- Status twscrape berakhiran partial/unverified tidak dihitung sebagai bukti cakupan lengkap.',
        '',
        '## Berkas',
        '',
        '- Data mentah: ../raw/x_*.jsonl',
        '- Log pengambilan: ../raw/browser_collection_log.jsonl',
        '- Cakupan: cakupan_interval_x.csv',
        '- Kandidat analisis: maganghub_bersih.csv',
        '- Penyaringan: log_preprocessing.csv',
        '- Tinjauan manusia: review_manual_x.csv (keputusan belum diisi otomatis)',
        '',
    ]
    (OUT / 'HASIL_PENGAMBILAN_X.md').write_text('\n'.join(report), encoding='utf-8')
    print(f'Raw={len(rows)}, candidates={len(clean)}, checked={complete}/{len(coverage)}, truncated={truncated}')


if __name__ == '__main__':
    main()

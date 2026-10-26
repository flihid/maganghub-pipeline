"""Explainable triage of promotional posts, separate from relevance/sentiment.

Rules identify OFFERS, never infer that an author is a bot (repeated text or posting
frequency alone is not evidence of automation). Ambiguous references to services,
requests for help and criticism stay available for human review or analysis.

promosi_v3 (audit TK2) changes versus v2:
- A single cue (CV/joki/DM/jasa, 'katanya', 'gratis', a money amount, hashtags) is never
  enough to hold a post. 'Rp 3 juta uang saku', '46 ribu lulusan', and 'katanya cair' are
  ordinary program discussion, so they stay 'keep' (signals are still recorded).
- An offer needs seller voice/headline + service + a commercial cue (contact, price, sales proof).
- Requests for a service ('ada jasa review cv?', 'yg pernah make jasa bikin CV') are not ads.
- Added clear non-career commercial offers (referral/cashback codes).

promosi_v4 (26 Okt 2026): pengumuman lowongan dari instansi/perusahaan mitra ("X membuka
kesempatan magang melalui MagangHub ... kirim lamaran melalui ...") di-exclude. Isinya relevan
dengan program, tetapi bukan opini publik dan berbentuk template siaran. Syarat: suara pengumuman
(judul lowongan, "membuka kesempatan", open recruitment) + instruksi melamar atau detail lowongan,
atau "membuka kesempatan ... melalui MagangHub/Kemnaker". Klausa relatif/pertanyaan ("yang buka
lowongan", "ga open recruitment", "mau tanya") tidak dihitung sebagai pengumuman.
"""
import re
import unicodedata

VERSION = 'promosi_v4'

PATTERNS = {
    'layanan': r'\bcv\b|\bresume\b|linkedin|cover\s*letter|surat\s+lamaran|portofolio|\bjoki\w*|psikotes|\btpa\b|mentoring|konsul(?:tasi)?\s+karir|latihan\s+interview|interview\s+practice|lolosin',
    'penawaran': (r'\b(?:aku+|saya|kami|admin)\s+(?:lagi\s+|juga\s+)?(?:open|buka|bantu\w*|terima|provide|melayani|handle)\b'
                  r'|\b(?:open|buka)\s+(?:jasa|joki|order|slot|mentoring|review)\b'
                  r'|\b(?:bisa|boleh)\b.{0,35}\bdi\s+(?:aku+|saya|sini)\b|\bdi\s+(?:aku+|saya)\s+(?:bisa|aja|ya+h?)\b'
                  r'|\b(?:aku+|saya)\s+(?:bisa|siap)\s+bantu\w*\b|\bhadir+\s+yu+k+\b|\bsini\s+ka+k+\b'
                  r'|\b(?:grab|order)\s+(?:your|now|sekarang)\b|\b(?:yang|yg)\s+mau\s+(?:review|bikin|dibantu|konsul)\w*\b.{0,80}\b(?:dm|chat|wa)\b|\blast\s+\d+\s+slot|\bslot\s+(?:terbatas|tersisa)'),
    'penawaran_eksplisit': (r'\b(?:open|buka)\s+(?:jasa|joki|order|slot)\b|\bjasa\s+joki\b'
                            r'|\bopen\s+form\s+order\b|\border\s+layanan\s+jasa'),
    'jasa_judul': r'\bjasa\s+(?:joki|bikin|buat|pembuatan|review)\b|\bjoki\s+(?:cv|tes|psikotes|tpa|maganghub|magang)\b',
    'kontak': (r'\b(?:wa|whatsapp|dm|chat)\b.{0,25}\b(?:bio+|profil\w*|link)\b'
               r'|\b(?:cek|check|klik|hubungi|link)\b.{0,15}\b(?:bio+|profil\w*|wa|whatsapp)\b'
               r'|\bdm\s+(?:aku|aja|ya+|me|sajo|saja)\b|\bchat\s+(?:aku|aja)\b|wa\.me/|t\.me/|lemme\s+know|\bhmu\b'
               r'|\bchat\s+(?:ke\s+)?(?:kak\s+)?@\w+'),
    'harga': r'\brp\.?\s*\d|\b\d+(?:[.,]\d+)?\s*(?:k|rb)\b|\bfee\b|\b(?:cuma|only|mulai|start)\s+(?:rp\.?\s*)?\d',
    'bukti_jual': (r'\btesti\w*|\btrusted\w*|\bfree\s+(?:revisi|konsultasi)|\bwording\b|career\s+package|\bstart\s+\d+'
                   r'|\d+\+?\s+(?:testi\w*|jobseeker|klien|client)|\bbanyak\s+klien|\b\d+\s+tahun\s+di\s+hr\b'
                   r'|\bhr\s+\d+\s+tahun\b|\b(?:banyak|udah\s+banyak)\s+yang\s+(?:tembus|lolos)\b'),
    'paket_layanan': r'\b1\.\s*(?:review|upgrade)\s+cv.{0,80}\b2\.\s*(?:review|upgrade)\s+cv',
    'referal': r'kode\s+(?:referal|referral|promo)|referral\s+code|cashback',
    'permintaan': (r'\b(?:ada(?:kah)?|cari|nyari|butuh|need|info|rekomendasi|spill|recommend)\b.{0,60}\b(?:jasa|review\s+(?:untuk\s+)?cv|joki)\b'
                   r'|\b(?:pernah|yg|yang)\s+(?:make|pake|pakai|nyoba)\s+jasa\b|\bada\s+yang\s+bisa\s+(?:bikin|editin|review)|\bwtb\b|\bdrop\s+(?:pl|pricelist|fee|price|harga)\b'),
    'kritik': (r'\b(?:jangan|stop|hindari)\b.{0,30}\b(?:joki|jasa|iklan)\b'
               r'|\b(?:kesal|kesel|muak|risih|capek|penuh|isinya|marak)\b.{0,70}\b(?:iklan|jasa|joki|promo)\b'
               r'|\b(?:iklan|jasa|joki|promo)\b.{0,70}\b(?:mengganggu|nyebelin|penipuan|menipu|mahal|merugikan)\b'
               r'|\b(?:dia\s+(?:bilang|nulis)|contoh\s+iklan)\b'),
    'indikasi_lama': r'link\s*di\s*bio|klik\s*link|cek\s*bio|dm\s*(?:aja|untuk|utk)|\bjasa\b|\bjoki\b|\bpromo\b|\bdiskon\b|bit\.ly|slot\s*gacor|judi|togel',
    'judi': r'slot\s*gacor|\btogel\b|\bmaxwin\b',
    'acara_promosi': (r'(?:^|[.!?✨🚀📢]\s*|\byu+k,?\s+)(?:ikuti|ikut|gabung|daftar)\w*\s+(?:di\s+)?'
                      r'(?:webinar|bootcamp|pelatihan|kelas|workshop|sertifikasi|course)\b'),
    'lowongan_judul': (r'^\W*(?:lowongan|loker|info\s+loker|open\s+recruit\w*|we\W?re\s+hiring|hiring|calling\s+all'
                       r'|open\s+magang|urgent\w*\s+needed|dibuka\s+lowongan)\b'
                       r'|\b(?:open\s+magang|urgently\s+needed|dibuka\s+lowongan\s+magang|jangan\s+lewatkan\s+kesempatan)\b'
                       r'|\b(?:lagi|sedang)\s+buka\s+loker\b'
                       r'|\b(?:membuka|buka)\s+(?:kesempatan|lowongan|rekrutmen|recruitment|pendaftaran\s+magang)\b'
                       r'|\bopen\s+recruit\w*|\bwe\W?re\s+hiring\b'
                       r'|\b(?:lagi|sedang|kembali)\s+(?:buka|membuka)\s+(?:kesempatan|lowongan|magang|opportunity|posisi)\b'
                       r'|\blowongan\s+magang\s+(?:di\s+)?(?:pt|cv|rs\w*|puskesmas|bank|balai|dinas|kantor|bpjs|bps|universitas)\b'
                       r'|\blowongan\s+maganghub\s+batch\s*\d\s+tahun'),
    'lowongan_via_program': (r'\bmembuka\s+(?:kesempatan|lowongan|program)\b.{0,80}'
                             r'\b(?:melalui|lewat|via|di|dalam)\s+(?:program\s+)?(?:magang\s*hub|maganghub|magang\s+nasional'
                             r'|pemagangan\s+nasional|magang\s+kemnaker|kemnaker)'),
    'lowongan_instruksi': (r'kirim\w*\s+(?:lamaran|cv)'
                           r'|\b(?:daftar|apply|lamar)\w*\s+(?:sekarang\s+)?(?:melalui|via|lewat|di\s+(?:web|website|situs|link|laman)|now)\b'
                           r'|cek\s+lowongan\w*\s+di|link\s+(?:pendaftaran|daftar|apply)|pendaftaran\s+(?:dibuka|ditutup)'
                           r'|deadline\s*:|batas\s+(?:akhir\s+)?pendaftaran|maganghub\.kemnaker\.go\.id'
                           r'|\bdaftar\s+sekarang\b|\bsilah?kan\s+apply\b|info\s+lengkap\s+cek'),
    'lowongan_detail': r'\bposisi\b|kualifikasi|persyaratan|📍|\bkuota\b|job\s*desc|jobdesk|benefit|penempatan\s*:',
    'lowongan_bukan': (r'\b(?:yg|yang|ga|gak|nggak|ngga|tidak|jarang|jarng|jrg|tinggal)\s+(?:\w+\s+){0,2}(?:open|buka|membuka)\b'
                       r'|\b(?:mau|mo)\s+(?:tanya|nanya)\b|\baku\s+(?:apply|daftar|lamar)'
                       r'|\bada\s+(?:ga|gak|nggak|ngga|kah)\b|\brekomendasi\b|\brecommend\w*'),
}
COMPILED = {key: re.compile(value, re.I) for key, value in PATTERNS.items()}
TANYA_PENJUAL = re.compile(r'\b(?:ada(?:kah)?|siapa)\s+(?:\w+\s+){0,2}(?:yg|yang)\s+(?:\w+\s+)?(?:buka|open|terima|jual|bisa)\b', re.I)


def _hasil(keputusan, alasan, cues):
    return dict(keputusan=keputusan, alasan=alasan, sinyal=','.join(sorted(cues)))


def klasifikasi_promosi(text, max_hashtag=5):
    text = re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', str(text))).strip()
    cues = {key for key, pattern in COMPILED.items() if pattern.search(text)}
    if len(re.findall(r'#\w+', text)) > max_hashtag:
        cues.add('tagar_banyak')
    seller = bool(cues & {'penawaran', 'penawaran_eksplisit', 'jasa_judul'})
    komersial = bool(cues & {'kontak', 'harga', 'bukti_jual'})
    if 'judi' in cues and 'kritik' not in cues:
        return _hasil('exclude', 'promosi_judi', cues)
    if 'referal' in cues and ('harga' in cues or 'promo' in text.lower()) and 'kritik' not in cues:
        return _hasil('exclude', 'promosi_komersial_kode_referal', cues)
    if 'kritik' in cues:
        return _hasil('review', 'kritik_atau_kutipan_layanan', cues)
    if TANYA_PENJUAL.search(text) and not cues & {'kontak', 'harga', 'bukti_jual'}:
        # 'Ada yg buka jasa review cv?' = mencari penjual, bukan menjual.
        cues.add('permintaan')
        return _hasil('keep', 'permintaan_layanan_bukan_penawaran', cues)
    pengumuman = bool(cues & {'lowongan_judul', 'lowongan_via_program'})
    if 'lowongan_bukan' in cues and 'lowongan_instruksi' not in cues:
        pengumuman = False  # 'yang buka lowongan', 'ga open recruitment', 'mau tanya' = bukan pengumuman
    if pengumuman and ('lowongan_via_program' in cues or cues & {'lowongan_instruksi', 'lowongan_detail'}):
        return _hasil('exclude', 'pengumuman_lowongan_mitra', cues)
    if 'acara_promosi' in cues and 'permintaan' not in cues:
        return _hasil('exclude', 'promosi_acara_pelatihan', cues)
    if {'layanan', 'kontak', 'bukti_jual'} <= cues:
        # 'Chat kak @x buat review CV, HR 6 tahun, udah banyak yang tembus BUMN' = iklan titipan.
        return _hasil('exclude', 'layanan_dengan_kontak_dan_bukti_jual', cues)
    if {'paket_layanan', 'kontak'} <= cues:
        return _hasil('exclude', 'paket_layanan_dengan_ajakan_kontak', cues)
    if 'permintaan' in cues and not cues & {'penawaran', 'penawaran_eksplisit', 'kontak', 'bukti_jual'}:
        # Permintaan jasa bukan iklan. Tetap di korpus; relevansi dinilai terpisah.
        return _hasil('keep', 'permintaan_layanan_bukan_penawaran', cues)
    if re.search(r'\bgratis\b|tanpa\s+biaya|\bfree\b(?!\s+(?:revisi|konsultasi))', text, re.I) \
            and 'harga' not in cues and seller and 'layanan' in cues:
        return _hasil('review', 'bantuan_gratis_perlu_konteks', cues)
    if 'penawaran_eksplisit' in cues and 'layanan' in cues:
        return _hasil('exclude', 'penawaran_eksplisit_jasa_atau_joki', cues)
    if seller and 'layanan' in cues and komersial:
        return _hasil('exclude', 'penawaran_layanan_dengan_kontak_harga_atau_testimoni', cues)
    if {'layanan', 'harga', 'bukti_jual'} <= cues:
        return _hasil('exclude', 'layanan_berharga_dengan_bukti_jual', cues)
    if 'penawaran' in cues and 'harga' in cues and cues & {'bukti_jual', 'kontak'}:
        return _hasil('exclude', 'penawaran_berharga_dengan_kontak_atau_testimoni', cues)
    if seller and ('layanan' in cues or komersial):
        return _hasil('review', 'indikasi_penawaran_belum_pasti', cues)
    if 'layanan' in cues and 'kontak' in cues:
        return _hasil('review', 'layanan_dengan_ajakan_kontak', cues)
    if 'tagar_banyak' in cues and cues & {'layanan', 'kontak', 'harga'}:
        return _hasil('review', 'tagar_banyak_dengan_sinyal_komersial', cues)
    return _hasil('keep', 'tanpa_penawaran_terdeteksi', cues)

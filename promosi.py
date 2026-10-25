"""Explainable triage of promotional posts, separate from relevance/sentiment.

Rules identify offers, never infer that an author is a bot. Ambiguous references
to services, requests for help and criticism remain available for human review.
"""
import re
import unicodedata

VERSION = 'promosi_v2'

PATTERNS = {
    'layanan': r'\bcv\b|\bresume\b|linkedin|cover\s*letter|\bjoki\b|psikotes|\btpa\b|mentoring|konsul(?:tasi)?\s+karir|latihan\s+interview|interview\s+practice',
    'penawaran': r'\b(?:aku+|saya|kami)\s+(?:lagi\s+)?(?:open|buka)\b|\b(?:open|buka)\s+(?:jasa|joki|order|mentoring)\b|\bjasa\s+(?:bikin|buat|pembuatan)\b|\b(?:bisa|boleh)\b.{0,35}\bdi\s+(?:aku+|saya)\b|\b(?:aku+|saya)\s+(?:bisa|siap)\s+bantu\w*\b|\bhadir+\s+yu+k+\b',
    'penawaran_pribadi': r'\b(?:aku+|saya|kami)\s+(?:lagi\s+)?(?:open|buka|bisa\s+bantu)\b|\bdi\s+(?:aku+|saya)\b',
    'kontak': r'\b(?:wa|whatsapp|dm|chat)\b.{0,25}\b(?:bio+|profil\w*|link)\b|\b(?:cek|check|hubungi)\b.{0,15}\b(?:bio+|profil\w*|wa|whatsapp)\b|wa\.me/|t\.me/',
    'harga': r'\b(?:rp\.?\s*)?\d+(?:[.,]\d+)?\s*(?:k\b|rb\b|ribu\b)|\brp\.?\s*\d+',
    'bukti_jual': r'\btesti\w*|\btrusted\w*|\bfree\s+(?:revisi|konsultasi)|\bwording\b|career\s+package|\bstart\s+\d+',
    'paket_layanan': r'\b1\.\s*(?:review|upgrade)\s+cv.{0,80}\b2\.\s*(?:review|upgrade)\s+cv',
    'permintaan': r'\b(?:ada(?:kah)?|cari|nyari|butuh|rekomendasi|spill)\b.{0,60}\b(?:jasa|review\s+(?:untuk\s+)?cv|joki)\b',
    'kritik': r'\b(?:jangan|stop|hindari)\b.{0,30}\b(?:joki|jasa|iklan)\b|\b(?:kesal|kesel|muak|risih|capek|penuh|isinya|marak)\b.{0,70}\b(?:iklan|jasa|joki|promo)\b|\b(?:iklan|jasa|joki|promo)\b.{0,70}\b(?:mengganggu|nyebelin|penipuan|menipu|mahal|merugikan)\b|\b(?:katanya|dia\s+(?:bilang|nulis)|contoh\s+iklan)\b',
    'indikasi_lama': r'link\s*di\s*bio|klik\s*link|cek\s*bio|dm\s*(?:aja|untuk|utk)|\bjasa\b|\bjoki\b|\bpromo\b|\bdiskon\b|bit\.ly|slot\s*gacor|judi|togel',
}
COMPILED = {key: re.compile(value, re.I) for key, value in PATTERNS.items()}


def klasifikasi_promosi(text, max_hashtag=5):
    text = re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', str(text))).strip()
    cues = {key for key, pattern in COMPILED.items() if pattern.search(text)}
    if len(re.findall(r'#\w+', text)) > max_hashtag:
        cues.add('tagar_banyak')
    evidence = ','.join(sorted(cues))
    if 'kritik' in cues:
        return dict(keputusan='review', alasan='kritik_atau_kutipan_layanan', sinyal=evidence)
    if re.search(r'\bgratis\b|tanpa\s+biaya', text, re.I) and 'harga' not in cues:
        return dict(keputusan='review', alasan='bantuan_gratis_perlu_konteks', sinyal=evidence)
    if {'paket_layanan', 'kontak'} <= cues:
        return dict(keputusan='exclude', alasan='paket_layanan_dengan_ajakan_kontak', sinyal=evidence)
    if 'permintaan' in cues and 'penawaran_pribadi' not in cues:
        return dict(keputusan='review', alasan='permintaan_layanan_bukan_penjual_pasti', sinyal=evidence)
    if 'penawaran' in cues and 'layanan' in cues:
        return dict(keputusan='exclude', alasan='penawaran_layanan_karier_atau_joki', sinyal=evidence)
    if {'layanan', 'harga', 'bukti_jual'} <= cues and 'permintaan' not in cues:
        return dict(keputusan='exclude', alasan='layanan_berharga_dengan_bukti_jual', sinyal=evidence)
    if cues & {'kontak', 'harga', 'bukti_jual', 'permintaan', 'indikasi_lama', 'tagar_banyak'}:
        return dict(keputusan='review', alasan='indikasi_promosi_belum_pasti', sinyal=evidence)
    return dict(keputusan='keep', alasan='tanpa_penawaran_terdeteksi', sinyal=evidence)

"""Cakupan pengambilan per tanggal WIB dari log/checkpoint aktual (bukan interval browser lama).

Kategori status_ringkas per (fase, tanggal) berdasarkan percobaan twscrape:
  belum_diambil            tidak ada percobaan twscrape untuk tanggal itu
  kena_batas               percobaan TERAKHIR berhenti karena batas harian/halaman/kuota (partial)
  stream_habis_unverified  percobaan terakhir: stream SDK habis (bukan sensus)
  tanpa_baris_unverified   SDK tidak mengembalikan baris (bukan bukti tidak ada percakapan)
  galat_atau_terputus      galat SDK/timeout/interupsi pada percobaan terakhir
'pernah_kena_batas' ditandai terpisah karena tanggal yang pernah dibatasi bisa kurang terwakili
walaupun percobaan terakhir habis. Tidak ada status yang berarti "lengkap".
"""
from __future__ import annotations

import csv
import io
import json
from datetime import date, timedelta
from pathlib import Path

BATAS = {"daily_limit_partial", "eligible_day_limit_partial", "page_budget_partial", "quota_partial"}
GALAT = {"sdk_error_partial", "interrupted_partial", "timeout_partial", "access_error_partial"}


def _ringkas(status: str | None) -> str:
    if status is None:
        return "belum_diambil"
    if status in BATAS:
        return "kena_batas"
    if status == "stream_ended_unverified":
        return "stream_habis_unverified"
    if status == "no_rows_unverified":
        return "tanpa_baris_unverified"
    if status in GALAT or status.endswith("_partial"):
        return "galat_atau_terputus"
    return "lainnya:" + status


def percobaan_twscrape(meta: Path) -> list[dict]:
    """Gabungkan log per kueri dan job di checkpoint; dedup berdasarkan (fase, since, started_at)."""
    entri = {}
    log = meta / "browser_collection_log.jsonl"
    if log.exists():
        for baris in log.read_bytes().split(b"\n"):
            if baris.strip():
                r = json.loads(baris)
                if str(r.get("collector", "")).startswith("twscrape"):
                    entri[(r.get("fase"), r.get("since"), r.get("started_at"))] = dict(r, sumber="log")
    for f in sorted(meta.glob("twscrape_state_*.json")):
        st = json.loads(f.read_text(encoding="utf-8"))
        for job in st.get("jobs", {}).values():
            kunci = (job.get("fase"), job.get("since"), job.get("started_at"))
            entri.setdefault(kunci, dict(job, sumber=f.name))
            entri[kunci]["checkpoint"] = f.name
            entri[kunci]["checkpoint_settings_per_day"] = st.get("settings", {}).get("per_day")
    return sorted(entri.values(), key=lambda r: (r.get("since") or "", r.get("started_at") or ""))


def cakupan_harian_x(meta: Path, jendela: dict) -> list[dict]:
    attempts = percobaan_twscrape(meta)
    hasil = []
    for fase, (since, until) in jendela.items():
        d, akhir = date.fromisoformat(since), date.fromisoformat(until)
        while d < akhir:
            hari = d.isoformat()
            a = [r for r in attempts if r.get("fase") == fase and r.get("since") == hari]
            terakhir = a[-1] if a else None
            v3 = [r for r in a if r.get("adapter_version") == 3 or "since_time" in str(r.get("search_query", ""))]
            hasil.append(dict(
                fase=fase, tanggal=hari, n_percobaan=len(a),
                status_semua=";".join(r.get("status", "") for r in a),
                status_terakhir=terakhir.get("status") if terakhir else None,
                status_ringkas=_ringkas(terakhir.get("status") if terakhir else None),
                status_terakhir_v3=v3[-1].get("status") if v3 else None,
                pernah_kena_batas=any(r.get("status") in BATAS for r in a),
                pernah_galat=any(r.get("status") in GALAT for r in a),
                seen_maks=max((r.get("seen") or 0) for r in a) if a else None,
                added_total=sum((r.get("added") or 0) for r in a) if a else None,
                percobaan_terakhir_mulai=terakhir.get("started_at") if terakhir else None,
            ))
            d += timedelta(days=1)
    return hasil


def cakupan_threads(meta: Path) -> list[dict]:
    """Log Threads apa adanya per kueri, plus tanggal tertua yang sempat terlihat."""
    f = meta / "log_scraping_threads.csv"
    if not f.exists():
        return []
    return list(csv.DictReader(io.StringIO(f.read_text(encoding="utf-8-sig"))))

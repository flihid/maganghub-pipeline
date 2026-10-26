"""Tes preprocessing TK2. Jalankan: python -m unittest test_preprocess_tk2 -v"""
import csv
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import relevansi
from promosi import klasifikasi_promosi
from tk2prep import duplikat, muat, pipeline, review, snapshot, teks

import config


def rec(pid, text, created="2026-08-31T05:00:00+00:00", **kw):
    base = dict(tweet_id=pid, username="pengguna_" + str(pid)[-3:], url="https://x.com/u/status/" + str(pid),
                text=text, created_at=created, post_lang="in", n_reply=0, n_repost=0, n_like=1, n_quote=0,
                conversation_id=str(pid), content_type="original", author_missing=False, fase="fase1_pengumuman",
                kueri='(maganghub OR "magang hub" OR "magang nasional" OR "magang kemnaker" OR "pemagangan nasional")',
                language_filter="in", since="2026-08-31", until="2026-09-01",
                scraped_at="2026-10-25T22:00:00+07:00", text_truncated=None, collector="twscrape_0.20.1")
    base.update(kw)
    return base


def tulis_jsonl(path, rows, raw_text=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = raw_text if raw_text is not None else "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    path.write_bytes(data.encode("utf-8") if isinstance(data, str) else data)


class Lingkungan:
    """Root sementara berisi data/raw; menjalankan snapshot + pipeline seperti CLI."""

    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.raw = self.root / "data/raw"
        self.raw.mkdir(parents=True)
        self.ann = self.root / "data/annotations"

    def jalankan(self):
        m = snapshot.buat_snapshot(self.root, self.raw, self.root / "data/interim/snapshots")
        folder = self.root / "data/interim/snapshots" / m["snapshot_id"]
        hasil = pipeline.proses(self.root, folder, self.root / "data/processed", self.ann)
        df = pd.read_csv(hasil["out"] / "dataset_x_semua_keputusan.csv", dtype={"post_id": str},
                         keep_default_na=False)
        return m, hasil, df.set_index("post_id")

    def close(self):
        self.tmp.cleanup()


class TestWaktuDanFase(unittest.TestCase):
    def test_batas_wib_interval_setengah_terbuka(self):
        j = config.JENDELA_WAKTU
        dt = lambda s: datetime.fromisoformat(s)
        self.assertEqual(pipeline.tentukan_fase(dt("2026-08-31T16:59:59+00:00"), j), "fase1_pengumuman")
        self.assertEqual(pipeline.tentukan_fase(dt("2026-08-31T17:00:00+00:00"), j), "fase2_seleksi")
        self.assertEqual(pipeline.tentukan_fase(dt("2026-06-30T17:00:00+00:00"), j), "fase1_pengumuman")
        self.assertIsNone(pipeline.tentukan_fase(dt("2026-06-30T16:59:59+00:00"), j))
        self.assertIsNone(pipeline.tentukan_fase(dt("2026-10-25T17:00:00+00:00"), j))  # 26 Okt WIB, eksklusif

    def test_timestamp_tanpa_zona_dikarantina(self):
        r, alasan = muat.validasi_record(rec("1", "MagangHub", created="2026-08-31T05:00:00"), "x", "f", 1)
        self.assertIsNone(r)
        self.assertEqual(alasan, "timestamp_tanpa_zona_waktu")


class TestValidasi(unittest.TestCase):
    def test_id_panjang_tetap_string(self):
        r, _ = muat.validasi_record(rec(2094406422507446499, "MagangHub"), "x", "f", 1)
        self.assertEqual(r["post_id"], "2094406422507446499")
        self.assertIn("post_id_numerik_dikonversi_string", r["flags_validasi"])
        r, alasan = muat.validasi_record(rec(2.094406422507446e18, "MagangHub"), "x", "f", 1)
        self.assertEqual(alasan, "post_id_float_presisi_hilang")

    def test_missing_bukan_nol(self):
        row = rec("5", "MagangHub")
        del row["n_quote"]
        row["n_like"] = None
        r, _ = muat.validasi_record(row, "x", "f", 1)
        self.assertIsNone(r["n_quote"])
        self.assertIsNone(r["n_like"])
        self.assertEqual(r["n_reply"], 0)
        self.assertIn("n_quote_tidak_dikumpulkan", r["flags_validasi"])
        self.assertEqual(muat.normalisasi_metrik(-3), (None, "metrik_negatif"))

    def test_normalisasi_flag_lama(self):
        for v, e in [(True, True), ("true", True), (1.0, True), ("False", False), (0, False),
                     (None, None), ("", None), (float("nan"), None), ("null", None)]:
            self.assertEqual(muat.normalisasi_bool(v), e, v)

    def test_author_missing_tidak_diberi_identitas_bersama(self):
        self.assertIsNone(pipeline.hash_user(None, "garam"))
        self.assertNotEqual(pipeline.hash_user("a", "garam"), pipeline.hash_user("b", "garam"))

    def test_u2028_tidak_memecah_record(self):
        data = (json.dumps(rec("9", "MagangHub baris dua tiga"), ensure_ascii=False) + "\n").encode()
        self.assertEqual(len(list(muat.pisah_baris_jsonl(data))), 1)
        self.assertGreater(len(data.decode().splitlines()), 1)  # alasan tidak memakai splitlines


class TestDedup(unittest.TestCase):
    def _v(self, text, trunc, scraped, like):
        r, _ = muat.validasi_record(rec("77", text, text_truncated=trunc, scraped_at=scraped, n_like=like),
                                    "x", "f", 1)
        return r

    def test_teks_lengkap_dipilih_metrik_terbaru(self):
        pendek = self._v("MagangHub uang saku…", True, "2026-10-26T10:00:00+07:00", 50)
        penuh = self._v("MagangHub uang saku belum cair sampai sekarang", False, "2026-10-25T10:00:00+07:00", 10)
        hasil, konflik = muat.dedup([pendek, penuh])
        self.assertEqual(len(hasil), 1)
        self.assertTrue(hasil[0]["text"].endswith("sekarang"))
        self.assertEqual(hasil[0]["n_like"], 50)       # metrik dari pengambilan terbaru
        self.assertTrue(hasil[0]["konflik_teks"] and hasil[0]["konflik_metrik"])
        self.assertEqual(len(konflik), 2)

    def test_none_tidak_dianggap_bukti_lengkap(self):
        unknown = self._v("MagangHub teks yang lebih panjang sekali", None, "2026-10-25T10:00:00+07:00", 1)
        lengkap = self._v("MagangHub teks", False, "2026-10-25T10:00:00+07:00", 1)
        hasil, _ = muat.dedup([unknown, lengkap])
        self.assertEqual(hasil[0]["text"], "MagangHub teks")
        self.assertIs(hasil[0]["text_truncated"], False)


class TestTeks(unittest.TestCase):
    def test_minimal_menjaga_emoji_negasi_kapital(self):
        raw = "@budi Uang saku BELUM cair, gak jelas!!! 👩🏻‍💼😭 &amp; https://t.co/x #MagangHub"
        m = teks.teks_minimal(raw)
        self.assertIn("BELUM", m)
        self.assertIn("gak", m)
        self.assertIn("!!!", m)
        self.assertIn("‍", m)
        self.assertIn("😭", m)
        self.assertIn("#MagangHub", m)
        self.assertIn("[USER]", m)
        self.assertIn("[URL]", m)
        self.assertNotIn("budi", m)
        self.assertIn("&", m)
        for v in (teks.teks_sentimen(m), teks.teks_embedding(m)):
            self.assertIn("BELUM", v)
            self.assertIn("😭", v)
        self.assertIn("belum", teks.teks_topik(m).split())
        self.assertIn("gak", teks.teks_topik(m).split())

    def test_slang_opsional_reversible_tanpa_kata_ambigu(self):
        s, ganti = teks.teks_sentimen_slang("u sm kl gak bisa")
        self.assertEqual(s, "u sm kl tidak bisa")
        self.assertEqual(ganti, [(8, "gak", "tidak")])

    def test_pii_dimasking(self):
        m = teks.teks_minimal("hubungi 0812-3456-7890 atau a.b@mail.com")
        self.assertIn("[PHONE]", m)
        self.assertIn("[EMAIL]", m)
        self.assertEqual(teks.audit_pii("nama saya Budi"), ["nama_diri"])


class TestRelevansiPromosi(unittest.TestCase):
    OR = '(maganghub OR "magang hub" OR "magang nasional")'

    def test_or_tidak_dianggap_jangkar(self):
        self.assertFalse(relevansi.dari_jangkar_tunggal(self.OR))
        self.assertTrue(relevansi.dari_jangkar_tunggal("maganghub"))
        self.assertEqual(relevansi.nilai_relevansi("uang saku batch 2 belum cair", [self.OR])[0], "konteks_or")
        self.assertEqual(relevansi.nilai_relevansi("uang saku batch 2 belum cair", ["maganghub"])[0],
                         "konteks_jangkar")
        self.assertEqual(relevansi.nilai_relevansi("enaknya self reward apa ya", [self.OR])[0], "tanpa_bukti")
        self.assertEqual(relevansi.nilai_relevansi("@maganghub_id kapan?", [self.OR])[0], "eksplisit_handle")
        self.assertEqual(relevansi.nilai_relevansi("#MagangHub jelek", [self.OR])[0], "eksplisit")

    def test_kompatibilitas_tandai_relevansi(self):
        df = pd.DataFrame(dict(platform="x", tweet_id=["1", "2"], kueri=[self.OR, "maganghub"],
                               text=["uang saku batch 2", "uang saku batch 2"]))
        self.assertEqual(list(relevansi.tandai_relevansi(df)), ["", "konteks"])

    def test_iklan_vs_kritik_permintaan_diskusi(self):
        k = lambda t: klasifikasi_promosi(t)["keputusan"]
        self.assertEqual(k("Aku open review CV MagangHub, WA di bio"), "exclude")
        self.assertEqual(k("JASA JOKI BIKIN CV ATS 📩 CUMA 30K"), "exclude")
        self.assertNotEqual(k("Search MagangHub isinya iklan joki CV doang, muak"), "exclude")
        self.assertEqual(k("Ada yg buka jasa review cv buat magang hub ga ya"), "keep")
        self.assertEqual(k("Review dong yg pernah make jasa bikin CV ATS"), "keep")
        self.assertEqual(k("uang saku MagangHub Rp 3,5 juta katanya cair besok"), "keep")
        self.assertEqual(k("46 Ribu Lulusan Lolos Magang Nasional 2026 #a #b #c"), "keep")
        self.assertEqual(k("DM aku kalau mau tanya pengalaman MagangHub"), "keep")


class TestDuplikat(unittest.TestCase):
    def test_negasi_dan_emoji_mencegah_penggabungan(self):
        recs = []
        for i, t in enumerate(["Uang saku MagangHub batch 2 sudah cair hari ini alhamdulillah 😍",
                               "Uang saku MagangHub batch 2 belum cair hari ini alhamdulillah 😍",
                               "Uang saku MagangHub batch 2 sudah cair hari ini alhamdulillah 😭",
                               "Uang saku MagangHub batch 2 sudah cair hari ini alhamdulillah 😍!"]):
            m = teks.teks_minimal(t)
            recs.append(dict(platform="x", post_id=str(i), text_minimal=m, text_embedding=teks.teks_embedding(m)))
        duplikat.kelompokkan(recs)
        self.assertIsNotNone(recs[0]["near_dup_grup"])
        self.assertEqual(recs[0]["near_dup_grup"], recs[3]["near_dup_grup"])
        self.assertNotEqual(recs[0]["split_group_id"], recs[1]["split_group_id"])  # sudah vs belum
        self.assertNotEqual(recs[0]["split_group_id"], recs[2]["split_group_id"])  # 😍 vs 😭


class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.env = Lingkungan()
        rows = [
            rec("2094406422507446499", "MagangHub mengecewakan 😭"),                        # pendek
            rec("2094406422507446500", "Aku open review CV MagangHub, WA di bio ya"),          # iklan
            rec("2094406422507446501", "MagangHub isinya iklan jasa review CV, aku risih!"),  # kritik
            rec("2094406422507446502", "uang saku batch 2 belum cair"),                        # konteks OR
            rec("2094406422507446503", "Gak jelas anjir", content_type="quote"),               # quote tanpa bukti
            rec("2094406422507446504", "Uang saku MagangHub belum cair juga"),
            rec("2094406422507446505", "Uang saku MagangHub belum cair juga", username="orang_lain"),
            rec("2094406422507446506", "MagangHub batas", created="2026-08-31T17:00:00+00:00"),
        ]
        del rows[0]["n_quote"]
        tulis_jsonl(self.env.raw / "x_fase1_pengumuman.jsonl", rows)

    def tearDown(self):
        self.env.close()

    def test_keputusan_dan_flag(self):
        _, hasil, df = self.env.jalankan()
        s = df["status_final"]
        self.assertEqual(s["2094406422507446499"], "keep")
        self.assertEqual(str(df.loc["2094406422507446499", "teks_pendek"]), "True")
        self.assertEqual(df.loc["2094406422507446499", "n_quote"], "")      # missing, bukan 0
        self.assertEqual(df.loc["2094406422507446500", "n_quote"], "0")
        self.assertEqual(s["2094406422507446500"], "exclude")
        self.assertEqual(s["2094406422507446501"], "pending")
        self.assertEqual(s["2094406422507446502"], "pending")
        self.assertEqual(df.loc["2094406422507446503", "alasan_utama"], "relevansi_otomatis_tanpa_bukti_teks")
        self.assertEqual(df.loc["2094406422507446503", "content_type"], "quote")
        # Teks identik dari ID berbeda tetap dua observasi, ditandai satu grup.
        self.assertEqual(s["2094406422507446504"], "keep")
        self.assertEqual(s["2094406422507446505"], "keep")
        self.assertEqual(df.loc["2094406422507446504", "teks_berulang_grup"],
                         df.loc["2094406422507446505", "teks_berulang_grup"])
        self.assertEqual(df.loc["2094406422507446506", "fase"], "fase2_seleksi")
        self.assertTrue(hasil["ringkas"]["platform"]["x"]["rekonsiliasi_ok"])
        self.assertNotIn("username", df.columns)
        self.assertNotIn("url", df.columns)
        out = hasil["out"]
        ids = set(pd.read_csv(out / "model_ready_x.csv", dtype={"post_id": str}).post_id)
        self.assertNotIn("2094406422507446501", ids)
        jl = [json.loads(x) for x in (out / "model_ready_x.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertIn("2094406422507446499", {r["post_id"] for r in jl})

    def test_konteks_threads_exclude_x_tetap_pending(self):
        tulis_jsonl(self.env.raw / "threads_magang-kemnaker.jsonl", [
            rec("th_1", "uang saku batch 2 belum cair", platform="threads", kueri="magang kemnaker"),
            rec("th_2", "uang saku MagangHub belum cair", platform="threads", kueri="magang kemnaker"),
        ])
        _, hasil, df = self.env.jalankan()
        self.assertEqual(df.loc["2094406422507446502", "status_final"], "pending")  # X: konteks tetap direview
        th = pd.read_csv(hasil["out"] / "threads/dataset_threads_semua_keputusan.csv", dtype={"post_id": str},
                         keep_default_na=False).set_index("post_id")
        self.assertEqual(th.loc["th_1", "status_final"], "exclude")
        self.assertEqual(th.loc["th_1", "alasan_utama"], "relevansi_konteks_tidak_dipakai")
        self.assertEqual(th.loc["th_2", "status_final"], "keep")
        # Keputusan manusia tetap menang atas aturan platform.
        isi = self.env.root / "isi_th.csv"
        pd.DataFrame([dict(platform="threads", post_id="th_1", reviewer="A", keputusan_relevansi="relevan")]
                     ).to_csv(isi, index=False)
        review.impor(isi, self.env.ann)
        _, hasil, _ = self.env.jalankan()
        th = pd.read_csv(hasil["out"] / "threads/dataset_threads_semua_keputusan.csv", dtype={"post_id": str},
                         keep_default_na=False).set_index("post_id")
        self.assertEqual(th.loc["th_1", "status_final"], "keep")

    def test_snapshot_mengabaikan_potongan_akhir_dan_idempoten(self):
        f = self.env.raw / "x_fase1_pengumuman.jsonl"
        lengkap = f.read_bytes()
        f.write_bytes(lengkap + b'{"tweet_id": "123", "text": "setengah')
        m1, h1, _ = self.env.jalankan()
        self.assertEqual(m1["files"][0]["incomplete_tail_bytes"], len(b'{"tweet_id": "123", "text": "setengah'))
        self.assertEqual(m1["files"][0]["n_records"], 8)
        self.assertEqual(f.read_bytes()[-8:], b"setengah")  # raw tidak diubah

        def sidik(folder):
            return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted(folder.rglob("*")) if p.is_file()}
        a = sidik(h1["out"])
        m2, h2, _ = self.env.jalankan()
        self.assertEqual(m1["snapshot_id"], m2["snapshot_id"])
        self.assertEqual(a, sidik(h2["out"]))

    def test_keputusan_review_bertahan(self):
        _, hasil, _ = self.env.jalankan()
        isi = self.env.root / "isi1.csv"
        pd.DataFrame([
            dict(platform="x", post_id="2094406422507446501", reviewer="A", keputusan_promosi="bukan_iklan",
                 keputusan_relevansi="relevan"),
            dict(platform="x", post_id="2094406422507446502", reviewer="A", keputusan_relevansi="relevan"),
            dict(platform="x", post_id="2094406422507446499", reviewer="agent", keputusan_relevansi="relevan"),
        ]).to_csv(isi, index=False)
        r = review.impor(isi, self.env.ann)
        self.assertEqual((r["diterima"], r["ditolak"]), (2, 1))
        _, _, df = self.env.jalankan()
        self.assertEqual(df.loc["2094406422507446501", "status_final"], "keep")
        self.assertEqual(df.loc["2094406422507446501", "sumber_keputusan"], "manusia")
        # Impor berikutnya dengan sel kosong tidak menghapus keputusan lama.
        isi2 = self.env.root / "isi2.csv"
        pd.DataFrame([dict(platform="x", post_id="2094406422507446501", reviewer="A",
                           keputusan_promosi="", keputusan_relevansi="", catatan="cek ulang", privasi_ok="ya")]
                     ).to_csv(isi2, index=False)
        review.impor(isi2, self.env.ann)
        # Reviewer kedua tidak sepakat -> konflik -> pending.
        isi3 = self.env.root / "isi3.csv"
        pd.DataFrame([dict(platform="x", post_id="2094406422507446502", reviewer="B",
                           keputusan_relevansi="tidak_relevan")]).to_csv(isi3, index=False)
        review.impor(isi3, self.env.ann)
        _, _, df = self.env.jalankan()
        self.assertEqual(df.loc["2094406422507446501", "status_final"], "keep")
        self.assertEqual(df.loc["2094406422507446502", "status_final"], "pending")
        self.assertEqual(df.loc["2094406422507446502", "relevansi_manual"], "konflik")
        with (self.env.ann / "review_decisions_log.csv").open(encoding="utf-8-sig") as stream:
            log = list(csv.DictReader(stream))
        self.assertEqual(len(log), 4)  # append-only


if __name__ == "__main__":
    unittest.main()

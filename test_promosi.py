import unittest
import importlib.util
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
from promosi import klasifikasi_promosi


class PromotionTests(unittest.TestCase):
    def test_output_separates_ads_review_and_candidates(self):
        spec = importlib.util.spec_from_file_location('preprocess', Path(__file__).with_name('03_preprocess.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        texts = ['Aku open review CV MagangHub. WA yah di bio',
                 'MagangHub isinya iklan review CV, aku risih!',
                 'MagangHub mengecewakan 😭']
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            raw, out = root/'raw', root/'out'
            raw.mkdir()
            rows = [dict(tweet_id=str(i), username='example', text=text, created_at='2026-08-31T05:00:00+00:00',
                         kueri='maganghub', fase='fase1_pengumuman', n_like=0,n_reply=0,n_repost=0)
                    for i,text in enumerate(texts,100)]
            (raw/'x_test.jsonl').write_text('\n'.join(json.dumps(r) for r in rows),encoding='utf-8')
            with patch.object(module,'DIR_RAW',raw), patch.object(module,'DIR_OUT',out), \
                 patch.object(module.config,'FILE_SALT',str(root/'salt')):
                module.main()
            def ids(name):
                return set(module.pd.read_csv(out/name,dtype={'post_id':str}).post_id)
            self.assertEqual(ids('maganghub_bersih.csv'), {'102'})
            self.assertEqual(ids('maganghub_kandidat.csv'), {'101','102'})
            self.assertEqual(ids('review_promosi.csv'), {'101'})
            self.assertEqual(ids('audit_penyaringan_promosi.csv'), {'100','101'})

    def test_clear_advertisements(self):
        cases = [
            'Aku open review & upgrade CV untuk MagangHub. Bisa WA yah di bioo!',
            'HADIRR yukk trustedd CV ATS indo 30k onlyy + free konsultasi. 1800+ testi maganghub free revisi',
            'open joki tes psikotes / joki TPA buat maganghub ya yuk',
            'FULL CAREER PACKAGE JASA BIKIN & BUAT CV ATS untuk MagangHub',
            'hari minggu ini aku open yaaa, yg mau review/bikin cv ats, konsul karir aku bisaaa. testi lengkap di profile',
            'Buat kalian yang cari kerja 1. Review CV 2. Upgrade CV 3. Diskusi CV. Bisa WA yah di bio #maganghub',
        ]
        for text in cases:
            with self.subTest(text=text):
                self.assertEqual(klasifikasi_promosi(text)['keputusan'], 'exclude')

    def test_questions_criticism_and_volunteer_help_not_excluded(self):
        cases = [
            'Ada jasa review untuk cv maganghub? Spill harga dong',
            'Adakah jasa bikin CV maganghub yang murah?',
            'Kesal search MagangHub isinya iklan jasa review CV, open joki tes pula!',
            'Jangan pakai joki tes MagangHub. Mereka menipu peserta.',
            'Contoh iklan: aku open review cv, WA di bio. Capek lihatnya.',
            'Aku open review CV gratis tanpa biaya buat teman MagangHub.',
            'DM aku terbuka untuk tanya tips CV MagangHub dan wawancara',
            'CV aku ditolak MagangHub, kecewa 😭',
            'maganghub matiin industri banget ya',
            'MagangHub penuh iklan: "jasa bikin CV 30k, free revisi"',
        ]
        for text in cases:
            with self.subTest(text=text):
                self.assertNotEqual(klasifikasi_promosi(text)['keputusan'], 'exclude')

    def test_pengumuman_lowongan_mitra(self):
        iklan = [
            'Lowongan Magang Puskesmas Kesunean\n\nPuskesmas Kesunean membuka kesempatan untuk bergabung magang '
            'menjadi Analis Laboratorium\n\nKirim lamaran melalui maganghub.kemnaker.go.id\n\nDeadline : 27okt - 1nov 2026',
            'PT PAL Indonesia kembali membuka kesempatan magang melalui Magang Hub Kemnaker untuk penempatan di Divisi HCM.',
            '📢 OPEN RECRUITMENT MAGANG KEMNAKER RSIA Restu Ibu. Posisi: Perawat, Bidan. Daftar melalui link di bawah',
            'Calling all fresh grad! WOM Finance lagi buka posisi Marketing Intern. 📍 Penempatan Sunter. Apply via link',
        ]
        for text in iklan:
            with self.subTest(text=text):
                self.assertEqual(klasifikasi_promosi(text)['alasan'], 'pengumuman_lowongan_mitra')
        opini = [
            'ngecek lowongan maganghub berasa war krs',
            'ada perusahaan yang buka lowongan staff exim di MagangHub, aku apply di sana. nggak ada kabar apa-apa',
            'banyak perusahaan cuma mengandalkan maganghub, jd ga open recruitment untuk posisi full time lg',
            'perusahaan besar jarng buka lowongan, ikut magang hub buka 10+ posisi',
            'ada ga rekomendasi perusahaan yg green flag dan buka lowongan maganghub untuk posisi HR',
            'lowongan maganghub jadi kosong lagi😃',
            'kalo loker di indo manusiawi dan gampang keterima jg gw gamau ikut maganghub',
        ]
        for text in opini:
            with self.subTest(text=text):
                self.assertNotEqual(klasifikasi_promosi(text)['alasan'], 'pengumuman_lowongan_mitra')

    def test_iklan_titipan_order_dan_acara(self):
        cases = {
            'Coba chat kak @hrkonsul kalo butuh bantuan buat bikin/review CV, cover letter, atau LinkedIn. '
            'HR 6 tahun pengalaman, udah banyak yang tembus ke BUMN': 'layanan_dengan_kontak_dan_bukti_jual',
            'jam 09.00 nanti open form order untuk yang mau order layanan jasa review CV maganghub':
                'penawaran_eksplisit_jasa_atau_joki',
            'Persiapkan dirimu! 🚀 Ikuti Webinar Bedah Seleksi MagangHub dan pelajari strategi lolos':
                'promosi_acara_pelatihan',
        }
        for text, alasan in cases.items():
            with self.subTest(text=text):
                self.assertEqual(klasifikasi_promosi(text)['alasan'], alasan)
        for text in ['info bootcamp/course office sama design grafis dong, buat nambah-nambah maganghub',
                     'aku ikut pelatihan kemnaker kemarin, seru juga sebelum maganghub']:
            with self.subTest(text=text):
                self.assertNotEqual(klasifikasi_promosi(text)['keputusan'], 'exclude')

    def test_unexplained_solicitation_needs_review(self):
        self.assertEqual(klasifikasi_promosi('Hai ka khusus maganghub di aku bisa. Check bio ya')['keputusan'], 'review')


if __name__ == '__main__':
    unittest.main()

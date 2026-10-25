# Pengambilan mandiri dari Brave

Alat ini berjalan lokal tanpa sesi chat atau pemantauan AI. Python tetap dipakai untuk mengimpor dan membersihkan hasil. Pengambilan dilakukan ekstensi pada halaman pencarian X yang terlihat, memakai akun yang sudah login di Brave. Tidak membaca cookie/password, tidak memanggil API privat, dan tidak menyamarkan otomatisasi.

## 1. Pasang sekali secara manual

1. Buka Brave yang biasa dipakai, lalu pastikan X sudah login.
2. Buka `brave://extensions`, aktifkan **Developer mode**, pilih **Load unpacked**.
3. Pilih folder **scraper_extension** di proyek ini (folder yang berisi manifest.json).
4. Klik ikon ekstensi **MagangHub X Collector**. Halaman kontrol akan terbuka.

Izin ekstensi terbatas pada x.com, penyimpanan lokal, dan penjadwalan. Kode sumber dapat diperiksa sebelum dipasang. Pemasangan tidak dilakukan otomatis oleh asisten.

## 2. Jalankan pilot

- Periksa konfigurasi tahun/tanggal program. Tanggal default masih mengikuti rancangan kelompok dan perlu diverifikasi terhadap program sasaran.
- Klik **Start pilot**. Batas awal: 100 post mentah per fase (maksimal 300), sejauh hasil tersedia.
- Pencarian dipecah per hari dan dijalankan bergiliran antarfase, dari akhir ke awal pada masing-masing fase. Ini pilot pengujian kualitas, bukan sampel acak.
- Ekstensi membuka tab pengambilan, menyimpan kelompok post sebelum scroll, melewati ID yang sudah ada, dan berpindah kueri otomatis.
- Biarkan Brave dan tab pengambilan tetap terbuka. Jangan mengganti kueri di tab tersebut. Boleh memakai tab lain; browser dapat memperlambat timer tab latar sehingga waktu selesai bisa bertambah.
- Status dan hitungan terlihat di halaman kontrol. Data disimpan dalam IndexedDB ekstensi, bukan otomatis di folder proyek.
- Jika dibatasi X, login habis, halaman berubah, atau scroll macet, proses berhenti dengan statusnya. Selesaikan login sendiri bila diperlukan. Tidak ada mekanisme menembus pembatasan.
- **Hentikan** menyimpan progres. **Lanjutkan progres** mengulang pekerjaan yang belum selesai dari atas dengan deduplikasi; tidak menjamin kembali ke posisi scroll persis.

## 3. Ekspor dan proses

Klik **Ekspor JSON**. Simpan unduhan `maganghub-x-....json` di Downloads. Ekspor berisi username dan teks publik; tetap simpan privat.

Di terminal proyek:

```powershell
.\.venv\Scripts\python.exe import_browser_export.py "$env:USERPROFILE\Downloads\NAMA_FILE_EKSPOR.json"
.\.venv\Scripts\python.exe 03_preprocess.py
.\.venv\Scripts\python.exe 04_audit_collection.py
```

Atau jalankan **PROSES_HASIL.ps1** untuk memakai ekspor `maganghub-x-*.json` terbaru di Downloads. Tidak perlu mengubah execution policy; bila .ps1 tidak diizinkan, gunakan tiga perintah Python di atas.

Impor menambah data ke data/raw dan mempertahankan ID yang sudah ada. Mengimpor ekspor yang sama tidak menggandakan post. Ekspor harus memakai fase yang sama dengan config.py. Pemeriksaan periode menggunakan timestamp WIB setiap post, bukan sekadar hasil filter tanggal X.

## 4. Pengambilan penuh

Setelah pilot dan aturan relevansi diperiksa, klik **Start pengambilan penuh**. Default: batas 150 post per hari, 10.000 mentah keseluruhan. Ini batas pengambilan, bukan target data bersih. Data pilot dipertahankan dan post yang sama tidak disimpan ulang.

- Latest dipakai sebagai korpus utama. Tidak memakai batas like minimum.
- Kata kunci tetap netral. Iklan/spam disaring sesudah pengambilan.
- Hari yang mencapai batas dicatat parsial. Scroll tanpa hasil baru bukan bukti seluruh percakapan X terkumpul.
- Data yang tersedia dan pembatasan X menentukan hasil akhir. Target 5.000 bersih tidak dijamin.
- Penyimpanan ekstensi terpisah dari 129 post yang sebelumnya diambil melalui alat browser. Penggabungan dan deduplikasi terjadi saat impor ke proyek.
- Ekspor berkala sebelum menghapus/menginstal ulang ekstensi atau membersihkan data browser. Tidak ada tombol yang menghapus dataset pada alat ini.

## Verifikasi

Logika tanggal, pembagian pekerjaan, batas kuota, penyimpanan/resume, dan impor diuji lokal. Pemasangan dan pengambilan nyata melalui ekstensi masih perlu diverifikasi di Brave setelah pengguna memasangnya. Ini tidak boleh diklaim sudah menghasilkan data baru sebelum ekspor nyata diperiksa.

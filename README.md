# 🌸 Dashboard by.ficlo

Dashboard Business Intelligence untuk UMKM **by.ficlo** (buket bunga & dekorasi), dibuat dengan Streamlit.

**7 halaman:** Overview · Sales Analytics · Inventory Monitoring · Order Monitoring · Financial Analytics · **Rekomendasi & Analisis** · **FAQ & Data Siap Impor**

## Kesesuaian dengan plan

| Butir plan | Status | Di mana |
|---|---|---|
| Laporan penjualan harian/bulanan, produk terlaris | ✅ | Sales Analytics → tab *Laporan & Cocokkan dengan Website* (+ unduh CSV, endpoint API) |
| Angka cocok dengan data pesanan website | ✅ alat siap, **butuh file ekspor website** | Tab yang sama: unggah CSV/XLSX pesanan website, dibandingkan per hari dan per ID |
| Peringatan stok menipis | ✅ | Inventory → *Peringatan Stok* (daftar belanja + biaya), lonceng 🔔, `GET /stok/menipis` |
| Analisis data & rekomendasi buket (budget, tema, momen) | ✅ | Rekomendasi & Analisis; `recommender.py` (scikit-learn); notebook `Analisis_byficlo.ipynb`; `POST /rekomendasi` |
| Tanya Rekomendasi menolak input kosong | ✅ | Budget, tema, momen wajib; kosong/whitespace/angka ≤ 0 ditolak (UI: pesan merah, API: HTTP 422) |
| Data produk, inventaris, FAQ siap impor DB | ✅ | `data_bersih/*.csv` + `schema.sql`; `python export_data.py --sqlite ficlo.db`; halaman FAQ & Data Siap Impor |
| Status pesanan sesuai plan | ✅ | Menunggu Verifikasi → Diproses → Siap Diambil/Dikirim → Selesai; gagal: Ditolak, Kedaluwarsa, Dibatalkan. Dropdown Excel sudah diperbarui; nama lama “Menunggu” dibaca otomatis |
| Financial Analytics | ➕ nilai tambah | Tetap ada, ditandai di luar plan; disembunyikan di mode publik |
| Tech stack (Python, pandas, scikit-learn, Jupyter/Colab, FastAPI) | ✅ | scikit-learn di rekomendasi, `api.py` FastAPI, 2 notebook. **Streamlit tidak ada di daftar plan**, konfirmasi ke admin apakah diterima; logika ada di `data_loader/analytics/recommender`, jadi UI mudah diganti |
| Privasi data | ✅ | Lihat [PRIVASI.md](PRIVASI.md): password, mode publik, ekspor tanpa data keuangan |

## Asumsi yang perlu dikonfirmasi

- **Kedaluwarsa:** pesanan *Menunggu Verifikasi* lebih dari 1 hari otomatis jadi Kedaluwarsa (`BATAS_VERIFIKASI_HARI` di `data_loader.py`). Plan tidak menyebut batasnya.
- **FAQ** (`faq.csv`) adalah draf; yang memuat kebijakan (DP, refund, ongkir, waktu pesan) bertanda *Perlu_Konfirmasi = Ya*. Harga di jawaban terisi otomatis dari katalog.
- **Kecocokan momen** di rekomendasi memakai aturan awal florist (`MOMEN` di `recommender.py`), karena baru 1 pesanan custom dan 20 transaksi (6 hari). Makin banyak data, makin bergeser ke data nyata.
- **Saran restock** = 2 × stok minimum − stok saat ini (`TARGET_RESTOCK_X`).
- Nama produk kembar (3× “Jasa Money Bucket”) dibedakan otomatis dari deskripsi.

## Struktur folder

```text
.
├── app.py                           # dashboard Streamlit (7 halaman)
├── data_loader.py                   # pembersihan & perhitungan data Excel
├── analytics.py                     # laporan, rekonsiliasi website, analisis
├── recommender.py                   # Tanya Rekomendasi (scikit-learn)
├── export_data.py                   # ekspor CSV bersih + SQLite
├── api.py                           # REST API FastAPI (opsional)
├── faq.csv                          # FAQ pelanggan (draf, bisa diedit)
├── data_bersih/                     # CSV siap impor + schema.sql
├── Dataset_Dasboard_DS_byficlo.xlsx # data
├── Dashboard_byficlo.ipynb          # notebook pembuat dashboard (Colab)
├── Analisis_byficlo.ipynb           # notebook analisis & rekomendasi
├── requirements.txt / requirements-api.txt
├── PRIVASI.md
└── .streamlit/config.toml           # tema hijau-pink
```

## Deploy ke Streamlit Community Cloud

1. Upload isi folder ke repository GitHub **private** (file di root repo).
2. <https://share.streamlit.io> → **Create app** → Main file path `app.py`.
3. *Settings → Secrets*: isi `APP_PASSWORD = "..."` (dan `FICLO_PUBLIC = "1"` bila perlu mode publik).

## Jalankan lokal

```bash
pip install -r requirements.txt
streamlit run app.py

# API (opsional)
pip install -r requirements-api.txt
uvicorn api:app --port 8000        # dokumentasi: http://localhost:8000/docs

# Ekspor data bersih
python export_data.py --sqlite ficlo.db
```

## Memperbarui data

Ganti file Excel di GitHub lalu klik **🔄 Muat ulang data**, atau unggah `.xlsx` baru di panel **🔎 Filter & sumber data**. Kolom `[AUTO]` dihitung ulang Python; masalah data tampil di **🧹 Catatan kualitas data** (Overview).

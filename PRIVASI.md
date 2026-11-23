# 🔒 Privasi & keamanan data by.ficlo

Plan menyebut data hanya untuk proyek ini dan tanpa identitas pelanggan. Yang sudah diterapkan:

| Hal | Penerapan |
|---|---|
| Identitas pelanggan | Dataset hanya memakai `Kode_Pelanggan` (PLG001). Jangan pernah mengisi nama/nomor WhatsApp di Excel, termasuk kolom `Catatan`. |
| Repo | Excel memuat **modal, pengeluaran, HPP, dan laba**. Pakai repository GitHub **Private**. Kalau harus publik, minta izin admin by.Ficlo dan ganti Excel dengan data contoh. |
| Gerbang password | Isi `APP_PASSWORD` di Streamlit Cloud → *Settings → Secrets* (`APP_PASSWORD = "isi-password"`). Tanpa password, siapa pun yang punya link bisa membuka dashboard. |
| Mode publik | `FICLO_PUBLIC = "1"` di Secrets: halaman Financial disembunyikan, data modal/pengeluaran dikosongkan, `Kode_Pelanggan` dan `Catatan` pesanan disamarkan, unggah dataset dimatikan. |
| Ekspor | `data_bersih/` hanya berisi produk, bahan, inventaris, FAQ. Data keuangan tidak pernah diekspor. Penjualan/pesanan baru ikut jika diminta (`--transaksi`), simpan hanya di repo private. |
| API | Set `API_KEY`; klien mengirim header `X-API-Key`. Tidak ada endpoint keuangan. |

**Batasan:** password dan mode publik adalah pengaman sederhana, bukan sistem login multi-user. File Excel tetap ikut ter-deploy, jadi kerahasiaannya bergantung pada repo private. Untuk data sensitif sungguhan, pindahkan data ke database dengan akses terkontrol.

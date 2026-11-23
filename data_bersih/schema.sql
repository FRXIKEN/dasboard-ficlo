-- Skema database by.ficlo (kompatibel SQLite / PostgreSQL / MySQL dengan penyesuaian tipe kecil).
-- Dibuat bersama CSV di folder ini oleh export_data.py. Semua CSV: UTF-8, header snake_case, tanggal ISO (YYYY-MM-DD).
-- Impor cepat ke SQLite:  python export_data.py --sqlite ficlo.db

CREATE TABLE produk (
    id_produk       TEXT PRIMARY KEY,
    nama_produk     TEXT NOT NULL,
    kategori        TEXT NOT NULL,
    deskripsi       TEXT,
    harga_jual      INTEGER NOT NULL,
    hpp_standar     INTEGER NOT NULL,
    margin_standar  INTEGER NOT NULL,
    persen_margin   REAL NOT NULL,          -- pecahan, 0.30 = 30%
    stok_awal       INTEGER NOT NULL,
    stok_minimum    INTEGER NOT NULL,
    mutasi_masuk    INTEGER NOT NULL,
    mutasi_keluar   INTEGER NOT NULL,
    stok_saat_ini   INTEGER NOT NULL,
    status_stok     TEXT NOT NULL,          -- Aman | Menipis | Habis
    satuan          TEXT,
    status          TEXT                    -- Aktif | Tidak Aktif
);

CREATE TABLE bahan (
    id_bahan          TEXT PRIMARY KEY,
    nama_bahan        TEXT NOT NULL,
    kategori_bahan    TEXT NOT NULL,
    tipe_bahan        TEXT,
    masa_simpan_hari  INTEGER,
    satuan            TEXT,
    stok_awal         INTEGER NOT NULL,
    stok_minimum      INTEGER NOT NULL,
    harga_beli_satuan INTEGER NOT NULL,
    supplier          TEXT,
    mutasi_masuk      INTEGER NOT NULL,
    mutasi_keluar     INTEGER NOT NULL,
    stok_saat_ini     INTEGER NOT NULL,
    nilai_persediaan  INTEGER NOT NULL,
    status_stok       TEXT NOT NULL,        -- Aman | Perlu Restock | Habis
    keterangan        TEXT
);

-- Gabungan produk jadi + bahan, satu tempat untuk halaman Inventory & peringatan stok.
CREATE TABLE inventaris (
    id_item                 TEXT PRIMARY KEY,   -- PRDxxx atau BHNxxx
    jenis_item              TEXT NOT NULL,      -- Produk | Bahan
    nama_item               TEXT NOT NULL,
    kategori                TEXT,
    satuan                  TEXT,
    stok_awal               INTEGER NOT NULL,
    mutasi_masuk            INTEGER NOT NULL,
    mutasi_keluar           INTEGER NOT NULL,
    stok_saat_ini           INTEGER NOT NULL,
    stok_minimum            INTEGER NOT NULL,
    harga_satuan            INTEGER NOT NULL,
    status_stok             TEXT NOT NULL,
    nilai_persediaan        INTEGER NOT NULL,
    saran_restock_qty       INTEGER NOT NULL,
    estimasi_biaya_restock  INTEGER NOT NULL
);

CREATE TABLE faq (
    id_faq            TEXT PRIMARY KEY,
    kategori          TEXT NOT NULL,
    pertanyaan        TEXT NOT NULL,
    jawaban           TEXT NOT NULL,
    kata_kunci        TEXT,
    perlu_konfirmasi  TEXT                   -- Ya = jawaban memuat kebijakan yang harus dikonfirmasi pemilik
);

-- Opsional (hanya bila export dijalankan dengan --transaksi). Berisi data penjualan/pesanan, simpan di repo PRIVATE.
CREATE TABLE penjualan (
    id_transaksi       TEXT PRIMARY KEY,
    tanggal            TEXT NOT NULL,
    id_produk          TEXT,
    nama_produk        TEXT,
    kategori           TEXT,
    jumlah_terjual     INTEGER NOT NULL,
    harga_jual_satuan  INTEGER NOT NULL,
    diskon             INTEGER NOT NULL,
    total_penjualan    INTEGER NOT NULL,
    hpp_satuan         INTEGER NOT NULL,
    total_hpp          INTEGER NOT NULL,
    laba_kotor         INTEGER NOT NULL,
    metode_pembayaran  TEXT,
    status_pembayaran  TEXT,
    kanal_penjualan    TEXT,
    tipe_pelanggan     TEXT,
    status_transaksi   TEXT,
    id_pesanan         TEXT
);

CREATE TABLE pesanan (
    id_pesanan        TEXT PRIMARY KEY,
    tanggal_pesanan   TEXT NOT NULL,
    kode_pelanggan    TEXT,
    id_produk         TEXT,
    nama_produk       TEXT,
    jumlah            INTEGER NOT NULL,
    jenis_order       TEXT,
    momen_acara       TEXT,
    tanggal_deadline  TEXT,
    tanggal_selesai   TEXT,
    status_pesanan    TEXT NOT NULL,   -- Menunggu Verifikasi | Diproses | Siap Diambil | Dikirim | Selesai | Dibatalkan | Ditolak | Kedaluwarsa
    tahap             TEXT,
    status_bayar      TEXT,            -- Belum Bayar | DP | Lunas
    status_sla        TEXT,
    total_harga       INTEGER NOT NULL,
    dp_dibayar        INTEGER NOT NULL,
    sisa_pembayaran   INTEGER NOT NULL
);

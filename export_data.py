"""
export_data.py — ekspor data BERSIH (produk, bahan, inventaris, FAQ) ke CSV siap impor database.

Pemakaian:
    python export_data.py                      # tulis CSV ke folder data_bersih/
    python export_data.py --transaksi          # + penjualan.csv & pesanan.csv (simpan di repo private!)
    python export_data.py --sqlite ficlo.db    # sekaligus bangun database SQLite dari schema.sql

Data keuangan (modal, pengeluaran) SENGAJA tidak pernah diekspor. Lihat PRIVASI.md.
"""
import argparse
import re
import sqlite3
from pathlib import Path

import pandas as pd

import data_loader as dl

HERE = Path(__file__).resolve().parent
DEFAULT_XLSX = HERE / "Dataset_Dasboard_DS_byficlo.xlsx"
OUT_DIR = HERE / "data_bersih"


def snake(c):
    return re.sub(r"[^0-9a-z]+", "_", str(c).lower()).strip("_")


def _siap_db(df, kolom=None):
    df = df.copy()
    if kolom:
        df = df[[c for c in kolom if c in df.columns]]
    for c in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            df[c] = df[c].dt.strftime("%Y-%m-%d")
        elif pd.api.types.is_float_dtype(df[c]) and c not in ("Persen_Margin",):
            # kolom angka bulat (uang/stok) jangan tampil 5.0
            if (df[c].dropna() % 1 == 0).all():
                df[c] = df[c].astype("Int64")
    if "Persen_Margin" in df.columns:
        df["Persen_Margin"] = df["Persen_Margin"].round(4)
    df.columns = [snake(c) for c in df.columns]
    return df


def tabel_ekspor(d, transaksi=False):
    out = {
        "produk": _siap_db(d["produk"], ["ID_Produk", "Nama_Produk", "Kategori", "Deskripsi", "Harga_Jual", "HPP_Standar",
                                         "Margin_Standar", "Persen_Margin", "Stok_Awal", "Stok_Minimum", "Mutasi_Masuk",
                                         "Mutasi_Keluar", "Stok_Saat_Ini", "Status_Stok", "Satuan", "Status"]),
        "bahan": _siap_db(d["bahan"], ["ID_Bahan", "Nama_Bahan", "Kategori_Bahan", "Tipe_Bahan", "Masa_Simpan_Hari", "Satuan",
                                       "Stok_Awal", "Stok_Minimum", "Harga_Beli_Satuan", "Supplier", "Mutasi_Masuk",
                                       "Mutasi_Keluar", "Stok_Saat_Ini", "Nilai_Persediaan", "Status_Stok", "Keterangan"]),
        "inventaris": _siap_db(d["inventaris"]),
        "faq": _siap_db(d["faq"]),
    }
    if transaksi:
        out["penjualan"] = _siap_db(d["penjualan"].drop(columns=["Bulan"]),
                                    ["ID_Transaksi", "Tanggal", "ID_Produk", "Nama_Produk", "Kategori", "Jumlah_Terjual",
                                     "Harga_Jual_Satuan", "Diskon", "Total_Penjualan", "HPP_Satuan", "Total_HPP", "Laba_Kotor",
                                     "Metode_Pembayaran", "Status_Pembayaran", "Kanal_Penjualan", "Tipe_Pelanggan",
                                     "Status_Transaksi", "ID_Pesanan"])
        out["pesanan"] = _siap_db(d["pesanan"], ["ID_Pesanan", "Tanggal_Pesanan", "Kode_Pelanggan", "ID_Produk", "Nama_Produk",
                                                 "Jumlah", "Jenis_Order", "Momen_Acara", "Tanggal_Deadline", "Tanggal_Selesai",
                                                 "Status_Pesanan", "Tahap", "Status_Bayar", "Status_SLA", "Total_Harga",
                                                 "DP_Dibayar", "Sisa_Pembayaran"])
    return out


def export_clean(d, outdir=OUT_DIR, transaksi=False):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    tabel = tabel_ekspor(d, transaksi)
    for nama, df in tabel.items():
        df.to_csv(outdir / f"{nama}.csv", index=False, encoding="utf-8")
    return tabel


def _py(v):
    """Nilai pandas/numpy -> tipe Python biasa untuk sqlite3 (NaN -> NULL)."""
    if v is None or (not isinstance(v, str) and pd.isna(v)):
        return None
    return v.item() if hasattr(v, "item") else v


def build_sqlite(tabel, db_path, schema=OUT_DIR / "schema.sql"):
    db_path = Path(db_path)
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.executescript(Path(schema).read_text(encoding="utf-8"))
    for nama, df in tabel.items():
        cols = ",".join(df.columns)
        ph = ",".join("?" * len(df.columns))
        rows = [tuple(_py(v) for v in r) for r in df.itertuples(index=False)]
        con.executemany(f"INSERT INTO {nama} ({cols}) VALUES ({ph})", rows)
    con.commit()
    jumlah = {n: con.execute(f"SELECT COUNT(*) FROM {n}").fetchone()[0] for n in tabel}
    con.close()
    return jumlah


PK = {"produk": "id_produk", "bahan": "id_bahan", "inventaris": "id_item", "faq": "id_faq",
      "penjualan": "id_transaksi", "pesanan": "id_pesanan"}
WAJIB = {
    "produk": ["id_produk", "nama_produk", "kategori", "harga_jual", "hpp_standar", "stok_minimum"],
    "bahan": ["id_bahan", "nama_bahan", "kategori_bahan", "harga_beli_satuan", "stok_minimum"],
    "inventaris": ["id_item", "nama_item", "stok_saat_ini", "stok_minimum"],
    "faq": ["id_faq", "pertanyaan", "jawaban"],
    "penjualan": ["id_transaksi", "tanggal", "jumlah_terjual", "total_penjualan"],
    "pesanan": ["id_pesanan", "tanggal_pesanan", "status_pesanan", "total_harga"],
}


def validasi_impor(tabel):
    """Cek kesiapan impor DB: ID unik & terisi, kolom wajib tidak kosong, angka tidak negatif. Return list (tabel, ok, pesan)."""
    hasil = []
    for nama, df in tabel.items():
        masalah = []
        if df.empty:
            masalah.append("tabel kosong")
        pk = PK.get(nama)
        if pk in df.columns:
            if df[pk].isna().any() or (df[pk].astype(str).str.strip() == "").any():
                masalah.append(f"{pk} ada yang kosong")
            if df[pk].duplicated().any():
                masalah.append(f"{pk} duplikat: {', '.join(df.loc[df[pk].duplicated(), pk].astype(str))}")
        for c in WAJIB.get(nama, []):
            if c in df.columns and df[c].isna().any():
                masalah.append(f"{c} kosong pada {int(df[c].isna().sum())} baris")
        for c in df.columns:
            if pd.api.types.is_numeric_dtype(df[c]) and (df[c].dropna() < 0).any() and c not in ("laba_kotor", "selisih", "margin_standar"):
                masalah.append(f"{c} bernilai negatif")
        hasil.append((nama, not masalah, "siap impor" if not masalah else "; ".join(masalah)))
    return hasil


def zip_bytes(tabel):
    """Semua CSV + schema.sql dalam satu ZIP (untuk tombol unduh di dashboard)."""
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for nama, df in tabel.items():
            z.writestr(f"{nama}.csv", df.to_csv(index=False))
        sk = OUT_DIR / "schema.sql"
        if sk.exists():
            z.writestr("schema.sql", sk.read_text(encoding="utf-8"))
    return buf.getvalue()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--xlsx", default=str(DEFAULT_XLSX))
    ap.add_argument("--out", default=str(OUT_DIR))
    ap.add_argument("--transaksi", action="store_true", help="sertakan penjualan.csv dan pesanan.csv")
    ap.add_argument("--sqlite", metavar="FILE.db", help="bangun database SQLite dari CSV + schema.sql")
    a = ap.parse_args()
    data = dl.load_all(a.xlsx)
    tbl = export_clean(data, a.out, a.transaksi)
    for n, df in tbl.items():
        print(f"{n}.csv  {len(df)} baris, {len(df.columns)} kolom")
    if a.sqlite:
        print("SQLite:", build_sqlite(tbl, a.sqlite, Path(a.out) / "schema.sql"))

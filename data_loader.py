"""
data_loader.py — pembersihan & perhitungan data UMKM by.ficlo
Dipakai oleh notebook (untuk preview) dan oleh app.py (dashboard Streamlit).

Prinsip:
- Kolom [AUTO] dihitung ulang di Python dari kolom dasarnya, jadi hasilnya tidak
  bergantung pada rumus/nilai cache di Excel (yang bisa kosong atau tidak sinkron).
- Baris kosong (sisa rumus template) dibuang.
- ID yang kosong diisi otomatis; penulisan kategori/nama dirapikan.
"""
import re
import difflib
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

SHEETS = {
    "PRODUK": "produk",
    "MASTER_BAHAN": "bahan",
    "PENJUALAN": "penjualan",
    "MUTASI_STOK": "mutasi",
    "PESANAN": "pesanan",
    "PRODUKSI": "produksi",
    "PENGELUARAN": "pengeluaran",
    "MODAL_KAS": "kas",
}

# Kolom yang dipakai untuk mendeteksi "baris benar-benar kosong"
KEY_COLS = {
    "PRODUK": ["Nama_Produk"],
    "MASTER_BAHAN": ["Nama_Bahan"],
    "PENJUALAN": ["Tanggal_Transaksi", "Jumlah_Terjual"],
    "MUTASI_STOK": ["Tanggal", "ID_Item"],
    "PESANAN": ["ID_Pesanan", "Tanggal_Pesanan"],
    "PRODUKSI": ["Tanggal_Produksi", "ID_Produk"],
    "PENGELUARAN": ["Tanggal", "Jumlah"],
    "MODAL_KAS": ["Tanggal", "Nominal"],
}

_UPPER_TOKENS = {"xs", "xl", "xxl", "xxs", "diy", "pcs"}
HERE = Path(__file__).resolve().parent
FAQ_CSV = HERE / "faq.csv"

# ---- Alur status pesanan --------------------------------------------------
# Urutan tahap sesuai plan: pembayaran -> produksi -> pengiriman -> selesai,
# dengan 3 jalur gagal (Ditolak / Kedaluwarsa / Dibatalkan).
STATUS_ALUR = ["Menunggu Verifikasi", "Diproses", "Siap Diambil", "Dikirim", "Selesai"]
STATUS_GAGAL = ["Ditolak", "Kedaluwarsa", "Dibatalkan"]
STATUS_SEMUA = STATUS_ALUR + STATUS_GAGAL
# nama lama di template Excel versi sebelumnya -> nama baku
STATUS_ALIAS = {"Menunggu": "Menunggu Verifikasi", "Menunggu Pembayaran": "Menunggu Verifikasi",
                "Batal": "Dibatalkan", "Menunggu Verifikasi Pembayaran": "Menunggu Verifikasi"}
TAHAP = {"Menunggu Verifikasi": "1. Pembayaran", "Diproses": "2. Produksi", "Siap Diambil": "3. Pengiriman",
         "Dikirim": "3. Pengiriman", "Selesai": "4. Selesai", "Ditolak": "Gagal", "Kedaluwarsa": "Gagal",
         "Dibatalkan": "Gagal"}
# Pesanan yang masih menunggu verifikasi lebih dari N hari dianggap Kedaluwarsa.
# ASUMSI: plan tidak menyebut batasnya, ubah sesuai aturan admin.
BATAS_VERIFIKASI_HARI = 1
TARGET_RESTOCK_X = 2  # saran restock = 2 x stok minimum - stok saat ini

_TYPO = {"thumbelian": "thumbelina"}


# ----------------------------------------------------------------- helper kecil
def _txt(s):
    """Rapikan spasi; nilai kosong tetap NaN."""
    return s.map(lambda v: re.sub(r"\s+", " ", str(v)).strip() if pd.notna(v) else np.nan)


def _title(s):
    def f(v):
        if pd.isna(v):
            return v
        words = re.sub(r"\s+", " ", str(v)).strip().split(" ")
        return " ".join(w.upper() if w.lower() in _UPPER_TOKENS else w.capitalize() for w in words)

    return s.map(f)


def _num(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)


def _date(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce").dt.normalize()


def _fill_ids(df, col, prefix):
    """Isi ID kosong dengan PREFIX + nomor baris. Return (jumlah diisi, contoh ID)."""
    filled = 0
    contoh = None
    out = []
    for i, v in enumerate(df[col] if col in df.columns else [np.nan] * len(df)):
        if pd.isna(v) or str(v).strip() == "":
            out.append(f"{prefix}{i + 1:03d}")
            contoh = contoh or out[-1]
            filled += 1
        else:
            out.append(str(v).strip().upper())
    df[col] = out
    return filled, contoh


def _canon(value, choices):
    """Samakan penulisan ke daftar baku (mis. 'artificial flowers' -> 'Artificial Flower')."""
    if pd.isna(value):
        return value
    v = re.sub(r"\s+", " ", str(value)).strip().lower()
    low = {c.lower(): c for c in choices}
    if v in low:
        return low[v]
    m = difflib.get_close_matches(v, list(low), n=1, cutoff=0.6)
    return low[m[0]] if m else _title(pd.Series([value])).iloc[0]


def _read(xl, sheet):
    df = xl.parse(sheet)
    df.columns = [re.sub(r"\s*\[AUTO\]\s*", "", str(c)).strip() for c in df.columns]
    df = df.dropna(how="all")
    keys = [c for c in KEY_COLS[sheet] if c in df.columns]
    if keys:
        df = df.dropna(subset=keys, how="all")
    return df.reset_index(drop=True)


def _status_stok(stok, minimum, label_min="Menipis"):
    if stok <= 0:
        return "Habis"
    if stok <= minimum:
        return label_min
    return "Aman"


def _hitung_stok(master, id_col, jenis, mutasi):
    m = mutasi[mutasi["Jenis_Item"] == jenis]
    masuk = m[m["Jenis_Mutasi"] == "Masuk"].groupby("ID_Item")["Jumlah"].sum()
    keluar = m[m["Jenis_Mutasi"] == "Keluar"].groupby("ID_Item")["Jumlah"].sum()
    master["Mutasi_Masuk"] = master[id_col].map(masuk).fillna(0)
    master["Mutasi_Keluar"] = master[id_col].map(keluar).fillna(0)
    master["Stok_Saat_Ini"] = master["Stok_Awal"] + master["Mutasi_Masuk"] - master["Mutasi_Keluar"]
    return master


def _rapikan_deskripsi(v):
    if pd.isna(v):
        return v
    t = re.sub(r"\s+", " ", str(v)).strip()
    for salah, benar in _TYPO.items():
        t = re.sub(salah, benar, t, flags=re.I)
    return t[:1].upper() + t[1:]


def _bedakan_nama_kembar(pr):
    """Nama produk yang sama dengan ID berbeda (mis. 3x 'Jasa Money Bucket') diberi pembeda dari deskripsi/harga."""
    dup = pr["Nama_Produk"].duplicated(keep=False)
    if not dup.any():
        return []
    diubah = []
    for i in pr.index[dup]:
        m = re.search(r"(\d+)\s*(lembar|tangkai|pcs)", str(pr.at[i, "Deskripsi"]), flags=re.I)
        suffix = f"{m.group(1)} {m.group(2).capitalize()}" if m else f"Rp{pr.at[i, 'Harga_Jual']:,.0f}".replace(",", ".")
        baru = f"{pr.at[i, 'Nama_Produk']} {suffix}"
        diubah.append(f"{pr.at[i, 'ID_Produk']}: {pr.at[i, 'Nama_Produk']} -> {baru}")
        pr.at[i, "Nama_Produk"] = baru
    return diubah


def _saran_mapping(pj, pr):
    """Untuk baris penjualan tanpa ID_Produk yang valid, sarankan produk katalog (nama mirip + harga sama)."""
    valid = set(pr["ID_Produk"])
    rows = []
    namas = list(pr["Nama_Produk"])
    for r in pj[~pj["ID_Produk"].isin(valid)].itertuples():
        nama = str(r.Nama_Produk).lower()
        skor = []
        for _, p in pr.iterrows():
            sim = difflib.SequenceMatcher(None, nama, p["Nama_Produk"].lower()).ratio()
            kat = 0.15 if str(r.Kategori).lower() == str(p["Kategori"]).lower() else 0
            harga = 0.5 if abs(p["Harga_Jual"] - r.Harga_Jual_Satuan) < 1 else 0
            skor.append((sim + kat + harga, p["ID_Produk"], p["Nama_Produk"], harga > 0))
        best = max(skor)
        rows.append({"ID_Transaksi": r.ID_Transaksi, "Nama_di_Penjualan": r.Nama_Produk, "Harga": r.Harga_Jual_Satuan,
                     "Saran_ID_Produk": best[1], "Saran_Nama_Katalog": best[2],
                     "Keyakinan": "Tinggi (nama mirip + harga sama)" if best[3] and best[0] > 1.0 else "Rendah (cek manual)"})
    return pd.DataFrame(rows, columns=["ID_Transaksi", "Nama_di_Penjualan", "Harga", "Saran_ID_Produk",
                                       "Saran_Nama_Katalog", "Keyakinan"])


def _isi_template_faq(teks, pr, bh, ps_momen):
    ctx = {
        "harga_min": f"Rp{pr['Harga_Jual'].min():,.0f}".replace(",", "."),
        "harga_max": f"Rp{pr['Harga_Jual'].max():,.0f}".replace(",", "."),
        "kategori": ", ".join(sorted(pr["Kategori"].unique())),
        "momen": ", ".join(ps_momen),
    }
    for k, v in ctx.items():
        teks = teks.replace("{" + k + "}", v)
    return teks


def load_faq(source_xl, pr, bh):
    """FAQ dari sheet 'FAQ' di Excel kalau ada, kalau tidak dari faq.csv. Placeholder {harga_min} dst diisi dari katalog."""
    df = None
    if source_xl is not None and "FAQ" in source_xl.sheet_names:
        df = source_xl.parse("FAQ")
    elif FAQ_CSV.exists():
        df = pd.read_csv(FAQ_CSV)
    cols = ["ID_FAQ", "Kategori", "Pertanyaan", "Jawaban", "Kata_Kunci", "Perlu_Konfirmasi"]
    if df is None or df.empty:
        return pd.DataFrame(columns=cols)
    df = df.dropna(subset=["Pertanyaan", "Jawaban"]).copy()
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    momen = ["Wisuda", "Ulang Tahun", "Anniversary", "Wedding/Lamaran", "Grand Opening"]
    df["Jawaban"] = df["Jawaban"].map(lambda t: _isi_template_faq(str(t), pr, bh, momen))
    df["Kata_Kunci"] = df["Kata_Kunci"].fillna("").astype(str)
    df["Perlu_Konfirmasi"] = df["Perlu_Konfirmasi"].fillna("Tidak").astype(str)
    return df[cols].reset_index(drop=True)


def _inventaris(pr, bh):
    """Gabungan stok produk jadi + bahan dalam satu tabel (siap impor DB)."""
    a = pd.DataFrame({
        "ID_Item": pr["ID_Produk"], "Jenis_Item": "Produk", "Nama_Item": pr["Nama_Produk"], "Kategori": pr["Kategori"],
        "Satuan": pr["Satuan"] if "Satuan" in pr.columns else "pcs", "Stok_Awal": pr["Stok_Awal"],
        "Mutasi_Masuk": pr["Mutasi_Masuk"], "Mutasi_Keluar": pr["Mutasi_Keluar"], "Stok_Saat_Ini": pr["Stok_Saat_Ini"],
        "Stok_Minimum": pr["Stok_Minimum"], "Harga_Satuan": pr["HPP_Standar"], "Status_Stok": pr["Status_Stok"],
    })
    b = pd.DataFrame({
        "ID_Item": bh["ID_Bahan"], "Jenis_Item": "Bahan", "Nama_Item": bh["Nama_Bahan"], "Kategori": bh["Kategori_Bahan"],
        "Satuan": bh["Satuan"], "Stok_Awal": bh["Stok_Awal"], "Mutasi_Masuk": bh["Mutasi_Masuk"],
        "Mutasi_Keluar": bh["Mutasi_Keluar"], "Stok_Saat_Ini": bh["Stok_Saat_Ini"], "Stok_Minimum": bh["Stok_Minimum"],
        "Harga_Satuan": bh["Harga_Beli_Satuan"], "Status_Stok": bh["Status_Stok"],
    })
    inv = pd.concat([a, b], ignore_index=True)
    inv["Nilai_Persediaan"] = inv["Stok_Saat_Ini"] * inv["Harga_Satuan"]
    # target isi ulang = 2x stok minimum (aturan umum; ubah TARGET_RESTOCK_X kalau perlu)
    inv["Saran_Restock_Qty"] = np.where(inv["Status_Stok"] != "Aman",
                                        np.maximum(inv["Stok_Minimum"] * TARGET_RESTOCK_X - inv["Stok_Saat_Ini"], 0), 0)
    inv["Estimasi_Biaya_Restock"] = inv["Saran_Restock_Qty"] * inv["Harga_Satuan"]
    return inv


# ----------------------------------------------------------------- loader utama
def load_all(source, today=None):
    """
    source : path file .xlsx atau file-like (BytesIO)
    return : dict DataFrame bersih + 'dq' (catatan kualitas data) + 'today'
    """
    today = pd.Timestamp(today or date.today()).normalize()
    xl = pd.ExcelFile(source)
    raw = {key: _read(xl, sheet) for sheet, key in SHEETS.items()}
    peringatan = []
    id_terisi = {}

    # ---------------- PRODUK
    pr = raw["produk"].copy()
    id_terisi["PRODUK"] = _fill_ids(pr, "ID_Produk", "PRD")
    pr["Nama_Produk"] = _title(_txt(pr["Nama_Produk"]))
    if "Deskripsi" in pr.columns:
        pr["Deskripsi"] = pr["Deskripsi"].map(_rapikan_deskripsi)
    _num(pr, ["Harga_Jual"])
    nama_kembar = _bedakan_nama_kembar(pr)
    kategori_baku = sorted(_txt(pr["Kategori"]).dropna().map(lambda x: x.title()).unique())
    pr["Kategori"] = pr["Kategori"].map(lambda v: _canon(v, kategori_baku))
    _num(pr, ["Harga_Jual", "HPP_Standar", "Stok_Awal", "Stok_Minimum"])
    pr["Margin_Standar"] = pr["Harga_Jual"] - pr["HPP_Standar"]
    pr["Persen_Margin"] = np.where(pr["Harga_Jual"] > 0, pr["Margin_Standar"] / pr["Harga_Jual"], 0)
    pr["Status"] = _title(_txt(pr["Status"])) if "Status" in pr.columns else "Aktif"
    stok_excel_produk = pd.to_numeric(pr.get("Stok_Saat_Ini"), errors="coerce")

    # ---------------- MASTER_BAHAN
    bh = raw["bahan"].copy()
    id_terisi["MASTER_BAHAN"] = _fill_ids(bh, "ID_Bahan", "BHN")
    bh["Nama_Bahan"] = _title(_txt(bh["Nama_Bahan"]))
    bh["Kategori_Bahan"] = _title(_txt(bh["Kategori_Bahan"]))
    bh["Supplier"] = _title(_txt(bh["Supplier"]))
    _num(bh, ["Stok_Awal", "Stok_Minimum", "Harga_Beli_Satuan", "Masa_Simpan_Hari"])
    stok_excel_bahan = pd.to_numeric(bh.get("Stok_Saat_Ini"), errors="coerce")

    # ---------------- MUTASI_STOK
    mt = raw["mutasi"].copy()
    mt["Jenis_Item"] = _title(_txt(mt["Jenis_Item"]))
    mt["Jenis_Mutasi"] = _title(_txt(mt["Jenis_Mutasi"]))
    mt["ID_Item"] = _txt(mt["ID_Item"]).str.upper()
    mt["Alasan_Mutasi"] = _title(_txt(mt["Alasan_Mutasi"]))
    _num(mt, ["Jumlah"])
    _date(mt, ["Tanggal"])

    # ---------------- stok saat ini (Stok_Awal + Masuk - Keluar)
    pr = _hitung_stok(pr, "ID_Produk", "Produk", mt)
    pr["Status_Stok"] = [_status_stok(s, m) for s, m in zip(pr["Stok_Saat_Ini"], pr["Stok_Minimum"])]
    bh = _hitung_stok(bh, "ID_Bahan", "Bahan", mt)
    bh["Nilai_Persediaan"] = bh["Stok_Saat_Ini"] * bh["Harga_Beli_Satuan"]
    bh["Status_Stok"] = [_status_stok(s, m, "Perlu Restock") for s, m in zip(bh["Stok_Saat_Ini"], bh["Stok_Minimum"])]
    bh["Rasio_Stok"] = np.where(bh["Stok_Minimum"] > 0, bh["Stok_Saat_Ini"] / bh["Stok_Minimum"], np.nan)

    nama_by_id = dict(zip(pr["ID_Produk"], pr["Nama_Produk"]))
    kat_by_id = dict(zip(pr["ID_Produk"], pr["Kategori"]))

    # ---------------- PENJUALAN
    pj = raw["penjualan"].copy()
    id_terisi["PENJUALAN"] = _fill_ids(pj, "ID_Transaksi", "TRX")
    cached = {c: pd.to_numeric(pj.get(c), errors="coerce") for c in ["Total_Penjualan", "Total_HPP", "Laba_Kotor"]}
    pj["ID_Produk"] = _txt(pj["ID_Produk"]).str.upper()
    pj["Nama_Produk"] = _title(_txt(pj["Nama_Produk"]))
    pj["Nama_Produk"] = pj["ID_Produk"].map(nama_by_id).fillna(pj["Nama_Produk"])
    pj["Kategori"] = pj["Kategori"].map(lambda v: _canon(v, kategori_baku))
    pj["Kategori"] = pj["ID_Produk"].map(kat_by_id).fillna(pj["Kategori"])
    for c in ["Metode_Pembayaran", "Status_Pembayaran", "Kanal_Penjualan", "Tipe_Pelanggan", "Status_Transaksi"]:
        pj[c] = _title(_txt(pj[c])).fillna("Tidak Diketahui")
    _num(pj, ["Jumlah_Terjual", "Harga_Jual_Satuan", "Diskon", "HPP_Satuan"])
    _date(pj, ["Tanggal_Transaksi"])
    pj["Total_Penjualan"] = pj["Jumlah_Terjual"] * pj["Harga_Jual_Satuan"] - pj["Diskon"]
    pj["Total_HPP"] = pj["Jumlah_Terjual"] * pj["HPP_Satuan"]
    pj["Laba_Kotor"] = pj["Total_Penjualan"] - pj["Total_HPP"]
    pj = pj.rename(columns={"Tanggal_Transaksi": "Tanggal"})
    pj["Bulan"] = pj["Tanggal"].dt.to_period("M").astype(str)

    # selisih nilai Excel vs hitung ulang
    rows = []
    for c, ser in cached.items():
        diff = ser.notna() & ((ser - pj[c]).abs() > 0.5)
        for i in pj.index[diff]:
            rows.append(
                {
                    "ID_Transaksi": pj.at[i, "ID_Transaksi"],
                    "Tanggal": pj.at[i, "Tanggal"],
                    "Produk": pj.at[i, "Nama_Produk"],
                    "Kolom": c,
                    "Nilai_di_Excel": ser.at[i],
                    "Nilai_Hitung_Ulang": pj.at[i, c],
                }
            )
    selisih_penjualan = pd.DataFrame(
        rows, columns=["ID_Transaksi", "Tanggal", "Produk", "Kolom", "Nilai_di_Excel", "Nilai_Hitung_Ulang"]
    )

    # ---------------- PESANAN
    ps = raw["pesanan"].copy()
    ps["ID_Pesanan"] = _txt(ps["ID_Pesanan"]).str.upper()
    ps = ps.dropna(subset=["ID_Pesanan"]).reset_index(drop=True)
    ps["ID_Produk"] = _txt(ps["ID_Produk"]).str.upper()
    ps["Nama_Produk"] = ps["ID_Produk"].map(nama_by_id).fillna(_title(_txt(ps["Nama_Produk"])))
    for c in ["Jenis_Order", "Momen_Acara", "Status_Pesanan"]:
        ps[c] = _title(_txt(ps[c])).fillna("Tidak Diketahui")
    ps["Status_Pesanan"] = ps["Status_Pesanan"].replace(STATUS_ALIAS)
    ps["Kode_Pelanggan"] = _txt(ps["Kode_Pelanggan"]).str.upper() if "Kode_Pelanggan" in ps.columns else np.nan
    _num(ps, ["Jumlah", "Total_Harga", "DP_Dibayar"])
    _date(ps, ["Tanggal_Pesanan", "Tanggal_Deadline", "Tanggal_Selesai"])
    ps["Sisa_Pembayaran"] = ps["Total_Harga"] - ps["DP_Dibayar"]

    # Menunggu Verifikasi yang terlalu lama otomatis Kedaluwarsa (aturan: BATAS_VERIFIKASI_HARI)
    umur = (today - ps["Tanggal_Pesanan"]).dt.days
    kadaluarsa = (ps["Status_Pesanan"] == "Menunggu Verifikasi") & (umur > BATAS_VERIFIKASI_HARI)
    ps["Status_Asli"] = ps["Status_Pesanan"]
    ps.loc[kadaluarsa, "Status_Pesanan"] = "Kedaluwarsa"
    ps["Tahap"] = ps["Status_Pesanan"].map(TAHAP).fillna("Lainnya")
    # status pembayaran diturunkan dari DP vs total
    ps["Status_Bayar"] = np.select(
        [ps["DP_Dibayar"] <= 0, ps["DP_Dibayar"] < ps["Total_Harga"]], ["Belum Bayar", "DP"], default="Lunas")

    def sla(r):
        if r["Status_Pesanan"] in STATUS_GAGAL:
            return "Batal"
        if pd.notna(r["Tanggal_Selesai"]):
            return "Tepat Waktu" if r["Tanggal_Selesai"] <= r["Tanggal_Deadline"] else "Terlambat"
        if pd.notna(r["Tanggal_Deadline"]) and today > r["Tanggal_Deadline"]:
            return "Overdue"
        return "On Track"

    ps["Status_SLA"] = ps.apply(sla, axis=1) if len(ps) else pd.Series(dtype=object)
    ps["Hari_ke_Deadline"] = (ps["Tanggal_Deadline"] - today).dt.days

    # ---------------- PRODUKSI
    pd_ = raw["produksi"].copy()
    pd_["ID_Produk"] = _txt(pd_["ID_Produk"]).str.upper()
    pd_["ID_Bahan"] = _txt(pd_["ID_Bahan"]).str.upper()
    _num(pd_, ["Jumlah_Diproduksi", "Jumlah_Bahan_Digunakan", "Harga_Beli_Satuan", "Biaya_Tambahan"])
    _date(pd_, ["Tanggal_Produksi"])
    pd_["Nama_Produk"] = pd_["ID_Produk"].map(nama_by_id).fillna(_title(_txt(pd_["Nama_Produk"])))
    pd_["Nama_Bahan"] = pd_["ID_Bahan"].map(dict(zip(bh["ID_Bahan"], bh["Nama_Bahan"]))).fillna(
        _title(_txt(pd_["Nama_Bahan"]))
    )
    pd_["Total_Biaya_Bahan"] = pd_["Jumlah_Bahan_Digunakan"] * pd_["Harga_Beli_Satuan"]
    pd_["Total_Biaya_Produksi"] = pd_["Total_Biaya_Bahan"] + pd_["Biaya_Tambahan"]

    # ---------------- PENGELUARAN
    pg = raw["pengeluaran"].copy()
    for c in ["Kategori_Pengeluaran", "Jenis_Biaya", "Metode_Pembayaran"]:
        pg[c] = _title(_txt(pg[c])).fillna("Tidak Diketahui")
    _num(pg, ["Jumlah"])
    _date(pg, ["Tanggal"])

    # ---------------- MODAL_KAS
    ks = raw["kas"].copy()
    ks["Jenis_Arus"] = _title(_txt(ks["Jenis_Arus"]))
    ks["Kategori_Kas"] = _title(_txt(ks["Kategori_Kas"]))
    _num(ks, ["Nominal"])
    _date(ks, ["Tanggal"])
    ks = ks.sort_values("Tanggal", kind="stable").reset_index(drop=True)
    ks["Nominal_Bertanda"] = np.where(ks["Jenis_Arus"] == "Masuk", ks["Nominal"], -ks["Nominal"])
    ks["Saldo_Kumulatif"] = ks["Nominal_Bertanda"].cumsum()

    # ---------------- Catatan kualitas data
    for sheet, (n, contoh) in id_terisi.items():
        if n:
            peringatan.append(f"Sheet {sheet}: {n} baris tidak punya ID, diisi otomatis (mis. {contoh}).")

    if len(selisih_penjualan):
        peringatan.append(
            f"PENJUALAN: {len(selisih_penjualan)} nilai kolom otomatis di Excel tidak sesuai hitungan "
            "(Jumlah × Harga − Diskon, dst.), kemungkinan terketik manual. Dashboard memakai hasil hitung ulang."
        )
    neg = pj[pj["Laba_Kotor"] < 0]
    if len(neg):
        peringatan.append(
            "PENJUALAN: " + ", ".join(neg["ID_Transaksi"]) + " memiliki laba kotor negatif (HPP_Satuan lebih besar "
            "dari Harga_Jual_Satuan). Cek kemungkinan salah input HPP."
        )
    kosong = int(cached["Total_Penjualan"].isna().sum())
    if kosong:
        peringatan.append(f"PENJUALAN: {kosong} baris Total_Penjualan kosong di Excel, dihitung ulang oleh dashboard.")

    ref_exp = set(pg.get("ID_Pengeluaran", pd.Series(dtype=object)).dropna().astype(str))
    ref_mut = mt["ID_Referensi"].dropna().astype(str) if "ID_Referensi" in mt.columns else pd.Series(dtype=object)
    hilang = sorted({r for r in ref_mut if r.upper().startswith("EXP") and r not in ref_exp})
    if hilang:
        peringatan.append(
            "MUTASI_STOK merujuk ID pengeluaran yang belum ada di sheet PENGELUARAN: " + ", ".join(hilang) + "."
        )

    ord_ids = set(ps["ID_Pesanan"])
    ord_hilang = sorted({o for o in pj.get("ID_Pesanan", pd.Series(dtype=object)).dropna().astype(str) if o not in ord_ids})
    if ord_hilang:
        peringatan.append("PENJUALAN merujuk ID pesanan yang tidak ada di sheet PESANAN: " + ", ".join(ord_hilang) + ".")

    katalog = {n.lower() for n in pr["Nama_Produk"]}
    tak_cocok = sorted({n for n in pj["Nama_Produk"].dropna() if n.lower() not in katalog})
    if tak_cocok:
        peringatan.append(
            f"{len(tak_cocok)} nama produk di PENJUALAN tidak ada di katalog PRODUK ({', '.join(tak_cocok)}). "
            "Isi kolom ID_Produk agar analisis per produk akurat."
        )

    if nama_kembar:
        peringatan.append("PRODUK: nama kembar dibedakan otomatis (" + "; ".join(nama_kembar) + ").")
    n_kdl = int(kadaluarsa.sum())
    if n_kdl:
        peringatan.append(f"PESANAN: {n_kdl} pesanan Menunggu Verifikasi lebih dari {BATAS_VERIFIKASI_HARI} hari, otomatis ditandai Kedaluwarsa.")
    tak_dikenal = sorted(set(ps["Status_Pesanan"]) - set(STATUS_SEMUA) - {"Tidak Diketahui"})
    if tak_dikenal:
        peringatan.append("PESANAN: status tidak dikenal (" + ", ".join(tak_dikenal) + "). Pakai: " + ", ".join(STATUS_SEMUA) + ".")
    saran_mapping = _saran_mapping(pj, pr)

    sel_stok = []
    for nama, df_, id_c, nm_c, ser in [
        ("Bahan", bh, "ID_Bahan", "Nama_Bahan", stok_excel_bahan),
        ("Produk", pr, "ID_Produk", "Nama_Produk", stok_excel_produk),
    ]:
        if ser is None:
            continue
        d = ser.notna() & ((ser - df_["Stok_Saat_Ini"]).abs() > 0.5)
        for i in df_.index[d]:
            sel_stok.append(
                {
                    "Jenis": nama,
                    "ID": df_.at[i, id_c],
                    "Nama": df_.at[i, nm_c],
                    "Stok_di_Excel": ser.at[i],
                    "Stok_Hitung_Ulang": df_.at[i, "Stok_Saat_Ini"],
                }
            )
    selisih_stok = pd.DataFrame(sel_stok, columns=["Jenis", "ID", "Nama", "Stok_di_Excel", "Stok_Hitung_Ulang"])
    if len(selisih_stok):
        peringatan.append(
            f"{len(selisih_stok)} stok di Excel berbeda dengan Stok_Awal + Mutasi Masuk − Mutasi Keluar. "
            "Dashboard memakai hasil hitung ulang dari MUTASI_STOK."
        )

    inventaris = _inventaris(pr, bh)
    faq = load_faq(xl, pr, bh)

    return {
        "inventaris": inventaris,
        "faq": faq,
        "produk": pr,
        "bahan": bh,
        "penjualan": pj,
        "mutasi": mt,
        "pesanan": ps,
        "produksi": pd_,
        "pengeluaran": pg,
        "kas": ks,
        "kategori": kategori_baku,
        "today": today,
        "dq": {"peringatan": peringatan, "selisih_penjualan": selisih_penjualan, "selisih_stok": selisih_stok,
               "saran_mapping": saran_mapping},
    }

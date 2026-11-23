"""
analytics.py — laporan penjualan, rekonsiliasi dengan data pesanan website, dan analisis untuk rekomendasi buket.
Dipakai oleh app.py (Streamlit) dan api.py (FastAPI) supaya angkanya selalu sama.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd


# ------------------------------------------------------------------ laporan penjualan
def _agg(pj, by):
    g = pj.groupby(by).agg(
        Transaksi=("ID_Transaksi", "nunique"), Item_Terjual=("Jumlah_Terjual", "sum"),
        Pendapatan=("Total_Penjualan", "sum"), HPP=("Total_HPP", "sum"), Laba_Kotor=("Laba_Kotor", "sum"),
    ).reset_index()
    g["Margin_Persen"] = np.where(g["Pendapatan"] > 0, g["Laba_Kotor"] / g["Pendapatan"] * 100, 0).round(1)
    return g


def laporan_harian(pj: pd.DataFrame) -> pd.DataFrame:
    return _agg(pj, "Tanggal").sort_values("Tanggal") if len(pj) else pd.DataFrame()


def laporan_bulanan(pj: pd.DataFrame) -> pd.DataFrame:
    return _agg(pj, "Bulan").sort_values("Bulan") if len(pj) else pd.DataFrame()


def produk_terlaris(pj: pd.DataFrame, n: int = 10, urut: str = "Item_Terjual") -> pd.DataFrame:
    if not len(pj):
        return pd.DataFrame()
    g = pj.groupby("Nama_Produk").agg(Item_Terjual=("Jumlah_Terjual", "sum"), Pendapatan=("Total_Penjualan", "sum"),
                                      Laba_Kotor=("Laba_Kotor", "sum")).reset_index()
    return g.sort_values(urut, ascending=False).head(n).reset_index(drop=True)


# ------------------------------------------------------------------ rekonsiliasi dengan data pesanan website
ALIAS = {
    "tanggal": ["tanggal", "date", "tgl", "tanggal_pesanan", "tanggal_transaksi", "order_date", "created_at", "waktu"],
    "total": ["total", "total_harga", "total_pesanan", "nominal", "jumlah_bayar", "grand_total", "amount", "total_penjualan", "total_bayar"],
    "id": ["id_pesanan", "order_id", "id_order", "no_pesanan", "id_transaksi", "kode_pesanan", "id"],
}


def _kolom(df, kunci):
    norm = {re.sub(r"[^a-z0-9]+", "_", str(c).lower()).strip("_"): c for c in df.columns}
    for a in ALIAS[kunci]:
        if a in norm:
            return norm[a]
    return None


def _parse_tanggal(ser):
    """Format ISO (2026-11-10) dibaca apa adanya; selain itu diasumsikan DD/MM/YYYY."""
    txt = ser.astype(str).str.strip()
    iso = pd.to_datetime(txt, format="%Y-%m-%d", errors="coerce")
    iso2 = pd.to_datetime(txt.str[:10], format="%Y-%m-%d", errors="coerce")
    alt = pd.to_datetime(txt, errors="coerce", dayfirst=True)
    return iso.fillna(iso2).fillna(alt).dt.normalize()


def baca_data_website(file, nama=""):
    """Baca CSV/XLSX ekspor pesanan website. Return (df_standar[tanggal,total,id], pesan_error)."""
    try:
        df = pd.read_excel(file) if str(nama).lower().endswith((".xlsx", ".xls")) else pd.read_csv(file, sep=None, engine="python")
    except Exception as e:  # noqa: BLE001
        return None, f"File tidak bisa dibaca: {e}"
    ct, cn, ci = _kolom(df, "tanggal"), _kolom(df, "total"), _kolom(df, "id")
    if ct is None or cn is None:
        return None, ("Kolom wajib tidak ditemukan. Butuh kolom tanggal (mis. 'tanggal') dan total (mis. 'total'). "
                      f"Kolom di file: {', '.join(map(str, df.columns))}")
    out = pd.DataFrame({
        "tanggal": _parse_tanggal(df[ct]),
        "total": pd.to_numeric(df[cn].astype(str).str.replace(r"[^0-9,.\-]", "", regex=True).str.replace(".", "", regex=False)
                               .str.replace(",", ".", regex=False), errors="coerce"),
        "id": df[ci].astype(str).str.strip().str.upper() if ci else np.nan,
    }).dropna(subset=["tanggal", "total"])
    if out.empty:
        return None, "Tidak ada baris valid (tanggal/total kosong atau tidak terbaca)."
    return out, None


def rekonsiliasi(pj: pd.DataFrame, web: pd.DataFrame, toleransi: float = 0.5) -> dict:
    """
    Bandingkan total harian PENJUALAN (Excel) vs pesanan website. Dipakai untuk membuktikan angka laporan cocok.
    Return dict: harian (DataFrame), ringkas (dict), per_id (DataFrame atau None).
    """
    a = pj.groupby("Tanggal")["Total_Penjualan"].sum().rename("Total_Dashboard")
    b = web.groupby("tanggal")["total"].sum().rename("Total_Website")
    h = pd.concat([a, b], axis=1).fillna(0).reset_index().rename(columns={"index": "Tanggal"})
    h["Selisih"] = h["Total_Dashboard"] - h["Total_Website"]
    h["Status"] = np.where(h["Selisih"].abs() <= toleransi, "Cocok",
                           np.where(h["Total_Website"] == 0, "Hanya di Dashboard",
                                    np.where(h["Total_Dashboard"] == 0, "Hanya di Website", "Selisih")))
    ringkas = {
        "hari": len(h), "cocok": int((h["Status"] == "Cocok").sum()),
        "total_dashboard": float(h["Total_Dashboard"].sum()), "total_website": float(h["Total_Website"].sum()),
        "selisih_total": float(h["Total_Dashboard"].sum() - h["Total_Website"].sum()),
    }
    ringkas["persen_cocok"] = ringkas["cocok"] / ringkas["hari"] if ringkas["hari"] else 0.0
    per_id = None
    if web["id"].notna().any() and "ID_Pesanan" in pj.columns and pj["ID_Pesanan"].notna().any():
        left = pj.dropna(subset=["ID_Pesanan"]).groupby("ID_Pesanan")["Total_Penjualan"].sum().rename("Total_Dashboard")
        right = web.dropna(subset=["id"]).groupby("id")["total"].sum().rename("Total_Website")
        per_id = pd.concat([left, right], axis=1).fillna(0).reset_index().rename(columns={"index": "ID_Pesanan"})
        per_id["Selisih"] = per_id["Total_Dashboard"] - per_id["Total_Website"]
        per_id["Status"] = np.where(per_id["Selisih"].abs() <= toleransi, "Cocok",
                                    np.where(per_id["Total_Dashboard"] == 0, "Hanya di Website",
                                             np.where(per_id["Total_Website"] == 0, "Hanya di Dashboard", "Selisih")))
    return {"harian": h, "ringkas": ringkas, "per_id": per_id}


TEMPLATE_WEBSITE_CSV = "tanggal,id_pesanan,total\n2026-11-10,ORD001,300000\n2026-11-11,ORD002,1000000\n"


# ------------------------------------------------------------------ analisis untuk rekomendasi buket
def band_harga(pr: pd.DataFrame) -> pd.DataFrame:
    """Sebaran produk per rentang harga (acuan untuk input budget)."""
    bins = [0, 50_000, 100_000, 150_000, 250_000, 10**9]
    lab = ["≤ Rp50rb", "Rp50-100rb", "Rp100-150rb", "Rp150-250rb", "> Rp250rb"]
    t = pr.assign(Rentang=pd.cut(pr["Harga_Jual"], bins=bins, labels=lab, right=True))
    return (t.groupby("Rentang", observed=False).agg(Jumlah_Produk=("ID_Produk", "count"), Rata_Margin=("Persen_Margin", "mean"))
            .reset_index().assign(Rata_Margin=lambda x: (x["Rata_Margin"] * 100).round(1)))


def kategori_performa(pj: pd.DataFrame, pr: pd.DataFrame) -> pd.DataFrame:
    if not len(pj):
        return pd.DataFrame()
    g = pj.groupby("Kategori").agg(Item_Terjual=("Jumlah_Terjual", "sum"), Pendapatan=("Total_Penjualan", "sum"),
                                   Laba_Kotor=("Laba_Kotor", "sum")).reset_index()
    g["Margin_Persen"] = (g["Laba_Kotor"] / g["Pendapatan"] * 100).round(1)
    g["Porsi_Pendapatan"] = (g["Pendapatan"] / g["Pendapatan"].sum() * 100).round(1)
    g["Jumlah_Katalog"] = g["Kategori"].map(pr.groupby("Kategori").size()).fillna(0).astype(int)
    return g.sort_values("Pendapatan", ascending=False).reset_index(drop=True)


def momen_performa(ps: pd.DataFrame) -> pd.DataFrame:
    if not len(ps):
        return pd.DataFrame(columns=["Momen_Acara", "Pesanan", "Nilai", "Rata_Nilai"])
    ok = ps[~ps["Status_Pesanan"].isin(["Ditolak", "Kedaluwarsa", "Dibatalkan"])]
    g = ok.groupby("Momen_Acara").agg(Pesanan=("ID_Pesanan", "count"), Nilai=("Total_Harga", "sum")).reset_index()
    g["Rata_Nilai"] = (g["Nilai"] / g["Pesanan"]).round(0)
    return g.sort_values("Pesanan", ascending=False)


def insight_otomatis(d: dict) -> list[str]:
    """Kalimat temuan yang dihitung dari data (bukan teks tetap), lengkap dengan peringatan ukuran sampel."""
    pj, pr, ps = d["penjualan"], d["produk"], d["pesanan"]
    out = []
    if len(pj):
        hari = pj["Tanggal"].nunique()
        out.append(f"Data penjualan mencakup {hari} hari ({pj['Tanggal'].min():%d %b} – {pj['Tanggal'].max():%d %b %Y}) dan {len(pj)} transaksi. "
                   + ("Itu masih sedikit, jadi anggap temuan di bawah sebagai indikasi awal." if len(pj) < 100 else ""))
        kp = kategori_performa(pj, pr)
        top = kp.iloc[0]
        out.append(f"Kategori terkuat: {top.Kategori} ({top.Porsi_Pendapatan:.0f}% pendapatan, margin {top.Margin_Persen:.0f}%).")
        low = kp.sort_values("Margin_Persen").iloc[0]
        if low.Margin_Persen < 30:
            out.append(f"Margin terendah ada di {low.Kategori} ({low.Margin_Persen:.0f}%). Cek HPP atau harga jualnya.")
        neg = pj[pj["Laba_Kotor"] < 0]
        if len(neg):
            out.append(f"{len(neg)} transaksi rugi ({', '.join(neg['ID_Transaksi'])}), kemungkinan salah input HPP_Satuan.")
        pop = pj.groupby("Tanggal")["Total_Penjualan"].sum()
        out.append(f"Hari terbaik: {pop.idxmax():%d %b} (Rp{pop.max():,.0f}); rata-rata Rp{pop.mean():,.0f}/hari.".replace(",", "."))
        ada_mawar = pr[pr["Nama_Produk"].str.contains("mawar", case=False)]
        if len(ada_mawar) and not pj["Nama_Produk"].str.contains("mawar", case=False).any():
            out.append("Produk mawar ada di katalog tetapi belum terjual pada periode ini.")
    if len(ps):
        mp = momen_performa(ps)
        if len(mp):
            out.append(f"Momen pesanan custom tersering: {mp.iloc[0].Momen_Acara} ({int(mp.iloc[0].Pesanan)} pesanan). "
                       + ("Baru " + str(len(ps)) + " pesanan, belum cukup untuk pola momen." if len(ps) < 20 else ""))
    inv = d["inventaris"]
    n_low = int((inv["Status_Stok"] != "Aman").sum())
    out.append(f"{n_low} item stok menipis/habis." if n_low else "Semua stok masih di atas batas minimum.")
    return [t.strip() for t in out]

"""
recommender.py — "Tanya Rekomendasi" buket by.ficlo (budget + tema + momen).

Metode (scikit-learn):
  1. Teks produk (nama + kategori + deskripsi) di-vektorkan dengan TF-IDF karakter (tahan typo, mis. 'thumbelian').
  2. Tema/momen/catatan pengguna diperluas jadi kata kunci, lalu dicocokkan dengan cosine similarity.
  3. Skor akhir = campuran: kecocokan budget, tema, momen, popularitas penjualan, margin, ketersediaan stok.

Catatan jujur soal data: penjualan baru beberapa hari dan pesanan custom masih sangat sedikit, jadi
kecocokan momen memakai 'prior' kategori (aturan umum florist, bisa diubah di MOMEN di bawah) yang
perlahan digeser oleh data nyata saat jumlah pesanan bertambah.

Input kosong DITOLAK: budget, tema, dan momen wajib diisi (lihat validasi()).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ------------------------------------------------------------------ pengetahuan domain (bisa diedit)
# Prior kecocokan kategori produk per momen, skala 0-1. Kunci kategori = kata kunci di nama kategori.
MOMEN = {
    "Wisuda":            {"artificial": 1.0, "money": 0.9, "bouquet": 0.8, "snack": 0.6},
    "Ulang Tahun":       {"snack": 1.0, "bouquet": 0.9, "artificial": 0.8, "money": 0.7},
    "Anniversary":       {"bouquet": 1.0, "artificial": 0.9, "snack": 0.4, "money": 0.5},
    "Wedding/Lamaran":   {"bouquet": 1.0, "artificial": 1.0, "money": 0.6, "snack": 0.3},
    "Grand Opening":     {"bouquet": 1.0, "artificial": 0.8, "snack": 0.5, "money": 0.3},
    "Hari Ibu":          {"bouquet": 1.0, "artificial": 0.9, "snack": 0.5, "money": 0.5},
    "Valentine":         {"bouquet": 1.0, "artificial": 0.9, "snack": 0.8, "money": 0.4},
    "Terima Kasih":      {"snack": 1.0, "bouquet": 0.8, "artificial": 0.7, "money": 0.5},
    "Duka Cita":         {"bouquet": 1.0, "artificial": 0.2, "snack": 0.1, "money": 0.1},
    "Lainnya":           {"bouquet": 0.6, "artificial": 0.6, "snack": 0.6, "money": 0.6},
}

# Tema -> kata kunci pencarian (dicocokkan ke teks produk) + warna pita/kemasan yang serasi.
TEMA = {
    "Romantis":            {"kata": "mawar merah pink romantis rose love", "warna": ["merah", "pink", "maroon"]},
    "Elegan & Mewah":      {"kata": "elegan mewah premium large gold mawar maroon", "warna": ["gold", "hitam", "maroon", "putih"]},
    "Ceria & Lucu":        {"kata": "ceria lucu warna warni snack small mini xs", "warna": ["kuning", "biru", "pink", "ungu"]},
    "Minimalis & Natural": {"kata": "minimalis natural aster fresh putih simple medium", "warna": ["putih", "cream", "khaki", "abu"]},
    "Manis (Pastel)":      {"kata": "pink ungu pastel thumbelina manis", "warna": ["pink", "ungu", "biru muda"]},
    "Maskulin & Netral":   {"kata": "hitam biru abu snack money netral", "warna": ["hitam", "biru", "abu"]},
    "Praktis (Uang/Camilan)": {"kata": "money bucket uang snack camilan praktis", "warna": ["hijau", "gold"]},
}

BOBOT = {"budget": 0.30, "tema": 0.25, "momen": 0.25, "populer": 0.10, "margin": 0.05, "stok": 0.05}
TOLERANSI_BUDGET = 0.10  # produk sampai 10% di atas budget masih ditampilkan (diberi catatan)


class InputKosongError(ValueError):
    """Dilempar bila budget/tema/momen kosong atau tidak valid. .errors berisi pesan per kolom."""

    def __init__(self, errors: dict[str, str]):
        self.errors = errors
        super().__init__("; ".join(errors.values()))


def rp(x) -> str:
    return "Rp" + f"{float(x):,.0f}".replace(",", ".")


def _kosong(v) -> bool:
    return v is None or (isinstance(v, float) and np.isnan(v)) or str(v).strip() == ""


def parse_budget(v) -> float | None:
    """Terima 150000, '150000', '150.000', 'Rp 150.000', '150rb', '150k'. Return None bila tidak bisa dibaca."""
    if _kosong(v):
        return None
    if isinstance(v, (int, float, np.integer, np.floating)):
        return float(v)
    t = str(v).lower().replace("rp", "").replace(" ", "")
    mult = 1
    if re.search(r"(rb|ribu|k)$", t):
        mult, t = 1000, re.sub(r"(rb|ribu|k)$", "", t)
    elif re.search(r"(jt|juta)$", t):
        mult, t = 1_000_000, re.sub(r"(jt|juta)$", "", t)
    t = t.replace(".", "").replace(",", ".") if mult == 1 else t.replace(",", ".")
    try:
        return float(t) * mult
    except ValueError:
        return None


def validasi(budget, tema, momen) -> dict[str, str]:
    """Return dict {kolom: pesan}. Kosong = valid."""
    err = {}
    b = parse_budget(budget)
    if _kosong(budget):
        err["budget"] = "Budget wajib diisi."
    elif b is None or b <= 0:
        err["budget"] = "Budget harus berupa angka lebih dari 0 (contoh: 150000 atau 150rb)."
    if _kosong(tema):
        err["tema"] = "Tema wajib dipilih/diisi."
    elif not re.search(r"[a-zA-Z0-9]", str(tema)):
        err["tema"] = "Tema tidak valid."
    if _kosong(momen):
        err["momen"] = "Momen wajib dipilih/diisi."
    elif not re.search(r"[a-zA-Z0-9]", str(momen)):
        err["momen"] = "Momen tidak valid."
    return err


def _kunci_kategori(kategori: str) -> str:
    k = str(kategori).lower()
    for key in ("artificial", "money", "snack", "bouquet"):
        if key in k:
            return key
    return "lain"


def _cocok_momen(momen: str) -> str:
    m = re.sub(r"\s+", " ", str(momen)).strip().lower()
    for nama in MOMEN:
        if nama.lower() == m:
            return nama
    for nama in MOMEN:  # kecocokan sebagian: 'wedding' -> 'Wedding/Lamaran'
        if m and (m in nama.lower() or any(tok and tok in m for tok in re.split(r"[/ ]", nama.lower()))):
            return nama
    return "Lainnya"


def _cocok_tema(tema: str) -> tuple[str | None, str]:
    """Return (nama_tema_baku atau None, kata kunci). Tema bebas ikut dipakai sebagai kata kunci."""
    t = re.sub(r"\s+", " ", str(tema)).strip().lower()
    for nama, v in TEMA.items():
        if nama.lower() == t or t.split(" ")[0] == nama.lower().split(" ")[0]:
            return nama, v["kata"]
    return None, t


@dataclass
class Hasil:
    produk: pd.DataFrame           # kandidat berurutan, kolom skor + alasan
    addon: list[dict] = field(default_factory=list)
    catatan: list[str] = field(default_factory=list)
    tema: str = ""
    momen: str = ""
    budget: float = 0.0


class Rekomendator:
    def __init__(self, d: dict):
        self.d = d
        pr = d["produk"].copy()
        self.pr = pr[pr["Status"].astype(str).str.lower() == "aktif"].reset_index(drop=True) if "Status" in pr.columns else pr
        self.bh = d["bahan"]
        self.pj = d["penjualan"]
        self.ps = d["pesanan"]
        self.pr["_doc"] = (self.pr["Nama_Produk"].fillna("") + " " + self.pr["Kategori"].fillna("") + " "
                           + self.pr.get("Deskripsi", pd.Series("", index=self.pr.index)).fillna(""))
        self.vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), lowercase=True, sublinear_tf=True)
        self.X = self.vec.fit_transform(self.pr["_doc"]) if len(self.pr) else None
        self._populer = self._hitung_populer()

    # ---- popularitas dari penjualan (kategori + produk bila ID bisa diselesaikan)
    def _hitung_populer(self) -> pd.Series:
        if not len(self.pr) or not len(self.pj):
            return pd.Series(0.0, index=self.pr.index)
        pj = self.pj
        per_kat = pj.groupby("Kategori")["Jumlah_Terjual"].sum()
        share_kat = (per_kat / per_kat.sum()).to_dict()
        valid = set(self.pr["ID_Produk"])
        per_id = pj[pj["ID_Produk"].isin(valid)].groupby("ID_Produk")["Jumlah_Terjual"].sum()
        skor = []
        for r in self.pr.itertuples():
            s_kat = share_kat.get(r.Kategori, 0.0)
            s_id = per_id.get(r.ID_Produk, 0) / per_id.sum() if per_id.sum() else 0.0
            skor.append(0.7 * s_kat + 0.3 * s_id)
        s = pd.Series(skor, index=self.pr.index)
        return s / s.max() if s.max() > 0 else s

    def _prior_momen(self, momen_baku: str) -> pd.Series:
        prior = MOMEN[momen_baku]
        p = pd.Series([prior.get(_kunci_kategori(k), 0.5) for k in self.pr["Kategori"]], index=self.pr.index)
        # geser dengan data nyata bila ada pesanan untuk momen ini (bobot n/(n+10), jadi kecil saat data sedikit)
        ps = self.ps[self.ps["Momen_Acara"].str.lower() == momen_baku.lower()] if len(self.ps) else self.ps
        n = len(ps)
        if n:
            kat_by_id = dict(zip(self.pr["ID_Produk"], self.pr["Kategori"]))
            obs = ps["ID_Produk"].map(kat_by_id).dropna().value_counts(normalize=True)
            if len(obs):
                o = pd.Series([obs.get(k, 0.0) for k in self.pr["Kategori"]], index=self.pr.index)
                o = o / o.max() if o.max() > 0 else o
                w = n / (n + 10)
                p = (1 - w) * p + w * o
        return p

    def _addon(self, tema_baku, tema_teks, sisa_budget, kat_kunci):
        warna = TEMA[tema_baku]["warna"] if tema_baku else [w for w in re.findall(r"[a-z]+", tema_teks)]
        out = []
        bh = self.bh[self.bh["Stok_Saat_Ini"] > 0]
        for jenis, key in (("Pita", "pita"), ("Kertas Cellophane", "cellophane")):
            if key == "cellophane" and kat_kunci in ("snack", "money"):
                continue
            cand = bh[bh["Nama_Bahan"].str.lower().str.contains(key)]
            for w in warna:
                m = cand[cand["Nama_Bahan"].str.lower().str.contains(re.escape(w))]
                if len(m):
                    r = m.iloc[0]
                    out.append({"Nama": r["Nama_Bahan"], "Alasan": f"warna {w} serasi dengan tema", "Stok": f"{r['Stok_Saat_Ini']:g} {r['Satuan']}"})
                    break
        kartu = bh[bh["Nama_Bahan"].str.lower().str.contains("ucapan")]
        if len(kartu):
            r = kartu.iloc[0]
            out.append({"Nama": r["Nama_Bahan"], "Alasan": "tambahkan ucapan personal", "Stok": f"{r['Stok_Saat_Ini']:g} {r['Satuan']}"})
        return out

    def rekomendasi(self, budget, tema, momen, catatan="", top_n=3) -> Hasil:
        err = validasi(budget, tema, momen)
        if err:
            raise InputKosongError(err)
        b = parse_budget(budget)
        momen_baku = _cocok_momen(momen)
        tema_baku, tema_kata = _cocok_tema(tema)
        notes = []
        if self.X is None or not len(self.pr):
            raise InputKosongError({"produk": "Katalog produk aktif kosong."})

        pr = self.pr.copy()
        q = f"{tema_kata} {momen} {catatan or ''}"
        sim = cosine_similarity(self.vec.transform([q]), self.X).ravel()
        pr["S_tema"] = sim / sim.max() if sim.max() > 0 else sim
        pr["S_momen"] = self._prior_momen(momen_baku).values
        pr["S_populer"] = self._populer.values
        pr["S_margin"] = pr["Persen_Margin"].clip(0, 1) / max(pr["Persen_Margin"].max(), 1e-9)
        pr["S_stok"] = pr["Status_Stok"].map({"Aman": 1.0, "Menipis": 0.6, "Habis": 0.0}).fillna(0.5)

        # kecocokan budget: makin dekat ke budget (tanpa melewati) makin baik
        def fit(h):
            if h <= b:
                return 0.55 + 0.45 * (h / b)
            if h <= b * (1 + TOLERANSI_BUDGET):
                return 0.35
            return 0.0

        pr["S_budget"] = pr["Harga_Jual"].map(fit)
        layak = pr[pr["S_budget"] > 0].copy()
        if layak.empty:
            termurah = pr.sort_values("Harga_Jual").head(top_n).copy()
            notes.append(f"Belum ada produk dengan harga sampai {rp(b)}. Produk termurah di katalog {rp(termurah['Harga_Jual'].min())}; "
                         "tampilkan opsi terdekat atau tawarkan custom (mis. ukuran lebih kecil).")
            layak = termurah.assign(S_budget=0.0)

        layak["Skor"] = sum(BOBOT[k] * layak[f"S_{k}"] for k in BOBOT)
        if layak["S_budget"].eq(0).all():  # fallback: semua di atas budget -> yang paling murah dulu
            layak = layak.sort_values(["Harga_Jual", "Skor"], ascending=[True, False]).head(top_n)
        else:
            layak = layak.sort_values(["Skor", "Harga_Jual"], ascending=[False, False]).head(top_n)
        layak["Skor"] = (layak["Skor"] * 100).round(0).astype(int)

        total_kat = self.pj.groupby("Kategori")["Jumlah_Terjual"].sum() if len(self.pj) else pd.Series(dtype=float)
        alasan = []
        for r in layak.itertuples():
            a = []
            if r.Harga_Jual <= b:
                a.append(f"Harga {rp(r.Harga_Jual)}, masih dalam budget (sisa {rp(b - r.Harga_Jual)})")
            elif r.Harga_Jual <= b * (1 + TOLERANSI_BUDGET):
                a.append(f"Harga {rp(r.Harga_Jual)}, sedikit di atas budget (+{rp(r.Harga_Jual - b)})")
            else:
                a.append(f"Harga {rp(r.Harga_Jual)} melebihi budget, opsi terdekat")
            prior = MOMEN[momen_baku].get(_kunci_kategori(r.Kategori), 0.5)
            if prior >= 0.9:
                a.append(f"{r.Kategori} sangat cocok untuk {momen_baku}")
            elif prior >= 0.7:
                a.append(f"{r.Kategori} cocok untuk {momen_baku}")
            if r.S_tema >= 0.35:
                a.append(f"cocok dengan tema {tema_baku or tema}")
            if len(total_kat) and r.Kategori in total_kat.index and total_kat.sum():
                sh = total_kat[r.Kategori] / total_kat.sum()
                if sh >= 0.25:
                    a.append(f"kategori ini ~{sh:.0%} dari item terjual")
            if r.Status_Stok == "Habis":
                a.append("stok habis: tawarkan pre-order")
            elif r.Status_Stok == "Menipis":
                a.append("stok menipis")
            a.append(f"margin {r.Persen_Margin:.0%}")
            alasan.append("; ".join(a))
        layak["Alasan"] = alasan

        kat_kunci = _kunci_kategori(layak.iloc[0]["Kategori"])
        sisa = b - layak.iloc[0]["Harga_Jual"]
        addon = self._addon(tema_baku, tema_kata, sisa, kat_kunci) if sisa >= 0 else []
        if not tema_baku:
            notes.append(f"Tema '{tema}' tidak ada di daftar baku; dicocokkan sebagai kata kunci bebas.")
        if len(self.pj) < 30:
            notes.append(f"Data penjualan baru {len(self.pj)} transaksi; kecocokan momen memakai aturan umum florist dan akan makin akurat saat data bertambah.")
        cols = ["ID_Produk", "Nama_Produk", "Kategori", "Harga_Jual", "Persen_Margin", "Stok_Saat_Ini", "Status_Stok", "Skor", "Alasan"]
        return Hasil(layak[cols].reset_index(drop=True), addon, notes, tema_baku or str(tema), momen_baku, b)

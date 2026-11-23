"""
api.py — REST API FastAPI untuk by.ficlo (stack plan: Python, pandas, scikit-learn, FastAPI).
Memakai modul yang sama dengan dashboard, jadi angkanya identik.

Jalankan:   pip install -r requirements-api.txt
            uvicorn api:app --reload --port 8000        # dokumentasi interaktif: http://localhost:8000/docs

Keamanan: set environment API_KEY, lalu kirim header  X-API-Key: <nilai>.  Tanpa API_KEY endpoint terbuka
(hanya untuk lokal). Endpoint keuangan (modal/pengeluaran) sengaja tidak disediakan.
"""
import hmac
import os
from pathlib import Path

import pandas as pd
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel

import analytics as an
import data_loader as dl
import recommender as rc

DATA_PATH = os.environ.get("FICLO_DATA", str(Path(__file__).resolve().parent / "Dataset_Dasboard_DS_byficlo.xlsx"))
API_KEY = os.environ.get("API_KEY", "")

app = FastAPI(title="by.ficlo API", version="1.0",
              description="Laporan penjualan, stok menipis, rekomendasi buket, dan FAQ.")


def auth(x_api_key: str = Header(default="")):
    if API_KEY and not hmac.compare_digest(x_api_key, API_KEY):
        raise HTTPException(401, "API key salah atau tidak ada.")


def data():
    return dl.load_all(DATA_PATH)  # dibaca ulang tiap request supaya selalu sesuai Excel terbaru


def _json(df: pd.DataFrame):
    df = df.copy()
    for c in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            df[c] = df[c].dt.strftime("%Y-%m-%d")
    return df.astype(object).where(df.notna(), None).to_dict("records")


class RekomendasiIn(BaseModel):
    budget: float | str | None = None
    tema: str | None = None
    momen: str | None = None
    catatan: str = ""
    top_n: int = 3


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/laporan/harian", dependencies=[Depends(auth)])
def laporan_harian():
    return _json(an.laporan_harian(data()["penjualan"]))


@app.get("/laporan/bulanan", dependencies=[Depends(auth)])
def laporan_bulanan():
    return _json(an.laporan_bulanan(data()["penjualan"]))


@app.get("/laporan/produk-terlaris", dependencies=[Depends(auth)])
def produk_terlaris(n: int = Query(10, ge=1, le=50), urut: str = Query("Item_Terjual", pattern="^(Item_Terjual|Pendapatan|Laba_Kotor)$")):
    return _json(an.produk_terlaris(data()["penjualan"], n, urut))


@app.get("/stok/menipis", dependencies=[Depends(auth)])
def stok_menipis():
    inv = data()["inventaris"]
    return _json(inv[inv["Status_Stok"] != "Aman"])


@app.get("/pesanan/status", dependencies=[Depends(auth)])
def pesanan_status():
    ps = data()["pesanan"]
    hitung = ps["Status_Pesanan"].value_counts().to_dict()
    return {s: int(hitung.get(s, 0)) for s in dl.STATUS_SEMUA}


@app.get("/faq", dependencies=[Depends(auth)])
def faq(q: str = ""):
    f = data()["faq"]
    if q:
        hay = (f["Pertanyaan"] + " " + f["Jawaban"] + " " + f["Kata_Kunci"]).str.lower()
        for t in q.lower().split():
            f = f[hay.loc[f.index].str.contains(t, regex=False)]
    return _json(f)


@app.post("/rekomendasi", dependencies=[Depends(auth)])
def rekomendasi(body: RekomendasiIn):
    try:
        h = rc.Rekomendator(data()).rekomendasi(body.budget, body.tema, body.momen, body.catatan, body.top_n)
    except rc.InputKosongError as e:
        raise HTTPException(422, detail=e.errors)  # input kosong ditolak
    return {"momen": h.momen, "tema": h.tema, "budget": h.budget, "produk": _json(h.produk), "pelengkap": h.addon, "catatan": h.catatan}

import hmac
import html
import io
import os
import zipfile
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import analytics as an
import data_loader as dl
import export_data as ex
import recommender as rc

st.set_page_config(page_title="by.ficlo Dashboard", page_icon="🌸", layout="wide")

HERE = Path(__file__).resolve().parent
DATA_PATH = os.environ.get("FICLO_DATA", str(HERE / "Dataset_Dasboard_DS_byficlo.xlsx"))

# ------------------------------------------------------------------ tema
GREEN, GREEN_L, PINK, PINK_L, PEACH = "#6B7F4B", "#A9BA8B", "#E8788F", "#F4B6C2", "#F2A883"
PALETTE = [GREEN, PINK, PEACH, GREEN_L, PINK_L, "#8E6C8A", "#E9C46A"]
STATUS_COLOR = {
    "Aman": GREEN, "Menipis": PEACH, "Perlu Restock": PEACH, "Habis": "#C0392B",
    "On Track": GREEN, "Tepat Waktu": GREEN_L, "Terlambat": PEACH, "Overdue": PINK, "Batal": "#9E9E9E",
    "Menunggu Verifikasi": PEACH, "Diproses": "#E9C46A", "Siap Diambil": GREEN_L, "Dikirim": "#8E6C8A", "Selesai": GREEN,
    "Ditolak": "#C0392B", "Kedaluwarsa": "#9E9E9E", "Dibatalkan": PINK,
    "Lunas": GREEN, "DP": PEACH, "Belum Bayar": PINK,
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&family=Dancing+Script:wght@600;700&display=swap');
:root { color-scheme: light; }
html, body, .stApp, .stApp p, .stApp label, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5,
.stApp button, .stApp input, .stApp textarea, .stApp summary, .stApp th, .stApp td { font-family: 'Poppins', sans-serif; }
/* jangan ubah font ikon (kalau tidak, nama ikon seperti 'arrow_right' tampil sebagai teks) */
span[data-testid="stIconMaterial"], .material-symbols-rounded, [class*="material-symbols"] {
    font-family: 'Material Symbols Rounded', 'Material Symbols Outlined' !important; }
.stApp { background: #FBF4F1; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 3.4rem; padding-bottom: 3rem; max-width: 1400px; }

/* ---------- sidebar ---------- */
section[data-testid="stSidebar"] { background: #66794A; }
section[data-testid="stSidebar"] .block-container { padding-top: 1.2rem; }
section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label { color: #FFFFFF; }
.logo { font-family: 'Dancing Script', cursive; font-size: 2.3rem; font-weight: 700; color: #fff; line-height: 1; margin-bottom: 2px; }
.logo-sub { font-size: .55rem; letter-spacing: .16em; color: #E4EBD6; margin-bottom: 14px; }
.admin-pill { display: inline-block; background: rgba(255,255,255,.18); color: #fff; padding: 3px 18px; border-radius: 999px;
              font-size: .62rem; letter-spacing: .12em; margin-bottom: 22px; }
section[data-testid="stSidebar"] div[role="radiogroup"] { gap: 6px; }
section[data-testid="stSidebar"] div[role="radiogroup"] > label { padding: 11px 16px; border-radius: 14px; width: 100%; cursor: pointer; }
section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child { display: none; }
section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover { background: rgba(255,255,255,.14); }
section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) { background: #FBF4F1; }
section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) p { color: #3F4F2B; font-weight: 600; }
.side-foot { margin-top: 40px; color: #E4EBD6; font-size: .7rem; line-height: 1.5; }
.side-flower { font-size: 3.4rem; opacity: .45; margin-top: 8px; }

/* ---------- header ---------- */
.topbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; }
.topbar .ttl { font-size: 1.9rem; font-weight: 600; color: #2F3A22; line-height: 1.15; }
.topbar .sub { font-size: .85rem; color: #6f6f6f; }
.topbar .right { display: flex; align-items: center; gap: 18px; }
.bell { position: relative; font-size: 1.3rem; }
.badge { position: absolute; top: -6px; right: -9px; background: #E8788F; color: #fff; font-size: .6rem; font-weight: 600;
         border-radius: 999px; padding: 1px 6px; }
.user { display: flex; align-items: center; gap: 8px; font-size: .8rem; font-weight: 600; color: #2F3A22; }
.avatar { width: 38px; height: 38px; border-radius: 50%; background: #F9DCE4; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; }

/* ---------- kartu KPI ---------- */
.kpi { border-radius: 20px; padding: 16px 18px; position: relative; overflow: hidden; min-height: 132px; box-shadow: 0 2px 10px rgba(90,70,60,.06); }
.kpi .top { display: flex; align-items: center; gap: 10px; }
.kpi .ico { width: 36px; height: 36px; border-radius: 12px; background: rgba(255,255,255,.75); display: flex; align-items: center; justify-content: center; font-size: 1.05rem; }
.kpi .lbl { font-size: .86rem; color: #4b4b4b; font-weight: 500; }
.kpi .val { font-size: 1.65rem; font-weight: 700; color: #2F3A22; margin: 8px 0 2px; }
.kpi .sub { font-size: .72rem; color: #7a7a7a; }
.kpi .deco { position: absolute; right: 10px; bottom: -8px; font-size: 3.4rem; opacity: .30; }
.kpi-green { background: #E4EBD6; } .kpi-pink { background: #F9DCE4; } .kpi-peach { background: #FCE5D6; }

/* ---------- panel putih ---------- */
.panel { background: #fff; border-radius: 20px; padding: 16px 18px; box-shadow: 0 2px 10px rgba(90,70,60,.06); }
.panel .ph { font-weight: 600; color: #2F3A22; font-size: .95rem; margin-bottom: 8px; }
.row { display: flex; align-items: center; gap: 12px; padding: 9px 0; border-top: 1px solid #F1E8E4; }
.row:first-of-type { border-top: none; }
.thumb { width: 44px; height: 44px; border-radius: 12px; background: #F9DCE4; display: flex; align-items: center; justify-content: center; font-size: 1.4rem; flex-shrink: 0; }
.row .meta { flex: 1; min-width: 0; }
.row .nm { font-size: .78rem; font-weight: 600; color: #2F3A22; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.row .amt { font-size: .85rem; font-weight: 700; color: #2F3A22; }
.row .dt { font-size: .68rem; color: #8a8a8a; }
.pill { font-size: .66rem; padding: 3px 10px; border-radius: 999px; font-weight: 600; white-space: nowrap; }
.pill-green { background: #E4EBD6; color: #4D5E33; } .pill-peach { background: #FCE5D6; color: #A5602F; }
.pill-pink { background: #F9DCE4; color: #A8405A; } .pill-grey { background: #EEE; color: #666; }
.banner { border-radius: 20px; min-height: 250px; padding: 28px 30px; position: relative; overflow: hidden;
          background: linear-gradient(120deg, #F4B6C2 0%, #F8D3DB 50%, #E4EBD6 100%); box-shadow: 0 2px 10px rgba(90,70,60,.06); }
.banner .bt { font-size: 1.9rem; font-weight: 600; color: #6B2F42; line-height: 1.2; margin-top: 70px; }
.banner .bs { font-size: .85rem; color: #7a4a58; margin-top: 8px; }
.banner .bf { position: absolute; right: 24px; top: 14px; font-size: 6rem; opacity: .55; }

/* ---------- komponen bawaan ---------- */
div[data-testid="stPlotlyChart"] { background: #fff; border-radius: 20px; padding: 8px 10px; box-shadow: 0 2px 10px rgba(90,70,60,.06); }
div[data-testid="stDataFrame"] { border-radius: 16px; overflow: hidden; box-shadow: 0 2px 10px rgba(90,70,60,.06); }
button[data-baseweb="tab"][aria-selected="true"] { color: #66794A; font-weight: 600; }
div[data-baseweb="tab-highlight"] { background-color: #66794A; }
div[data-testid="stExpander"] { background: #fff; border-radius: 16px; border: none; box-shadow: 0 2px 10px rgba(90,70,60,.06); }
.stDownloadButton button, .stButton button { border-radius: 999px; border: 1px solid #66794A; color: #66794A; background: #fff; }
h2, h3 { color: #2F3A22; }
button[data-testid="stBaseButton-primary"] { background: #66794A; border-color: #66794A; }
button[data-testid="stBaseButton-primary"]:hover { background: #55663D; border-color: #55663D; }
button[data-testid="stBaseButton-primary"] p { color: #FFFFFF !important; }

/* ---------- kunci warna teks agar selalu terbaca (tema terang maupun gelap) ---------- */
.stApp, .stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5,
.stApp summary, .stApp summary *, [data-testid="stWidgetLabel"] p, [data-testid="stCaptionContainer"] { color: #2F3A22; }
[data-testid="stCaptionContainer"] { color: #6f6f6f; }
.stApp label[data-baseweb="radio"] p, .stApp div[role="radiogroup"] label p { color: #2F3A22; }
section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span, section[data-testid="stSidebar"] label { color: #FFFFFF; }
section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) p { color: #3F4F2B; font-weight: 600; }
button[data-baseweb="tab"] p { color: #7a7a7a; }
button[data-baseweb="tab"][aria-selected="true"] p { color: #66794A; font-weight: 600; }
div[data-testid="stExpander"] details, div[data-testid="stExpander"] summary { background: #fff; border-radius: 16px; }
div[data-testid="stExpander"] summary { padding: 12px 16px; }
div[data-testid="stAlert"] { background: #FFFFFF; border: 1px solid #EFE3DE; border-radius: 14px; box-shadow: 0 2px 10px rgba(90,70,60,.06); overflow: hidden; }
div[data-testid="stAlert"] > div, div[data-testid="stAlert"] [data-baseweb="notification"], div[data-testid="stAlertContainer"] { background: transparent !important; }
div[data-testid="stAlert"] p, div[data-testid="stAlert"] span, div[data-testid="stAlert"] strong { color: #2F3A22 !important; }

/* ---------- baris status (mis. validasi impor) ---------- */
.status { display: flex; align-items: center; gap: 14px; background: #fff; border-radius: 16px; padding: 12px 16px;
          margin-bottom: 10px; box-shadow: 0 2px 10px rgba(90,70,60,.06); border-left: 5px solid #66794A; }
.status .ic { width: 30px; height: 30px; border-radius: 50%; background: #E4EBD6; color: #4D5E33; font-weight: 700;
              display: flex; align-items: center; justify-content: center; flex-shrink: 0; font-size: .95rem; }
.status .tx { flex: 1; min-width: 0; font-size: .88rem; color: #2F3A22; }
.status .tx b { font-weight: 700; color: #2F3A22; }
.status .tx span { color: #5f6b4d; margin-left: 6px; }
.status .tag { font-size: .68rem; font-weight: 600; padding: 3px 12px; border-radius: 999px; background: #E4EBD6; color: #4D5E33; white-space: nowrap; }
.status.bad { border-left-color: #D9708A; }
.status.bad .ic { background: #F9DCE4; color: #A8405A; }
.status.bad .tx span { color: #A8405A; }
.status.bad .tag { background: #F9DCE4; color: #A8405A; }
input, textarea, div[data-baseweb="select"] > div, div[data-baseweb="input"] { background-color: #FFFFFF !important; color: #2F3A22 !important; }
div[data-testid="stFileUploaderDropzone"] { background: #FBF4F1; border-radius: 14px; }
div[data-testid="stFileUploaderDropzone"] *, div[data-testid="stFileUploader"] small { color: #2F3A22; }
div[data-baseweb="popover"] > div, ul[role="listbox"], div[data-baseweb="calendar"] { background: #FFFFFF !important; }
div[data-baseweb="popover"] li, div[data-baseweb="popover"] *:not(svg):not(path) { color: #2F3A22; }
/* ---------- kolom isian & filter: terang, lembut, teks terbaca ---------- */
div[data-baseweb="input"], div[data-baseweb="base-input"], div[data-baseweb="select"] > div, div[data-baseweb="textarea"],
div[data-testid="stDateInput"] div[data-baseweb="input"], div[data-testid="stNumberInputContainer"] {
    background: #FFFFFF !important; border: 1.5px solid #E4EBD6 !important; border-radius: 12px !important; box-shadow: none !important; }
div[data-baseweb="input"] *, div[data-baseweb="base-input"] *, div[data-baseweb="select"] > div > div, div[data-baseweb="textarea"] * {
    background-color: transparent !important; color: #2F3A22 !important; }
div[data-baseweb="select"] svg, div[data-baseweb="input"] svg, div[data-testid="stDateInput"] svg { fill: #66794A !important; color: #66794A !important; }
div[data-baseweb="input"]:focus-within, div[data-baseweb="select"] > div:focus-within, div[data-baseweb="textarea"]:focus-within {
    border-color: #66794A !important; box-shadow: 0 0 0 3px rgba(102,121,74,.15) !important; }
input::placeholder, textarea::placeholder { color: #9AA58A !important; opacity: 1 !important; }
div[data-baseweb="select"] input { background: transparent !important; }
/* tag pilihan (multiselect) */
span[data-baseweb="tag"] { background: #E4EBD6 !important; border-radius: 999px !important; }
span[data-baseweb="tag"], span[data-baseweb="tag"] span, span[data-baseweb="tag"] svg { color: #4D5E33 !important; fill: #4D5E33 !important; background-color: transparent !important; }
span[data-baseweb="tag"] { background-color: #E4EBD6 !important; }
/* unggah file */
div[data-testid="stFileUploaderDropzone"] { background: #F4F8EC !important; border: 1.5px dashed #B9C79A !important; border-radius: 16px !important; }
div[data-testid="stFileUploaderDropzone"] *:not(button):not(button *) { color: #4D5E33 !important; background: transparent !important; }
div[data-testid="stFileUploaderDropzone"] button { background: #FFFFFF !important; border: 1.5px solid #66794A !important; border-radius: 999px !important; }
div[data-testid="stFileUploaderDropzone"] button, div[data-testid="stFileUploaderDropzone"] button * { color: #4D5E33 !important; }
div[data-testid="stFileUploaderDropzone"] button:hover { background: #E4EBD6 !important; }
.topbar .ttl { margin-bottom: 2px; }
.topbar .sub { margin-top: 2px; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ------------------------------------------------------------------ helper tampilan
def rp(x):
    try:
        return "Rp " + f"{float(x):,.0f}".replace(",", ".")
    except Exception:
        return "-"


def pct(x):
    try:
        return f"{float(x) * 100:.1f}%"
    except Exception:
        return "-"


def num(x):
    return f"{int(x):,}".replace(",", ".")


DECO = {"green": "🌿", "pink": "🌸", "peach": "🌼"}


def cards(items):
    """items: (label, nilai, keterangan, ikon, tema[green|pink|peach])"""
    cols = st.columns(len(items))
    for col, (label, value, sub, icon, theme) in zip(cols, items):
        col.markdown(
            f'<div class="kpi kpi-{theme}"><div class="top"><div class="ico">{icon}</div><div class="lbl">{html.escape(str(label))}</div></div>'
            f'<div class="val">{html.escape(str(value))}</div><div class="sub">{html.escape(str(sub))}</div>'
            f'<div class="deco">{DECO[theme]}</div></div>',
            unsafe_allow_html=True,
        )


def style(fig, height=340):
    fig.update_layout(
        template="plotly_white", height=height, margin=dict(l=10, r=10, t=48, b=10),
        legend=dict(orientation="h", y=-0.22), colorway=PALETTE,
        paper_bgcolor="#fff", plot_bgcolor="#fff",
        font=dict(family="Poppins, sans-serif", color="#4b4b4b"),
        title=dict(font=dict(size=15, color="#2F3A22")),
    )
    fig.update_xaxes(gridcolor="#F1E8E4")
    fig.update_yaxes(gridcolor="#F1E8E4")
    return fig


def plot(fig, height=340):
    st.plotly_chart(style(fig, height), theme=None)


def table(df, money=(), pct_cols=(), dates=()):
    cfg = {}
    for c in money:
        if c in df.columns:
            cfg[c] = st.column_config.NumberColumn(c.replace("_", " "), format="Rp %d")
    for c in pct_cols:
        if c in df.columns:
            cfg[c] = st.column_config.NumberColumn(c.replace("_", " "), format="%.1f%%")
    for c in dates:
        if c in df.columns:
            cfg[c] = st.column_config.DateColumn(c.replace("_", " "), format="DD/MM/YYYY")
    st.dataframe(df, hide_index=True, column_config=cfg)


def empty(df, msg="Belum ada data untuk bagian ini."):
    if df is None or len(df) == 0:
        st.info(msg)
        return True
    return False


def cat_icon(cat):
    c = str(cat).lower()
    if "snack" in c:
        return "🍫"
    if "money" in c:
        return "💵"
    if "artificial" in c:
        return "🌸"
    if "kemasan" in c:
        return "🎁"
    if "pita" in c:
        return "🎀"
    if "alat" in c:
        return "✂️"
    if "bunga" in c:
        return "🌷"
    return "💐"


def pill_class(status):
    s = str(status).lower()
    if s in ("selesai", "lunas", "aman", "tepat waktu", "on track", "siap diambil", "dikirim"):
        return "pill-green"
    if s in ("diproses", "menunggu", "menunggu verifikasi", "dp", "belum lunas", "menipis", "perlu restock"):
        return "pill-peach"
    if s in ("dibatalkan", "batal", "habis", "overdue", "terlambat", "ditolak", "kedaluwarsa", "belum bayar"):
        return "pill-pink"
    return "pill-grey"


# ------------------------------------------------------------------ sidebar (navigasi)
def _secret(name, default=""):
    """Baca dari Streamlit secrets (Cloud) atau environment variable (lokal/Colab)."""
    try:
        v = st.secrets.get(name)
    except Exception:  # tidak ada secrets.toml
        v = None
    return str(v if v is not None else os.environ.get(name, default))


APP_PASSWORD = _secret("APP_PASSWORD")
PUBLIC_MODE = _secret("FICLO_PUBLIC", "0").strip().lower() in ("1", "true", "yes", "ya")

P_OV, P_SALES, P_INV, P_ORD, P_FIN, P_REC, P_FAQ = (
    "🏠 Overview", "📈 Sales Analytics", "📦 Inventory Monitoring", "🧾 Order Monitoring", "💰 Financial Analytics",
    "💡 Rekomendasi & Analisis", "❓ FAQ & Data Siap Impor",
)
# Mode publik: halaman keuangan (modal, pengeluaran, laba bersih) tidak ditampilkan sama sekali.
PAGES = [P_OV, P_SALES, P_INV, P_ORD, P_REC, P_FAQ] if PUBLIC_MODE else [P_OV, P_SALES, P_INV, P_ORD, P_FIN, P_REC, P_FAQ]

# ---- gerbang password (opsional): aktif bila APP_PASSWORD diisi di Secrets / environment
if APP_PASSWORD and not st.session_state.get("auth_ok"):
    st.markdown('<div class="logo" style="color:#66794A;font-size:2.6rem">by.ficlo</div>', unsafe_allow_html=True)
    st.subheader("🔒 Dashboard khusus admin")
    pw = st.text_input("Password", type="password")
    if st.button("Masuk"):
        if hmac.compare_digest(pw.encode(), APP_PASSWORD.encode()):
            st.session_state["auth_ok"] = True
            st.rerun()
        else:
            st.error("Password salah.")
    st.stop()

st.sidebar.markdown(
    '<div class="logo">by.ficlo</div><div class="logo-sub">FLORIST &amp; BOUQUET DECOR</div>'
    '<div class="admin-pill">ADMIN PANEL</div>',
    unsafe_allow_html=True,
)
page = st.sidebar.radio("Navigasi", PAGES, label_visibility="collapsed")
if PUBLIC_MODE:
    st.sidebar.caption("🔓 Mode publik: data keuangan & kode pelanggan disembunyikan.")
elif APP_PASSWORD:
    st.sidebar.caption("🔒 Dilindungi password.")

# ------------------------------------------------------------------ slot header, lalu kontrol data
header_slot = st.container()
ctrl = st.expander("🔎 Filter & sumber data")


@st.cache_data(show_spinner="Membaca & membersihkan data...")
def load(file_bytes, path, mtime):
    src = io.BytesIO(file_bytes) if file_bytes else path
    return dl.load_all(src)


with ctrl:
    u1, u2 = st.columns([3, 1])
    with u1:
        upload = None if PUBLIC_MODE else st.file_uploader("Ganti dataset (.xlsx)", type=["xlsx"])
        if PUBLIC_MODE:
            st.caption("Unggah dataset dimatikan di mode publik.")
    with u2:
        st.write("")
        st.write("")
        if st.button("🔄 Muat ulang data"):
            st.cache_data.clear()
            st.rerun()

if upload is not None:
    d = load(upload.getvalue(), None, 0)
elif os.path.exists(DATA_PATH):
    d = load(None, DATA_PATH, os.path.getmtime(DATA_PATH))
else:
    st.error(f"File '{DATA_PATH}' tidak ditemukan. Taruh file Excel di folder yang sama dengan app.py, atau unggah lewat panel Filter.")
    st.stop()

if PUBLIC_MODE:
    d = dict(d)
    d["pesanan"] = d["pesanan"].assign(Kode_Pelanggan="PLG***", Catatan="")
    d["kas"], d["pengeluaran"] = d["kas"].iloc[0:0], d["pengeluaran"].iloc[0:0]
produk, bahan, penjualan = d["produk"], d["bahan"], d["penjualan"]
mutasi, pesanan, produksi = d["mutasi"], d["pesanan"], d["produksi"]
pengeluaran, kas, today = d["pengeluaran"], d["kas"], d["today"]

if len(penjualan):
    dmin, dmax = penjualan["Tanggal"].min().date(), penjualan["Tanggal"].max().date()
else:
    dmin = dmax = today.date()
opt_kat = sorted(penjualan["Kategori"].dropna().unique())
opt_kanal = sorted(penjualan["Kanal_Penjualan"].dropna().unique())
opt_status = sorted(penjualan["Status_Transaksi"].dropna().unique())

with ctrl:
    st.markdown("**Filter data penjualan**")
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        rentang = st.date_input("Periode", value=(dmin, dmax), min_value=dmin, max_value=dmax)
    with f2:
        f_kat = st.multiselect("Kategori produk", opt_kat, default=opt_kat)
    with f3:
        f_kanal = st.multiselect("Kanal penjualan", opt_kanal, default=opt_kanal)
    with f4:
        f_status = st.multiselect("Status transaksi", opt_status, default=opt_status)

start, end = (rentang if isinstance(rentang, (list, tuple)) and len(rentang) == 2 else (dmin, dmax))
pj = penjualan[
    (penjualan["Tanggal"] >= pd.Timestamp(start))
    & (penjualan["Tanggal"] <= pd.Timestamp(end))
    & penjualan["Kategori"].isin(f_kat)
    & penjualan["Kanal_Penjualan"].isin(f_kanal)
    & penjualan["Status_Transaksi"].isin(f_status)
]
pg = pengeluaran[(pengeluaran["Tanggal"] >= pd.Timestamp(start)) & (pengeluaran["Tanggal"] <= pd.Timestamp(end))]

# ---- ringkasan peringatan (untuk lonceng di header)
stok_items = pd.concat([
    produk.assign(Nama=produk["Nama_Produk"], Min=produk["Stok_Minimum"], Jenis="Produk", Kat=produk["Kategori"],
                  Satuan=produk["Satuan"] if "Satuan" in produk.columns else "pcs")[["Nama", "Stok_Saat_Ini", "Min", "Satuan", "Status_Stok", "Jenis", "Kat"]],
    bahan.assign(Nama=bahan["Nama_Bahan"], Min=bahan["Stok_Minimum"], Jenis="Bahan", Kat=bahan["Kategori_Bahan"])[["Nama", "Stok_Saat_Ini", "Min", "Satuan", "Status_Stok", "Jenis", "Kat"]],
], ignore_index=True)
n_stok = int((stok_items["Status_Stok"] != "Aman").sum())
n_overdue = int((pesanan["Status_SLA"] == "Overdue").sum())
n_notif = n_stok + n_overdue + len(d["dq"]["peringatan"])

SUBTITLE = {
    P_OV: "Selamat datang kembali, Admin! Ringkasan kondisi bisnis by.ficlo.",
    P_SALES: "Laporan harian/bulanan, produk terlaris, dan pencocokan dengan data pesanan website.",
    P_INV: "Peringatan stok menipis, stok bunga, wrapping, pita, aksesoris, dan produk jadi.",
    P_ORD: "Alur pesanan: Menunggu Verifikasi → Diproses → Siap Diambil/Dikirim → Selesai (jalur gagal: Ditolak, Kedaluwarsa, Dibatalkan).",
    P_FIN: "Nilai tambah di luar plan: modal, pengeluaran, pendapatan, dan keuntungan.",
    P_REC: "Tanya Rekomendasi buket (budget, tema, momen) dan analisis data pendukungnya.",
    P_FAQ: "Pertanyaan umum pelanggan dan data bersih (produk, inventaris, FAQ) siap impor ke database.",
}
TITLE = {P_OV: "Overview", P_SALES: "Sales Analytics", P_INV: "Inventory Monitoring", P_ORD: "Order Monitoring",
         P_FIN: "Financial Analytics", P_REC: "Rekomendasi & Analisis", P_FAQ: "FAQ & Data Siap Impor"}
with header_slot:
    st.markdown(
        f'<div class="topbar"><div><div class="ttl">☰ {TITLE[page]}</div><div class="sub">{SUBTITLE[page]}</div></div>'
        f'<div class="right"><div class="bell">🔔<span class="badge">{n_notif}</span></div>'
        f'<div class="user"><div class="avatar">🌸</div>Admin Ficlo</div></div></div>',
        unsafe_allow_html=True,
    )

st.sidebar.markdown(
    f'<div class="side-foot">Data per {today.strftime("%d %b %Y")}<br>{len(pj)} baris penjualan terpilih</div>'
    '<div class="side-flower">🌸🌿</div>',
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------ 1. OVERVIEW
def page_overview():
    omzet, laba = pj["Total_Penjualan"].sum(), pj["Laba_Kotor"].sum()
    n_trx = pj["ID_Transaksi"].nunique()
    cards([
        ("Total Pendapatan", rp(omzet), f"Margin kotor {pct(laba / omzet)}" if omzet else "-", "💰", "peach"),
        ("Total Pesanan", num(n_trx), f"+ {len(pesanan)} custom order (PO)", "🛍️", "green"),
        ("Keuntungan (Laba Kotor)", rp(laba), "Pendapatan − HPP", "📈", "pink"),
        ("Produk Terjual", num(pj["Jumlah_Terjual"].sum()), "Total item pada periode", "📦", "green"),
    ])
    st.write("")

    if len(pj) == 0:
        st.info("Tidak ada penjualan pada filter yang dipilih.")
    else:
        c1, c2 = st.columns([2, 1])
        with c1:
            gran = st.radio("Tampilkan per", ["Harian", "Mingguan", "Bulanan"], horizontal=True, key="gran_ov")
            freq = {"Harian": "D", "Mingguan": "W", "Bulanan": "MS"}[gran]
            tren = pj.groupby(pd.Grouper(key="Tanggal", freq=freq))["Total_Penjualan"].sum().reset_index()
            fig = go.Figure(go.Scatter(
                x=tren["Tanggal"], y=tren["Total_Penjualan"], mode="lines+markers",
                line=dict(color=GREEN, width=3, shape="spline"), marker=dict(size=8, color=GREEN),
                fill="tozeroy", fillcolor="rgba(107,127,75,0.15)",
                hovertemplate="%{x|%d %b %Y}<br>Rp %{y:,.0f}<extra></extra>"))
            fig.update_layout(title="Grafik Pendapatan", yaxis_title=None, xaxis_title=None)
            plot(fig, 340)
        with c2:
            terbaru = pj.sort_values(["Tanggal", "ID_Transaksi"], ascending=False).head(4)
            rows = "".join(
                f'<div class="row"><div class="thumb">{cat_icon(r.Kategori)}</div><div class="meta">'
                f'<div class="nm">{html.escape(r.ID_Transaksi)} · {html.escape(str(r.Nama_Produk))}</div>'
                f'<div class="amt">{rp(r.Total_Penjualan)}</div><div class="dt">{r.Tanggal.strftime("%d %b %Y")}</div></div>'
                f'<span class="pill {pill_class(r.Status_Pembayaran)}">{html.escape(str(r.Status_Pembayaran))}</span></div>'
                for r in terbaru.itertuples()
            )
            st.markdown(f'<div class="panel" style="min-height:392px"><div class="ph">Pesanan Terbaru</div>{rows}</div>', unsafe_allow_html=True)

    st.write("")
    c1, c2 = st.columns([1, 2])
    with c1:
        urut = stok_items.assign(_s=stok_items["Status_Stok"].map({"Habis": 0, "Menipis": 1, "Perlu Restock": 1, "Aman": 2}),
                                 _r=stok_items["Stok_Saat_Ini"] / stok_items["Min"].where(stok_items["Min"] > 0))
        urut = urut.sort_values(["_s", "_r"]).head(3)
        judul = "Stok Menipis" if n_stok else "Stok Terendah (semua masih aman)"
        rows = "".join(
            f'<div class="row"><div class="thumb">{cat_icon(r.Kat)}</div><div class="meta"><div class="nm">{html.escape(str(r.Nama))}</div>'
            f'<div class="dt">Stok tersisa: {r.Stok_Saat_Ini:g} {html.escape(str(r.Satuan))}</div></div>'
            f'<span class="pill {pill_class(r.Status_Stok)}">&lt; {r.Min:g}</span></div>'
            for r in urut.itertuples()
        )
        st.markdown(f'<div class="panel" style="min-height:250px"><div class="ph">⚠️ {judul}</div>{rows}</div>', unsafe_allow_html=True)
    with c2:
        st.markdown(
            '<div class="banner"><div class="bf">💐</div><div class="bt">Make It Bloom<br>With by.ficlo ♡</div>'
            '<div class="bs">Buket cantik, untuk setiap momen spesialmu.</div></div>',
            unsafe_allow_html=True,
        )

    if len(pj):
        st.write("")
        c1, c2 = st.columns(2)
        with c1:
            kat = pj.groupby("Kategori")["Total_Penjualan"].sum().reset_index()
            plot(px.pie(kat, names="Kategori", values="Total_Penjualan", hole=0.55, title="Pendapatan per Kategori"), 320)
        with c2:
            top = (pj.groupby("Nama_Produk").agg(Omzet=("Total_Penjualan", "sum"), Terjual=("Jumlah_Terjual", "sum"))
                   .reset_index().sort_values("Omzet", ascending=False).head(5).sort_values("Omzet"))
            fig = px.bar(top, x="Omzet", y="Nama_Produk", orientation="h", text="Terjual", title="Top 5 Produk Terjual (label = jumlah)")
            fig.update_traces(marker_color=PINK)
            fig.update_layout(yaxis_title=None)
            plot(fig, 320)

    st.write("")
    with st.expander(f"🧹 Catatan kualitas data ({len(d['dq']['peringatan'])})"):
        st.caption("Catatan otomatis dari proses pembersihan. Rapikan di Excel supaya angka makin akurat.")
        if not d["dq"]["peringatan"]:
            st.success("Tidak ada masalah yang terdeteksi ✅")
        for w in d["dq"]["peringatan"]:
            st.warning(w)
        if len(d["dq"]["selisih_penjualan"]):
            st.markdown("**Selisih nilai Excel vs hitung ulang (PENJUALAN)**")
            table(d["dq"]["selisih_penjualan"], money=["Nilai_di_Excel", "Nilai_Hitung_Ulang"], dates=["Tanggal"])
        if len(d["dq"]["selisih_stok"]):
            st.markdown("**Selisih stok Excel vs hitung ulang**")
            table(d["dq"]["selisih_stok"])
        if len(d["dq"]["saran_mapping"]):
            st.markdown("**Saran isi ID_Produk untuk baris penjualan yang belum terhubung ke katalog**")
            st.caption("Dicocokkan dari nama mirip + harga sama. Cek manual sebelum dipakai; hanya saran, tidak mengubah data.")
            table(d["dq"]["saran_mapping"], money=["Harga"])


# ------------------------------------------------------------------ 2. SALES
def page_sales():
    if len(pj) == 0:
        st.info("Tidak ada penjualan pada filter yang dipilih.")
        return
    omzet, laba = pj["Total_Penjualan"].sum(), pj["Laba_Kotor"].sum()
    n_trx = pj["ID_Transaksi"].nunique()
    cards([
        ("Pendapatan", rp(omzet), "Periode terpilih", "💰", "peach"),
        ("Laba Kotor", rp(laba), f"Margin {pct(laba / omzet)}" if omzet else "-", "📈", "green"),
        ("Transaksi", num(n_trx), f"Item terjual: {num(pj['Jumlah_Terjual'].sum())}", "🛍️", "pink"),
        ("Rata-rata / Transaksi", rp(omzet / n_trx) if n_trx else "-", "Nilai keranjang", "🧺", "green"),
    ])
    st.write("")
    t1, t2, t3, t4, t5, t6 = st.tabs(["Tren Penjualan", "Produk Terlaris", "Pendapatan Bulanan", "Kanal & Pelanggan", "Data Transaksi",
                                      "Laporan & Cocokkan dengan Website"])

    with t1:
        gran = st.radio("Granularitas", ["Harian", "Mingguan", "Bulanan"], horizontal=True, key="gran_sales")
        freq = {"Harian": "D", "Mingguan": "W", "Bulanan": "MS"}[gran]
        tren = pj.groupby([pd.Grouper(key="Tanggal", freq=freq), "Kategori"])["Total_Penjualan"].sum().reset_index()
        fig = px.bar(tren, x="Tanggal", y="Total_Penjualan", color="Kategori", title=f"Pendapatan {gran} per Kategori")
        fig.update_layout(yaxis_title="Rupiah", xaxis_title=None, legend_title=None)
        plot(fig, 380)
        kum = pj.groupby("Tanggal")["Total_Penjualan"].sum().cumsum().reset_index(name="Omzet_Kumulatif")
        fig = px.area(kum, x="Tanggal", y="Omzet_Kumulatif", title="Pendapatan Kumulatif")
        fig.update_traces(line_color=GREEN, fillcolor="rgba(107,127,75,0.15)")
        plot(fig, 300)

    with t2:
        ringkas = (pj.groupby("Nama_Produk").agg(Omzet=("Total_Penjualan", "sum"), Terjual=("Jumlah_Terjual", "sum"),
                                                 Laba_Kotor=("Laba_Kotor", "sum")).reset_index())
        ringkas["Margin_Persen"] = (ringkas["Laba_Kotor"] / ringkas["Omzet"]).fillna(0) * 100
        metrik = st.radio("Urutkan berdasarkan", ["Omzet", "Terjual", "Laba_Kotor"], horizontal=True)
        top = ringkas.sort_values(metrik, ascending=False).head(10).sort_values(metrik)
        fig = px.bar(top, x=metrik, y="Nama_Produk", orientation="h", title=f"Produk Terlaris berdasarkan {metrik.replace('_', ' ')}")
        fig.update_traces(marker_color=PINK)
        fig.update_layout(yaxis_title=None)
        plot(fig, 380)
        fig = px.bar(ringkas.sort_values("Margin_Persen"), x="Margin_Persen", y="Nama_Produk", orientation="h", title="Margin Kotor per Produk (%)")
        fig.update_traces(marker_color=GREEN)
        fig.update_layout(yaxis_title=None)
        plot(fig, 320)
        table(ringkas.sort_values("Omzet", ascending=False), money=["Omzet", "Laba_Kotor"], pct_cols=["Margin_Persen"])

    with t3:
        bln = pj.groupby("Bulan").agg(Pendapatan=("Total_Penjualan", "sum"), Laba_Kotor=("Laba_Kotor", "sum")).reset_index()
        fig = px.bar(bln, x="Bulan", y=["Pendapatan", "Laba_Kotor"], barmode="group", title="Pendapatan & Laba Kotor per Bulan",
                     color_discrete_map={"Pendapatan": GREEN, "Laba_Kotor": PINK})
        fig.update_layout(yaxis_title="Rupiah", xaxis_title=None, legend_title=None)
        plot(fig, 380)
        bk = pj.groupby(["Bulan", "Kategori"])["Total_Penjualan"].sum().reset_index()
        plot(px.bar(bk, x="Bulan", y="Total_Penjualan", color="Kategori", title="Pendapatan Bulanan per Kategori"), 320)
        table(bln, money=["Pendapatan", "Laba_Kotor"])

    with t4:
        c1, c2 = st.columns(2)
        for col, kolom, judul in [(c1, "Kanal_Penjualan", "Pendapatan per Kanal"), (c2, "Metode_Pembayaran", "Per Metode Pembayaran"),
                                  (c1, "Tipe_Pelanggan", "Per Tipe Pelanggan"), (c2, "Status_Pembayaran", "Status Pembayaran")]:
            with col:
                g = pj.groupby(kolom)["Total_Penjualan"].sum().reset_index()
                plot(px.pie(g, names=kolom, values="Total_Penjualan", hole=0.55, title=judul), 300)
        belum = pj[pj["Status_Pembayaran"] != "Lunas"]["Total_Penjualan"].sum()
        st.info(f"Penjualan belum lunas (piutang): **{rp(belum)}**")

    with t5:
        kolom = ["ID_Transaksi", "Tanggal", "Nama_Produk", "Kategori", "Jumlah_Terjual", "Harga_Jual_Satuan", "Diskon",
                 "Total_Penjualan", "Total_HPP", "Laba_Kotor", "Metode_Pembayaran", "Status_Pembayaran", "Kanal_Penjualan",
                 "Tipe_Pelanggan", "Status_Transaksi"]
        table(pj[kolom], money=["Harga_Jual_Satuan", "Diskon", "Total_Penjualan", "Total_HPP", "Laba_Kotor"], dates=["Tanggal"])
        st.download_button("⬇️ Unduh CSV", pj[kolom].to_csv(index=False).encode("utf-8"), "penjualan_terfilter.csv", "text/csv")

    with t6:
        st.markdown("#### Laporan penjualan")
        st.caption("Mengikuti filter periode/kategori/kanal di panel Filter. Angka yang sama dipakai API (`api.py`).")
        harian, bulanan, terlaris = an.laporan_harian(pj), an.laporan_bulanan(pj), an.produk_terlaris(pj, 10)
        money = ["Pendapatan", "HPP", "Laba_Kotor"]
        r1, r2 = st.tabs(["Harian", "Bulanan"])
        with r1:
            table(harian, money=money, pct_cols=["Margin_Persen"], dates=["Tanggal"])
            st.download_button("⬇️ Laporan harian (CSV)", harian.to_csv(index=False).encode("utf-8"), "laporan_harian.csv", "text/csv")
        with r2:
            table(bulanan, money=money, pct_cols=["Margin_Persen"])
            st.download_button("⬇️ Laporan bulanan (CSV)", bulanan.to_csv(index=False).encode("utf-8"), "laporan_bulanan.csv", "text/csv")
        st.markdown("**Produk terlaris**")
        table(terlaris, money=["Pendapatan", "Laba_Kotor"])

        st.markdown("#### Cocokkan angka dengan data pesanan website")
        st.info(
            "Sumber dashboard ini adalah Excel (PENJUALAN), bukan database pesanan website. Untuk membuktikan angkanya cocok, unggah "
            "ekspor pesanan dari website (CSV/XLSX, kolom tanggal + total, opsional id_pesanan). Dashboard membandingkan total per hari."
        )
        c1, c2 = st.columns([3, 1])
        with c1:
            web_file = st.file_uploader("Ekspor pesanan website", type=["csv", "xlsx"], key="web_up")
        with c2:
            st.write("")
            st.download_button("⬇️ Contoh format CSV", an.TEMPLATE_WEBSITE_CSV.encode("utf-8"), "contoh_pesanan_website.csv", "text/csv")
        abaikan_batal = st.checkbox("Abaikan transaksi berstatus Dibatalkan", value=True)
        if web_file is not None:
            web, err = an.baca_data_website(web_file, web_file.name)
            if err:
                st.error(err)
            else:
                basis = penjualan[penjualan["Status_Transaksi"] != "Dibatalkan"] if abaikan_batal else penjualan
                rk = an.rekonsiliasi(basis, web)
                r = rk["ringkas"]
                cards([
                    ("Hari Cocok", f"{r['cocok']}/{r['hari']}", pct(r["persen_cocok"]), "✅", "green"),
                    ("Total Dashboard", rp(r["total_dashboard"]), "dari Excel PENJUALAN", "📊", "peach"),
                    ("Total Website", rp(r["total_website"]), "dari file yang diunggah", "🌐", "pink"),
                    ("Selisih", rp(r["selisih_total"]), "Dashboard − Website", "⚖️", "green"),
                ])
                if r["cocok"] == r["hari"]:
                    st.success("Semua hari cocok. Angka dashboard sama dengan data pesanan website.")
                else:
                    st.warning("Ada hari yang tidak cocok. Cek baris bertanda Selisih / Hanya di ... di bawah.")
                st.write("")
                table(rk["harian"], money=["Total_Dashboard", "Total_Website", "Selisih"], dates=["Tanggal"])
                if rk["per_id"] is not None:
                    st.markdown("**Per ID pesanan**")
                    table(rk["per_id"], money=["Total_Dashboard", "Total_Website", "Selisih"])


# ------------------------------------------------------------------ 3. INVENTORY
def stok_chart(df, nama_col, judul, tinggi=380):
    long = df.melt(id_vars=[nama_col], value_vars=["Stok_Saat_Ini", "Stok_Minimum"], var_name="Jenis", value_name="Jumlah")
    fig = px.bar(long, x=nama_col, y="Jumlah", color="Jenis", barmode="group", title=judul,
                 color_discrete_map={"Stok_Saat_Ini": GREEN, "Stok_Minimum": PINK})
    fig.update_layout(xaxis_title=None, legend_title=None)
    return fig


def page_inventory():
    cards([
        ("Produk Aktif", num((produk["Status"] == "Aktif").sum()), f"{len(produk)} produk di katalog", "💐", "green"),
        ("Produk Menipis / Habis", num((produk["Status_Stok"] != "Aman").sum()), "Perlu produksi ulang", "🎁", "pink"),
        ("Bahan Perlu Restock", num((bahan["Status_Stok"] != "Aman").sum()), f"dari {len(bahan)} jenis bahan", "⚠️", "peach"),
        ("Nilai Persediaan Bahan", rp(bahan["Nilai_Persediaan"].sum()), "Stok × harga beli", "🧮", "green"),
    ])
    st.write("")
    t0, t1, t2, t3 = st.tabs(["🚨 Peringatan Stok", "Produk Jadi", "Bunga, Wrapping, Pita & Aksesoris", "Mutasi & Produksi"])

    with t0:
        inv = d["inventaris"]
        rendah = inv[inv["Status_Stok"] != "Aman"].copy()
        habis = int((rendah["Status_Stok"] == "Habis").sum())
        if rendah.empty:
            st.success("Semua stok di atas batas minimum. Tidak ada yang perlu dibeli saat ini.")
        else:
            st.error(f"{len(rendah)} item butuh perhatian: {habis} habis, {len(rendah) - habis} menipis. "
                     f"Estimasi biaya isi ulang {rp(rendah['Estimasi_Biaya_Restock'].sum())}.")
            rendah["_u"] = rendah["Status_Stok"].map({"Habis": 0}).fillna(1)
            rendah = rendah.sort_values(["_u", "Stok_Saat_Ini"])
            kol = ["ID_Item", "Jenis_Item", "Nama_Item", "Kategori", "Stok_Saat_Ini", "Stok_Minimum", "Satuan", "Status_Stok",
                   "Saran_Restock_Qty", "Harga_Satuan", "Estimasi_Biaya_Restock"]
            table(rendah[kol], money=["Harga_Satuan", "Estimasi_Biaya_Restock"])
            st.download_button("⬇️ Unduh daftar belanja (CSV)", rendah[kol].to_csv(index=False).encode("utf-8"), "daftar_restock.csv", "text/csv")
        st.caption(f"Aturan: status Menipis/Perlu Restock bila stok ≤ stok minimum, Habis bila ≤ 0. Saran restock = {dl.TARGET_RESTOCK_X} × stok minimum − stok saat ini. "
                   "Jumlah peringatan juga tampil di lonceng 🔔 pojok kanan atas semua halaman.")
        pantau = inv.assign(Rasio=inv["Stok_Saat_Ini"] / inv["Stok_Minimum"].where(inv["Stok_Minimum"] > 0))
        pantau = pantau[pantau["Status_Stok"] == "Aman"].sort_values("Rasio").head(8)
        if len(pantau):
            st.markdown("**Hampir menipis (masih aman, rasio stok/minimum terendah)**")
            table(pantau[["ID_Item", "Nama_Item", "Stok_Saat_Ini", "Stok_Minimum", "Satuan", "Rasio"]])

    with t1:
        plot(stok_chart(produk, "Nama_Produk", "Stok Produk vs Stok Minimum"), 380)
        table(produk[["ID_Produk", "Nama_Produk", "Kategori", "Harga_Jual", "HPP_Standar", "Persen_Margin", "Stok_Awal",
                      "Stok_Saat_Ini", "Stok_Minimum", "Status_Stok", "Status"]].assign(Persen_Margin=lambda x: x["Persen_Margin"] * 100),
              money=["Harga_Jual", "HPP_Standar"], pct_cols=["Persen_Margin"])

    with t2:
        ringkas = bahan.groupby("Kategori_Bahan").agg(Jenis=("ID_Bahan", "count"), Nilai=("Nilai_Persediaan", "sum"),
                                                      Restock=("Status_Stok", lambda s: int((s != "Aman").sum()))).reset_index()
        temas = ["green", "pink", "peach"]
        cards([(r.Kategori_Bahan, f"{r.Jenis} jenis", f"Nilai {rp(r.Nilai)} · {r.Restock} perlu restock", cat_icon(r.Kategori_Bahan), temas[i % 3])
               for i, r in enumerate(ringkas.itertuples())][:4])
        st.write("")
        pilih = st.radio("Kategori bahan", ["Semua"] + sorted(bahan["Kategori_Bahan"].unique()), horizontal=True)
        b = bahan if pilih == "Semua" else bahan[bahan["Kategori_Bahan"] == pilih]
        c1, c2 = st.columns(2)
        with c1:
            g = b.groupby("Status_Stok").size().reset_index(name="Jumlah")
            plot(px.pie(g, names="Status_Stok", values="Jumlah", hole=0.55, title="Status Stok Bahan",
                        color="Status_Stok", color_discrete_map=STATUS_COLOR), 300)
        with c2:
            g = b.groupby("Kategori_Bahan")["Nilai_Persediaan"].sum().reset_index()
            fig = px.bar(g, x="Kategori_Bahan", y="Nilai_Persediaan", title="Nilai Persediaan per Kategori")
            fig.update_traces(marker_color=PINK)
            fig.update_layout(xaxis_title=None)
            plot(fig, 300)
        rendah = b.dropna(subset=["Rasio_Stok"]).sort_values("Rasio_Stok").head(10)
        if len(rendah):
            plot(stok_chart(rendah, "Nama_Bahan", "10 Bahan dengan Rasio Stok/Minimum Terendah"), 380)
        table(b[["ID_Bahan", "Nama_Bahan", "Kategori_Bahan", "Supplier", "Satuan", "Stok_Awal", "Mutasi_Masuk", "Mutasi_Keluar",
                 "Stok_Saat_Ini", "Stok_Minimum", "Harga_Beli_Satuan", "Nilai_Persediaan", "Status_Stok"]],
              money=["Harga_Beli_Satuan", "Nilai_Persediaan"])

    with t3:
        st.markdown("**Mutasi stok**")
        if not empty(mutasi, "Belum ada mutasi stok."):
            g = mutasi.groupby(["Alasan_Mutasi", "Jenis_Mutasi"])["Jumlah"].sum().reset_index()
            plot(px.bar(g, x="Alasan_Mutasi", y="Jumlah", color="Jenis_Mutasi", barmode="group", title="Mutasi per Alasan"), 300)
            table(mutasi.drop(columns=["Nama_Item"], errors="ignore"), dates=["Tanggal"])
        st.markdown("**Produksi (pemakaian bahan)**")
        if not empty(produksi, "Belum ada catatan produksi."):
            g = produksi.groupby("Nama_Produk")[["Total_Biaya_Bahan", "Biaya_Tambahan"]].sum().reset_index()
            plot(px.bar(g, x="Nama_Produk", y=["Total_Biaya_Bahan", "Biaya_Tambahan"], title="Biaya Produksi per Produk"), 300)
            table(produksi, money=["Harga_Beli_Satuan", "Total_Biaya_Bahan", "Biaya_Tambahan", "Total_Biaya_Produksi"], dates=["Tanggal_Produksi"])


# ------------------------------------------------------------------ 4. ORDERS
def page_orders():
    n = lambda *st_: int(pesanan["Status_Pesanan"].isin(st_).sum())  # noqa: E731
    cards([
        ("Menunggu Verifikasi", num(n("Menunggu Verifikasi")), "Pembayaran/DP sedang dicek admin", "🕑", "peach"),
        ("Diproses", num(n("Diproses")), "Sedang dikerjakan", "🛠️", "peach"),
        ("Siap Diambil / Dikirim", num(n("Siap Diambil", "Dikirim")), "Menunggu serah-terima", "📦", "green"),
        ("Selesai", num(n("Selesai")), "Sudah diserahkan", "✅", "green"),
    ])
    st.write("")
    cards([
        ("Ditolak", num(n("Ditolak")), "Pembayaran/pesanan ditolak", "⛔", "pink"),
        ("Kedaluwarsa", num(n("Kedaluwarsa")), f"Tidak diverifikasi dalam {dl.BATAS_VERIFIKASI_HARI} hari", "⌛", "pink"),
        ("Dibatalkan", num(n("Dibatalkan")), "Dibatalkan pelanggan/admin", "✖️", "pink"),
        ("Total Pesanan Masuk", num(len(pesanan)), "Semua status", "📥", "green"),
    ])
    if empty(pesanan, "Belum ada data pesanan."):
        return
    st.write("")
    selesai = pesanan[pesanan["Status_SLA"].isin(["Tepat Waktu", "Terlambat"])]
    ontime = (selesai["Status_SLA"] == "Tepat Waktu").mean() if len(selesai) else None
    aktif = pesanan[~pesanan["Status_Pesanan"].isin(dl.STATUS_GAGAL)]
    cards([
        ("Overdue", num((pesanan["Status_SLA"] == "Overdue").sum()), "Lewat deadline, belum selesai", "⏰", "pink"),
        ("Tepat Waktu", pct(ontime) if ontime is not None else "-", "Dari pesanan yang sudah selesai", "🎯", "green"),
        ("Nilai Pesanan Aktif", rp(aktif["Total_Harga"].sum()), f"DP diterima {rp(aktif['DP_Dibayar'].sum())}", "💰", "peach"),
        ("Sisa Tagihan", rp(aktif["Sisa_Pembayaran"].sum()), "Total − DP (tanpa pesanan gagal)", "🧾", "peach"),
    ])
    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        alur = pd.DataFrame({"Status": dl.STATUS_SEMUA})
        alur["Jumlah"] = alur["Status"].map(pesanan["Status_Pesanan"].value_counts()).fillna(0).astype(int)
        fig = px.bar(alur, x="Status", y="Jumlah", color="Status", color_discrete_map=STATUS_COLOR, title="Pesanan per Status")
        fig.update_layout(showlegend=False, xaxis_title=None)
        fig.update_xaxes(tickangle=-30)
        plot(fig, 340)
    with c2:
        g = pesanan.groupby("Status_Bayar").size().reset_index(name="Jumlah")
        plot(px.pie(g, names="Status_Bayar", values="Jumlah", hole=0.55, title="Status Pembayaran (dari DP vs total)",
                    color="Status_Bayar", color_discrete_map=STATUS_COLOR), 340)
    c1, c2 = st.columns(2)
    with c1:
        g = pesanan.groupby("Momen_Acara")["Total_Harga"].sum().reset_index()
        plot(px.pie(g, names="Momen_Acara", values="Total_Harga", hole=0.55, title="Nilai Pesanan per Momen Acara"), 320)
    with c2:
        g = pesanan.groupby("Jenis_Order").size().reset_index(name="Jumlah")
        fig = px.bar(g, x="Jenis_Order", y="Jumlah", title="Jenis Order")
        fig.update_traces(marker_color=GREEN)
        fig.update_layout(xaxis_title=None)
        plot(fig, 320)
    st.caption(
        "Status baku mengikuti plan: " + " → ".join(dl.STATUS_ALUR) + "; jalur gagal: " + ", ".join(dl.STATUS_GAGAL)
        + f". Pesanan Menunggu Verifikasi lebih dari {dl.BATAS_VERIFIKASI_HARI} hari otomatis menjadi Kedaluwarsa "
        "(ubah BATAS_VERIFIKASI_HARI di data_loader.py). Nama lama “Menunggu” otomatis dibaca sebagai Menunggu Verifikasi."
    )

    tl = pesanan.dropna(subset=["Tanggal_Pesanan", "Tanggal_Deadline"]).copy()
    if len(tl):
        tl["Deadline_Akhir"] = tl["Tanggal_Deadline"].where(tl["Tanggal_Deadline"] > tl["Tanggal_Pesanan"], tl["Tanggal_Pesanan"] + pd.Timedelta(days=1))
        fig = px.timeline(tl, x_start="Tanggal_Pesanan", x_end="Deadline_Akhir", y="ID_Pesanan", color="Status_SLA",
                          color_discrete_map=STATUS_COLOR, title="Timeline Pesanan (tanggal pesan → deadline)")
        fig.update_yaxes(autorange="reversed")
        st.write("")
        plot(fig, 140 + 40 * min(len(tl), 25))

    st.subheader("Daftar Pesanan")
    f1, f2 = st.columns(2)
    with f1:
        opsi_s = [x for x in dl.STATUS_SEMUA if x in set(pesanan["Status_Pesanan"])] + sorted(set(pesanan["Status_Pesanan"]) - set(dl.STATUS_SEMUA))
        pilih_s = st.multiselect("Filter status pesanan", opsi_s, default=opsi_s)
    with f2:
        opsi = sorted(pesanan["Status_SLA"].unique())
        pilih = st.multiselect("Filter SLA", opsi, default=opsi)
    tabel = pesanan[pesanan["Status_SLA"].isin(pilih) & pesanan["Status_Pesanan"].isin(pilih_s)].sort_values("Tanggal_Deadline")
    table(tabel[["ID_Pesanan", "Tanggal_Pesanan", "Kode_Pelanggan", "Nama_Produk", "Jumlah", "Jenis_Order", "Momen_Acara",
                 "Tanggal_Deadline", "Hari_ke_Deadline", "Status_Pesanan", "Tahap", "Status_Bayar", "Status_SLA", "Total_Harga",
                 "DP_Dibayar", "Sisa_Pembayaran", "Catatan"]],
          money=["Total_Harga", "DP_Dibayar", "Sisa_Pembayaran"], dates=["Tanggal_Pesanan", "Tanggal_Deadline"])


# ------------------------------------------------------------------ 5. FINANCIAL
def page_financial():
    incl = st.checkbox("Sertakan pembelian bahan/stok sebagai biaya operasional", value=False,
                       help="Biasanya HPP sudah memuat biaya bahan, jadi pembelian stok tidak dihitung lagi agar tidak ganda.")
    mask_bahan = pg["Kategori_Pengeluaran"].astype(str).str.contains("bahan|stok|pembelian", case=False, na=False)
    biaya = pg if incl else pg[~mask_bahan]

    omzet, hpp = pj["Total_Penjualan"].sum(), pj["Total_HPP"].sum()
    laba_kotor, ops = omzet - hpp, biaya["Jumlah"].sum()
    laba_bersih = laba_kotor - ops
    modal_masuk = kas.loc[kas["Jenis_Arus"] == "Masuk", "Nominal"].sum()
    modal_keluar = kas.loc[kas["Jenis_Arus"] == "Keluar", "Nominal"].sum()
    diterima = penjualan.loc[penjualan["Status_Pembayaran"] == "Lunas", "Total_Penjualan"].sum()
    est_kas = modal_masuk - modal_keluar + diterima - pengeluaran["Jumlah"].sum()
    piutang = penjualan.loc[penjualan["Status_Pembayaran"] != "Lunas", "Total_Penjualan"].sum()

    cards([
        ("Modal", rp(modal_masuk), f"Prive/penarikan {rp(modal_keluar)}", "🏦", "green"),
        ("Pengeluaran", rp(ops), "Biaya operasional periode ini", "🧾", "pink"),
        ("Pendapatan", rp(omzet), f"HPP {rp(hpp)}", "💰", "peach"),
        ("Keuntungan Bersih", rp(laba_bersih), f"Margin {pct(laba_bersih / omzet)}" if omzet else "-", "📈", "green"),
    ])
    st.write("")
    cards([
        ("Laba Kotor", rp(laba_kotor), f"Margin {pct(laba_kotor / omzet)}" if omzet else "-", "🌿", "green"),
        ("Estimasi Saldo Kas", rp(est_kas), "Modal + penjualan lunas − pengeluaran", "👛", "peach"),
        ("ROI", pct(laba_bersih / modal_masuk) if modal_masuk else "-", "Laba bersih ÷ modal masuk", "🎯", "pink"),
        ("Piutang", rp(piutang), "Penjualan belum lunas", "⏳", "green"),
    ])
    st.write("")

    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure(go.Waterfall(
            x=["Pendapatan", "HPP", "Laba Kotor", "Pengeluaran", "Laba Bersih"],
            measure=["absolute", "relative", "total", "relative", "total"],
            y=[omzet, -hpp, 0, -ops, 0],
            connector={"line": {"color": "#BBB"}},
            increasing={"marker": {"color": GREEN}}, decreasing={"marker": {"color": PINK}},
            totals={"marker": {"color": GREEN_L}},
        ))
        fig.update_layout(title="Dari Pendapatan ke Laba Bersih")
        plot(fig, 360)
    with c2:
        if len(pg):
            g = pg.groupby("Kategori_Pengeluaran")["Jumlah"].sum().reset_index()
            plot(px.pie(g, names="Kategori_Pengeluaran", values="Jumlah", hole=0.55, title="Pengeluaran per Kategori"), 360)
        else:
            st.info("Belum ada pengeluaran pada periode ini.")

    if len(pg):
        g = pg.groupby(["Tanggal", "Jenis_Biaya"])["Jumlah"].sum().reset_index()
        plot(px.bar(g, x="Tanggal", y="Jumlah", color="Jenis_Biaya", title="Pengeluaran Harian (Tetap vs Variabel)"), 300)
        table(pg.drop(columns=["ID_Referensi"], errors="ignore"), money=["Jumlah"], dates=["Tanggal"])

    st.subheader("Arus Kas Modal")
    if not empty(kas, "Belum ada catatan modal/kas."):
        fig = px.line(kas, x="Tanggal", y="Saldo_Kumulatif", markers=True, line_shape="hv", title="Saldo Kumulatif Modal")
        fig.update_traces(line_color=GREEN)
        plot(fig, 300)
        table(kas[["ID_Kas", "Tanggal", "Jenis_Arus", "Kategori_Kas", "Keterangan", "Nominal", "Metode_Pembayaran", "Saldo_Kumulatif"]],
              money=["Nominal", "Saldo_Kumulatif"], dates=["Tanggal"])


# ------------------------------------------------------------------ 6. REKOMENDASI & ANALISIS
def _kartu_rekomendasi(r, peringkat):
    alasan = "".join(f"<li>{html.escape(a.strip())}</li>" for a in r.Alasan.split(";") if a.strip())
    stok = f"Stok {r.Stok_Saat_Ini:g}" if r.Status_Stok != "Habis" else "Stok habis"
    return (
        f'<div class="panel" style="min-height:300px"><div class="row" style="border-top:none">'
        f'<div class="thumb">{cat_icon(r.Kategori)}</div><div class="meta"><div class="nm">#{peringkat} {html.escape(r.Nama_Produk)}</div>'
        f'<div class="amt">{rp(r.Harga_Jual)}</div><div class="dt">{html.escape(r.Kategori)} · {stok}</div></div>'
        f'<span class="pill pill-green">Cocok {r.Skor}%</span></div>'
        f'<ul style="font-size:.78rem;color:#4b4b4b;padding-left:18px;margin:6px 0 0">{alasan}</ul></div>'
    )


def page_rekomendasi():
    R = rc.Rekomendator(d)
    t1, t2 = st.tabs(["💬 Tanya Rekomendasi", "📊 Analisis Data"])

    # ------------------------------------------------ Tanya Rekomendasi
    with t1:
        st.caption("Isi **budget, tema, dan momen** (ketiganya wajib). Isian kosong akan ditolak, lalu sistem mencocokkan katalog, stok, dan data penjualan.")
        c1, c2, c3 = st.columns(3)
        with c1:
            budget = st.text_input("Budget maksimal (Rp)", key="rec_budget", placeholder="mis. 150000 atau 150rb")
        with c2:
            tema_sel = st.selectbox("Tema", list(rc.TEMA) + ["Lainnya (ketik sendiri)"], index=None, placeholder="Pilih tema...", key="rec_tema")
            tema = tema_sel
            if tema_sel == "Lainnya (ketik sendiri)":
                tema = st.text_input("Tema sendiri", key="rec_tema_txt", placeholder="mis. pastel biru")
        with c3:
            momen = st.selectbox("Momen", list(rc.MOMEN), index=None, placeholder="Pilih momen...", key="rec_momen")
        catatan = st.text_input("Catatan tambahan (opsional)", key="rec_cat", placeholder="mis. untuk ibu, suka warna pink")

        if st.button("✨ Tanya Rekomendasi", type="primary"):
            try:
                st.session_state["rec_hasil"] = R.rekomendasi(budget, tema, momen, catatan)
            except rc.InputKosongError as e:
                st.session_state["rec_hasil"] = None
                for kolom, pesan in e.errors.items():
                    st.error(f"**{kolom.capitalize()}**: {pesan}")
        h = st.session_state.get("rec_hasil")
        if h is not None:
            st.write("")
            st.markdown(f"**Rekomendasi untuk {h.momen} · tema {h.tema} · budget {rp(h.budget)}**")
            cols = st.columns(len(h.produk))
            for i, (col, r) in enumerate(zip(cols, h.produk.itertuples()), start=1):
                col.markdown(_kartu_rekomendasi(r, i), unsafe_allow_html=True)
            if h.addon:
                st.write("")
                rows = "".join(
                    f'<div class="row"><div class="thumb">{cat_icon(a["Nama"])}</div><div class="meta"><div class="nm">{html.escape(a["Nama"])}</div>'
                    f'<div class="dt">{html.escape(a["Alasan"])} · stok {html.escape(a["Stok"])}</div></div></div>' for a in h.addon)
                st.markdown(f'<div class="panel"><div class="ph">🎀 Pelengkap yang disarankan (stok tersedia)</div>{rows}</div>', unsafe_allow_html=True)
            for c in h.catatan:
                st.caption("ℹ️ " + c)
            top = h.produk.iloc[0]
            pesan = (f"Halo kak 🌸 Untuk {h.momen} dengan tema {h.tema} dan budget {rp(h.budget)}, rekomendasi kami: "
                     + "; ".join(f"{r.Nama_Produk} ({rp(r.Harga_Jual)})" for r in h.produk.itertuples())
                     + (f". Bisa ditambah {', '.join(a['Nama'] for a in h.addon[:2])}." if h.addon else ".")
                     + " Mau pilih yang mana, kak?")
            st.markdown("**Draf balasan untuk pelanggan** (salin & sesuaikan)")
            st.code(pesan, language=None)

    # ------------------------------------------------ Analisis Data
    with t2:
        pr_aktif = produk[produk["Status"] == "Aktif"] if "Status" in produk.columns else produk
        kp = an.kategori_performa(penjualan, produk)
        cards([
            ("Produk Aktif", num(len(pr_aktif)), f"{produk['Kategori'].nunique()} kategori", "💐", "green"),
            ("Harga Median", rp(pr_aktif["Harga_Jual"].median()), f"{rp(pr_aktif['Harga_Jual'].min())} – {rp(pr_aktif['Harga_Jual'].max())}", "🏷️", "peach"),
            ("Kategori Terkuat", kp.iloc[0]["Kategori"] if len(kp) else "-", f"{kp.iloc[0]['Porsi_Pendapatan']:.0f}% pendapatan" if len(kp) else "belum ada penjualan", "🏆", "pink"),
            ("Margin Katalog", pct(pr_aktif["Persen_Margin"].mean()), "Rata-rata per produk", "📈", "green"),
        ])
        st.write("")
        st.markdown("#### Temuan otomatis")
        for t in an.insight_otomatis(d):
            st.markdown(f"- {t}")
        st.write("")
        c1, c2 = st.columns(2)
        with c1:
            bh = an.band_harga(pr_aktif)
            fig = px.bar(bh, x="Rentang", y="Jumlah_Produk", text="Jumlah_Produk", title="Produk per Rentang Harga (acuan budget pelanggan)")
            fig.update_traces(marker_color=PINK)
            fig.update_layout(xaxis_title=None, yaxis_title="Jumlah produk")
            plot(fig, 330)
        with c2:
            if len(kp):
                fig = px.bar(kp, x="Kategori", y=["Pendapatan", "Laba_Kotor"], barmode="group", title="Pendapatan & Laba per Kategori",
                             color_discrete_map={"Pendapatan": GREEN, "Laba_Kotor": PINK})
                fig.update_layout(xaxis_title=None, yaxis_title="Rupiah", legend_title=None)
                plot(fig, 330)
            else:
                st.info("Belum ada penjualan.")
        if len(kp):
            table(kp, money=["Pendapatan", "Laba_Kotor"], pct_cols=["Margin_Persen", "Porsi_Pendapatan"])

        st.markdown("#### Momen acara")
        mp = an.momen_performa(pesanan)
        c1, c2 = st.columns(2)
        with c1:
            if len(mp):
                fig = px.bar(mp, x="Momen_Acara", y="Pesanan", text="Pesanan", title="Pesanan custom per Momen (data nyata)")
                fig.update_traces(marker_color=GREEN)
                fig.update_layout(xaxis_title=None)
                plot(fig, 300)
                st.caption(f"Baru {len(pesanan)} pesanan tercatat, jadi pola momen belum bisa diandalkan.")
            else:
                st.info("Belum ada pesanan custom.")
        with c2:
            prior = pd.DataFrame(rc.MOMEN).T.rename(columns={"bouquet": "Flower Bouquet", "artificial": "Artificial Flower",
                                                             "snack": "Snack Bouquet", "money": "Money Bouquet"})
            prior = prior[["Flower Bouquet", "Artificial Flower", "Snack Bouquet", "Money Bouquet"]]
            fig = px.imshow(prior, text_auto=".1f", aspect="auto", color_continuous_scale=["#FBF4F1", "#F4B6C2", "#6B7F4B"],
                            title="Aturan awal: kecocokan kategori × momen (0–1)")
            plot(fig, 300)

        st.markdown("#### Simulasi: produk teratas per budget × momen")
        tema_sim = st.selectbox("Tema simulasi", list(rc.TEMA), key="sim_tema")
        budgets = [50_000, 100_000, 150_000, 200_000, 300_000]
        sim = {}
        for m in rc.MOMEN:
            sim[m] = [R.rekomendasi(b, tema_sim, m, top_n=1).produk.iloc[0]["Nama_Produk"] for b in budgets]
        st.dataframe(pd.DataFrame(sim, index=[rp(b) for b in budgets]).T, width="stretch")

        with st.expander("🧠 Cara kerja rekomendasi"):
            st.markdown(
                "- **Teknologi:** Python, pandas, dan **scikit-learn** (TF-IDF karakter + cosine similarity untuk mencocokkan tema ke teks produk).\n"
                f"- **Skor akhir** = budget {rc.BOBOT['budget']:.0%} · tema {rc.BOBOT['tema']:.0%} · momen {rc.BOBOT['momen']:.0%} · "
                f"popularitas penjualan {rc.BOBOT['populer']:.0%} · margin {rc.BOBOT['margin']:.0%} · stok {rc.BOBOT['stok']:.0%}.\n"
                f"- **Budget:** produk ≤ budget diprioritaskan; sampai {rc.TOLERANSI_BUDGET:.0%} di atas budget masih muncul dengan catatan.\n"
                "- **Momen:** memakai aturan awal kecocokan kategori (heatmap di atas, bisa diubah di `recommender.py`) lalu bergeser ke data nyata "
                "seiring bertambahnya pesanan.\n"
                "- **Input kosong ditolak:** budget, tema, momen wajib diisi; budget harus angka > 0.\n"
                "- Produk berstatus Tidak Aktif tidak direkomendasikan; produk stok habis ditandai pre-order."
            )


# ------------------------------------------------------------------ 7. FAQ & DATA SIAP IMPOR
def page_faq():
    t1, t2 = st.tabs(["❓ FAQ Pelanggan", "🗃️ Data Bersih Siap Impor"])
    faq = d["faq"]

    with t1:
        if empty(faq, "Belum ada FAQ. Tambahkan sheet 'FAQ' di Excel atau isi faq.csv."):
            pass
        else:
            c1, c2 = st.columns([2, 2])
            with c1:
                q = st.text_input("Cari pertanyaan", placeholder="mis. pembayaran, kedaluwarsa, custom")
            with c2:
                kats = sorted(faq["Kategori"].unique())
                pilih = st.multiselect("Kategori", kats, default=kats)
            hay = (faq["Pertanyaan"] + " " + faq["Jawaban"] + " " + faq["Kata_Kunci"]).str.lower()
            ok = faq["Kategori"].isin(pilih)
            for tok in q.lower().split():
                ok &= hay.str.contains(tok, regex=False)
            hasil = faq[ok]
            st.caption(f"{len(hasil)} dari {len(faq)} pertanyaan. Harga pada jawaban diambil otomatis dari katalog produk.")
            if hasil.empty:
                st.info("Tidak ada FAQ yang cocok. Coba kata kunci lain.")
            for kat, grp in hasil.groupby("Kategori", sort=False):
                st.markdown(f"**{kat}**")
                for r in grp.itertuples():
                    with st.expander(r.Pertanyaan):
                        st.write(r.Jawaban)
                        if str(r.Perlu_Konfirmasi).lower() == "ya":
                            st.caption("⚠️ Memuat kebijakan yang belum pasti. Konfirmasi ke pemilik usaha sebelum dipublikasikan di website.")
            n_konf = int((faq["Perlu_Konfirmasi"].str.lower() == "ya").sum())
            if n_konf:
                st.info(f"{n_konf} FAQ berstatus draf (perlu konfirmasi kebijakan). Edit di `faq.csv` atau sheet FAQ di Excel.")

    with t2:
        transaksi = False
        if not PUBLIC_MODE:
            transaksi = st.checkbox("Sertakan penjualan & pesanan (simpan hanya di repo private)", value=False)
        tabel = ex.tabel_ekspor(d, transaksi)
        cek = ex.validasi_impor(tabel)
        cards([
            ("Produk", num(len(tabel["produk"])), f"{int((produk['Status'] == 'Aktif').sum())} aktif", "💐", "pink"),
            ("Bahan", num(len(tabel["bahan"])), f"{bahan['Kategori_Bahan'].nunique()} kategori", "🎀", "green"),
            ("Inventaris", num(len(tabel["inventaris"])), "produk + bahan", "📦", "peach"),
            ("FAQ", num(len(tabel["faq"])), "pertanyaan", "❓", "green"),
        ])
        st.write("")
        for nama, ok, pesan in cek:
            st.markdown(
                f'<div class="status {"" if ok else "bad"}"><div class="ic">{"✓" if ok else "!"}</div>'
                f'<div class="tx"><b>{nama}.csv</b><span>{pesan}</span></div>'
                f'<div class="tag">{"Siap" if ok else "Perlu dicek"}</div></div>',
                unsafe_allow_html=True)
        st.download_button("⬇️ Unduh semua (ZIP: CSV + schema.sql)", ex.zip_bytes(tabel), "data_bersih_byficlo.zip", "application/zip", type="primary")
        st.caption("CSV: UTF-8, header snake_case, tanggal ISO, angka tanpa format. `schema.sql` berisi CREATE TABLE lengkap. "
                   "Data keuangan (modal/pengeluaran) tidak pernah diekspor.")
        tabs = st.tabs(list(tabel))
        for tb, (nama, df) in zip(tabs, tabel.items()):
            with tb:
                st.dataframe(df, hide_index=True)
                st.download_button(f"⬇️ {nama}.csv", df.to_csv(index=False).encode("utf-8"), f"{nama}.csv", "text/csv", key=f"dl_{nama}")


PAGE_FUNCS = {P_OV: page_overview, P_SALES: page_sales, P_INV: page_inventory, P_ORD: page_orders,
              P_FIN: page_financial, P_REC: page_rekomendasi, P_FAQ: page_faq}
PAGE_FUNCS[page]()

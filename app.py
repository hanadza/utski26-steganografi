"""
app.py
------
StegoShield - Aplikasi Web Steganografi LSB & Enkripsi AES-256 (Streamlit).
Tema terang/gelap dan navigasi sidebar diatur lewat CSS, tanpa .streamlit/config.toml.
"""

from __future__ import annotations

import html
import io
import os
import random
import tempfile

import matplotlib
matplotlib.use("Agg")
import numpy as np
import pandas as pd
from PIL import Image
import streamlit as st

import steg_engine as se
import steg_testing as stesting


st.set_page_config(
    page_title="StegoShield - Steganografi LSB & AES-256",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------
# Tema
# --------------------------------------------------------------------------
THEMES = {
    "light": dict(ink="#15132E", soft="#5F5C7E", bg="#EFEDF8", card="#FFFFFF", field="#F8F7FD", line="#E4E1F1",
                  v="#5B4BDB", vd="#4638B8", vt="#EEEBFD", vx="#4638B8", mint="#0F9F79", mint_t="#DFF6EE",
                  mint_x="#0B7A5D", coral="#D6404A", coral_t="#FDE8E9", coral_x="#A82830", vb="#D6D0F8",
                  mb="#BDE9DB", cb="#F6C4C7", dz="#B8B0EE", ring="#DAD5FA", side="#FFFFFF"),
    "dark": dict(ink="#ECEAFB", soft="#A29EC8", bg="#0D0C1B", card="#16142B", field="#1E1C38", line="#2D2A4C",
                 v="#7C6CF5", vd="#6A5AE8", vt="#26224F", vx="#B9B1FF", mint="#2FD1A2", mint_t="#12372E",
                 mint_x="#5BE3BC", coral="#F0646C", coral_t="#3B1D22", coral_x="#FF9AA0", vb="#3A3479",
                 mb="#1F5A4A", cb="#6A2C33", dz="#4B4590", ring="#3B3486", side="#110F24"),
}
st.session_state.setdefault("dark", False)
mode = "dark" if st.session_state["dark"] else "light"
ROOT = f":root{{color-scheme:{mode};" + "".join(f"--{k.replace('_', '-')}:{v};" for k, v in THEMES[mode].items()) + "}"

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
""" + ROOT + """

/* ---------- Dasar ---------- */
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"]{background:var(--bg) !important; color:var(--ink);}
[data-testid="stHeader"], [data-testid="stToolbar"]{background:transparent !important;}
/* Sembunyikan hanya Deploy & menu di kanan; toolbar kiri (tombol buka sidebar) tetap tampil */
[data-testid="stToolbarActions"], [data-testid="stMainMenu"], [data-testid="stAppDeployButton"], .stDeployButton,
[data-testid="stDecoration"], #MainMenu, footer{display:none !important;}
[data-testid="stSidebarCollapseButton"] *, [data-testid="stSidebarCollapsedControl"] *, [data-testid="stExpandSidebarButton"] *{color:var(--soft) !important; fill:var(--soft) !important;}
[data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapsedControl"] button{background:var(--card) !important; border:1px solid var(--line) !important; border-radius:10px !important; box-shadow:0 4px 12px -6px rgba(0,0,0,.4);}
.block-container{max-width:1080px; margin:1.2rem auto 2rem; padding:2.1rem 2.3rem !important; background:var(--card); border:1px solid var(--line); border-radius:24px;}
@media (max-width:860px){ .block-container{padding:1.2rem 1rem !important; border-radius:16px;} }

[data-testid="stMarkdownContainer"], label, input, textarea, button{font-family:'Plus Jakarta Sans',sans-serif;}
[data-testid="stMarkdownContainer"]{color:var(--ink) !important;}
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li{color:var(--ink);}
[data-testid="stWidgetLabel"] p, label p{color:var(--ink) !important; font-weight:600;}
[data-testid="stSpinner"] *{color:var(--ink) !important;}
[data-testid="stImage"] img{border-radius:14px; border:1px solid var(--line);}
hr{border-color:var(--line) !important; margin:1.4rem 0 !important;}

/* ---------- Sidebar & navigasi ---------- */
[data-testid="stSidebar"]{background:var(--side) !important; border-right:1px solid var(--line);}
[data-testid="stSidebar"] > div{background:var(--side) !important;}
.brand{display:flex; align-items:center; gap:.6rem; font-family:'Bricolage Grotesque',sans-serif; font-weight:800; font-size:1.4rem; color:var(--ink) !important;}
.logo{width:2.3rem; height:2.3rem; border-radius:11px; background:var(--v); display:flex; align-items:center; justify-content:center; font-size:1.15rem;}
.side-sub{font-size:.84rem; color:var(--soft) !important; margin:.5rem 0 1.4rem;}
.side-h{font-size:.82rem; font-weight:700; color:var(--soft) !important; margin:0 0 .5rem .3rem;}
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"]{gap:.3rem;}
[data-testid="stSidebar"] [data-testid="stRadio"] label{width:100%; margin:0 !important; padding:.65rem .9rem; border-radius:12px; cursor:pointer; transition:background .15s;}
[data-testid="stSidebar"] [data-testid="stRadio"] label *:not(input):not(:has([data-testid="stMarkdownContainer"])):not([data-testid="stMarkdownContainer"]):not([data-testid="stMarkdownContainer"] *){display:none !important;}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover{background:var(--vt);}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(:is(input:checked, input[aria-checked="true"])){background:var(--v);}
[data-testid="stSidebar"] [data-testid="stRadio"] label p{color:var(--ink) !important; font-weight:600; font-size:.95rem;}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(:is(input:checked, input[aria-checked="true"])) p{color:#fff !important;}
.side-foot{font-size:.78rem; line-height:1.6; color:var(--soft) !important; margin-top:1rem;}

/* ---------- Hero & fitur ---------- */
.hero{background:linear-gradient(135deg,#15132E 0%,#2B2470 100%); border:1px solid rgba(255,255,255,.08); border-radius:22px; padding:2.4rem 2.6rem;
  display:flex; align-items:center; justify-content:space-between; gap:2.5rem; margin-bottom:1rem;}
.hero-title{font-family:'Bricolage Grotesque',sans-serif; font-size:2.7rem; line-height:1.08; font-weight:800; color:#fff !important; max-width:30rem; margin:0 0 .9rem;}
.hero-text{color:#CFCBF0 !important; font-size:1.03rem; line-height:1.65; max-width:33rem; margin:0 0 1.3rem;}
.chips{display:flex; flex-wrap:wrap; gap:.5rem;}
.chip{background:rgba(255,255,255,.10); color:#EEEBFF !important; border:1px solid rgba(255,255,255,.2); border-radius:999px; padding:.3rem .9rem; font-size:.84rem; font-weight:600;}
.pixels{display:grid; grid-template-columns:repeat(14,1fr); gap:4px; width:270px; flex-shrink:0;}
.pixels i{display:block; aspect-ratio:1; border-radius:3px; background:rgba(255,255,255,.07);}
.pixels i.on{background:#8A7DF5;} .pixels i.hot{background:#3DD6AC;}
.feats{display:grid; grid-template-columns:repeat(3,1fr); gap:1rem; margin-bottom:1.4rem;}
.feat{background:var(--field); border:1px solid var(--line); border-radius:18px; padding:1.2rem 1.3rem;}
.feat .ic{width:2.4rem; height:2.4rem; border-radius:12px; background:var(--vt); display:flex; align-items:center; justify-content:center; font-size:1.2rem; margin-bottom:.7rem;}
.feat .ft{font-family:'Bricolage Grotesque',sans-serif; font-weight:700; font-size:1.05rem; color:var(--ink) !important; margin-bottom:.25rem;}
.feat .fd{font-size:.9rem; line-height:1.55; color:var(--soft) !important;}
@media (max-width:860px){ .pixels{display:none;} .hero{padding:1.6rem 1.3rem;} .hero-title{font-size:2rem;} .feats{grid-template-columns:1fr;} }

/* ---------- Input: semua lapisan transparan, latar hanya di satu tempat ---------- */
[data-testid="stTextInput"] div, [data-testid="stTextArea"] div{background:transparent !important; box-shadow:none !important;}
[data-testid="stTextInput"] [data-testid="stTextInputRootElement"], [data-testid="stTextArea"] [data-testid="stTextAreaRootElement"]{
  background:var(--field) !important; border:0 !important; border-radius:12px !important;}
[data-testid="stTextInput"] [data-baseweb="input"], [data-testid="stTextArea"] [data-baseweb="textarea"]{
  background:var(--field) !important; border:1px solid var(--line) !important; border-radius:12px !important;}
[data-testid="stTextInput"] [data-baseweb="input"]:focus-within, [data-testid="stTextArea"] [data-baseweb="textarea"]:focus-within{
  border-color:var(--v) !important; box-shadow:0 0 0 3px var(--ring) !important;}
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea, input, textarea{
  background:transparent !important; color:var(--ink) !important; -webkit-text-fill-color:var(--ink) !important; caret-color:var(--v);}
[data-testid="stTextInput"] input::placeholder, [data-testid="stTextArea"] textarea::placeholder{color:var(--soft) !important; -webkit-text-fill-color:var(--soft) !important;}
[data-testid="stTextInput"] [data-testid="stTextInputRootElement"] *:not(input), [data-testid="stTextInput"] button, [data-testid="stTextInput"] button *{color:var(--soft) !important;}
[data-testid="stTextInput"] svg, [data-testid="stTextInput"] svg *{fill:var(--soft) !important; opacity:1 !important;}
[data-testid="stTextInput"] button:hover, [data-testid="stTextInput"] button:hover *{color:var(--v) !important; fill:var(--v) !important;}
[data-testid="stTextInput"] button{background:transparent !important; box-shadow:none !important; opacity:1 !important;}
[data-testid="InputInstructions"], [data-testid="InputInstructions"] *{color:var(--soft) !important;}

[data-testid="stFileUploaderDropzone"]{background:var(--field) !important; border:1.5px dashed var(--dz) !important; border-radius:16px !important; padding:1.3rem !important;}
[data-testid="stFileUploaderDropzone"]:hover{background:var(--vt) !important; border-color:var(--v) !important;}
[data-testid="stFileUploaderDropzone"] *{color:var(--soft) !important;}
[data-testid="stFileUploaderDropzone"] svg{fill:var(--v) !important;}
[data-testid="stFileUploaderDropzone"] button{background:var(--card) !important; border:1px solid var(--line) !important; border-radius:10px !important;}
[data-testid="stFileUploaderDropzone"] button *{color:var(--vx) !important; font-weight:600;}
[data-testid="stFileUploaderFile"] *{color:var(--ink) !important;}

/* ---------- Tombol ---------- */
.stButton button, .stDownloadButton button{background:var(--v) !important; border:0 !important; border-radius:12px; padding:.75rem 1.5rem; font-weight:700;
  box-shadow:0 8px 18px -10px var(--v); transition:transform .15s, background .15s;}
.stButton button *, .stDownloadButton button *{color:#fff !important;}
.stButton button:hover, .stDownloadButton button:hover{background:var(--vd) !important; transform:translateY(-1px);}
.stButton button:focus-visible, .stDownloadButton button:focus-visible{outline:3px solid var(--dz); outline-offset:2px;}

/* ---------- Komponen konten ---------- */
.section-title{font-family:'Bricolage Grotesque',sans-serif; font-size:1.6rem; font-weight:700; color:var(--ink) !important; margin:0 0 .2rem;}
.section-desc{color:var(--soft) !important; line-height:1.6; margin:0 0 1.2rem; max-width:46rem;}
.img-label{display:inline-block; background:var(--vt); color:var(--vx) !important; font-weight:700; font-size:.84rem; padding:.22rem .75rem; border-radius:8px; margin-bottom:.5rem;}

.steps{display:flex; gap:.6rem; flex-wrap:wrap; margin:0 0 1.5rem;}
.step{flex:1; min-width:140px; display:flex; align-items:center; gap:.6rem; padding:.6rem .85rem; border-radius:12px; background:var(--field); border:1px solid var(--line); font-weight:600; font-size:.88rem; color:var(--soft) !important;}
.step b{width:1.55rem; height:1.55rem; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:.78rem; background:var(--line); color:var(--soft) !important; flex-shrink:0;}
.step.done{color:var(--ink) !important;} .step.done b{background:var(--mint); color:#fff !important;}
.step.cur{border-color:var(--v); background:var(--vt); color:var(--vx) !important;} .step.cur b{background:var(--v); color:#fff !important;}

.stats{display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:.8rem; margin:.5rem 0 1rem;}
.stat{background:var(--field); border:1px solid var(--line); border-radius:14px; padding:.9rem 1.1rem;}
.stat span{display:block; color:var(--soft) !important; font-size:.82rem; font-weight:600; margin-bottom:.25rem;}
.stat strong{font-family:'Bricolage Grotesque',sans-serif; font-size:1.45rem; color:var(--ink) !important;}

.meter{margin:.2rem 0 1.2rem;}
.meter-top{display:flex; justify-content:space-between; font-size:.85rem; font-weight:600; margin-bottom:.4rem;}
.meter-top span{color:var(--soft) !important;}
.meter-bar{height:10px; background:var(--line); border-radius:99px; overflow:hidden;}
.meter-bar i{display:block; height:100%; border-radius:99px;}
.meter.ok i{background:var(--mint);} .meter.warn i{background:#E0A526;} .meter.bad i{background:var(--coral);}

.callout{display:flex; gap:.7rem; align-items:flex-start; padding:.85rem 1.1rem; border-radius:12px; font-size:.92rem; line-height:1.55; margin:.5rem 0 1rem; border:1px solid;}
.callout > .co-ic{width:1.4rem; height:1.4rem; flex-shrink:0; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:.8rem; color:#fff !important; font-weight:700; font-style:normal;}
.callout span{color:var(--ink) !important;}
.callout.info{background:var(--vt); border-color:var(--vb);} .callout.info > .co-ic{background:var(--v);}
.callout.success{background:var(--mint-t); border-color:var(--mb);} .callout.success > .co-ic{background:var(--mint);}
.callout.error{background:var(--coral-t); border-color:var(--cb);} .callout.error > .co-ic{background:var(--coral);}

.badge{display:inline-block; padding:.3rem .8rem; border-radius:999px; font-weight:700; font-size:.88rem;}
.badge.g{background:var(--mint-t); color:var(--mint-x) !important;} .badge.r{background:var(--coral-t); color:var(--coral-x) !important;}

.msgbox{background:var(--field); border:1px solid var(--line); border-radius:14px; padding:1rem 1.2rem; white-space:pre-wrap; word-break:break-word; line-height:1.65; min-height:120px; color:var(--ink) !important;}

.tblwrap{overflow-x:auto; border:1px solid var(--line); border-radius:14px; margin:.5rem 0 1rem;}
.tbl{width:100%; border-collapse:collapse; font-size:.9rem;}
.tbl th{background:var(--field); color:var(--soft) !important; text-align:left; font-weight:700; padding:.65rem 1rem; border-bottom:1px solid var(--line);}
.tbl td{padding:.6rem 1rem; border-bottom:1px solid var(--line); color:var(--ink) !important;}
.tbl tr:last-child td{border-bottom:0;}
.tbl td.g{color:var(--mint-x) !important; font-weight:700;} .tbl td.r{color:var(--coral-x) !important; font-weight:700;}

.footer{display:flex; flex-wrap:wrap; justify-content:center; gap:.4rem 1.4rem; margin-top:2.2rem; padding-top:1.2rem; border-top:1px solid var(--line); font-size:.84rem;}
.footer span{color:var(--soft) !important;}

/* ---------- Animasi & Transisi Tambahan ---------- */

/* 1. Animasi Masuk (Fade-In & Slide-Up) untuk halaman */
@keyframes fadeInUp {
  0% { opacity: 0; transform: translateY(15px); }
  100% { opacity: 1; transform: translateY(0); }
}
.block-container {
  animation: fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

/* 2. Efek melayang (Hover) mulus pada kartu fitur, stat, dan kotak info */
.feat, .stat, .callout {
  transition: transform 0.3s ease, box-shadow 0.3s ease !important;
}
.feat:hover, .stat:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 25px -10px var(--v);
}

/* 3. Efek klik (Active) memantul pada tombol */
.stButton button, .stDownloadButton button {
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1), background 0.2s, box-shadow 0.2s !important;
}
.stButton button:active, .stDownloadButton button:active {
  transform: scale(0.96) !important;
  box-shadow: 0 2px 5px -2px var(--v) !important;
}

/* 4. Transisi warna mulus pada Stepper (Langkah-langkah) */
.step {
  transition: background 0.3s ease, border-color 0.3s ease, color 0.3s ease;
}
.step b {
  transition: background 0.3s ease, color 0.3s ease;
}

/* 5. Animasi denyut (Pulse) bercahaya untuk ornamen piksel di Hero Section */
@keyframes pulse {
  0% { transform: scale(1); opacity: 0.7; }
  50% { transform: scale(1.15); opacity: 1; box-shadow: 0 0 6px var(--v); }
  100% { transform: scale(1); opacity: 0.7; }
}
.pixels i.on {
  animation: pulse 2.5s infinite ease-in-out;
}
.pixels i.hot {
  animation: pulse 1.8s infinite alternate ease-in-out;
}

/* 6. Hover membesar secara halus (Zoom) pada gambar stego & cover */
[data-testid="stImage"] img {
  transition: transform 0.4s ease;
}
[data-testid="stImage"] img:hover {
  transform: scale(1.02);
}

/* ---------- Responsivitas Mobile (Mobile-Friendly) ---------- */

/* Untuk layar Tablet & HP (lebar maksimal 768px) */
@media (max-width: 768px) {
    /* Mengurangi jarak padding luar agar ruang untuk konten lebih lega */
    .block-container {
        padding: 1rem 0.8rem !important;
        margin-top: 0.5rem;
    }
    
    /* Hero Section: Tata letak tengah dan teks lebih proporsional */
    .hero {
        padding: 1.5rem 1rem;
        flex-direction: column;
        text-align: center;
        gap: 1.2rem;
    }
    .hero-title {
        font-size: 1.8rem;
        line-height: 1.2;
        margin-bottom: 0.5rem;
    }
    .hero-text {
        font-size: 0.95rem;
        margin: 0 auto 1.3rem;
    }
    .chips {
        justify-content: center;
    }
    
    /* Memperkecil teks judul section */
    .section-title {
        font-size: 1.3rem;
    }
    .section-desc {
        font-size: 0.9rem;
    }
    
    /* Stepper: Menyusun langkah-langkah ke bawah (vertikal) di HP */
    .steps {
        flex-direction: column;
        gap: 0.4rem;
    }
    .step {
        min-width: 100%; /* Memenuhi lebar layar */
        padding: 0.5rem 0.7rem;
    }
    
    /* Stats: Di HP ukuran standar, bagi menjadi 2 kolom */
    .stats {
        grid-template-columns: 1fr 1fr;
    }
    .stat {
        padding: 0.7rem 0.9rem;
    }
    .stat strong {
        font-size: 1.2rem;
    }
    
    /* Tabel: Teks dan jarak sel diperkecil */
    .tbl {
        font-size: 0.8rem;
    }
    .tbl th, .tbl td {
        padding: 0.5rem;
    }
    
    /* Callout / Kotak info: Teks lebih ringkas */
    .callout {
        font-size: 0.85rem;
        padding: 0.7rem 0.9rem;
    }
}

/* Untuk layar HP yang lebih sempit (misal iPhone lama, lebar maksimal 480px) */
@media (max-width: 480px) {
    /* Stats: Ubah menjadi 1 kolom penuh agar tidak menyempit */
    .stats {
        grid-template-columns: 1fr; 
    }
    /* Chip badges: Lebih kecil lagi */
    .chips {
        gap: 0.3rem;
    }
    .chip {
        font-size: 0.75rem;
        padding: 0.2rem 0.6rem;
    }
    /* Tombol hero: Memenuhi layar */
    .hero button {
        width: 100% !important;
    }
}

/* Untuk layar HP yang lebih sempit (misal iPhone lama, lebar maksimal 480px) */
@media (max-width: 480px) {
    /* Stats: Ubah menjadi 1 kolom penuh agar tidak menyempit */
    .stats {
        grid-template-columns: 1fr; 
    }
    /* Chip badges: Lebih kecil lagi */
    .chips {
        gap: 0.3rem;
    }
    .chip {
        font-size: 0.75rem;
        padding: 0.2rem 0.6rem;
    }
    /* Tombol hero: Memenuhi layar */
    .hero button {
        width: 100% !important;
    }
}

/* ---------- Styling untuk Tombol Link (ABOUT) ---------- */
  [data-testid="stLinkButton"] a {
  background: var(--v) !important; 
  border: 0 !important; 
  border-radius: 12px !important; 
  padding: .65rem 1.5rem !important; 
  font-weight: 700 !important;
  box-shadow: 0 8px 18px -10px var(--v) !important; 
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1), background 0.2s, box-shadow 0.2s !important;
  width: 100% !important;
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
  text-decoration: none !important;
}
[data-testid="stLinkButton"] a p {
  color: #fff !important; 
  margin: 0 !important;
}
[data-testid="stLinkButton"] a:hover {
  background: var(--vd) !important; 
  transform: translateY(-1px) !important;
}
[data-testid="stLinkButton"] a:active {
  transform: scale(0.96) !important; 
  box-shadow: 0 2px 5px -2px var(--v) !important;
}

/* ---------- Panel informasi & materi ---------- */
details.info{background:var(--field); border:1px solid var(--line); border-radius:14px; margin:0 0 1.3rem; overflow:hidden;}
details.info summary{cursor:pointer; list-style:none; padding:.85rem 1.1rem; font-weight:700; color:var(--vx) !important; display:flex; align-items:center; gap:.5rem; user-select:none;}
details.info summary::-webkit-details-marker{display:none;}
details.info summary::after{content:"+"; margin-left:auto; font-size:1.2rem; color:var(--soft);}
details.info[open] summary{border-bottom:1px solid var(--line);}
details.info[open] summary::after{content:"−";}
.info-body{padding:1rem 1.2rem .6rem; font-size:.94rem; line-height:1.7;}
.info-body p, .info-body li{color:var(--ink) !important; margin:0 0 .7rem;}
.info-body ol, .info-body ul{margin:.1rem 0 .8rem 1.2rem; padding:0;}
.info-body li{margin-bottom:.4rem;}
.info-body b{color:var(--ink) !important;}
.info-body code{background:var(--vt); color:var(--vx) !important; padding:.08rem .4rem; border-radius:6px; font-size:.88em;}
.learn{display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-bottom:1rem;}
.fd b{color:var(--ink) !important;}
.bits{display:flex; align-items:center; flex-wrap:wrap; gap:.5rem; margin-top:.8rem; font-family:ui-monospace,Consolas,monospace; font-size:.95rem;}
.bits span{color:var(--ink) !important;}
.bits b.hl{background:var(--coral-t); color:var(--coral-x) !important; padding:0 .2rem; border-radius:4px;}
.flowlabel{font-size:.82rem; font-weight:700; color:var(--soft) !important; margin:.6rem 0 .3rem;}
.flowrow{display:flex; flex-wrap:wrap; align-items:center; gap:.4rem; margin-bottom:.5rem;}
.fnode{background:var(--vt); border:1px solid var(--vb); color:var(--vx) !important; border-radius:10px; padding:.4rem .75rem; font-size:.85rem; font-weight:600;}
.fnode.g{background:var(--mint-t); border-color:var(--mb); color:var(--mint-x) !important;}
.farrow{color:var(--soft) !important; font-weight:700;}
@media (max-width:768px){ .learn{grid-template-columns:1fr;} }
.lanes{display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-bottom:.8rem;}
.lane{background:var(--field); border:1px solid var(--line); border-radius:18px; padding:1.2rem 1.3rem .5rem;}
.lane-h{display:flex; align-items:center; gap:.75rem; margin-bottom:1.1rem;}
.lane-ic{width:2.6rem; height:2.6rem; border-radius:13px; background:var(--v); display:flex; align-items:center; justify-content:center; font-size:1.3rem;}
.lane-t{font-family:'Bricolage Grotesque',sans-serif; font-weight:700; font-size:1.15rem; color:var(--ink) !important;}
.lane-s{font-size:.82rem; color:var(--soft) !important;}
.tl{list-style:none !important; margin:0 !important; padding:0 !important;}
.tl li{position:relative; display:flex; gap:.85rem; margin:0 !important; padding-bottom:1.05rem; opacity:0; animation:slideIn .5s ease forwards;}
.tl li:nth-child(2){animation-delay:.08s;} .tl li:nth-child(3){animation-delay:.16s;} .tl li:nth-child(4){animation-delay:.24s;}
.tl li:nth-child(5){animation-delay:.32s;} .tl li:nth-child(6){animation-delay:.4s;}
.tl li:not(:last-child)::before{content:""; position:absolute; left:1.05rem; top:2.3rem; bottom:.15rem; width:2px; background:var(--vb);}
.dot{width:2.1rem; height:2.1rem; flex-shrink:0; border-radius:50%; background:var(--vt); border:1px solid var(--vb); display:flex; align-items:center; justify-content:center; font-size:1rem; z-index:1; transition:transform .2s;}
.dot.end{background:var(--mint-t); border-color:var(--mb);}
.tl li:hover .dot{transform:scale(1.14);}
.tt{font-weight:700; font-size:.95rem; color:var(--ink) !important;}
.td{font-size:.86rem; line-height:1.5; color:var(--soft) !important;}
.keybar{display:flex; align-items:center; gap:.7rem; background:var(--vt); border:1px solid var(--vb); border-radius:14px; padding:.85rem 1.1rem; font-size:.92rem; line-height:1.5;}
.keybar span{color:var(--ink) !important;} .keybar b{color:var(--ink) !important;}
@keyframes slideIn{from{opacity:0; transform:translateX(-10px);} to{opacity:1; transform:none;}}
@media (max-width:768px){ .lanes{grid-template-columns:1fr;} }
"""
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)



# --------------------------------------------------------------------------
# Helper tampilan
# --------------------------------------------------------------------------
def H(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def info(title: str, *blocks: str, open_: bool = False) -> None:
    """Panel materi yang bisa dibuka/ditutup."""
    body = "".join(blocks)
    H(f'<details class="info"{" open" if open_ else ""}><summary>💡 {title}</summary>'
      f'<div class="info-body">{body}</div></details>')


def ol(*items: str) -> str:
    return "<ol>" + "".join(f"<li>{i}</li>" for i in items) + "</ol>"


def ul(*items: str) -> str:
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def lane(icon: str, title: str, sub: str, steps: list[tuple[str, str, str]]) -> str:
    """Satu jalur proses berbentuk timeline vertikal."""
    items = "".join(
        f'<li><span class="dot{" end" if i == len(steps) - 1 else ""}">{e}</span>'
        f'<div><div class="tt">{t}</div><div class="td">{d}</div></div></li>'
        for i, (e, t, d) in enumerate(steps))
    return (f'<div class="lane"><div class="lane-h"><span class="lane-ic">{icon}</span>'
            f'<div><div class="lane-t">{title}</div><div class="lane-s">{sub}</div></div></div>'
            f'<ul class="tl">{items}</ul></div>')


def section(title: str, desc: str = "") -> None:
    H(f'<div class="section-title">{title}</div>' + (f'<div class="section-desc">{desc}</div>' if desc else ""))


def img_label(text: str) -> None:
    H(f'<span class="img-label">{text}</span>')


def callout(kind: str, text: str) -> None:
    icon = {"info": "i", "success": "✓", "error": "!"}[kind]
    H(f'<div class="callout {kind}"><i class="co-ic">{icon}</i><span>{text}</span></div>')


def stats(items: list[tuple[str, str]]) -> None:
    H('<div class="stats">' + "".join(
        f'<div class="stat"><span>{l}</span><strong>{v}</strong></div>' for l, v in items) + "</div>")


def meter(pct: float) -> None:
    cls = "ok" if pct < 50 else "warn" if pct < 85 else "bad"
    H(f'<div class="meter {cls}"><div class="meter-top"><span>Kapasitas terpakai</span><span>{pct:.2f}%</span></div>'
      f'<div class="meter-bar"><i style="width:{min(pct, 100):.2f}%"></i></div></div>')


def stepper(done: int) -> str:
    names = ["Pilih cover", "Tulis pesan", "Sisipkan", "Download"]
    out = ""
    for i, n in enumerate(names):
        cls = "done" if i < done else "cur" if i == done else ""
        out += f'<div class="step {cls}"><b>{"✓" if i < done else i + 1}</b>{n}</div>'
    return f'<div class="steps">{out}</div>'


def table(df: pd.DataFrame) -> None:
    def cell(v):
        is_bool = isinstance(v, (bool, np.bool_))
        s = ("Ya" if v else "Tidak") if is_bool else str(v)
        cls = "g" if s in ("PASS", "Ya") else "r" if s in ("FAIL", "Tidak") or s.startswith("ERROR") else ""
        return f'<td class="{cls}">{html.escape(s)}</td>'
    head = "".join(f"<th>{html.escape(str(c))}</th>" for c in df.columns)
    rows = "".join("<tr>" + "".join(cell(v) for v in r) + "</tr>" for r in df.itertuples(index=False))
    H(f'<div class="tblwrap"><table class="tbl"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>')


def pixel_grid(cols: int = 14, rows: int = 6) -> str:
    rng = random.Random(7)
    cells = ""
    for _ in range(cols * rows):
        r = rng.random()
        cells += '<i class="hot"></i>' if r > 0.90 else '<i class="on"></i>' if r > 0.62 else "<i></i>"
    return f'<div class="pixels">{cells}</div>'


# --------------------------------------------------------------------------
# Sidebar: navigasi + pengaturan tema
# --------------------------------------------------------------------------
HOME, EMBED, EXTRACT = "🏠  Beranda", "📥  Sisipkan pesan", "📤  Ekstrak pesan"
VIS, CHISQ, HIST, FRAG, BATCH = "👁️  Steganalisis visual", "📊  Steganalisis Chi-Square", "📈  Histogram warna", "💥  Uji kerapuhan JPEG", "🧪  Batch testing"
st.session_state.setdefault("page", HOME)


def go(target: str) -> None:
    st.session_state["page"] = target


def flip_theme() -> None:
    st.session_state["dark"] = not st.session_state["dark"]


with st.sidebar:
    H('<div class="brand"><span class="logo">🛡️</span>StegoShield</div>'
      '<div class="side-sub">Steganografi LSB &amp; AES-256</div><div class="side-h">Menu</div>')
    page = st.radio("Menu", [HOME, EMBED, EXTRACT, VIS, CHISQ, HIST, FRAG, BATCH], key="page", label_visibility="collapsed")

    st.markdown("---")
    
    # Tambahan tombol ABOUT menuju GitHub
    st.link_button("ℹ️  ABOUT (GitHub)", "https://github.com/hanadza/utski26-steganografi/blob/main/README.md", use_container_width=True)
    
    st.button("☀️  Mode terang" if st.session_state["dark"] else "🌙  Mode gelap",
              on_click=flip_theme, use_container_width=True)
    H('<div class="side-foot">StegoShield v1.0<br>AES-256-CBC, LSB 1-bit per kanal RGB, PRNG LCG 64-bit, PNG lossless</div>')

# --------------------------------------------------------------------------
# Beranda
# --------------------------------------------------------------------------
if page == HOME:
    H('<div class="hero"><div>'
      '<div class="hero-title">Sembunyikan pesan rahasia di dalam gambar biasa</div>'
      '<div class="hero-text">Pesan dienkripsi dengan AES-256, lalu disebar ke piksel yang diacak. '
      'Hasilnya nyaris tidak bisa dibedakan dari gambar aslinya.</div>'
      '<div class="chips"><span class="chip">AES-256-CBC</span><span class="chip">LSB acak</span>'
      '<span class="chip">PSNR &amp; MSE</span><span class="chip">PNG lossless</span></div></div>'
      + pixel_grid() + '</div>')
    H('<div class="feats">'
      '<div class="feat"><div class="ic">🔐</div><div class="ft">Dienkripsi dulu</div>'
      '<div class="fd">Pesan diamankan dengan AES-256-CBC sebelum disisipkan, jadi tetap aman walau bitnya ditemukan.</div></div>'
      '<div class="feat"><div class="ic">🎲</div><div class="ft">Tersebar acak</div>'
      '<div class="fd">Bit disimpan di piksel pilihan PRNG LCG 64-bit, bukan berurutan dari pojok gambar.</div></div>'
      '<div class="feat"><div class="ic">📏</div><div class="ft">Terukur</div>'
      '<div class="fd">Kualitas dinilai dengan PSNR dan MSE, dilengkapi histogram dan uji kompresi JPEG.</div></div></div>')
    section("Memahami steganografi", "Sebelum mencoba fitur, ini gambaran singkat apa yang terjadi di balik layar.")
    H('<div class="learn">'
      '<div class="feat"><div class="ft">Steganografi vs kriptografi</div>'
      '<div class="fd">Kriptografi mengacak isi pesan agar tidak terbaca, tetapi orang tetap tahu ada pesan rahasia. '
      'Steganografi menyembunyikan <b>keberadaan</b> pesan di dalam media biasa seperti gambar. '
      'StegoShield memakai keduanya: pesan dienkripsi dulu, baru disembunyikan.</div></div>'
      '<div class="feat"><div class="ft">Apa itu LSB?</div>'
      '<div class="fd">Tiap piksel punya kanal R, G, B bernilai 0 sampai 255 (8 bit). Bit paling kanan, '
      '<b>Least Significant Bit</b>, paling kecil pengaruhnya: mengubahnya hanya menggeser warna sebesar 1 dan tidak terlihat mata. '
      'Satu bit pesan dititipkan di satu LSB.</div>'
      '<div class="bits"><span>150 =</span><span>1001011<b class="hl">0</b></span><span>→</span>'
      '<span>1001011<b class="hl">1</b></span><span>= 151</span></div></div></div>')
    section("Alur kerja", "Dua sisi proses yang saling mengunci lewat stego-key yang sama.")
    H('<div class="lanes">'
      + lane("📥", "Penyisipan", "Sisi pengirim", [
          ("📝", "Tulis pesan", "Pesan teks dan stego-key menjadi masukan."),
          ("🔐", "Enkripsi AES-256", "Kunci diturunkan dari stego-key (SHA-256), IV acak ditaruh di depan hasil."),
          ("🏷️", "Tambah header", "32 bit di awal menyimpan panjang payload."),
          ("🎲", "Acak urutan piksel", "PRNG LCG 64-bit dan Fisher-Yates, seed dari stego-key."),
          ("✍️", "Tulis ke LSB", "Tiap bit menggantikan LSB satu kanal R, G, atau B."),
          ("💾", "Simpan PNG", "Format lossless menjaga bit tetap utuh. Jadilah citra stego."),
      ])
      + lane("📤", "Ekstraksi", "Sisi penerima", [
          ("🖼️", "Buka citra stego", "Gambar PNG hasil penyisipan, tanpa diedit."),
          ("🎲", "Bentuk ulang urutan", "Stego-key yang sama menghasilkan urutan piksel yang sama."),
          ("🏷️", "Baca header", "32 bit pertama memberi tahu panjang payload."),
          ("🔎", "Baca bit LSB", "Ambil bit sebanyak panjang payload dari posisi yang sudah diacak."),
          ("🔓", "Dekripsi AES-256", "Pisahkan IV, dekripsi, lalu buang padding."),
          ("✅", "Pesan kembali", "Bila key salah, header atau dekripsi gagal dan pesan tidak muncul."),
      ])
      + '</div>'
      '<div class="keybar"><span>🔑</span><span><b>Stego-key adalah penghubungnya.</b> '
      'Key yang sama membentuk urutan piksel dan kunci AES yang sama di kedua sisi.</span></div>')
    st.markdown("---")
    b1, b2 = st.columns(2, gap="medium")
    b1.button("Mulai sisipkan pesan", on_click=go, args=(EMBED,), use_container_width=True)
    b2.button("Ekstrak pesan dari gambar", on_click=go, args=(EXTRACT,), use_container_width=True)


# --------------------------------------------------------------------------
# Sisipkan pesan
# --------------------------------------------------------------------------
elif page == EMBED:
    section("Sisipkan pesan rahasia", "Pilih gambar cover, tulis pesan, lalu tentukan stego-key untuk mengenkripsinya.")
    info("Cara kerja penyisipan",
         "<p>Pesan teks diubah menjadi bit, lalu dititipkan di bit paling kanan (LSB) piksel gambar. Langkahnya:</p>",
         ol("<b>Enkripsi.</b> Pesan diacak dengan AES-256-CBC memakai kunci turunan stego-key. Hasilnya (payload) sedikit lebih besar dari teks asli karena ada padding dan data tambahan enkripsi.",
            "<b>Header.</b> Panjang payload ditulis di awal agar saat ekstraksi pembacaan berhenti tepat.",
            "<b>Acak posisi.</b> PRNG LCG 64-bit yang di-seed dari stego-key menentukan urutan piksel, jadi bit tersebar di seluruh gambar, bukan berurutan dari pojok.",
            "<b>Tulis LSB.</b> Satu bit disimpan di satu kanal R/G/B. Nilai kanal paling banyak berubah 1.",
            "<b>Simpan sebagai PNG.</b> Format lossless menjaga bit tetap utuh."),
         "<p><b>Kapasitas.</b> Kira-kira lebar × tinggi × 3 bit (dibagi 8 untuk byte), dikurangi ruang header. Gambar besar menampung pesan lebih panjang, dan pesan yang melebihi kapasitas ditolak.</p>",
         "<p><b>Membaca hasil.</b> MSE adalah rata-rata kuadrat selisih piksel cover dan stego. PSNR = 10·log10(255² / MSE); makin tinggi makin mirip. Karena tiap kanal berubah paling banyak 1, PSNR pada LSB 1-bit selalu di atas sekitar 48 dB, jauh di atas batas lulus 30 dB.</p>")
    step_slot = st.empty()
    done_steps = 0

    col1, col2 = st.columns(2, gap="large")
    with col1:
        uploaded_cover = st.file_uploader("Citra cover (PNG/BMP/JPG)", type=["png", "bmp", "jpg", "jpeg"], key="cover_uploader")
        stego_key_input = st.text_input("Stego-key (passphrase)", value="secret-passphrase-2026", type="password")
    with col2:
        secret_message = st.text_area(
            "Pesan rahasia",
            value="Ini adalah pesan rahasia yang dienkripsi AES-256 dan disisipkan menggunakan LSB acak.",
            height=190,
        )

    if uploaded_cover is None:
        callout("info", "Upload citra cover untuk melihat kapasitas dan memulai penyisipan.")
    else:
        done_steps = 2 if secret_message.strip() else 1
        cover_image = Image.open(uploaded_cover).convert("RGB")
        width, height = cover_image.size
        total_bits, max_bytes = se.calculate_capacity(cover_image)

        encrypted_sample = se.encrypt_message(secret_message, stego_key_input)
        payload_size = len(encrypted_sample)
        usage_pct = (payload_size / max_bytes) * 100 if max_bytes > 0 else 100

        st.markdown("---")
        section("Kapasitas citra cover")
        stats([
            ("Dimensi", f"{width} × {height} px"),
            ("Kapasitas maksimum", f"{max_bytes:,} Byte"),
            ("Ukuran payload", f"{payload_size:,} Byte"),
        ])
        meter(usage_pct)

        if payload_size > max_bytes:
            callout("error", f"Kapasitas terlampaui: payload {payload_size} Byte, kapasitas citra {max_bytes} Byte. "
                             "Pakai gambar yang lebih besar atau persingkat pesan.")
        else:
            if st.button("Sisipkan pesan", type="primary", use_container_width=True):
                with st.spinner("Mengenkripsi dan menyisipkan pesan..."):
                    with tempfile.TemporaryDirectory() as tmp_dir:
                        cp = os.path.join(tmp_dir, "cover.png")
                        sp = os.path.join(tmp_dir, "stego.png")
                        cover_image.save(cp, format="PNG")
                        se.embed_message(cp, secret_message, stego_key_input, sp)
                        mse, psnr, passed, label = stesting.evaluate_image_quality(cp, sp)
                        stego_img = Image.open(sp).convert("RGB")
                        buf = io.BytesIO()
                        stego_img.save(buf, format="PNG")
                st.session_state["emb"] = dict(
                    name=uploaded_cover.name, png=buf.getvalue(),
                    mse=mse, psnr=psnr, passed=passed, label=label,
                )

            # Hasil disimpan di session_state agar tidak hilang saat tombol download ditekan
            emb = st.session_state.get("emb")
            if emb and emb["name"] == uploaded_cover.name:
                done_steps = 4
                st.markdown("---")
                callout("success", "Pesan berhasil disisipkan. Download citra stego di bagian bawah.")
                section("Cover vs stego", "Kedua gambar seharusnya tampak identik bagi mata.")
                i1, i2 = st.columns(2, gap="large")
                with i1:
                    img_label("Citra cover")
                    st.image(cover_image, use_container_width=True)
                with i2:
                    img_label("Citra stego")
                    st.image(Image.open(io.BytesIO(emb["png"])), use_container_width=True)

                psnr_txt = f"{emb['psnr']:.2f} dB" if emb["psnr"] != float("inf") else "Tak hingga"
                badge = ('<span class="badge g">Lulus (PSNR ≥ 30 dB)</span>' if emb["passed"]
                         else '<span class="badge r">Gagal (PSNR &lt; 30 dB)</span>')
                section("Kualitas citra")
                stats([("MSE", f"{emb['mse']:.6f}"), ("PSNR", psnr_txt), ("Status", badge)])
                callout("success" if emb["passed"] else "error", f"Klasifikasi: {html.escape(str(emb['label']))}")

                base_name = os.path.splitext(uploaded_cover.name)[0]
                download_filename = f"{base_name}_stego.png"

                st.download_button(
                    f"Download citra stego ({download_filename})", data=emb["png"], file_name=download_filename,
                    mime="image/png", type="primary", use_container_width=True,
                )
    step_slot.markdown(stepper(done_steps), unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Ekstrak pesan
# --------------------------------------------------------------------------
elif page == EXTRACT:
    section("Ekstrak pesan rahasia", "Upload citra stego dan masukkan stego-key yang dipakai saat penyisipan.")
    info("Cara kerja ekstraksi",
         ol("<b>Seed sama.</b> Stego-key membentuk seed PRNG yang sama seperti saat penyisipan, sehingga urutan piksel yang sama terbentuk kembali.",
            "<b>Baca LSB.</b> Bit dibaca dari posisi-posisi tersebut, mulai dari header untuk mengetahui panjang payload.",
            "<b>Ambil payload.</b> Hanya sejumlah byte sesuai header yang dibaca.",
            "<b>Dekripsi.</b> Payload didekripsi dengan AES-256-CBC memakai kunci dari stego-key."),
         "<p><b>Kenapa stego-key salah gagal?</b> Key berbeda menghasilkan urutan piksel dan kunci AES yang berbeda, sehingga bit yang terbaca acak dan dekripsi hampir pasti gagal. Coba masukkan key yang salah untuk melihatnya.</p>",
         "<p><b>Catatan.</b> Gunakan file stego PNG asli. Gambar yang sudah dikompres JPEG, di-screenshot, atau dikirim lewat aplikasi yang mengompres ulang akan merusak bit pesan.</p>")

    c1, c2 = st.columns(2, gap="large")
    with c1:
        uploaded_stego = st.file_uploader("Citra stego (PNG)", type=["png", "bmp"], key="stego_uploader")
    with c2:
        stego_key_extract = st.text_input("Stego-key", value="secret-passphrase-2026", type="password", key="extract_key_input")

    if uploaded_stego is None:
        callout("info", "Upload citra stego untuk mulai mengekstrak pesan.")
    else:
        stego_img_input = Image.open(uploaded_stego).convert("RGB")
        st.markdown("---")
        left, right = st.columns(2, gap="large")
        with left:
            img_label("Citra stego")
            st.image(stego_img_input, use_container_width=True)
        with right:
            if st.button("Ekstrak dan dekripsi pesan", type="primary", use_container_width=True):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    p = os.path.join(tmp_dir, "stego_input.png")
                    stego_img_input.save(p, format="PNG")
                    try:
                        text = se.extract_message(p, stego_key_extract)
                        callout("success", "Pesan berhasil diekstrak dan didekripsi.")
                        img_label("Isi pesan")
                        H(f'<div class="msgbox">{html.escape(text)}</div>')
                    except se.ExtractionError as err:
                        callout("error", f"Ekstraksi gagal: {html.escape(str(err))}. "
                                         "Pastikan stego-key sama dan citra belum diedit atau dikompres.")


# --------------------------------------------------------------------------
# Steganalisis visual
# --------------------------------------------------------------------------
elif page == VIS:
    section(
        "Steganalisis visual (Enhanced LSB)",
        "Bit paling tidak signifikan tiap piksel diisolasi lalu dikalikan 255, sehingga tampil sebagai pola "
        "hitam-putih. Bandingkan pola cover dan stego untuk melihat area yang berubah.",
    )
    info("Cara membaca steganalisis visual",
         "<p>Steganalisis adalah upaya mendeteksi keberadaan pesan tersembunyi. Di sini bit LSB tiap piksel (0 atau 1) dikalikan 255, sehingga menjadi hitam (0) atau putih (255).</p>",
         ul("<b>Gambar asli:</b> bidang LSB tampak seperti noise, kadang masih menyisakan pola dari gambar.",
            "<b>Penyisipan berurutan:</b> area yang terisi pesan tampak jauh lebih acak dibanding area lain, sehingga mudah dikenali.",
            "<b>StegoShield:</b> posisi piksel diacak, jadi bit pesan tersebar merata dan perubahan sulit dibedakan dengan mata. Itulah gunanya PRNG."))
    v1, v2 = st.columns(2, gap="large")
    with v1:
        up_vis_cover = st.file_uploader("Citra cover", type=["png", "bmp", "jpg"], key="vis_cover")
    with v2:
        up_vis_stego = st.file_uploader("Citra stego", type=["png", "bmp"], key="vis_stego")

    if up_vis_cover is None or up_vis_stego is None:
        callout("info", "Upload citra cover dan citra stego untuk membandingkan bidang bit LSB.")
    else:
        enh_c = se.get_enhanced_lsb_image(Image.open(up_vis_cover).convert("RGB"))
        enh_s = se.get_enhanced_lsb_image(Image.open(up_vis_stego).convert("RGB"))
        st.markdown("---")
        a, b = st.columns(2, gap="large")
        with a:
            img_label("Enhanced LSB cover")
            st.image(enh_c, use_container_width=True)
        with b:
            img_label("Enhanced LSB stego")
            st.image(enh_s, use_container_width=True)


# --------------------------------------------------------------------------
# Steganalisis Chi-Square (Statistical Attack)
# --------------------------------------------------------------------------
elif page == CHISQ:
    section(
        "Steganalisis Statistik Uji Chi-Square (Westfeld & Pfitzmann Attack)",
        "Mendeteksi keberadaan pesan rahasia LSB berdasarkan ketidakseimbangan statistik pada pasangan nilai piksel / Pairs of Values (PoV).",
    )
    info(
        "Bagaimana Uji Chi-Square Bekerja?",
        "<p>Uji Chi-Square (<b>χ² Attack</b>) menganalisis kesetaraan frekuensi piksel berpasangan 2k dan 2k+1 (misal 4 & 5, 10 & 11).</p>",
        ul(
            "<b>Gambar Alami (Cover):</b> Frekuensi piksel 2k dan 2k+1 biasanya tidak seimbang.",
            "<b>Penyisipan LSB (Stego):</b> Bit rahasia yang terenkripsi acak menyamakan frekuensi 2k dan 2k+1.",
            "<b>Interpretasi Probabilitas:</b> Jika p-value mendekati <b>100%</b>, gambar hampir pasti mengandung data tersembunyi LSB. Jika mendekati <b>0%</b>, gambar dinilai alami/bersih.",
        ),
    )

    c1, c2 = st.columns(2, gap="large")
    with c1:
        up_chi_cover = st.file_uploader("Citra Cover (Opsional untuk Pembanding)", type=["png", "jpg", "bmp"], key="chi_cover")
    with c2:
        up_chi_stego = st.file_uploader("Citra Stego / Uji (Wajib)", type=["png", "bmp", "jpg"], key="chi_stego")

    if up_chi_stego is None:
        callout("info", "Upload citra stego (atau gambar yang ingin dianalisis) di kolom kanan untuk menghitung probabilitas Chi-Square.")
    else:
        with tempfile.TemporaryDirectory() as tmp_dir:
            p_stego_file = os.path.join(tmp_dir, "test_stego.png")
            Image.open(up_chi_stego).convert("RGB").save(p_stego_file)

            if up_chi_cover is not None:
                p_cover_file = os.path.join(tmp_dir, "test_cover.png")
                Image.open(up_chi_cover).convert("RGB").save(p_cover_file)
                plot_file = os.path.join(tmp_dir, "chi_sq_result.png")

                with st.spinner("Menghitung analisis Uji Chi-Square..."):
                    p_cov, p_stg = stesting.plot_chi_square_progression(p_cover_file, p_stego_file, plot_file)

                st.markdown("---")
                a, b = st.columns(2, gap="large")
                with a:
                    pct_val = p_stg * 100
                    status_text = "TERINDIKASI STEGO LSB" if pct_val > 50 else "TERLIHAT GAMBAR ALAMI"
                    stats([
                        ("Probabilitas File Stego/Uji", f"{pct_val:.1f}%"),
                        ("Status Deteksi", status_text),
                        ("Probabilitas Cover Pembanding", f"{p_cov * 100:.1f}%"),
                    ])
                    callout("error" if pct_val > 50 else "success", f"<b>Hasil analisis:</b> Gambar Uji {status_text} (Probabilitas Chi-Square: {pct_val:.1f}%).")
                with b:
                    st.image(plot_file, use_container_width=True)
            else:
                with st.spinner("Menghitung analisis Uji Chi-Square..."):
                    pcts, p_vals, overall_p = stesting.analyze_chi_square_progression(p_stego_file)

                pct_val = overall_p * 100
                st.markdown("---")
                left, right = st.columns(2, gap="large")
                with left:
                    status_badge = "Terindikasi Mengandung Pesan LSB" if pct_val > 50 else "Gambar Bersih (Tidak Terdeteksi LSB)"
                    callout("error" if pct_val > 50 else "success", f"<b>Hasil Deteksi:</b> {status_badge}")
                    stats([
                        ("Probabilitas Akhir Chi-Square", f"{pct_val:.2f}%"),
                        ("Indikasi Steganografi", "TINGGI" if pct_val > 50 else "RENDAH"),
                    ])
                with right:
                    import matplotlib.pyplot as plt
                    fig, ax = plt.subplots(figsize=(6, 3.5))
                    ax.plot(pcts, [p * 100 for p in p_vals], "r-o", label=f"File Uji (Final: {pct_val:.1f}%)", linewidth=2)
                    ax.axhline(50, color="gray", linestyle="--", alpha=0.6, label="Threshold Deteksi (50%)")
                    ax.set_title("Kurva Steganalisis Chi-Square")
                    ax.set_xlabel("Persentase Sampel Piksel (%)")
                    ax.set_ylabel("Probabilitas Stego (%)")
                    ax.set_ylim(-5, 105)
                    ax.grid(True, linestyle=":", alpha=0.6)
                    ax.legend()
                    fig.tight_layout()
                    st.pyplot(fig)
                    plt.close(fig)


# --------------------------------------------------------------------------
# Histogram warna
# --------------------------------------------------------------------------
elif page == HIST:
    section("Histogram RGB: cover vs stego", "Histogram yang hampir sama berarti sebaran warna tidak banyak berubah.")
    info("Cara membaca histogram",
         "<p>Histogram menghitung berapa banyak piksel untuk tiap nilai warna 0 sampai 255, terpisah untuk kanal R, G, dan B.</p>",
         "<p>Mengubah LSB hanya menggeser nilai sebesar 1, jadi bentuk histogram cover dan stego nyaris sama. Itu tandanya sebaran warna terjaga dan perubahan tidak mencolok.</p>",
         "<p>Perbedaan kecil tetap ada: nilai genap dan ganjil yang bersebelahan (misalnya 150 dan 151) cenderung makin seimbang jumlahnya bila makin banyak bit disisipkan. Pola inilah yang dimanfaatkan uji statistik seperti chi-square untuk mendeteksi steganografi.</p>")
    h1, h2 = st.columns(2, gap="large")
    with h1:
        up_h_cover = st.file_uploader("Cover", type=["png", "jpg"], key="h_cover")
    with h2:
        up_h_stego = st.file_uploader("Stego", type=["png"], key="h_stego")

    if up_h_cover is not None and up_h_stego is not None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tc, ts, th = (os.path.join(tmp_dir, n) for n in ("cover.png", "stego.png", "hist.png"))
            Image.open(up_h_cover).convert("RGB").save(tc)
            Image.open(up_h_stego).convert("RGB").save(ts)
            stesting.plot_histogram_comparison(tc, ts, th)
            st.image(th, use_container_width=True)
    else:
        callout("info", "Upload cover dan stego untuk menampilkan histogram.")


# --------------------------------------------------------------------------
# Uji kerapuhan JPEG
# --------------------------------------------------------------------------
elif page == FRAG:
    section("Uji kerapuhan terhadap kompresi JPEG",
            "Stego dikompres JPEG pada beberapa kualitas, lalu pesan dicoba diekstrak kembali.")
    info("Kenapa LSB rapuh terhadap JPEG?",
         "<p>JPEG adalah kompresi <b>lossy</b>: gambar dibagi blok 8×8, diubah ke domain frekuensi (DCT), lalu detail halus dibuang lewat kuantisasi. Akibatnya nilai piksel berubah, termasuk bit LSB tempat pesan disimpan.</p>",
         ul("Kualitas JPEG lebih rendah berarti perubahan lebih besar, tetapi kualitas tinggi pun biasanya sudah cukup untuk merusak pesan.",
            "Status <b>utuh</b> berarti pesan hasil ekstraksi sama persis dengan pesan asli."),
         "<p><b>Kesimpulan:</b> LSB bersifat rapuh (fragile). Pesan hanya aman selama stego tetap berupa PNG. Kirim lewat aplikasi atau media sosial yang mengompres ulang gambar dapat menghapus pesan. Inilah trade-off LSB: kapasitas besar dan tak terlihat, tetapi tidak tahan modifikasi.</p>")
    f1, f2 = st.columns(2, gap="large")
    with f1:
        up_f_stego = st.file_uploader("Citra stego", type=["png"], key="f_stego")
    with f2:
        f_msg = st.text_input("Pesan asli", value="Test message for LSB.")
        f_key = st.text_input("Stego-key", value="secret-passphrase-002", type="password")

    if up_f_stego is None:
        callout("info", "Upload citra stego untuk menjalankan uji kerapuhan.")
    elif st.button("Jalankan uji kerapuhan", type="primary"):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tf = os.path.join(tmp_dir, "stego.png")
            Image.open(up_f_stego).convert("RGB").save(tf)
            res = stesting.fragility_test_jpeg(tf, f_key, f_msg, tmp_dir)
            df = pd.DataFrame(res)[["quality", "status", "berhasil_utuh"]]
            df.columns = ["Kualitas JPEG", "Status", "Pesan utuh"]
            table(df)


# --------------------------------------------------------------------------
# Batch testing
# --------------------------------------------------------------------------
elif page == BATCH:
    section("Pengujian otomatis 5 citra × 3 ukuran pesan",
            "Citra uji dibuat acak (256×256 px), lalu tiap pesan disisipkan dan dinilai dengan PSNR/MSE.")
    info("Apa yang diuji di sini?",
         "<p>Lima citra diuji dengan tiga ukuran pesan (100 B, 1 KB, 5 KB) untuk melihat pengaruh ukuran pesan terhadap kualitas.</p>",
         ul("Makin besar pesan, makin banyak piksel yang diubah, sehingga MSE naik dan PSNR turun perlahan, tetapi tetap jauh di atas 30 dB.",
            "Status <b>PASS</b> berarti PSNR ≥ 30 dB.",
            "Citra uji berupa noise acak 256×256 px, yaitu citra kecil yang penuh tekstur, sebagai kondisi yang cukup ketat."))

    if "batch_results" not in st.session_state:
        st.session_state["batch_results"] = None
        st.session_state["batch_images"] = []

    if st.button("Jalankan batch test", type="primary"):
        with st.spinner("Memproses batch test..."):
            messages = {"Kecil (100B)": "A" * 100, "Sedang (1KB)": "B" * 1000, "Besar (5KB)": "C" * 5000}
            results = []
            sample_images = []
            key_test = "batch-test-key"

            with tempfile.TemporaryDirectory() as tmp_dir:
                for i in range(1, 6):
                    c_img = Image.fromarray(np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8))
                    c_path = os.path.join(tmp_dir, f"cover_{i}.png")
                    c_img.save(c_path)

                    c_buf = io.BytesIO()
                    c_img.save(c_buf, format="PNG")
                    c_bytes = c_buf.getvalue()

                    for msg_label, msg in messages.items():
                        s_path = os.path.join(tmp_dir, f"stego_{i}_{msg_label}.png")
                        try:
                            se.embed_message(c_path, msg, key_test, s_path)
                            mse, psnr, passed, _ = stesting.evaluate_image_quality(c_path, s_path)

                            s_img = Image.open(s_path)
                            s_buf = io.BytesIO()
                            s_img.save(s_buf, format="PNG")
                            s_bytes = s_buf.getvalue()

                            results.append({
                                "Citra Cover": f"Citra #{i} (256x256)", "Ukuran Pesan": msg_label,
                                "MSE": round(mse, 6), "PSNR (dB)": round(psnr, 2),
                                "Status (>30dB)": "PASS" if passed else "FAIL",
                            })

                            sample_images.append({
                                "label": f"Citra #{i} - Pesan {msg_label}",
                                "cover_bytes": c_bytes,
                                "stego_bytes": s_bytes,
                                "filename": f"stego_citra_{i}_{msg_label.split()[0].lower()}.png",
                                "psnr": round(psnr, 2),
                            })
                        except Exception as e:
                            results.append({
                                "Citra Cover": f"Citra #{i}", "Ukuran Pesan": msg_label,
                                "MSE": -1, "PSNR (dB)": 0, "Status (>30dB)": f"ERROR ({e})",
                            })

            st.session_state["batch_results"] = results
            st.session_state["batch_images"] = sample_images

    if st.session_state["batch_results"] is not None:
        results = st.session_state["batch_results"]
        images = st.session_state.get("batch_images", [])
        ok = sum(r["Status (>30dB)"] == "PASS" for r in results)
        valid = [r["PSNR (dB)"] for r in results if r["MSE"] != -1]
        callout("success", "Batch test selesai.")
        stats([
            ("Total uji", str(len(results))),
            ("Lulus", f"{ok} / {len(results)}"),
            ("Rata-rata PSNR", f"{np.mean(valid):.2f} dB" if valid else "-"),
        ])
        table(pd.DataFrame(results))

        # Opsi Unduh Laporan CSV
        df_export = pd.DataFrame(results)
        csv_data = df_export.to_csv(index=False).encode("utf-8")
        st.markdown("---")
        st.download_button(
            label="📥 Download Hasil Tabel Batch Test (CSV)",
            data=csv_data,
            file_name="hasil_batch_test_stegoshield.csv",
            mime="text/csv",
            use_container_width=True,
        )

        # Galeri visual & Unduh Citra Stego Hasil Uji
        if images:
            section("Galeri & Unduh Citra Uji Stego (PNG)", "Pengguna/penguji dapat melihat dan mengunduh langsung file citra stego hasil pengujian batch test.")
            sel_img = st.selectbox("Pilih Sampel Hasil Citra Uji untuk Diinspeksi / Diunduh:", [img["label"] for img in images])
            selected_item = next(img for img in images if img["label"] == sel_img)

            g1, g2 = st.columns(2, gap="large")
            with g1:
                img_label(f"Cover ({selected_item['label']})")
                st.image(selected_item["cover_bytes"], use_container_width=True)
            with g2:
                img_label(f"Stego ({selected_item['label']} - PSNR: {selected_item['psnr']} dB)")
                st.image(selected_item["stego_bytes"], use_container_width=True)
                st.download_button(
                    label=f"📥 Download File PNG ({selected_item['filename']})",
                    data=selected_item["stego_bytes"],
                    file_name=selected_item["filename"],
                    mime="image/png",
                    use_container_width=True,
                )
    else:
        callout("info", "Tekan tombol di atas untuk menjalankan pengujian otomatis.")

"""
app.py
------
Aplikasi Web Steganografi LSB (Least Significant Bit) & Enkripsi AES-256
berbasis Streamlit.
"""

from __future__ import annotations

import io
import os
import tempfile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
import streamlit as st

import steg_engine as se
import steg_testing as stesting


# --- Streamlit Configuration & Styling ---

st.set_page_config(
    page_title="StegoShield - Steganografi LSB & AES-256",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        color: #1E88E5;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #555555;
        margin-bottom: 1.5rem;
    }
    .pass-badge {
        background-color: #E8F5E9;
        color: #2E7D32;
        padding: 0.3rem 0.6rem;
        border-radius: 0.3rem;
        font-weight: bold;
    }
    .fail-badge {
        background-color: #FFEBEE;
        color: #C62828;
        padding: 0.3rem 0.6rem;
        border-radius: 0.3rem;
        font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --- Sidebar ---

with st.sidebar:
    st.title("🔒 StegoShield")
    st.caption("LSB Steganography & AES-256 Engine")
    st.markdown("---")
    st.markdown("### Spesifikasi")
    st.markdown("- **Kriptografi:** AES-256-CBC")
    st.markdown("- **Steganografi:** LSB 1-Bit per kanal RGB")
    st.markdown("- **Pengacak Piksel:** PRNG LCG 64-Bit")
    st.markdown("- **Format Citra:** PNG Lossless")
    st.markdown("---")
    st.caption("StegoShield v1.0")


# --- Main Header ---

st.markdown('<div class="main-header">StegoShield: Steganografi LSB & AES-256</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Penyembunyian pesan teks terenkripsi pada citra digital '
    'dengan PRNG acak dan evaluasi kuantitatif (PSNR/MSE).</div>',
    unsafe_allow_html=True,
)

tab1, tab2, tab3, tab4 = st.tabs([
    "📥 1. Enkripsi & Penyisipan",
    "📤 2. Ekstraksi & Dekripsi",
    "👁️ 3. Steganalisis Visual (Enhanced LSB)",
    "📊 4. Pengujian Kuantitatif & Kerapuhan",
])


# --- Tab 1: Embedding ---

with tab1:
    st.subheader("Penyisipan Pesan Rahasia ke Citra Cover")
    col_input1, col_input2 = st.columns([1, 1])

    with col_input1:
        uploaded_cover = st.file_uploader(
            "Upload Citra Cover (PNG/BMP/JPG):",
            type=["png", "bmp", "jpg", "jpeg"],
            key="cover_uploader",
        )
        stego_key_input = st.text_input(
            "Stego-Key (Passphrase):",
            value="secret-passphrase-2026",
            type="password",
        )

    with col_input2:
        secret_message = st.text_area(
            "Pesan Rahasia:",
            value="Ini adalah pesan rahasia yang dienkripsi AES-256 dan disisipkan menggunakan LSB acak.",
            height=130,
        )

    if uploaded_cover is not None:
        cover_image = Image.open(uploaded_cover).convert("RGB")
        width, height = cover_image.size
        total_bits, max_bytes = se.calculate_capacity(cover_image)

        encrypted_sample = se.encrypt_message(secret_message, stego_key_input)
        payload_size = len(encrypted_sample)
        usage_pct = (payload_size / max_bytes) * 100 if max_bytes > 0 else 100

        st.markdown("---")
        st.markdown("#### Informasi Kapasitas Citra Cover")
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("Dimensi Citra", f"{width} × {height} px")
        m_col2.metric("Kapasitas Maksimum", f"{max_bytes:,} Byte")
        m_col3.metric("Ukuran Payload", f"{payload_size:,} Byte")
        m_col4.metric("Kapasitas Terpakai", f"{usage_pct:.2f}%")

        st.progress(min(usage_pct / 100, 1.0))

        if payload_size > max_bytes:
            st.error(
                f"Kapasitas terlampaui! Payload ({payload_size} Byte) melebihi "
                f"kapasitas maksimum citra ({max_bytes} Byte)."
            )
        else:
            if st.button("Proses Penyisipan Pesan", type="primary", use_container_width=True):
                with st.spinner("Mengenkripsi & menyisipkan pesan..."):
                    with tempfile.TemporaryDirectory() as tmp_dir:
                        tmp_cover_path = os.path.join(tmp_dir, "cover.png")
                        tmp_stego_path = os.path.join(tmp_dir, "stego.png")

                        cover_image.save(tmp_cover_path, format="PNG")
                        se.embed_message(tmp_cover_path, secret_message, stego_key_input, tmp_stego_path)

                        stego_image = Image.open(tmp_stego_path).convert("RGB")
                        mse, psnr, passed, label = stesting.evaluate_image_quality(tmp_cover_path, tmp_stego_path)

                        st.success("Penyisipan berhasil!")

                        st.markdown("### Perbandingan Citra Cover vs Stego")
                        img_col1, img_col2 = st.columns(2)

                        with img_col1:
                            st.markdown("**Citra Cover**")
                            st.image(cover_image, use_container_width=True)

                        with img_col2:
                            st.markdown("**Citra Stego**")
                            st.image(stego_image, use_container_width=True)

                        st.markdown("### Evaluasi Kualitatif & Kuantitatif")
                        q_col1, q_col2, q_col3 = st.columns(3)
                        q_col1.metric("MSE", f"{mse:.6f}")
                        q_col2.metric("PSNR", f"{psnr:.2f} dB" if psnr != float("inf") else "Tak Hingga")

                        status_badge = '<span class="pass-badge">PASS (PSNR ≥ 30 dB)</span>' if passed else '<span class="fail-badge">FAIL</span>'
                        q_col3.markdown(f"**Status:**<br>{status_badge}", unsafe_allow_html=True)
                        st.info(f"Klasifikasi: {label}")

                        buf = io.BytesIO()
                        stego_image.save(buf, format="PNG")
                        st.download_button(
                            label="Download Citra Stego (PNG)",
                            data=buf.getvalue(),
                            file_name="stego_result.png",
                            mime="image/png",
                            type="primary",
                        )


# --- Tab 2: Extracting ---

with tab2:
    st.subheader("Ekstraksi Pesan Rahasia")

    col_ext1, col_ext2 = st.columns([1, 1])

    with col_ext1:
        uploaded_stego = st.file_uploader(
            "Upload Citra Stego (PNG):",
            type=["png", "bmp"],
            key="stego_uploader",
        )
    with col_ext2:
        stego_key_extract = st.text_input(
            "Masukkan Stego-Key:",
            value="secret-passphrase-2026",
            type="password",
            key="extract_key_input",
        )

    if uploaded_stego is not None:
        stego_img_input = Image.open(uploaded_stego).convert("RGB")
        st.image(stego_img_input, caption="Citra Stego", width=320)

        if st.button("Ekstrak & Dekripsi Pesan", type="primary", use_container_width=True):
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_ext_path = os.path.join(tmp_dir, "stego_input.png")
                stego_img_input.save(tmp_ext_path, format="PNG")

                try:
                    extracted_text = se.extract_message(tmp_ext_path, stego_key_extract)
                    st.success("Ekstraksi & dekripsi AES-256 berhasil!")
                    st.text_area("Isi Pesan:", value=extracted_text, height=140, disabled=True)
                except se.ExtractionError as err:
                    st.error(f"Ekstraksi Gagal: {err}")


# --- Tab 3: Visual Steganalysis ---

with tab3:
    st.subheader("Steganalisis Visual (Enhanced LSB)")
    st.markdown(
        "Visualisasi bit LSB dilakukan dengan mengisolasi bit terakhir piksel "
        "dan mengalikan nilainya dengan 255 untuk menghasilkan kontras hitam-putih."
    )

    col_vis1, col_vis2 = st.columns(2)
    with col_vis1:
        up_vis_cover = st.file_uploader("Citra Cover:", type=["png", "bmp", "jpg"], key="vis_cover")
    with col_vis2:
        up_vis_stego = st.file_uploader("Citra Stego:", type=["png", "bmp"], key="vis_stego")

    if up_vis_cover is not None and up_vis_stego is not None:
        img_c = Image.open(up_vis_cover).convert("RGB")
        img_s = Image.open(up_vis_stego).convert("RGB")

        enh_c = se.get_enhanced_lsb_image(img_c)
        enh_s = se.get_enhanced_lsb_image(img_s)

        st.markdown("### Perbandingan Bidang Bit LSB")
        v_col1, v_col2 = st.columns(2)
        with v_col1:
            st.markdown("**Enhanced LSB Cover**")
            st.image(enh_c, use_container_width=True)
        with v_col2:
            st.markdown("**Enhanced LSB Stego**")
            st.image(enh_s, use_container_width=True)


# --- Tab 4: Quantitative Testing & Fragility ---

with tab4:
    st.subheader("Pengujian Kuantitatif & Ketahanan")

    subtab1, subtab2, subtab3 = st.tabs([
        "📈 Histogram Warna",
        "💥 Uji Kerapuhan JPEG",
        "🧪 Batch Testing (5 Citra × 3 Pesan)",
    ])

    with subtab1:
        st.markdown("#### Histogram RGB (Cover vs Stego)")
        up_h_cover = st.file_uploader("Cover:", type=["png", "jpg"], key="h_cover")
        up_h_stego = st.file_uploader("Stego:", type=["png"], key="h_stego")

        if up_h_cover is not None and up_h_stego is not None:
            with tempfile.TemporaryDirectory() as tmp_dir:
                tc_path = os.path.join(tmp_dir, "cover.png")
                ts_path = os.path.join(tmp_dir, "stego.png")
                thist_path = os.path.join(tmp_dir, "hist.png")

                Image.open(up_h_cover).convert("RGB").save(tc_path)
                Image.open(up_h_stego).convert("RGB").save(ts_path)

                stesting.plot_histogram_comparison(tc_path, ts_path, thist_path)
                st.image(thist_path, use_container_width=True)

    with subtab2:
        st.markdown("#### Uji Kerapuhan Terhadap Kompresi JPEG")
        up_f_stego = st.file_uploader("Citra Stego:", type=["png"], key="f_stego")
        f_msg = st.text_input("Pesan Asli:", value="Test message for LSB.")
        f_key = st.text_input("Stego-Key:", value="secret-passphrase-002", type="password")

        if up_f_stego is not None and st.button("Jalankan Uji Kerapuhan"):
            with tempfile.TemporaryDirectory() as tmp_dir:
                tf_path = os.path.join(tmp_dir, "stego.png")
                Image.open(up_f_stego).convert("RGB").save(tf_path)

                res = stesting.fragility_test_jpeg(tf_path, f_key, f_msg, tmp_dir)
                df_frag = pd.DataFrame(res)
                st.table(df_frag[["quality", "status", "berhasil_utuh"]])

    with subtab3:
        st.markdown("#### Pengujian Otomatis Matriks 5 Citra × 3 Ukuran Pesan")

        if st.button("Jalankan Batch Test", type="primary"):
            with st.spinner("Memproses batch test..."):
                messages = {
                    "Kecil (100B)": "A" * 100,
                    "Sedang (1KB)": "B" * 1000,
                    "Besar (5KB)": "C" * 5000,
                }
                test_results = []
                key_test = "batch-test-key"

                with tempfile.TemporaryDirectory() as tmp_dir:
                    for i in range(1, 6):
                        c_path = os.path.join(tmp_dir, f"cover_{i}.png")
                        img_arr = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)
                        Image.fromarray(img_arr).save(c_path)

                        for msg_label, msg_content in messages.items():
                            s_path = os.path.join(tmp_dir, f"stego_{i}_{msg_label}.png")
                            try:
                                se.embed_message(c_path, msg_content, key_test, s_path)
                                mse, psnr, passed, label = stesting.evaluate_image_quality(c_path, s_path)
                                test_results.append({
                                    "Citra Cover": f"Citra #{i} (256x256)",
                                    "Ukuran Pesan": msg_label,
                                    "MSE": round(mse, 6),
                                    "PSNR (dB)": round(psnr, 2),
                                    "Status (>30dB)": "PASS" if passed else "FAIL",
                                })
                            except Exception as e:
                                test_results.append({
                                    "Citra Cover": f"Citra #{i}",
                                    "Ukuran Pesan": msg_label,
                                    "MSE": -1,
                                    "PSNR (dB)": 0,
                                    "Status (>30dB)": f"ERROR ({e})",
                                })

                df_batch = pd.DataFrame(test_results)
                st.dataframe(df_batch, use_container_width=True)
                st.success("Batch test selesai.")

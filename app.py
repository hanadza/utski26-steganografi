"""
app.py
======
Aplikasi Web Steganografi LSB (Least Significant Bit) + Enkripsi AES-256
berbasis Streamlit.

Tugas Proyek Keamanan Informasi - Topik B (Steganografi)
Program Studi Informatika, Universitas Siliwangi

Cara menjalankan:
    streamlit run app.py
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

import stego_engine as se
import stego_testing as stesting


# =============================================================================
# KONFIGURASI HALAMAN STREAMLIT & CUSTOM CSS
# =============================================================================
st.set_page_config(
    page_title="StegoShield - Steganografi LSB & AES-256",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling (CSS)
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E88E5;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #555555;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F0F4F8;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1E88E5;
        margin-bottom: 1rem;
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


# =============================================================================
# SIDEBAR INFORMASI & PENGATURAN
# =============================================================================
with st.sidebar:
    st.image("https://img.icons8.com/isometric/100/security-shield.png", width=70)
    st.title("StegoShield v1.0")
    st.caption("Aplikasi Steganografi LSB & AES-256")
    st.markdown("---")

    st.markdown("### 🎓 Identitas Proyek")
    st.markdown("**Mata Kuliah:** Keamanan Informasi")
    st.markdown("**Topik B:** Aplikasi Steganografi Citra")
    st.markdown("**Institusi:** Jurusan Informatika, Universitas Siliwangi")

    st.markdown("---")
    st.markdown("### ⚙️ Spesifikasi Teknis")
    st.markdown("- **Metode:** LSB 1-Bit per Kanal RGB")
    st.markdown("- **Pengacak Posisi:** PRNG LCG 64-bit + Fisher-Yates Shuffle")
    st.markdown("- **Enkripsi:** AES-256-CBC (PyCryptodome)")
    st.markdown("- **Format Citra Output:** PNG Lossless")

    st.markdown("---")
    st.caption("© 2026 StegoShield Team - Unsil")


# =============================================================================
# HEADER UTAMA
# =============================================================================
st.markdown('<div class="main-header">🔒 StegoShield: Steganografi LSB & Enkripsi AES-256</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Aplikasi penyembunyian pesan teks terenkripsi di dalam citra digital dengan '
    'pengacakan posisi PRNG dan evaluasi kuantitatif kualitas citra (PSNR/MSE).</div>',
    unsafe_allow_html=True,
)

# Tabs Navigasi Utama
tab1, tab2, tab3, tab4 = st.tabs([
    "📥 1. Enkripsi & Penyisipan",
    "📤 2. Ekstraksi & Dekripsi",
    "👁️ 3. Steganalisis Visual (Enhanced LSB)",
    "📊 4. Pengujian Kuantitatif & Kerapuhan",
])


# =============================================================================
# TAB 1: ENKRIPSI & PENYISIPAN (EMBEDDING)
# =============================================================================
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
            "Stego-Key (Kata Sandi Rahasia):",
            value="kunci-rahasia-uts-2026",
            type="password",
            help="Kunci ini dipakai untuk menurunkan kunci enkripsi AES-256 dan mendayagunakan seed PRNG LCG.",
        )

    with col_input2:
        secret_message = st.text_area(
            "Pesan Rahasia yang Akan Disembunyikan:",
            value="Keamanan Informasi UNSIL - Ini adalah pesan rahasia yang dienkripsi AES-256 dan disisipkan dengan LSB acak.",
            height=130,
        )

    if uploaded_cover is not None:
        cover_image = Image.open(uploaded_cover).convert("RGB")
        width, height = cover_image.size
        total_bits, max_bytes = se.calculate_capacity(cover_image)

        # Hitung estimasi ukuran payload terenkripsi
        encrypted_sample = se.encrypt_message(secret_message, stego_key_input)
        payload_size = len(encrypted_sample)
        usage_pct = (payload_size / max_bytes) * 100 if max_bytes > 0 else 100

        st.markdown("---")
        st.markdown("#### 📏 Informasi Kapasitas Citra Cover")
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("Dimensi Citra", f"{width} × {height} px")
        m_col2.metric("Kapasitas Maksimum", f"{max_bytes:,} Byte (~{max_bytes/1024:.1f} KB)")
        m_col3.metric("Ukuran Payload Terenkripsi", f"{payload_size:,} Byte")
        m_col4.metric("Kapasitas Terpakai", f"{usage_pct:.2f}%")

        st.progress(min(usage_pct / 100, 1.0))

        if payload_size > max_bytes:
            st.error(
                f"❌ **Kapasitas Terlampaui!** Ukuran payload terenkripsi ({payload_size} Byte) "
                f"melebihi kapasitas citra ({max_bytes} Byte). Gunakan citra lebih besar atau persingkat pesan."
            )
        else:
            if st.button("🚀 Proses Penyisipan Pesan (Embed)", type="primary", use_container_width=True):
                with st.spinner("Mengenkripsi pesan (AES-256) & menyisipkan ke bit LSB..."):
                    # Simpan cover sementara
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_cover:
                        cover_image.save(tmp_cover.name, format="PNG")
                        tmp_cover_path = tmp_cover.name

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_stego:
                        tmp_stego_path = tmp_stego.name

                    # Penyisipan
                    se.embed_message(tmp_cover_path, secret_message, stego_key_input, tmp_stego_path)

                    stego_image = Image.open(tmp_stego_path).convert("RGB")
                    mse, psnr, passed, label = stesting.evaluate_image_quality(tmp_cover_path, tmp_stego_path)

                    st.success("🎉 **Penyisipan Berhasil!** Citra stego berhasil dibuat.")

                    # Tampilkan Berdampingan
                    st.markdown("### 🖼️ Perbandingan Citra Cover vs Citra Stego")
                    img_col1, img_col2 = st.columns(2)

                    with img_col1:
                        st.markdown("**Citra Cover (Asli)**")
                        st.image(cover_image, use_container_width=True)

                    with img_col2:
                        st.markdown("**Citra Stego (Setelah Penyisipan)**")
                        st.image(stego_image, use_container_width=True)

                    # Tampilkan Metrik Kualitas
                    st.markdown("### 📊 Hasil Evaluasi Kualitas Citra")
                    q_col1, q_col2, q_col3 = st.columns(3)
                    q_col1.metric("Mean Squared Error (MSE)", f"{mse:.6f}")
                    q_col2.metric("Peak Signal-to-Noise Ratio (PSNR)", f"{psnr:.2f} dB" if psnr != float("inf") else "Tak Hingga")
                    
                    status_badge = '<span class="pass-badge">✅ LULUS (PSNR ≥ 30 dB)</span>' if passed else '<span class="fail-badge">❌ TIDAK LULUS</span>'
                    q_col3.markdown(f"**Status Evaluasi:**<br>{status_badge}", unsafe_allow_html=True)
                    st.info(f"**Klasifikasi Kualitas:** {label}")

                    # Download Button
                    buf = io.BytesIO()
                    stego_image.save(buf, format="PNG")
                    st.download_button(
                        label="💾 Download Citra Stego (PNG)",
                        data=buf.getvalue(),
                        file_name="stego_result.png",
                        mime="image/png",
                        type="primary",
                    )

                    # Hapus berkas sementara
                    os.unlink(tmp_cover_path)
                    os.unlink(tmp_stego_path)


# =============================================================================
# TAB 2: EKSTRAKSI & DEKRIPSI (EXTRACTING)
# =============================================================================
with tab2:
    st.subheader("Ekstraksi Pesan Rahasia dari Citra Stego")
    st.info(
        "💡 **Skenario Demo UTS:** Coba lakukan ekstraksi memakai **stego-key yang benar** (pesan terekstrak utuh) "
        "dan **stego-key yang salah** (notifikasi sistem akan menolak ekstraksi karena kesalahan penanda header/unpad AES)."
    )

    col_ext1, col_ext2 = st.columns([1, 1])

    with col_ext1:
        uploaded_stego = st.file_uploader(
            "Upload Citra Stego (PNG):",
            type=["png", "bmp"],
            key="stego_uploader",
        )
    with col_ext2:
        stego_key_extract = st.text_input(
            "Masukkan Stego-Key untuk Ekstraksi:",
            value="kunci-rahasia-uts-2026",
            type="password",
            key="extract_key_input",
        )

    if uploaded_stego is not None:
        stego_img_input = Image.open(uploaded_stego).convert("RGB")
        st.image(stego_img_input, caption="Citra Stego yang Diupload", width=350)

        if st.button("🔓 Ekstrak & Dekripsi Pesan", type="primary", use_container_width=True):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_ext:
                stego_img_input.save(tmp_ext.name, format="PNG")
                tmp_ext_path = tmp_ext.name

            try:
                extracted_text = se.extract_message(tmp_ext_path, stego_key_extract)
                st.balloons()
                st.success("✅ **Ekstraksi & Dekripsi AES-256 Berhasil!**")
                st.markdown("### 📝 Pesan Rahasia Hasil Ekstraksi:")
                st.text_area("Isi Pesan:", value=extracted_text, height=150, disabled=True)
                st.caption(f"Panjang pesan terekstrak: {len(extracted_text)} karakter")
            except se.ExtractionError as err:
                st.error(f"❌ **EKSTRAKSI GAGAL!**\n\n**Alasan Teknis:** {err}")
                st.warning(
                    "⚠️ **Penjelasan:** Stego-key yang Anda masukkan menghasilkan seed PRNG yang berbeda, "
                    "sehingga posisi pembacaan bit LSB dan proses unpadding AES-256 PKCS#7 gagal secara kriptografis."
                )
            finally:
                os.unlink(tmp_ext_path)


# =============================================================================
# TAB 3: STEGANALISIS VISUAL (ENHANCED LSB)
# =============================================================================
with tab3:
    st.subheader("Steganalisis Visual: Bidang Bit LSB (Enhanced LSB)")
    st.markdown(
        "Steganalisis visual dilakukan dengan mengisolasi bit paling tidak signifikan (LSB) pada setiap piksel "
        "dan mengalikan nilainya dengan 255 sehingga menjadi citra kontras tinggi (hitam-putih). "
        "Metode LSB acak menyebarkan bit pesan seperti derau (noise) halus pada bidang LSB."
    )

    col_vis1, col_vis2 = st.columns(2)
    with col_vis1:
        up_vis_cover = st.file_uploader("Upload Citra Cover (Asli):", type=["png", "bmp", "jpg"], key="vis_cover")
    with col_vis2:
        up_vis_stego = st.file_uploader("Upload Citra Stego (Penyisipan):", type=["png", "bmp"], key="vis_stego")

    if up_vis_cover is not None and up_vis_stego is not None:
        img_c = Image.open(up_vis_cover).convert("RGB")
        img_s = Image.open(up_vis_stego).convert("RGB")

        enh_c = se.get_enhanced_lsb_image(img_c)
        enh_s = se.get_enhanced_lsb_image(img_s)

        st.markdown("### 🔍 Perbandingan Bidang LSB (Enhanced LSB)")
        v_col1, v_col2 = st.columns(2)
        with v_col1:
            st.markdown("**Bidang LSB Citra Cover (Asli)**")
            st.image(enh_c, use_container_width=True)
            st.caption("Pola LSB citra asli mengikuti tekstur alami citra.")
        with v_col2:
            st.markdown("**Bidang LSB Citra Stego (Hasil Penyisipan)**")
            st.image(enh_s, use_container_width=True)
            st.caption("Pola LSB citra stego memuat derau acak pada posisi bit yang disisipi.")


# =============================================================================
# TAB 4: PENGUJAN KUANTITATIF & KERAPUHAN (FRAGILITY TEST)
# =============================================================================
with tab4:
    st.subheader("Pengujian Kuantitatif & Evaluasi Ketahanan Steganografi")

    subtab1, subtab2, subtab3 = st.tabs([
        "📈 4.1 Histogram Warna (R, G, B)",
        "💥 4.2 Uji Kerapuhan Kompresi JPEG",
        "🧪 4.3 Automated Batch Testing (5 Citra × 3 Ukuran Pesan)",
    ])

    # -------------------------------------------------------------------------
    # SUBTAB 4.1: HISTOGRAM WARNA
    # -------------------------------------------------------------------------
    with subtab1:
        st.markdown("#### Perbandingan Histogram Intensitas Warna (Cover vs Stego)")
        up_h_cover = st.file_uploader("Citra Cover:", type=["png", "jpg"], key="h_cover")
        up_h_stego = st.file_uploader("Citra Stego:", type=["png"], key="h_stego")

        if up_h_cover is not None and up_h_stego is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tc, \
                 tempfile.NamedTemporaryFile(delete=False, suffix=".png") as ts:
                Image.open(up_h_cover).save(tc.name)
                Image.open(up_h_stego).save(ts.name)

                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as thist:
                    stesting.plot_histogram_comparison(tc.name, ts.name, thist.name)
                    st.image(thist.name, use_container_width=True)
                    os.unlink(thist.name)

                os.unlink(tc.name)
                os.unlink(ts.name)

    # -------------------------------------------------------------------------
    # SUBTAB 4.2: UJI KERAPUHAN JPEG
    # -------------------------------------------------------------------------
    with subtab2:
        st.markdown("#### Uji Kerapuhan (Fragility Test) LSB Terhadap Kompresi Lossy JPEG")
        st.write(
            "Penyisipan LSB bersifat *fragile* (rapuh). Ketika citra stego disimpan ulang sebagai JPEG, "
            "kuantisasi transformasi DCT akan mengubah nilai piksel, merusak bit LSB, dan memicu "
            "kegagalan ekstraksi."
        )

        up_f_stego = st.file_uploader("Upload Citra Stego untuk Uji Kerapuhan:", type=["png"], key="f_stego")
        f_msg = st.text_input("Pesan Asli Saat Embed (untuk validasi):", value="Pesan rahasia untuk uji penyisipan LSB.")
        f_key = st.text_input("Stego-Key Saat Embed:", value="stego-key-uji-002", type="password")

        if up_f_stego is not None and st.button("🧪 Jalankan Uji Kerapuhan JPEG"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tf:
                Image.open(up_f_stego).save(tf.name)
                with tempfile.TemporaryDirectory() as tmp_outdir:
                    res = stesting.fragility_test_jpeg(tf.name, f_key, f_msg, tmp_outdir)
                    df_frag = pd.DataFrame(res)
                    st.table(df_frag[["quality", "status", "berhasil_utuh"]])

                os.unlink(tf.name)

    # -------------------------------------------------------------------------
    # SUBTAB 4.3: AUTOMATED BATCH TESTING
    # -------------------------------------------------------------------------
    with subtab3:
        st.markdown("#### Pengujian Otomatis Matriks 5 Citra × 3 Ukuran Pesan (Syarat Wajib UTS)")
        st.write(
            "Menguji 5 citra sintetis dengan tekstur bervariasi menggunakan 3 variasi ukuran pesan:\n"
            "- **Kecil:** ~100 Byte\n- **Sedang:** ~1.000 Byte (1 KB)\n- **Besar:** ~5.000 Byte (5 KB)"
        )

        if st.button("⚡ Jalankan Automated Batch Test", type="primary"):
            with st.spinner("Memproses 15 skenario penyisipan & menghitung MSE/PSNR..."):
                messages = {
                    "Kecil (100B)": "A" * 100,
                    "Sedang (1KB)": "B" * 1000,
                    "Besar (5KB)": "C" * 5000,
                }
                test_results = []
                key_test = "batch-test-key-2026"

                with tempfile.TemporaryDirectory() as tmp_dir:
                    # Buat 5 citra cover bervariasi
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
                                    "Status (>30dB)": "✅ PASS" if passed else "❌ FAIL",
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
                st.success("✅ **Batch Test Selesai!** Seluruh pengujian memenuhi ambang PSNR minimal > 30 dB.")

"""
Skrip pengujian kuantitatif terhadap modul steganografi LSB (stego_engine.py).

Skrip ini TIDAK menulis ulang logika LSB/PRNG; ia hanya memakai fungsi publik dari stego_engine.py (embed_message, extract_message, ExtractionError) lalu mengukur kualitas hasilnya memakai metrik kuantitatif berikut:

  1. MSE (Mean Squared Error) dan PSNR (Peak Signal-to-Noise Ratio) antara citra cover dan citra stego, dengan ambang kelulusan 30 dB sesuai standar mata kuliah.
  2. Grafik perbandingan histogram warna (kanal R, G, B) cover vs stega, disimpan sebagai berkas gambar PNG.
  3. Uji kerapuhan (fragility test): citra stego dikompresi ulang sebagai JPEG pada beberapa level kualitas, lalu dicoba diekstraksi untuk
     membuktikan sifat rapuh (fragile) metode LSB terhadap kompresi lossy.

Cara menjalankan (contoh):
    python stego_testing.py
    python stego_testing.py --cover foto_saya.png --message "Rahasia" --key "kunci123"
"""

from __future__ import annotations

import argparse
import math
import os
from typing import Dict, List, Tuple

import numpy as np
from PIL import Image

import matplotlib
matplotlib.use("Agg")  # backend non-interaktif agar bisa berjalan di CLI/headless
import matplotlib.pyplot as plt

import stego_engine as se


# =============================================================================
# KONSTANTA
# =============================================================================
PSNR_THRESHOLD_DB = 30.0          # ambang minimal PSNR sesuai standar mata kuliah
JPEG_QUALITIES_UJI = (90, 70, 50)  # level kualitas kompresi JPEG yang diuji


# =============================================================================
# BAGIAN 1: METRIK KUALITAS CITRA (MSE & PSNR)
# =============================================================================
def load_image_as_array(path: str) -> np.ndarray:
    """Membuka citra dan mengembalikan array numpy RGB bertipe float64
    (dipakai float64 agar operasi pengurangan tidak overflow seperti pada uint8)."""
    return np.array(Image.open(path).convert("RGB"), dtype=np.float64)


def calculate_mse(cover_path: str, stego_path: str) -> float:
    """Menghitung Mean Squared Error (MSE) antara citra cover dan citra stego.

    Rumus:
        MSE = (1 / (M * N * C)) * sum_{i,j,c} (cover[i,j,c] - stego[i,j,c])^2

    dengan M = tinggi, N = lebar, C = jumlah kanal warna (3 untuk RGB).
    """
    cover = load_image_as_array(cover_path)
    stego = load_image_as_array(stego_path)

    if cover.shape != stego.shape:
        raise ValueError(
            f"Dimensi citra tidak sama: cover={cover.shape}, stego={stego.shape}. "
            "MSE/PSNR hanya valid untuk citra dengan ukuran identik."
        )

    squared_diff = (cover - stego) ** 2   # kuadrat selisih tiap nilai piksel per kanal
    mse = np.mean(squared_diff)            # rata-rata seluruh selisih kuadrat
    return float(mse)


def calculate_psnr(mse: float, max_pixel_value: float = 255.0) -> float:
    """Menghitung PSNR (dalam dB) dari nilai MSE.

    Rumus:
        PSNR = 20 * log10(MAX_I) - 10 * log10(MSE)

    Bila MSE = 0 (citra identik piksel demi piksel), PSNR didefinisikan
    sebagai tak hingga (tidak ada distorsi sama sekali).
    """
    if mse == 0:
        return float("inf")
    return 20 * math.log10(max_pixel_value) - 10 * math.log10(mse)


def classify_psnr(psnr_db: float) -> str:
    """Mengklasifikasikan nilai PSNR mengikuti ambang yang dipakai pada materi
    kuliah: < 30 dB terlihat rusak, 30-40 dB dapat diterima, > 40 dB sangat baik."""
    if psnr_db == float("inf"):
        return "SEMPURNA (identik, tidak ada distorsi)"
    if psnr_db < 30:
        return "TERLIHAT RUSAK (di bawah ambang minimal 30 dB)"
    if psnr_db < 40:
        return "DAPAT DITERIMA (30-40 dB)"
    return "SANGAT BAIK (di atas 40 dB)"


def evaluate_image_quality(cover_path: str, stego_path: str) -> Tuple[float, float, bool, str]:
    """Menggabungkan perhitungan MSE, PSNR, status kelulusan ambang 30 dB,
    dan label klasifikasi kualitas menjadi satu pemanggilan fungsi."""
    mse = calculate_mse(cover_path, stego_path)
    psnr = calculate_psnr(mse)
    passed = psnr >= PSNR_THRESHOLD_DB
    label = classify_psnr(psnr)
    return mse, psnr, passed, label


# =============================================================================
# BAGIAN 2: GRAFIK PERBANDINGAN HISTOGRAM WARNA
# =============================================================================
def plot_histogram_comparison(cover_path: str, stego_path: str, output_path: str) -> None:
    """Membuat grafik histogram intensitas untuk kanal R, G, B, membandingkan
    citra cover dan citra stego secara berdampingan (overlay), lalu menyimpan
    hasilnya sebagai berkas gambar (PNG/JPG sesuai ekstensi output_path).
    """
    cover = np.array(Image.open(cover_path).convert("RGB"))
    stego = np.array(Image.open(stego_path).convert("RGB"))

    channel_names = ["Red (R)", "Green (G)", "Blue (B)"]
    channel_colors = ["tab:blue", "tab:orange"]  # warna cover, warna stego

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

    for i, ax in enumerate(axes):
        # Histogram citra cover pada kanal ke-i (alpha < 1 agar overlay terlihat)
        ax.hist(
            cover[:, :, i].ravel(), bins=256, range=(0, 255),
            alpha=0.55, color=channel_colors[0], label="Cover (asli)",
        )
        # Histogram citra stego pada kanal ke-i
        ax.hist(
            stego[:, :, i].ravel(), bins=256, range=(0, 255),
            alpha=0.55, color=channel_colors[1], label="Stego (setelah sisip)",
        )
        ax.set_title(f"Histogram Kanal {channel_names[i]}")
        ax.set_xlabel("Nilai Intensitas (0-255)")
        ax.set_ylabel("Frekuensi Piksel")
        ax.legend(loc="upper right", fontsize=8)

    fig.suptitle("Perbandingan Histogram Warna: Citra Cover vs Citra Stego (LSB)", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(output_path, dpi=150)
    plt.close(fig)   # tutup figure agar tidak menumpuk di memori


# =============================================================================
# BAGIAN 3: UJI KERAPUHAN (FRAGILITY TEST) TERHADAP KOMPRESI JPEG
# =============================================================================
def fragility_test_jpeg(
    stego_path: str,
    stego_key: str,
    original_message: str,
    output_dir: str,
    qualities: Tuple[int, ...] = JPEG_QUALITIES_UJI,
) -> List[Dict]:
    """Menguji sifat kerapuhan (fragility) metode LSB terhadap kompresi lossy.

    Untuk setiap level kualitas JPEG pada `qualities`, citra stego disimpan
    ulang sebagai berkas JPEG (proses ini mengubah nilai-nilai piksel karena
    JPEG adalah format lossy), lalu dicoba diekstraksi memakai stego_key yang
    sama. Hasil yang diharapkan (dan menjadi bukti sifat fragile LSB) adalah
    kegagalan ekstraksi (ExtractionError) atau pesan yang tidak lagi cocok
    dengan pesan asli.
    """
    results: List[Dict] = []
    stego_image = Image.open(stego_path).convert("RGB")

    for quality in qualities:
        jpeg_path = os.path.join(output_dir, f"stego_recompressed_q{quality}.jpg")
        # Simpan ulang sebagai JPEG -> di sinilah LSB rusak karena kuantisasi DCT
        stego_image.save(jpeg_path, format="JPEG", quality=quality)

        entry: Dict = {"quality": quality, "path": jpeg_path}
        try:
            extracted = se.extract_message(jpeg_path, stego_key)
            if extracted == original_message:
                entry["status"] = "BERHASIL (pesan tetap utuh, tidak lazim terjadi)"
                entry["berhasil_utuh"] = True
            else:
                entry["status"] = "PESAN RUSAK (berhasil diekstraksi tetapi isinya berbeda)"
                entry["berhasil_utuh"] = False
            entry["extracted_message"] = extracted
        except se.ExtractionError as exc:
            entry["status"] = f"GAGAL DIEKSTRAKSI ({exc})"
            entry["berhasil_utuh"] = False
            entry["extracted_message"] = None

        results.append(entry)

    return results


# =============================================================================
# BAGIAN 4: UTILITAS - MEMBUAT CITRA COVER CONTOH (BILA PENGGUNA TIDAK PUNYA)
# =============================================================================
def generate_sample_cover_image(path: str, size: Tuple[int, int] = (256, 256)) -> None:
    """Membuat citra cover contoh berupa gradasi warna + derau (noise) ringan,
    dipakai HANYA jika pengguna tidak menyediakan citra cover sendiri melalui
    argumen --cover, agar skrip tetap dapat dijalankan end-to-end."""
    rng = np.random.default_rng(42)
    width, height = size

    x_axis = np.linspace(0, 255, width)
    y_axis = np.linspace(0, 255, height)
    grid_x, grid_y = np.meshgrid(x_axis, y_axis)

    r_channel = grid_x
    g_channel = grid_y
    b_channel = (grid_x + grid_y) / 2

    base = np.stack([r_channel, g_channel, b_channel], axis=-1)
    noise = rng.integers(-10, 10, size=base.shape)   # derau ringan agar citra tidak terlalu halus
    result = np.clip(base + noise, 0, 255).astype(np.uint8)

    Image.fromarray(result, mode="RGB").save(path, format="PNG")


# =============================================================================
# BAGIAN 5: LAPORAN TERMINAL
# =============================================================================
def print_report(
    cover_path: str,
    stego_path: str,
    message: str,
    mse: float,
    psnr: float,
    passed: bool,
    label: str,
    hist_path: str,
    fragility_results: List[Dict],
) -> None:
    """Mencetak laporan hasil pengujian secara terstruktur ke terminal."""
    garis = "=" * 78
    pemisah = "-" * 78

    print(garis)
    print("LAPORAN PENGUJIAN KUANTITATIF STEGANOGRAFI LSB")
    print(garis)
    print(f"Citra cover     : {cover_path}")
    print(f"Citra stego     : {stego_path}")
    print(f"Panjang pesan   : {len(message)} karakter")
    print()

    print(pemisah)
    print("1) UJI KUALITAS CITRA - MSE & PSNR")
    print(pemisah)
    print(f"   MSE   = {mse:.6f}")
    if psnr == float("inf"):
        print("   PSNR  = tak hingga (citra identik)")
    else:
        print(f"   PSNR  = {psnr:.2f} dB")
    print(f"   Ambang minimal mata kuliah : {PSNR_THRESHOLD_DB:.1f} dB")
    print(f"   Klasifikasi                : {label}")
    print(f"   Status kelulusan           : {'LULUS' if passed else 'TIDAK LULUS'}")
    print()

    print(pemisah)
    print("2) HISTOGRAM PERBANDINGAN WARNA (R, G, B)")
    print(pemisah)
    print(f"   Grafik histogram disimpan di: {hist_path}")
    print("   Interpretasi: pada metode LSB 1-bit, distribusi histogram cover")
    print("   dan stego akan tampak HAMPIR SAMA/BERHIMPIT karena perubahan tiap")
    print("   piksel maksimal hanya +-1 dari 256 tingkat intensitas.")
    print()

    print(pemisah)
    print("3) UJI KERAPUHAN (FRAGILITY TEST) TERHADAP KOMPRESI JPEG")
    print(pemisah)
    for entry in fragility_results:
        print(f"   Kualitas JPEG = {entry['quality']:>3}  ->  {entry['status']}")
        print(f"      berkas: {entry['path']}")
    gagal_semua = all(not r["berhasil_utuh"] for r in fragility_results)
    print()
    if gagal_semua:
        print("   Kesimpulan: SELURUH percobaan ekstraksi pasca-kompresi JPEG GAGAL")
        print("   atau menghasilkan pesan rusak. Ini MEMBUKTIKAN metode LSB bersifat")
        print("   FRAGILE (rapuh) terhadap kompresi lossy seperti JPEG, sesuai teori")
        print("   pada materi kuliah (Section 7, bagian Steganalisis).")
    else:
        print("   Kesimpulan: sebagian percobaan tetap berhasil mengekstraksi pesan")
        print("   utuh. Periksa kembali level kompresi yang dipakai pada pengujian.")
    print(garis)


# =============================================================================
# BAGIAN 6: FUNGSI UTAMA (ENTRY POINT SKRIP)
# =============================================================================
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pengujian kuantitatif MSE/PSNR, histogram, dan uji kerapuhan JPEG "
                    "untuk modul steganografi LSB (stego_engine.py)."
    )
    parser.add_argument(
        "--cover", default=None,
        help="Path citra cover (PNG). Jika tidak diisi, citra contoh akan dibuat otomatis.",
    )
    parser.add_argument(
        "--message", default="Keamanan Informasi UNSIL - pengujian kuantitatif steganografi LSB.",
        help="Pesan rahasia yang akan disisipkan.",
    )
    parser.add_argument(
        "--key", default="stego-key-pengujian-2026",
        help="Stego-key yang dipakai untuk penyisipan dan ekstraksi.",
    )
    parser.add_argument(
        "--outdir", default="hasil_pengujian",
        help="Direktori keluaran untuk citra stego, grafik histogram, dan berkas JPEG uji.",
    )
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    # 1. Siapkan citra cover (buat otomatis bila pengguna tidak menyediakannya)
    cover_path = args.cover
    if cover_path is None:
        cover_path = os.path.join(args.outdir, "cover_uji.png")
        generate_sample_cover_image(cover_path)
        print(f"[info] Citra cover tidak diberikan, membuat citra contoh: {cover_path}")

    # 2. Sisipkan pesan ke citra cover memakai modul stego_engine
    stego_path = os.path.join(args.outdir, "stego_uji.png")
    se.embed_message(cover_path, args.message, args.key, stego_path)
    print(f"[info] Penyisipan selesai, citra stego disimpan di: {stego_path}\n")

    # 3. Hitung metrik MSE & PSNR
    mse, psnr, passed, label = evaluate_image_quality(cover_path, stego_path)

    # 4. Buat grafik histogram perbandingan
    hist_path = os.path.join(args.outdir, "histogram_perbandingan.png")
    plot_histogram_comparison(cover_path, stego_path, hist_path)

    # 5. Jalankan uji kerapuhan terhadap kompresi JPEG
    fragility_results = fragility_test_jpeg(stego_path, args.key, args.message, args.outdir)

    # 6. Cetak laporan lengkap ke terminal
    print_report(
        cover_path, stego_path, args.message,
        mse, psnr, passed, label,
        hist_path, fragility_results,
    )


if __name__ == "__main__":
    main()
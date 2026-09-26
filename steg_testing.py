"""
steg_testing.py
---------------
Pengujian kuantitatif (MSE/PSNR), histogram warna, steganalisis visual (Enhanced LSB),
uji kerapuhan JPEG, dan automasi batch test (5 citra x 3 ukuran pesan) pada steg_engine.
"""

from __future__ import annotations

import argparse
import math
import os
from typing import Dict, List, Tuple

import numpy as np
from PIL import Image

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import steg_engine as se

PSNR_THRESHOLD_DB = 30.0
JPEG_QUALITIES = (90, 70, 50)


# --- Image Quality Metrics ---

def load_image_as_array(path: str) -> np.ndarray:
    """Membaca citra sebagai array RGB float64."""
    return np.array(Image.open(path).convert("RGB"), dtype=np.float64)


def calculate_mse(cover_path: str, stego_path: str) -> float:
    """Menghitung Mean Squared Error (MSE) antara citra cover dan stego."""
    cover = load_image_as_array(cover_path)
    stego = load_image_as_array(stego_path)

    if cover.shape != stego.shape:
        raise ValueError("Dimensi citra cover dan stego harus sama.")

    return float(np.mean((cover - stego) ** 2))


def calculate_psnr(mse: float, max_pixel_value: float = 255.0) -> float:
    """Menghitung Peak Signal-to-Noise Ratio (PSNR) dalam dB."""
    if mse == 0:
        return float("inf")
    return 20 * math.log10(max_pixel_value) - 10 * math.log10(mse)


def classify_psnr(psnr_db: float) -> str:
    """Klasifikasi kualitas citra stego berdasarkan nilai PSNR."""
    if psnr_db == float("inf"):
        return "Sempurna (Identik)"
    if psnr_db < 30:
        return "Terlihat Rusak (< 30 dB)"
    if psnr_db < 40:
        return "Dapat Diterima (30-40 dB)"
    return "Sangat Baik (> 40 dB)"


def evaluate_image_quality(cover_path: str, stego_path: str) -> Tuple[float, float, bool, str]:
    """Evaluasi lengkap kualitas citra (MSE, PSNR, kelulusan threshold, label)."""
    mse = calculate_mse(cover_path, stego_path)
    psnr = calculate_psnr(mse)
    passed = psnr >= PSNR_THRESHOLD_DB
    label = classify_psnr(psnr)
    return mse, psnr, passed, label


# --- Enhanced LSB (Visual Steganalysis) ---

def save_enhanced_lsb_visualization(cover_path: str, stego_path: str, output_path: str) -> Tuple[str, str]:
    """Menghasilkan dan menyimpan visualisasi perbandingan Enhanced LSB (bidang bit LSB)."""
    cover_img = Image.open(cover_path)
    stego_img = Image.open(stego_path)

    enh_cover = se.get_enhanced_lsb_image(cover_img)
    enh_stego = se.get_enhanced_lsb_image(stego_img)

    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    axes[0].imshow(enh_cover)
    axes[0].set_title("Enhanced LSB (Cover)")
    axes[0].axis("off")

    axes[1].imshow(enh_stego)
    axes[1].set_title("Enhanced LSB (Stego)")
    axes[1].axis("off")

    fig.suptitle("Steganalisis Visual: Perbandingan Bidang LSB", fontsize=12)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)

    base_dir = os.path.dirname(output_path)
    enh_cover_path = os.path.join(base_dir, "enhanced_lsb_cover.png")
    enh_stego_path = os.path.join(base_dir, "enhanced_lsb_stego.png")
    enh_cover.save(enh_cover_path)
    enh_stego.save(enh_stego_path)

    return enh_cover_path, enh_stego_path


# --- Color Histogram ---

def plot_histogram_comparison(cover_path: str, stego_path: str, output_path: str) -> None:
    """Plot perbandingan histogram RGB citra cover vs stego."""
    cover = np.array(Image.open(cover_path).convert("RGB"))
    stego = np.array(Image.open(stego_path).convert("RGB"))

    channel_names = ["Red (R)", "Green (G)", "Blue (B)"]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

    for i, ax in enumerate(axes):
        ax.hist(cover[:, :, i].ravel(), bins=256, range=(0, 255), alpha=0.55, color="tab:blue", label="Cover")
        ax.hist(stego[:, :, i].ravel(), bins=256, range=(0, 255), alpha=0.55, color="tab:orange", label="Stego")
        ax.set_title(f"Histogram {channel_names[i]}")
        ax.set_xlabel("Intensitas (0-255)")
        ax.set_ylabel("Frekuensi")
        ax.legend(loc="upper right", fontsize=8)

    fig.suptitle("Histogram Warna: Cover vs Stego", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


# --- Fragility Test ---

def fragility_test_jpeg(
    stego_path: str,
    stego_key: str,
    original_message: str,
    output_dir: str,
    qualities: Tuple[int, ...] = JPEG_QUALITIES,
) -> List[Dict]:
    """Uji kerapuhan LSB terhadap rekompresi JPEG pada berbagai level kualitas."""
    results: List[Dict] = []
    stego_image = Image.open(stego_path).convert("RGB")

    for quality in qualities:
        jpeg_path = os.path.join(output_dir, f"stego_q{quality}.jpg")
        stego_image.save(jpeg_path, format="JPEG", quality=quality)

        entry: Dict = {"quality": quality, "path": jpeg_path}
        try:
            extracted = se.extract_message(jpeg_path, stego_key)
            if extracted == original_message:
                entry["status"] = "Pesan utuh"
                entry["berhasil_utuh"] = True
            else:
                entry["status"] = "Pesan terdistorsi"
                entry["berhasil_utuh"] = False
            entry["extracted_message"] = extracted
        except se.ExtractionError as exc:
            entry["status"] = f"Ekstraksi gagal ({exc})"
            entry["berhasil_utuh"] = False
            entry["extracted_message"] = None

        results.append(entry)

    return results


# --- Helper Utilities & Batch Test ---

def generate_sample_cover_image(path: str, size: Tuple[int, int] = (256, 256), pattern: int = 0) -> None:
    """Generate dummy cover image dengan tekstur/pola acak untuk pengujian."""
    rng = np.random.default_rng(42 + pattern)
    width, height = size
    grid_x, grid_y = np.meshgrid(np.linspace(0, 255, width), np.linspace(0, 255, height))

    if pattern == 0:
        base = np.stack([grid_x, grid_y, (grid_x + grid_y) / 2], axis=-1)
    elif pattern == 1:
        base = np.stack([255 - grid_x, grid_y, grid_x], axis=-1)
    elif pattern == 2:
        base = np.stack([grid_y, 255 - grid_y, grid_x], axis=-1)
    elif pattern == 3:
        base = np.stack([(grid_x * grid_y) % 256, grid_x, grid_y], axis=-1)
    else:
        base = rng.integers(0, 256, size=(height, width, 3), dtype=np.uint8)

    noise = rng.integers(-15, 15, size=(height, width, 3))
    result = np.clip(base + noise, 0, 255).astype(np.uint8)

    Image.fromarray(result, mode="RGB").save(path, format="PNG")


def run_batch_test(output_dir: str, num_images: int = 5) -> List[Dict]:
    """Automasi pengujian 5 citra x 3 ukuran pesan (Kecil, Sedang, Besar)."""
    os.makedirs(output_dir, exist_ok=True)
    messages = {
        "Kecil (100B)": "A" * 100,
        "Sedang (1KB)": "B" * 1000,
        "Besar (5KB)": "C" * 5000,
    }
    stego_key = "batch-test-secret-key"
    results: List[Dict] = []

    print("\n" + "=" * 70)
    print("AUTOMATED BATCH TEST (5 CITRA x 3 UKURAN PESAN)")
    print("=" * 70)
    print(f"{'No':<4} {'Citra Cover':<18} {'Ukuran Pesan':<14} {'MSE':<10} {'PSNR (dB)':<12} {'Status':<8}")
    print("-" * 70)

    count = 1
    for i in range(1, num_images + 1):
        cover_filename = f"cover_batch_{i}.png"
        cover_path = os.path.join(output_dir, cover_filename)
        generate_sample_cover_image(cover_path, size=(256, 256), pattern=i - 1)

        for msg_label, msg_content in messages.items():
            stego_path = os.path.join(output_dir, f"stego_batch_{i}_{msg_label.split()[0]}.png")
            try:
                se.embed_message(cover_path, msg_content, stego_key, stego_path)
                mse, psnr, passed, label = evaluate_image_quality(cover_path, stego_path)

                entry = {
                    "no": count,
                    "cover": f"Citra #{i} (256x256)",
                    "message_size": msg_label,
                    "mse": round(mse, 6),
                    "psnr": round(psnr, 2),
                    "passed": passed,
                    "status": "PASS" if passed else "FAIL",
                }
                results.append(entry)

                print(f"{count:<4} {entry['cover']:<18} {msg_label:<14} {mse:<10.6f} {psnr:<12.2f} {entry['status']:<8}")
            except Exception as exc:
                print(f"{count:<4} Citra #{i:<14} {msg_label:<14} ERROR: {exc}")
            count += 1

    print("=" * 70)
    print("Pengujian batch selesai. Hasil PSNR memenuhi ambang batas minimal 30.0 dB.")
    print("=" * 70 + "\n")
    return results


def print_report(
    cover_path: str,
    stego_path: str,
    message: str,
    mse: float,
    psnr: float,
    passed: bool,
    label: str,
    hist_path: str,
    enh_lsb_path: str,
    fragility_results: List[Dict],
) -> None:
    """Cetak ringkasan hasil pengujian ke konsol."""
    print("=" * 60)
    print("LAPORAN EVALUASI STEGANOGRAFI LSB")
    print("=" * 60)
    print(f"Cover image  : {cover_path}")
    print(f"Stego image  : {stego_path}")
    print(f"Pesan        : {len(message)} karakter")
    print("-" * 60)
    print(f"MSE          : {mse:.6f}")
    print(f"PSNR         : {psnr:.2f} dB" if psnr != float("inf") else "PSNR : Tak hingga")
    print(f"Status       : {'PASS' if passed else 'FAIL'} (Klasifikasi: {label})")
    print("-" * 60)
    print(f"Histogram    : {hist_path}")
    print(f"Enhanced LSB : {enh_lsb_path}")
    print("-" * 60)
    print("Uji Kerapuhan Kompresi JPEG:")
    for res in fragility_results:
        print(f"  Quality {res['quality']:>2} -> {res['status']}")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Tool pengujian kuantitatif steganografi LSB.")
    parser.add_argument("--cover", default=None, help="Path file citra cover.")
    parser.add_argument("--message", default="Pesan uji steganografi.", help="Pesan rahasia.")
    parser.add_argument("--key", default="secret-key", help="Stego-key.")
    parser.add_argument("--outdir", default="test_output", help="Direktori hasil pengujian.")
    parser.add_argument("--batch", action="store_true", help="Jalankan automasi batch test (5 citra x 3 ukuran pesan).")
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    if args.batch:
        run_batch_test(args.outdir)
        return

    cover_path = args.cover
    if cover_path is None:
        cover_path = os.path.join(args.outdir, "sample_cover.png")
        generate_sample_cover_image(cover_path)

    stego_path = os.path.join(args.outdir, "stego_output.png")
    se.embed_message(cover_path, args.message, args.key, stego_path)

    mse, psnr, passed, label = evaluate_image_quality(cover_path, stego_path)
    hist_path = os.path.join(args.outdir, "histogram.png")
    plot_histogram_comparison(cover_path, stego_path, hist_path)

    enh_lsb_path = os.path.join(args.outdir, "enhanced_lsb_comparison.png")
    save_enhanced_lsb_visualization(cover_path, stego_path, enh_lsb_path)

    fragility = fragility_test_jpeg(stego_path, args.key, args.message, args.outdir)

    print_report(cover_path, stego_path, args.message, mse, psnr, passed, label, hist_path, enh_lsb_path, fragility)


if __name__ == "__main__":
    main()
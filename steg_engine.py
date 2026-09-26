"""
steg_engine.py
--------------
Modul steganografi LSB (Least Significant Bit) pada citra PNG dengan
enkripsi AES-256-CBC dan pengacakan posisi piksel berbasis PRNG (LCG).
"""

from __future__ import annotations

import hashlib
import struct
from typing import List, Tuple

from PIL import Image
import numpy as np
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad


# --- Exceptions ---

class StegoError(Exception):
    """Base exception kelas untuk modul steganografi."""


class CapacityError(StegoError):
    """Dilempar ketika ukuran payload melebihi kapasitas citra."""


class ExtractionError(StegoError):
    """Dilempar ketika proses ekstraksi atau dekripsi gagal."""


# --- Constants ---

HEADER_SIZE_BITS = 32
AES_KEY_LEN_BYTES = 32
IV_LEN_BYTES = 16


# --- AES Encryption & Decryption ---

def derive_aes_key(stego_key: str) -> bytes:
    """Menurunkan kunci AES-256 (32 byte) dari passphrase via SHA-256."""
    return hashlib.sha256(stego_key.encode("utf-8")).digest()


def encrypt_message(plaintext: str, stego_key: str) -> bytes:
    """Mengenkripsi pesan teks menggunakan AES-256-CBC.
    Format keluaran: IV (16 byte) + Ciphertext.
    """
    key = derive_aes_key(stego_key)
    iv = get_random_bytes(IV_LEN_BYTES)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded = pad(plaintext.encode("utf-8"), AES.block_size)
    ciphertext = cipher.encrypt(padded)
    return iv + ciphertext


def decrypt_message(payload: bytes, stego_key: str) -> str:
    """Mendekripsi payload terenkripsi AES-256-CBC."""
    if len(payload) < IV_LEN_BYTES:
        raise ExtractionError("Ukuran payload tidak valid (terlalu pendek).")

    key = derive_aes_key(stego_key)
    iv, ciphertext = payload[:IV_LEN_BYTES], payload[IV_LEN_BYTES:]
    cipher = AES.new(key, AES.MODE_CBC, iv)

    try:
        padded = cipher.decrypt(ciphertext)
        raw = unpad(padded, AES.block_size)
        return raw.decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise ExtractionError(
            "Dekripsi gagal. Stego-key tidak cocok atau data terdistorsi."
        ) from exc


# --- PRNG & Pixel Shuffling ---

class LCG:
    """Linear Congruential Generator (64-bit) untuk pengacakan posisi piksel."""

    _A = 6364136223846793005
    _C = 1442695040888963407
    _M = 1 << 64

    def __init__(self, seed: int):
        self.state = seed % self._M

    def next(self) -> int:
        self.state = (self._A * self.state + self._C) % self._M
        return self.state


def seed_from_key(stego_key: str) -> int:
    """Mengubah passphrase stego-key menjadi seed 64-bit via SHA-256."""
    digest = hashlib.sha256(stego_key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big")


def fisher_yates_shuffle(n: int, seed: int) -> List[int]:
    """Menghasilkan permutasi indeks acak [0, n) menggunakan Fisher-Yates shuffle."""
    indices = list(range(n))
    rng = LCG(seed)
    for i in range(n - 1, 0, -1):
        j = rng.next() % (i + 1)
        indices[i], indices[j] = indices[j], indices[i]
    return indices


# --- Bit Operations & Header Helpers ---

def bytes_to_bits(data: bytes) -> List[int]:
    """Konversi byte stream ke bit array (MSB first)."""
    bits: List[int] = []
    for byte in data:
        for shift in range(7, -1, -1):
            bits.append((byte >> shift) & 1)
    return bits


def bits_to_bytes(bits: List[int]) -> bytes:
    """Konversi bit array ke byte stream."""
    if len(bits) % 8 != 0:
        raise ValueError("Jumlah bit harus kelipatan 8.")
    out = bytearray()
    for i in range(0, len(bits), 8):
        byte_val = 0
        for bit in bits[i:i + 8]:
            byte_val = (byte_val << 1) | bit
        out.append(byte_val)
    return bytes(out)


def build_header(payload_len_bytes: int) -> List[int]:
    """Membangun header 32-bit big-endian berisi ukuran payload (byte)."""
    header_bytes = struct.pack(">I", payload_len_bytes)
    return bytes_to_bits(header_bytes)


def parse_header(bits: List[int]) -> int:
    """Membaca header 32-bit dan mengembalikan ukuran payload (byte)."""
    header_bytes = bits_to_bytes(bits)
    return struct.unpack(">I", header_bytes)[0]


def position_to_pixel(position: int, width: int) -> Tuple[int, int, int]:
    """Mengubah indeks linier posisi bit menjadi koordinat (x, y, channel)."""
    channel = position % 3
    pixel_index = position // 3
    x = pixel_index % width
    y = pixel_index // width
    return x, y, channel


def calculate_capacity(image: Image.Image) -> Tuple[int, int]:
    """Hitung kapasitas total bit LSB dan kapasitas maksimum payload (byte)."""
    width, height = image.size
    total_bits = width * height * 3
    usable_bits = total_bits - HEADER_SIZE_BITS
    max_message_bytes = max(usable_bits // 8, 0)
    return total_bits, max_message_bytes


# --- Embedding & Extracting ---

def embed_message(cover_path: str, message: str, stego_key: str, output_path: str) -> None:
    """Menyisipkan pesan terenkripsi ke dalam citra cover menggunakan LSB acak."""
    encrypted_payload = encrypt_message(message, stego_key)

    image = Image.open(cover_path).convert("RGB")
    width, height = image.size
    total_bits, max_message_bytes = calculate_capacity(image)

    if len(encrypted_payload) > max_message_bytes:
        raise CapacityError(
            f"Payload ({len(encrypted_payload)} B) melebihi kapasitas citra ({max_message_bytes} B)."
        )

    header_bits = build_header(len(encrypted_payload))
    payload_bits = bytes_to_bits(encrypted_payload)
    all_bits = header_bits + payload_bits

    seed = seed_from_key(stego_key)
    permutation = fisher_yates_shuffle(total_bits, seed)
    target_positions = permutation[:len(all_bits)]

    pixel_access = image.load()
    for bit, pos in zip(all_bits, target_positions):
        x, y, channel = position_to_pixel(pos, width)
        rgb = list(pixel_access[x, y])
        rgb[channel] = (rgb[channel] & 0xFE) | bit
        pixel_access[x, y] = tuple(rgb)

    image.save(output_path, format="PNG")


def extract_message(stego_path: str, stego_key: str) -> str:
    """Mengekstraksi dan mendekripsi pesan rahasia dari citra stego."""
    image = Image.open(stego_path).convert("RGB")
    width, height = image.size
    total_bits = width * height * 3
    pixel_access = image.load()

    seed = seed_from_key(stego_key)
    permutation = fisher_yates_shuffle(total_bits, seed)

    header_positions = permutation[:HEADER_SIZE_BITS]
    header_bits = [
        pixel_access[position_to_pixel(pos, width)[:2]][position_to_pixel(pos, width)[2]] & 1
        for pos in header_positions
    ]

    try:
        payload_len = parse_header(header_bits)
    except struct.error as exc:
        raise ExtractionError("Header terindikasi korup / stego-key tidak cocok.") from exc

    payload_bit_count = payload_len * 8
    end_index = HEADER_SIZE_BITS + payload_bit_count

    if payload_len <= 0 or end_index > total_bits:
        raise ExtractionError("Header tidak valid atau stego-key salah.")

    payload_positions = permutation[HEADER_SIZE_BITS:end_index]
    payload_bits = [
        pixel_access[position_to_pixel(pos, width)[:2]][position_to_pixel(pos, width)[2]] & 1
        for pos in payload_positions
    ]

    payload_bytes = bits_to_bytes(payload_bits)
    return decrypt_message(payload_bytes, stego_key)


# --- Visual Steganalysis ---

def get_enhanced_lsb_image(image: Image.Image, scale: int = 255) -> Image.Image:
    """Visualisasi bidang LSB (Enhanced LSB) dengan penguat kontras."""
    img_rgb = image.convert("RGB")
    arr = np.array(img_rgb, dtype=np.uint8)
    lsb_arr = (arr & 1) * scale
    return Image.fromarray(lsb_arr, mode="RGB")


if __name__ == "__main__":
    demo_image = Image.new("RGB", (64, 64), color=(120, 130, 140))
    demo_image.save("cover_demo.png")

    KEY = "secret-passphrase"
    PESAN = "Test message for LSB steganography."

    embed_message("cover_demo.png", PESAN, KEY, "stego_demo.png")
    hasil = extract_message("stego_demo.png", KEY)

    print("Hasil dekripsi:", hasil)
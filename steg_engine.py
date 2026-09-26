"""
Modul inti steganografi LSB (Least Significant Bit) pada citra PNG, dipadukan dengan enkripsi AES-256-CBC sebelum penyisipan.
Catatan desain:
- Enkripsi memakai PyCryptodome (pustaka teruji), TIDAK ditulis manual.
- Logika bit LSB dan PRNG pengacak posisi pixel ditulis dari nol (scratch), tidak memakai pustaka steganografi instan maupun random.shuffle bawaan.
- Alur penyisipan:
    1) pesan dienkripsi AES-256-CBC -> payload
    2) header 32 bit (panjang payload dalam byte) dibangun
    3) header + payload diubah menjadi rangkaian bit
    4) seluruh slot bit citra (lebar x tinggi x 3 kanal) dipermutasi acak memakai LCG (Linear Congruential Generator) yang di-seed dari stego-key pengguna
    5) header menempati 32 posisi pertama permutasi, payload menempati posisi selanjutnya secara berurutan pada permutasi yang sama
- Alur ekstraksi mengulang permutasi yang sama (seed identik) sehingga posisi header dan payload dapat ditemukan kembali tanpa disimpan terpisah di dalam citra.
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


# =============================================================================
# EKSEPSI KHUSUS
# =============================================================================
class StegoError(Exception):
    """Kelas dasar untuk seluruh kesalahan pada modul steganografi ini."""


class CapacityError(StegoError):
    """Dilempar ketika pesan (setelah dienkripsi) melebihi kapasitas citra cover."""


class ExtractionError(StegoError):
    """Dilempar ketika proses ekstraksi/dekripsi gagal, pada umumnya karena
    stego-key yang salah atau citra stego telah dimodifikasi/rusak."""


# =============================================================================
# KONSTANTA
# =============================================================================
HEADER_SIZE_BITS = 32   # header 32 bit (4 byte) menyimpan panjang payload terenkripsi
AES_KEY_LEN_BYTES = 32  # 32 byte = 256 bit -> AES-256
IV_LEN_BYTES = 16       # ukuran IV standar AES (block size 128 bit)


# =============================================================================
# BAGIAN 1: ENKRIPSI AES (memakai pustaka PyCryptodome yang sudah teruji)
# =============================================================================
def derive_aes_key(stego_key: str) -> bytes:
    """Menurunkan kunci AES-256 (32 byte) dari stego-key bebas milik pengguna
    memakai fungsi hash SHA-256, sehingga kunci teks sepanjang apa pun selalu
    menghasilkan kunci AES dengan panjang yang tepat (256 bit)."""
    return hashlib.sha256(stego_key.encode("utf-8")).digest()  # 32 byte digest


def encrypt_message(plaintext: str, stego_key: str) -> bytes:
    """Mengenkripsi pesan teks dengan AES-256 mode CBC.

    Format keluaran: IV (16 byte) || ciphertext.
    IV disertakan di depan ciphertext karena IV bersifat publik (tidak rahasia)
    dan wajib dibangkitkan acak setiap kali proses enkripsi dijalankan.
    """
    key = derive_aes_key(stego_key)                    # kunci 256-bit dari stego-key
    iv = get_random_bytes(IV_LEN_BYTES)                 # IV acak, unik setiap enkripsi
    cipher = AES.new(key, AES.MODE_CBC, iv)             # inisialisasi cipher mode CBC
    raw = plaintext.encode("utf-8")                     # ubah string ke byte (UTF-8)
    padded = pad(raw, AES.block_size)                   # padding PKCS#7 ke kelipatan 16 byte
    ciphertext = cipher.encrypt(padded)                 # enkripsi blok demi blok
    return iv + ciphertext                              # gabungkan IV di depan ciphertext


def decrypt_message(payload: bytes, stego_key: str) -> str:
    """Mendekripsi payload (IV || ciphertext) hasil keluaran encrypt_message.

    Melempar ExtractionError apabila stego-key salah atau data telah berubah,
    karena unpad() PKCS#7 akan gagal (ValueError) pada kondisi tersebut.
    """
    if len(payload) < IV_LEN_BYTES:
        raise ExtractionError("Payload terlalu pendek untuk memuat IV yang valid.")

    key = derive_aes_key(stego_key)                     # turunkan kunci dari stego-key
    iv, ciphertext = payload[:IV_LEN_BYTES], payload[IV_LEN_BYTES:]  # pisahkan IV & ciphertext
    cipher = AES.new(key, AES.MODE_CBC, iv)              # cipher dengan IV yang sama

    try:
        padded = cipher.decrypt(ciphertext)              # dekripsi mentah (masih ber-padding)
        raw = unpad(padded, AES.block_size)               # buang padding PKCS#7
    except ValueError as exc:
        # unpad gagal jika kunci AES salah (hasil dekripsi acak) atau ciphertext rusak
        raise ExtractionError(
            "Dekripsi gagal. Stego-key kemungkinan salah atau data telah dimodifikasi."
        ) from exc

    try:
        return raw.decode("utf-8")                        # ubah kembali byte ke string
    except UnicodeDecodeError as exc:
        raise ExtractionError(
            "Hasil dekripsi bukan teks UTF-8 yang valid. Stego-key kemungkinan salah."
        ) from exc


# =============================================================================
# BAGIAN 2: PRNG MANUAL (Linear Congruential Generator) UNTUK PENGACAKAN POSISI
# =============================================================================
class LCG:
    """Linear Congruential Generator ditulis dari nol (scratch), memakai
    parameter 64-bit ala generator MMIX milik Knuth.

    Rumus rekurensi:  X_(n+1) = (a * X_n + c) mod m

    PRNG ini SENGAJA ditulis manual (tidak memakai modul `random` bawaan
    Python) agar seluruh proses pengacakan posisi pixel dapat ditelusuri
    dan dipahami langkah demi langkah.
    """

    _A = 6364136223846793005   # pengali (multiplier)
    _C = 1442695040888963407   # penambah (increment)
    _M = 1 << 64                # modulus, 2^64

    def __init__(self, seed: int):
        self.state = seed % self._M   # state awal = seed (dibatasi ke rentang modulus)

    def next(self) -> int:
        """Menghasilkan satu bilangan pseudo-random 64-bit berikutnya."""
        self.state = (self._A * self.state + self._C) % self._M  # iterasi LCG
        return self.state


def seed_from_key(stego_key: str) -> int:
    """Mengubah stego-key (string bebas) menjadi seed integer 64-bit memakai
    SHA-256, sehingga:
      - kunci yang sama SELALU menghasilkan seed yang sama (deterministik),
      - perubahan satu karakter pada kunci menghasilkan seed yang jauh
        berbeda (efek longsoran dari fungsi hash).
    """
    digest = hashlib.sha256(stego_key.encode("utf-8")).digest()  # hash SHA-256 (32 byte)
    return int.from_bytes(digest[:8], byteorder="big")           # ambil 8 byte pertama -> int 64-bit


def fisher_yates_shuffle(n: int, seed: int) -> List[int]:
    """Menghasilkan permutasi acak dari himpunan indeks [0, n) memakai
    algoritma Fisher-Yates yang digerakkan oleh LCG manual di atas.

    Algoritma ini dipakai untuk menentukan URUTAN posisi bit LSB mana pada
    citra yang akan dipakai untuk menyisipkan header dan payload, sehingga
    posisi penyisipan tidak berurutan (tidak sekuensial dari pixel pertama).
    """
    indices = list(range(n))     # indeks awal 0..n-1 masih berurutan
    rng = LCG(seed)               # PRNG di-seed dari stego-key
    for i in range(n - 1, 0, -1):
        j = rng.next() % (i + 1)                    # pilih indeks acak pada rentang [0, i]
        indices[i], indices[j] = indices[j], indices[i]   # tukar posisi ke-i dan ke-j
    return indices


# =============================================================================
# BAGIAN 3: UTILITAS BIT & HEADER
# =============================================================================
def bytes_to_bits(data: bytes) -> List[int]:
    """Mengubah rangkaian byte menjadi list bit, MSB (bit paling signifikan)
    lebih dulu untuk setiap byte."""
    bits: List[int] = []
    for byte in data:
        for shift in range(7, -1, -1):          # mulai dari bit ke-7 (MSB) turun ke bit ke-0
            bits.append((byte >> shift) & 1)     # geser lalu mask 1 bit -> ambil nilai bit
    return bits


def bits_to_bytes(bits: List[int]) -> bytes:
    """Mengubah list bit menjadi rangkaian byte (kebalikan dari bytes_to_bits)."""
    if len(bits) % 8 != 0:
        raise ValueError("Jumlah bit harus kelipatan 8 untuk dikonversi ke byte.")
    out = bytearray()
    for i in range(0, len(bits), 8):
        byte_val = 0
        for bit in bits[i:i + 8]:
            byte_val = (byte_val << 1) | bit     # susun 8 bit berurutan menjadi 1 byte
        out.append(byte_val)
    return bytes(out)


def build_header(payload_len_bytes: int) -> List[int]:
    """Membangun header 32 bit (format big-endian) berisi panjang payload
    terenkripsi dalam byte. Header inilah yang membuat proses ekstraksi tahu
    persis kapan harus berhenti membaca bit, tanpa perlu menandai akhir
    pesan dengan karakter khusus."""
    header_bytes = struct.pack(">I", payload_len_bytes)   # unsigned int 4 byte, big-endian
    return bytes_to_bits(header_bytes)


def parse_header(bits: List[int]) -> int:
    """Membaca 32 bit header hasil ekstraksi dan mengembalikan panjang
    payload (dalam byte) yang tersimpan di dalamnya."""
    header_bytes = bits_to_bytes(bits)
    return struct.unpack(">I", header_bytes)[0]


# =============================================================================
# BAGIAN 4: PEMETAAN POSISI BIT <-> KOORDINAT PIXEL
# =============================================================================
def position_to_pixel(position: int, width: int) -> Tuple[int, int, int]:
    """Mengubah satu indeks posisi bit "linear" (0 .. lebar*tinggi*3 - 1)
    menjadi koordinat (x, y, channel) pada citra RGB.

    Konvensi: posisi = (pixel_index * 3) + channel, channel 0=R, 1=G, 2=B.
    """
    channel = position % 3          # sisa bagi 3 -> menentukan kanal R/G/B
    pixel_index = position // 3     # hasil bagi 3 -> indeks pixel ke berapa
    x = pixel_index % width         # kolom pixel
    y = pixel_index // width        # baris pixel
    return x, y, channel


# =============================================================================
# BAGIAN 5: KAPASITAS CITRA
# =============================================================================
def calculate_capacity(image: Image.Image) -> Tuple[int, int]:
    """Menghitung kapasitas citra untuk metode LSB 1-bit per kanal RGB.

    Returns:
        total_bits         : total slot bit LSB yang tersedia (lebar * tinggi * 3)
        max_message_bytes  : kapasitas efektif untuk PAYLOAD (setelah dikurangi
                              32 bit yang wajib dipakai untuk header)
    """
    width, height = image.size
    total_bits = width * height * 3                 # 3 kanal (R, G, B), 1 bit LSB tiap kanal
    usable_bits = total_bits - HEADER_SIZE_BITS       # sisihkan slot untuk header 32 bit
    max_message_bytes = max(usable_bits // 8, 0)      # bulatkan ke bawah, tidak boleh negatif
    return total_bits, max_message_bytes


# =============================================================================
# BAGIAN 6: PENYISIPAN (EMBEDDING)
# =============================================================================
def embed_message(cover_path: str, message: str, stego_key: str, output_path: str) -> None:
    """Menyisipkan `message` ke dalam citra `cover_path` memakai LSB dengan
    posisi pixel yang diacak berdasarkan `stego_key`, lalu menyimpan hasilnya
    (citra stego) sebagai PNG ke `output_path`.

    Raises:
        CapacityError: bila pesan terenkripsi melebihi kapasitas citra.
    """
    # 1. Enkripsi pesan terlebih dahulu (AES-256-CBC) -> payload
    encrypted_payload = encrypt_message(message, stego_key)

    # 2. Buka citra cover dan paksa mode RGB agar selalu tersedia 3 kanal
    image = Image.open(cover_path).convert("RGB")
    width, height = image.size
    total_bits, max_message_bytes = calculate_capacity(image)

    # 3. Validasi kapasitas SEBELUM satu pun bit disisipkan ke citra
    if len(encrypted_payload) > max_message_bytes:
        raise CapacityError(
            f"Pesan terenkripsi ({len(encrypted_payload)} byte) melebihi kapasitas "
            f"maksimum citra cover ({max_message_bytes} byte). Gunakan citra yang "
            f"lebih besar atau persingkat pesan."
        )

    # 4. Susun seluruh bit yang akan disisipkan: header (32 bit) lalu payload
    header_bits = build_header(len(encrypted_payload))
    payload_bits = bytes_to_bits(encrypted_payload)
    all_bits = header_bits + payload_bits

    # 5. Bangun permutasi posisi bit berdasarkan seed dari stego-key
    seed = seed_from_key(stego_key)
    permutation = fisher_yates_shuffle(total_bits, seed)
    target_positions = permutation[:len(all_bits)]   # ambil sejumlah posisi sesuai kebutuhan

    # 6. Akses pixel citra secara langsung (mode baca-tulis)
    pixel_access = image.load()

    # 7. Sisipkan setiap bit pesan ke LSB kanal pada posisi acak yang dipilih
    for bit, pos in zip(all_bits, target_positions):
        x, y, channel = position_to_pixel(pos, width)   # terjemahkan posisi -> koordinat
        r, g, b = pixel_access[x, y]                      # ambil nilai (R, G, B) saat ini
        channel_values = [r, g, b]
        channel_values[channel] = (channel_values[channel] & 0xFE) | bit
        # baris di atas: nolkan LSB (AND 0xFE = ...11111110) lalu OR-kan bit pesan
        pixel_access[x, y] = tuple(channel_values)         # tulis kembali pixel yang termodifikasi

    # 8. Simpan citra stego sebagai PNG (format lossless, wajib agar LSB tidak rusak)
    image.save(output_path, format="PNG")


# =============================================================================
# BAGIAN 7: EKSTRAKSI (EXTRACTING)
# =============================================================================
def extract_message(stego_path: str, stego_key: str) -> str:
    """Mengekstraksi dan mendekripsi pesan rahasia dari citra `stego_path`
    memakai `stego_key` yang HARUS identik dengan yang dipakai saat
    penyisipan, karena seed permutasi bergantung sepenuhnya pada kunci ini.

    Raises:
        ExtractionError: bila header tidak masuk akal atau dekripsi gagal
                          (indikasi stego-key salah / citra telah diubah).
    """
    image = Image.open(stego_path).convert("RGB")
    width, height = image.size
    total_bits = width * height * 3
    pixel_access = image.load()

    # 1. Bangun ulang permutasi posisi memakai seed yang sama dari stego-key
    seed = seed_from_key(stego_key)
    permutation = fisher_yates_shuffle(total_bits, seed)

    # 2. Baca 32 posisi pertama pada permutasi sebagai bit header
    header_positions = permutation[:HEADER_SIZE_BITS]
    header_bits = []
    for pos in header_positions:
        x, y, channel = position_to_pixel(pos, width)
        rgb = pixel_access[x, y]
        header_bits.append(rgb[channel] & 1)     # ambil LSB kanal terkait sebagai 1 bit

    try:
        payload_len = parse_header(header_bits)   # panjang payload (byte) hasil dekode header
    except struct.error as exc:
        raise ExtractionError("Header tidak valid. Stego-key kemungkinan salah.") from exc

    payload_bit_count = payload_len * 8
    end_index = HEADER_SIZE_BITS + payload_bit_count

    # 3. Validasi bahwa panjang payload hasil baca header masih masuk akal
    #    (stego-key yang salah akan membuat header terbaca sebagai angka acak/raksasa)
    if payload_len <= 0 or end_index > total_bits:
        raise ExtractionError(
            "Panjang payload hasil pembacaan header tidak masuk akal. "
            "Stego-key kemungkinan salah atau citra bukan hasil penyisipan yang valid."
        )

    # 4. Ambil posisi payload lanjutan dari permutasi yang sama (indeks 32 dst.)
    payload_positions = permutation[HEADER_SIZE_BITS:end_index]
    payload_bits = []
    for pos in payload_positions:
        x, y, channel = position_to_pixel(pos, width)
        rgb = pixel_access[x, y]
        payload_bits.append(rgb[channel] & 1)

    payload_bytes = bits_to_bytes(payload_bits)

    # 5. Dekripsi payload dengan AES; ExtractionError otomatis muncul bila kunci salah
    return decrypt_message(payload_bytes, stego_key)


# =============================================================================
# BAGIAN 8: STEGANALISIS VISUAL (ENHANCED LSB)
# =============================================================================
def get_enhanced_lsb_image(image: Image.Image, scale: int = 255) -> Image.Image:
    """Menghasilkan citra Steganalisis Visual (Enhanced LSB).
    Mengambil bit LSB dari setiap piksel/kanal lalu mengalikan nilainya dengan `scale` (default 255),
    sehingga bit LSB (0 atau 1) terlihat jelas sebagai pola kontras hitam-putih.
    """
    img_rgb = image.convert("RGB")
    arr = np.array(img_rgb, dtype=np.uint8)
    lsb_arr = (arr & 1) * scale
    return Image.fromarray(lsb_arr, mode="RGB")


# =============================================================================
# CONTOH PEMAKAIAN (dijalankan hanya bila file ini dieksekusi langsung)
# =============================================================================
if __name__ == "__main__":
    # Contoh alur singkat: buat citra dummy, sisipkan pesan, lalu ekstrak kembali.
    demo_image = Image.new("RGB", (64, 64), color=(120, 130, 140))
    demo_image.save("cover_demo.png")

    KEY = "kunci-rahasia-uts-2026"
    PESAN = "Keamanan Informasi UNSIL - pesan rahasia dari mahasiswa."

    embed_message("cover_demo.png", PESAN, KEY, "stego_demo.png")
    hasil = extract_message("stego_demo.png", KEY)

    print("Pesan asli   :", PESAN)
    print("Pesan hasil  :", hasil)
    print("Cocok?       :", hasil == PESAN)
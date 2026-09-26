"""
Unit test untuk modul steg_engine.py.

Lima pengujian wajib sesuai spesifikasi tugas:
1. test_enkripsi_dekripsi_aes_roundtrip  -> fungsi enkripsi (dan dekripsi pasangannya)
2. test_penyisipan_pesan_ke_citra        -> fungsi penyisipan (embedding)
3. test_pengacakan_seed_dari_stego_key   -> fungsi pengacakan PRNG (LCG + Fisher-Yates)
4. test_ekstraksi_pesan_dari_citra       -> fungsi ekstraksi (extracting)
5. test_ekstraksi_gagal_stego_key_salah  -> uji kegagalan bila stego-key salah

Ditambah satu pengujian tambahan (bonus) untuk validasi kapasitas citra.

Cara menjalankan:
    python -m unittest test_stega.py -v
"""

import os
import shutil
import tempfile
import unittest

from PIL import Image

import stego_engine as se


class TestStegoEngine(unittest.TestCase):
    """Kumpulan unit test untuk seluruh fungsi inti pada stego_engine.py."""

    @classmethod
    def setUpClass(cls):
        """Disiapkan sekali untuk seluruh test: direktori sementara dan citra
        cover dummy berukuran cukup besar agar kapasitas LSB mencukupi."""
        cls.temp_dir = tempfile.mkdtemp(prefix="stego_test_")

        # Citra cover 100 x 100 piksel RGB -> kapasitas = 100*100*3 = 30.000 bit
        # (setara 3.750 byte, dikurangi 4 byte header -> cukup untuk pesan uji)
        cls.cover_path = os.path.join(cls.temp_dir, "cover.png")
        cover_image = Image.new("RGB", (100, 100), color=(0, 0, 0))
        # Beri variasi warna acak sederhana agar citra tidak seragam (mendekati kasus nyata)
        pixel_access = cover_image.load()
        counter = 0
        for y in range(100):
            for x in range(100):
                counter = (counter + 37) % 256
                pixel_access[x, y] = (counter, (counter * 3) % 256, (counter * 7) % 256)
        cover_image.save(cls.cover_path, format="PNG")

    @classmethod
    def tearDownClass(cls):
        """Membersihkan seluruh berkas sementara setelah semua test selesai."""
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    # -------------------------------------------------------------------
    # TEST 1: FUNGSI ENKRIPSI (DAN DEKRIPSI) AES
    # -------------------------------------------------------------------
    def test_enkripsi_dekripsi_aes_roundtrip(self):
        """Pesan yang dienkripsi dengan encrypt_message harus dapat
        dikembalikan persis sama oleh decrypt_message memakai kunci yang sama."""
        pesan_asli = "Keamanan Informasi UNSIL - pengujian AES 256 CBC."
        kunci = "stego-key-uji-001"

        payload = se.encrypt_message(pesan_asli, kunci)

        # Payload harus berupa IV (16 byte) + ciphertext, jadi lebih panjang dari pesan asli
        self.assertGreater(len(payload), se.IV_LEN_BYTES)

        pesan_hasil = se.decrypt_message(payload, kunci)
        self.assertEqual(pesan_asli, pesan_hasil)

        # Dua kali enkripsi pesan yang sama harus menghasilkan ciphertext BERBEDA
        # karena IV dibangkitkan acak setiap kali (properti keamanan AES-CBC).
        payload_kedua = se.encrypt_message(pesan_asli, kunci)
        self.assertNotEqual(payload, payload_kedua)

    # -------------------------------------------------------------------
    # TEST 2: FUNGSI PENYISIPAN (EMBEDDING)
    # -------------------------------------------------------------------
    def test_penyisipan_pesan_ke_citra(self):
        """embed_message harus menghasilkan berkas citra stego yang valid,
        dan citra tersebut harus berbeda dari citra cover asli (karena
        sejumlah bit LSB telah diubah)."""
        pesan = "Pesan rahasia untuk uji penyisipan LSB."
        kunci = "stego-key-uji-002"
        output_path = os.path.join(self.temp_dir, "stego_embed_test.png")

        se.embed_message(self.cover_path, pesan, kunci, output_path)

        # Berkas hasil penyisipan harus benar-benar terbentuk
        self.assertTrue(os.path.exists(output_path))

        cover_image = Image.open(self.cover_path).convert("RGB")
        stego_image = Image.open(output_path).convert("RGB")

        # Ukuran citra tidak boleh berubah, hanya nilai LSB tiap kanal yang berubah
        self.assertEqual(cover_image.size, stego_image.size)

        # Pastikan ada perbedaan pixel (artinya penyisipan benar-benar terjadi)
        cover_pixels = list(cover_image.getdata())
        stego_pixels = list(stego_image.getdata())
        self.assertNotEqual(cover_pixels, stego_pixels)

        # Selisih tiap kanal warna maksimal 1 (karena hanya LSB yang boleh berubah)
        for (r1, g1, b1), (r2, g2, b2) in zip(cover_pixels, stego_pixels):
            self.assertLessEqual(abs(r1 - r2), 1)
            self.assertLessEqual(abs(g1 - g2), 1)
            self.assertLessEqual(abs(b1 - b2), 1)

    # -------------------------------------------------------------------
    # TEST 3: FUNGSI PENGACAKAN SEED / PRNG (LCG + FISHER-YATES)
    # -------------------------------------------------------------------
    def test_pengacakan_seed_dari_stego_key(self):
        """Menguji tiga sifat penting PRNG manual:
        (a) deterministik -> kunci sama menghasilkan seed dan permutasi sama,
        (b) sensitif -> kunci berbeda menghasilkan seed dan permutasi berbeda,
        (c) valid -> hasil shuffle tetap berupa permutasi lengkap (tidak ada
            indeks yang hilang atau berulang).
        """
        kunci_a = "kunci-rahasia-A"
        kunci_b = "kunci-rahasia-B"

        seed_a1 = se.seed_from_key(kunci_a)
        seed_a2 = se.seed_from_key(kunci_a)
        seed_b = se.seed_from_key(kunci_b)

        # (a) Deterministik: seed dari kunci yang sama harus identik
        self.assertEqual(seed_a1, seed_a2)

        # (b) Sensitif: kunci berbeda (walau mirip) harus hasilkan seed berbeda
        self.assertNotEqual(seed_a1, seed_b)

        n = 1000
        permutasi_a1 = se.fisher_yates_shuffle(n, seed_a1)
        permutasi_a2 = se.fisher_yates_shuffle(n, seed_a2)
        permutasi_b = se.fisher_yates_shuffle(n, seed_b)

        # Permutasi dari seed yang sama harus identik persis
        self.assertEqual(permutasi_a1, permutasi_a2)

        # Permutasi dari seed yang berbeda harus berbeda (sangat kecil peluang sama)
        self.assertNotEqual(permutasi_a1, permutasi_b)

        # (c) Validitas permutasi: berisi seluruh indeks 0..n-1 tanpa duplikat
        self.assertEqual(sorted(permutasi_a1), list(range(n)))

    # -------------------------------------------------------------------
    # TEST 4: FUNGSI EKSTRAKSI (EXTRACTING)
    # -------------------------------------------------------------------
    def test_ekstraksi_pesan_dari_citra(self):
        """Alur lengkap embed -> extract dengan stego-key yang benar harus
        mengembalikan pesan asli tanpa kehilangan satu karakter pun."""
        pesan_asli = "Universitas Siliwangi - Tugas UTS Keamanan Informasi 2026."
        kunci = "stego-key-uji-003"
        output_path = os.path.join(self.temp_dir, "stego_extract_test.png")

        se.embed_message(self.cover_path, pesan_asli, kunci, output_path)
        pesan_hasil = se.extract_message(output_path, kunci)

        self.assertEqual(pesan_asli, pesan_hasil)

    # -------------------------------------------------------------------
    # TEST 5: UJI KEGAGALAN BILA STEGO-KEY SALAH
    # -------------------------------------------------------------------
    def test_ekstraksi_gagal_stego_key_salah(self):
        """Ekstraksi dengan stego-key yang berbeda dari saat penyisipan wajib
        gagal (melempar ExtractionError), karena permutasi posisi bit yang
        dihasilkan akan sepenuhnya berbeda sehingga header/payload tidak
        dapat dibaca dengan benar."""
        pesan_asli = "Pesan ini hanya boleh terbaca dengan kunci yang benar."
        kunci_benar = "kunci-benar-2026"
        kunci_salah = "kunci-salah-2026"
        output_path = os.path.join(self.temp_dir, "stego_wrongkey_test.png")

        se.embed_message(self.cover_path, pesan_asli, kunci_benar, output_path)

        with self.assertRaises(se.ExtractionError):
            se.extract_message(output_path, kunci_salah)

    # -------------------------------------------------------------------
    # TEST TAMBAHAN (BONUS): VALIDASI KAPASITAS CITRA
    # -------------------------------------------------------------------
    def test_bonus_kapasitas_terlampaui_memicu_error(self):
        """embed_message wajib menolak (CapacityError) apabila pesan yang
        sudah dienkripsi lebih besar dari kapasitas LSB citra cover."""
        # Citra sangat kecil (4 x 4 piksel) -> kapasitas jauh lebih kecil
        tiny_path = os.path.join(self.temp_dir, "tiny_cover.png")
        Image.new("RGB", (4, 4), color=(50, 50, 50)).save(tiny_path, format="PNG")

        pesan_panjang = "X" * 500   # jelas melebihi kapasitas citra 4x4
        output_path = os.path.join(self.temp_dir, "tiny_stego.png")

        with self.assertRaises(se.CapacityError):
            se.embed_message(tiny_path, pesan_panjang, "kunci-apa-saja", output_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
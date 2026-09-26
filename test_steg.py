"""
test_steg.py
------------
Unit test suite untuk modul steg_engine.py.
"""

import os
import shutil
import tempfile
import unittest

from PIL import Image

import steg_engine as se


class TestStegEngine(unittest.TestCase):
    """Unit test suite untuk memverifikasi fungsionalitas steg_engine."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp(prefix="steg_test_")
        cls.cover_path = os.path.join(cls.temp_dir, "cover.png")

        cover_image = Image.new("RGB", (100, 100), color=(0, 0, 0))
        pixel_access = cover_image.load()
        counter = 0
        for y in range(100):
            for x in range(100):
                counter = (counter + 37) % 256
                pixel_access[x, y] = (counter, (counter * 3) % 256, (counter * 7) % 256)
        cover_image.save(cls.cover_path, format="PNG")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_enkripsi_dekripsi_aes_roundtrip(self):
        """Uji integritas enkripsi dan dekripsi AES-256-CBC."""
        pesan_asli = "Test AES encryption roundtrip."
        kunci = "secret-passphrase-001"

        payload = se.encrypt_message(pesan_asli, kunci)
        self.assertGreater(len(payload), se.IV_LEN_BYTES)

        pesan_hasil = se.decrypt_message(payload, kunci)
        self.assertEqual(pesan_asli, pesan_hasil)

        # Verifikasi keacakan IV (dua kali enkripsi menghasilkan ciphertext berbeda)
        payload_2 = se.encrypt_message(pesan_asli, kunci)
        self.assertNotEqual(payload, payload_2)

    def test_penyisipan_pesan_ke_citra(self):
        """Uji penyisipan pesan (embedding) ke citra cover."""
        pesan = "Pesan uji LSB embedding."
        kunci = "secret-passphrase-002"
        output_path = os.path.join(self.temp_dir, "stego_embed.png")

        se.embed_message(self.cover_path, pesan, kunci, output_path)
        self.assertTrue(os.path.exists(output_path))

        cover_img = Image.open(self.cover_path).convert("RGB")
        stego_img = Image.open(output_path).convert("RGB")

        self.assertEqual(cover_img.size, stego_img.size)

        import numpy as np
        cover_pixels = np.array(cover_img, dtype=np.int16)
        stego_pixels = np.array(stego_img, dtype=np.int16)
        self.assertFalse(np.array_equal(cover_pixels, stego_pixels))

        # Selisih kanal maksimal 1 (sifat LSB 1-bit)
        diff = np.abs(cover_pixels - stego_pixels)
        self.assertTrue(np.all(diff <= 1))

    def test_pengacakan_seed_dari_stego_key(self):
        """Uji sifat PRNG: deterministik, sensitivitas kunci, dan integritas permutasi."""
        kunci_a = "key-alpha"
        kunci_b = "key-beta"

        seed_a1 = se.seed_from_key(kunci_a)
        seed_a2 = se.seed_from_key(kunci_a)
        seed_b = se.seed_from_key(kunci_b)

        self.assertEqual(seed_a1, seed_a2)
        self.assertNotEqual(seed_a1, seed_b)

        n = 1000
        perm_a1 = se.fisher_yates_shuffle(n, seed_a1)
        perm_a2 = se.fisher_yates_shuffle(n, seed_a2)
        perm_b = se.fisher_yates_shuffle(n, seed_b)

        self.assertEqual(perm_a1, perm_a2)
        self.assertNotEqual(perm_a1, perm_b)
        self.assertEqual(sorted(perm_a1), list(range(n)))

    def test_ekstraksi_pesan_dari_citra(self):
        """Uji alur lengkap embedding dan ekstraksi dengan stego-key yang valid."""
        pesan_asli = "Steganography LSB test message."
        kunci = "secret-passphrase-003"
        output_path = os.path.join(self.temp_dir, "stego_extract.png")

        se.embed_message(self.cover_path, pesan_asli, kunci, output_path)
        pesan_hasil = se.extract_message(output_path, kunci)
        self.assertEqual(pesan_asli, pesan_hasil)

    def test_ekstraksi_gagal_stego_key_salah(self):
        """Uji kebalikan: ekstraksi harus gagal apabila stego-key salah."""
        pesan_asli = "Secret content."
        kunci_benar = "correct-key"
        kunci_salah = "wrong-key"
        output_path = os.path.join(self.temp_dir, "stego_wrong_key.png")

        se.embed_message(self.cover_path, pesan_asli, kunci_benar, output_path)
        with self.assertRaises(se.ExtractionError):
            se.extract_message(output_path, kunci_salah)

    def test_kapasitas_terlampaui_memicu_error(self):
        """Uji validasi batas kapasitas citra."""
        tiny_path = os.path.join(self.temp_dir, "tiny_cover.png")
        Image.new("RGB", (4, 4), color=(50, 50, 50)).save(tiny_path, format="PNG")

        pesan_panjang = "X" * 500
        output_path = os.path.join(self.temp_dir, "tiny_stego.png")

        with self.assertRaises(se.CapacityError):
            se.embed_message(tiny_path, pesan_panjang, "pass", output_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
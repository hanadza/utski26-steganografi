# StegoShield - Aplikasi Steganografi LSB & Kriptografi AES-256

Aplikasi steganografi citra digital berteknologi **Least Significant Bit (LSB)** yang dipadukan dengan enkripsi **AES-256-CBC** dan pengacakan posisi piksel berbasis **Linear Congruential Generator (LCG)**.

Proyek ini disusun untuk memenuhi **Tugas Proyek Keamanan Informasi (Topik B - Steganografi)**, Jurusan Informatika, Universitas Siliwangi.

---

## 👥 Anggota Kelompok

| No | Nama | NPM | Peran / Kontribusi |
| :-: | :--- | :--- | :--- |
| 1 | **Bimantara Prakasa Jantika** | `247006111061` | Pengembang Antarmuka Web App Streamlit serta Pengujian Kuantitatif & Evaluasi PSNR/MSE |
| 2 | **Aditya Ihsan Maulana** | `247006111069` | Pengembang Utama / Kriptografi & Steganografi |

---

## 🚀 Fitur Utama

- **Penyisipan & Ekstraksi LSB Acak:** Menyisipkan pesan ke kanal RGB citra PNG secara non-sekuensial.
- **Enkripsi Kuat AES-256-CBC:** Pesan dienkripsi sebelum disisipkan ke citra. Kunci AES diturunkan via PBKDF/SHA-256 dan IV acak dibangkitkan menggunakan CSPRNG (`Crypto.Random`).
- **Header Bit Metadata:** Header 32-bit big-endian menyimpan ukuran payload terenkripsi secara presisi.
- **Validasi Kapasitas:** Otomatis menghitung kapasitas maksimal citra dan menolak penyisipan bila payload melebihi kapasitas.
- **Visual Steganalisis (Enhanced LSB):** Memvisualisasikan bidang bit LSB dalam kontras hitam-putih.
- **Steganalisis Statistik (Uji Chi-Square $\chi^2$):** Mendeteksi keberadaan pesan tersembunyi LSB berbasis kesetaraan distribusi *Pairs of Values* (PoV) (Serangan Westfeld & Pfitzmann).
- **Evaluasi Kuantitatif Citra (MSE & PSNR):** Menghitung nilai distorsi citra dengan ambang kelulusan standar perkuliahan (PSNR $\ge$ 30 dB).
- **Uji Kerapuhan JPEG (Fragility Test):** Membuktikan sifat *fragile* LSB terhadap kompresi *lossy* JPEG.
- **Aplikasi Web Interaktif (Streamlit):** GUI berbasis web yang responsif dengan fitur perbandingan berdampingan.

---

## 🛠️ Instalasi & Persyaratan System

### Prasyarat
- Python 3.9 atau lebih baru.
- Virtual environment (disarankan).

### Langkah Instalasi
1. Clone repositori ini:
   ```bash
   git clone https://github.com/hanadza/utski26-steganografi.git
   cd utski26-steganografi
   ```
2. (Opsional) Buat dan aktifkan *virtual environment*:
   ```bash
   python -m venv venv
   # Pada Windows PowerShell:
   .\venv\Scripts\Activate.ps1
   # Pada Linux/macOS:
   source venv/bin/activate
   ```
3. Install dependensi modul Python:
   ```bash
   pip install pycryptodome pillow numpy matplotlib streamlit pandas
   ```

---

## 💻 Cara Menjalankan

### 1. Menjalankan Aplikasi Web (Streamlit GUI)
```bash
streamlit run app.py
```
*Aplikasi akan terbuka otomatis di peramban pada alamat `http://localhost:8501`.*

### 2. Menjalankan Pengujian Tunggal via CLI
```bash
python steg_testing.py
```

### 3. Menjalankan Automasi Batch Testing (5 Citra × 3 Ukuran Pesan)
```bash
python steg_testing.py --batch
```

### 4. Menjalankan Unit Test Suite (7 Pengujian Lengkap)
```bash
python -m unittest test_steg.py -v
```

---

## 📖 Contoh Penggunaan Modul (Python Code)

```python
import steg_engine as se

# 1. Penyisipan Pesan Rahasia (Embedding)
cover_path = "cover.png"
secret_message = "Pesan rahasia ini dienkripsi dengan AES-256."
stego_key = "kunci-rahasia-pengguna"
output_path = "stego_result.png"

se.embed_message(cover_path, secret_message, stego_key, output_path)
print("Pesan berhasil disisipkan ke", output_path)

# 2. Ekstraksi & Dekripsi Pesan (Extracting)
extracted_text = se.extract_message(output_path, stego_key)
print("Pesan terekstrak:", extracted_text)
```

---

## 🛡️ Kepatuhan Ketentuan Teknis & Keamanan

- **Pembangkit Acak Kriptografis (CSPRNG):** IV dan byte acak dibangkitkan menggunakan `Crypto.Random.get_random_bytes` yang menggunakan sumber entropy `os.urandom`.
- **Manajemen Kunci:** Tidak ada *hardcoded key* atau kata sandi yang ditulis langsung pada kode sumber.
- **Standar Algoritma:** Menggunakan mode aman **AES-256-CBC** dan **SHA-256**. Tidak menggunakan algoritma usang (MD5, SHA-1, DES, RC4) maupun mode ECB.
- **Jaminan Unit Test:** Memiliki 6 unit test otomatis untuk pengujian skenario enkripsi, penyisipan, ekstraksi kunci benar, kegagalan kunci salah, pengacakan PRNG, dan batas kapasitas.

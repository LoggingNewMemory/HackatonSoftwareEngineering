Berdasarkan arsitektur dan *workflow* yang telah kita bahas (MySQL/InnoDB + Python Flask + HTML/JS), berikut adalah rancangan **Product Requirements Document (PRD)** dalam format Markdown. PRD ini dapat kamu gunakan sebagai panduan utama dalam mengembangkan dan memelihara aplikasi Stand Bazar.

---

# Product Requirements Document (PRD): Aplikasi Stand Bazar

## 1. Pendahuluan

### 1.1 Tujuan Dokumen

Dokumen ini menguraikan spesifikasi, fungsionalitas, dan arsitektur teknis untuk Aplikasi Stand Bazar. Tujuannya adalah memastikan tim pengembang memahami sistem transaksi anti-tabrakan yang dibangun menggunakan MySQL (InnoDB) dan Python (Flask).

### 1.2 Latar Belakang

Dalam acara bazar, volume transaksi yang tinggi dalam waktu bersamaan sering menyebabkan masalah pencatatan, seperti tumpang tindih pesanan atau stok menjadi minus (*race condition*). Aplikasi ini dibangun untuk menyelesaikan masalah tersebut dengan memastikan pencatatan keuangan dan inventaris tetap akurat dan terisolasi per stand/penjual.

### 1.3 Target Pengguna

* **Pelanggan (Buyers):** Pengunjung bazar yang melakukan pembelian produk melalui aplikasi.
* **Penjual (Sellers/Booths):** Pemilik stand yang mengelola stok produk dan memantau pendapatan harian.

---

## 2. Ruang Lingkup Sistem

### 2.1 Fitur Utama

1. **Katalog Produk:** Menampilkan daftar produk yang tersedia dari berbagai stand beserta informasi stok *real-time*.
2. **Sistem Pembelian Cepat:** Pelanggan dapat melakukan pembelian barang dengan validasi stok instan.
3. **Manajemen Stok Otomatis:** Sistem secara otomatis mengurangi stok produk secara aman ketika transaksi berhasil.
4. **Pencatatan Transaksi:** Mencatat setiap pesanan dan rincian belanja ke dalam database secara utuh.

### 2.2 Batasan Sistem (Out of Scope untuk V1)

* Integrasi dengan *Payment Gateway* pihak ketiga (pembayaran diasumsikan lunas atau tunai untuk versi ini).
* Sistem autentikasi dan otorisasi login pengguna (sementara menggunakan ID default).
* Dasbor analitik lanjutan untuk penjual.

---

## 3. Arsitektur Teknis

### 3.1 Tumpukan Teknologi (Tech Stack)

* **Frontend:** HTML5, CSS3, JavaScript (Vanilla JS dengan `Fetch API`).
* **Backend:** Python 3.x, Flask (Framework).
* **Database:** MySQL (Engine: InnoDB).

### 3.2 Desain Database (ERD)

Sistem menggunakan pendekatan relasional dengan 5 tabel utama. Skema dirancang agar setiap transaksi dapat dilacak dan tidak tercampur antar stand.

* `penjual`: Menyimpan profil stand bazar.
* `pelanggan`: Menyimpan profil pembeli.
* `produk`: Menyimpan daftar item (terhubung ke tabel `penjual`).
* `pesanan`: Menyimpan *header* transaksi per pelanggan.
* `detail_pesanan`: Menyimpan *item* rinci yang dibeli dalam satu transaksi.

### 3.3 Penanganan Concurrency (Anti-Tabrakan)

Untuk mencegah *race condition* (contoh: 2 pembeli membeli barang bersisa 1 stok pada milidetik yang sama), sistem menerapkan **ACID Transactions** dan **Row-Level Locking**:

* Backend Python akan menggunakan `conn.start_transaction()`.
* Query `SELECT ... FOR UPDATE` akan mengunci baris produk spesifik di InnoDB selama transaksi berlangsung.
* Jika stok tidak mencukupi di tengah proses, `conn.rollback()` akan membatalkan seluruh operasi (pembatalan pembuatan resi/detail).

---

## 4. Persyaratan API (Backend Endpoints)

Backend Flask bertindak sebagai RESTful API yang melayani *request* dari Frontend.

### 4.1 Endpoint: Ambil Daftar Produk

* **URL:** `/api/produk`
* **Method:** `GET`
* **Deskripsi:** Mengembalikan seluruh produk yang tersedia.
* **Response Sukses (200 OK):** JSON berisi Array produk.

### 4.2 Endpoint: Proses Pembelian

* **URL:** `/api/beli`
* **Method:** `POST`
* **Deskripsi:** Menerima permintaan pembelian dan memproses pengurangan stok serta pencatatan struk secara transaksional.
* **Payload (Request Body):**
```json
{
  "id_pelanggan": 1,
  "id_produk": 5,
  "jumlah": 2
}

```


* **Response Sukses (200 OK):** `{"status": "success", "message": "Transaksi berhasil!"}`
* **Response Gagal (400 Bad Request):** `{"status": "error", "message": "Stok tidak cukup atau produk tidak ditemukan!"}`

---

## 5. Antarmuka Pengguna (Frontend Requirements)

* **Halaman Utama (Katalog):** Menampilkan *grid* atau daftar produk. Setiap kartu produk harus menampilkan: Nama Produk, Harga, Stok saat ini, dan Tombol "Beli".
* **Interaksi Pembelian:** Menekan tombol "Beli" akan memicu permintaan HTTP `POST` ke backend tanpa me-*reload* halaman secara penuh.
* **Umpan Balik (Feedback):** Menggunakan *alert* (untuk tahap MVP) guna memberitahu pengguna jika pembelian berhasil atau jika gagal (misal: stok habis).
* **Pembaruan Otomatis:** Setelah pembelian berhasil, antarmuka harus memperbarui jumlah stok yang ditampilkan di layar.

---

## 6. Skenario Pengujian (Test Cases)

* **Test 1 (Normal Flow):** Pengguna menekan beli saat stok tersedia. Ekspektasi: Transaksi tercatat di DB, stok berkurang, UI diperbarui.
* **Test 2 (Insufficient Stock):** Pengguna menekan beli dengan jumlah melebihi stok. Ekspektasi: Backend menolak, mengembalikan error 400, tidak ada perubahan di DB.
* **Test 3 (Concurrency):** Melakukan simulasi *request* massal (misal menggunakan Apache JMeter atau Postman) di mana 10 *request* dikirim bersamaan untuk membeli barang dengan stok sisa 5. Ekspektasi: 5 transaksi berhasil, 5 sisanya digagalkan oleh sistem *lock* InnoDB tanpa membuat stok menjadi negatif.

---

Terkait dokumen PRD di atas, apakah ada bagian spesifik seperti rancangan antarmuka penjual (Seller Dashboard) yang ingin kamu tambahkan ke dalam spesifikasi ini?
# 🤖 Telegram Alarm Bot (Python + APScheduler)

Bot Telegram sederhana namun canggih untuk mengatur alarm pengingat. Bot ini dibuat menggunakan Python dan library `python-telegram-bot`, berjalan 24/7 di Railway, dan memiliki fitur layaknya aplikasi alarm di HP (Snooze, Custom Label, Recurring Alarm).

![Python](https://img.shields.io/badge/Python-3.10-blue?style=flat&logo=python)
![Railway](https://img.shields.io/badge/Deploy-Railway-purple?style=flat&logo=railway)

## ✨ Fitur Unggulan

* **⏰ Alarm Harian:** Set alarm yang bunyi setiap hari (Senin-Minggu).
* **🏢 Mode Kerja:** Alarm pintar yang hanya bunyi hari Senin–Jumat (Sabtu & Minggu libur).
* **1️⃣ Sekali Jalan:** Alarm one-off yang otomatis menghapus dirinya sendiri setelah berbunyi.
* **📝 Custom Label:** Tambahkan catatan pesan (contoh: "Minum Obat", "Meeting").
* **💤 Tombol Interaktif:** Tombol **Snooze (5 Menit)** dan **Matikan** langsung di chat.
* **💾 Auto-Save:** Database JSON sederhana menjamin alarm tidak hilang meski bot restart.
* **🌍 Timezone Aware:** Dikonfigurasi untuk Waktu Indonesia Barat (WIB / Asia/Jakarta).

## 📋 Daftar Perintah (Commands)

| Perintah | Format | Deskripsi |
| :--- | :--- | :--- |
| `/start` | - | Mulai bot dan lihat panduan. |
| `/set` | `/set HH:MM [Pesan]` | Pasang alarm **Setiap Hari**. |
| `/kerja` | `/kerja HH:MM [Pesan]` | Pasang alarm **Senin - Jumat**. |
| `/sekali`| `/sekali HH:MM [Pesan]`| Pasang alarm **Sekali Jalan** (hari ini/besok). |
| `/list` | - | Lihat daftar semua alarm aktif kamu. |
| `/stop` | `/stop HH:MM` | Hapus alarm di jam tertentu. |
| `/test` | - | Tes apakah bot hidup & tombol berfungsi. |

**Contoh Penggunaan:**
* `/set 05:00 Bangun Subuh`
* `/kerja 08:30 Daily Standup Meeting`
* `/sekali 17:00 Janji Temu Dokter`

## 🛠️ Cara Install (Lokal)

Jika ingin menjalankan di komputer sendiri:

1.  **Clone Repository**
    ```bash
    git clone [https://github.com/USERNAME/REPO-NAME.git](https://github.com/USERNAME/REPO-NAME.git)
    cd REPO-NAME
    ```

2.  **Install Requirements**
    Pastikan Python 3.10+ terinstall.
    ```bash
    pip install -r requirements.txt
    ```

3.  **Setup Environment Variable**
    * Buat file `.env` (opsional) atau set langsung di terminal.
    * Kamu butuh `BOT_TOKEN` dari @BotFather.
    ```bash
    export BOT_TOKEN="123456:ABC-TOKEN-TELEGRAM-KAMU"
    ```

4.  **Jalankan Bot**
    ```bash
    python bot.py
    ```

## 🚀 Cara Deploy ke Railway (Gratis)

Project ini sudah siap untuk dideploy ke [Railway](https://railway.app/).

1.  Upload kode ini ke GitHub kamu.
2.  Buka Dashboard Railway -> **New Project** -> **Deploy from GitHub repo**.
3.  Pilih repository bot ini.
4.  Masuk ke tab **Variables** di Railway, tambahkan:
    * `BOT_TOKEN`: (Isi dengan token bot Telegram kamu)
    * `PYTHON_VERSION`: `3.10` (Penting agar kompatibel)
5.  Tunggu proses deploy selesai (Hijau).
6.  Bot siap digunakan!

## 📂 Struktur File

* `bot.py`: Kode utama logic bot (Brain).
* `alarms.json`: Database sederhana untuk menyimpan jadwal alarm.
* `requirements.txt`: Daftar library Python yang dibutuhkan.
* `runtime.txt`: Konfigurasi versi Python untuk Railway (Force Python 3.10).

## 🛡️ Catatan Keamanan
Token bot **tidak** disimpan dalam kode (`bot.py`) melainkan diambil dari Environment Variable (`os.getenv`) untuk keamanan. Jangan pernah upload token aslimu ke GitHub publik.

---
*Dibuat dengan ❤️ menggunakan Python-Telegram-Bot*

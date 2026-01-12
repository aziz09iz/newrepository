import logging
import json
import os
import asyncio
from datetime import time
import pytz

# Library Telegram & Scheduler
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv # Baris ini sebenernya tidak perlu jika tanpa .env, tapi amannya kita pakai os saja.
# KITA HAPUS import dotenv karena kamu tidak mau pakai file .env lagi

# --- KONFIGURASI ---
# Bot akan mencari token dari settingan Railway (Environment Variable)
TOKEN = os.getenv("BOT_TOKEN")

# Setup Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Setup Timezone Jakarta
JAKARTA_TZ = pytz.timezone('Asia/Jakarta')
FILE_DB = 'alarms.json'

# --- DATABASE & LOGIC ---

def load_alarms():
    """Membaca database dari file JSON"""
    try:
        with open(FILE_DB, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_alarm_to_db(chat_id, time_str):
    """Menyimpan alarm baru ke JSON"""
    alarms = load_alarms()
    alarms.append({"chat_id": chat_id, "time": time_str})
    with open(FILE_DB, 'w') as f:
        json.dump(alarms, f, indent=4)

async def send_alarm_message(context: ContextTypes.DEFAULT_TYPE):
    """Fungsi yang dipanggil saat alarm berbunyi"""
    chat_id = context.job.data['chat_id']
    try:
        await context.bot.send_message(chat_id=chat_id, text="⏰ ALARM! Waktunya bangun/beraktivitas!")
        print(f"Sukses kirim alarm ke {chat_id}")
    except Exception as e:
        print(f"Gagal kirim alarm: {e}")

async def set_alarm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani perintah /set HH:MM"""
    chat_id = update.effective_chat.id
    
    try:
        if not context.args:
            raise ValueError("Tidak ada jam")
            
        time_input = context.args[0] # format HH:MM
        hour, minute = map(int, time_input.split(':'))
        
        # Simpan ke database
        save_alarm_to_db(chat_id, time_input)
        
        # Pasang Alarm Harian
        context.job_queue.run_daily(
            send_alarm_message,
            time=time(hour=hour, minute=minute, tzinfo=JAKARTA_TZ),
            data={'chat_id': chat_id},
            name=str(chat_id)
        )
        
        await update.message.reply_text(f"✅ Alarm diset setiap jam {time_input} WIB!")
        
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Format salah. Gunakan: /set HH:MM\nContoh: /set 07:00")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Halo! Saya Bot Alarm.\nGunakan /set HH:MM untuk pasang alarm harian.")

async def restore_alarms(application):
    """Mengembalikan alarm yang tersimpan saat bot restart"""
    alarms = load_alarms()
    print(f"🔄 Mengembalikan {len(alarms)} alarm dari database...")
    
    for alarm in alarms:
        try:
            h, m = map(int, alarm['time'].split(':'))
            application.job_queue.run_daily(
                send_alarm_message,
                time=time(hour=h, minute=m, tzinfo=JAKARTA_TZ),
                data={'chat_id': alarm['chat_id']}
            )
        except Exception as e:
            print(f"Gagal restore alarm: {e}")

# --- MAIN PROGRAM ---
if __name__ == '__main__':
    # Cek apakah TOKEN ada
    if not TOKEN:
        print("❌ ERROR FATAL: Token tidak ditemukan!")
        print("TIPS: Di Dashboard Railway, masuk tab 'Variables', tambahkan 'BOT_TOKEN' dengan isi token botmu.")
        exit()

    # Buat Aplikasi
    application = ApplicationBuilder().token(TOKEN).build()

    # Tambah Handler
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('set', set_alarm))

    # Restore alarm saat inisialisasi
    async def post_init(app):
        await restore_alarms(app)
    application.post_init = post_init

    # Jalankan
    print("🚀 Bot sedang berjalan...")
    application.run_polling()

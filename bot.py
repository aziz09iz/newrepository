import logging
import json
import os
import asyncio
from datetime import time, timedelta, datetime
import pytz

# Library Telegram & Scheduler
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from telegram.error import BadRequest

# --- KONFIGURASI ---
TOKEN = os.getenv("BOT_TOKEN")
JAKARTA_TZ = pytz.timezone('Asia/Jakarta')
FILE_DB = 'alarms.json'

# Setup Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- DATABASE LOGIC ---
def load_alarms():
    try:
        with open(FILE_DB, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_alarm_to_db(chat_id, time_str):
    alarms = load_alarms()
    # Cek duplikat biar gak double
    for a in alarms:
        if a['chat_id'] == chat_id and a['time'] == time_str:
            return
    alarms.append({"chat_id": chat_id, "time": time_str})
    with open(FILE_DB, 'w') as f:
        json.dump(alarms, f, indent=4)

def remove_alarm_from_db(chat_id, time_str):
    alarms = load_alarms()
    # Filter: Ambil semua KECUALI yang mau dihapus
    new_alarms = [a for a in alarms if not (a['chat_id'] == chat_id and a['time'] == time_str)]
    with open(FILE_DB, 'w') as f:
        json.dump(new_alarms, f, indent=4)

# --- FITUR BOT ---

async def send_alarm_message(context: ContextTypes.DEFAULT_TYPE):
    """Fungsi yang dipanggil saat alarm berbunyi"""
    job = context.job
    chat_id = job.data['chat_id']
    pesan = job.data.get('message', "⏰ ALARM! Waktunya bangun/beraktivitas!")
    
    try:
        await context.bot.send_message(chat_id=chat_id, text=pesan)
        print(f"✅ Sukses kirim alarm ke {chat_id}")
    except Exception as e:
        print(f"❌ Gagal kirim alarm: {e}")

async def set_alarm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command: /set HH:MM"""
    chat_id = update.effective_chat.id
    
    try:
        if not context.args:
            raise ValueError("Jam kosong")
            
        time_input = context.args[0] # HH:MM
        hour, minute = map(int, time_input.split(':'))
        
        # Nama job unik: "12345_07:00"
        job_name = f"{chat_id}_{time_input}"
        
        # Cek apakah sudah ada alarm yang sama di job queue
        current_jobs = context.job_queue.get_jobs_by_name(job_name)
        if current_jobs:
            await update.message.reply_text(f"⚠️ Alarm {time_input} sudah ada sebelumnya.")
            return

        # Simpan ke DB
        save_alarm_to_db(chat_id, time_input)
        
        # Jadwalkan
        new_job = context.job_queue.run_daily(
            send_alarm_message,
            time=time(hour=hour, minute=minute, tzinfo=JAKARTA_TZ),
            data={'chat_id': chat_id},
            name=job_name
        )
        
        # Info debug kapan trigger selanjutnya
        next_run = new_job.next_t.astimezone(JAKARTA_TZ).strftime('%Y-%m-%d %H:%M:%S')
        
        await update.message.reply_text(
            f"✅ Alarm diset jam {time_input} WIB!\n"
            f"📅 Akan bunyi berikutnya pada: {next_run}"
        )
        print(f"Alarm baru diset user {chat_id} untuk {next_run}")
        
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Format salah. Gunakan: /set HH:MM (Contoh: /set 07:00)")

async def stop_alarm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command: /stop HH:MM"""
    chat_id = update.effective_chat.id
    try:
        time_input = context.args[0]
        job_name = f"{chat_id}_{time_input}"
        
        jobs = context.job_queue.get_jobs_by_name(job_name)
        if not jobs:
            await update.message.reply_text(f"❌ Tidak ditemukan alarm jam {time_input}.")
            return
            
        # Hapus semua job dengan nama itu (biasanya cuma 1)
        for job in jobs:
            job.schedule_removal()
            
        # Hapus dari DB
        remove_alarm_from_db(chat_id, time_input)
        
        await update.message.reply_text(f"🗑️ Alarm jam {time_input} berhasil dihapus/dimatikan.")
        
    except (IndexError, ValueError):
        await update.message.reply_text("Gunakan: /stop HH:MM (Contoh: /stop 07:00)")

async def list_alarms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command: /list"""
    chat_id = update.effective_chat.id
    alarms = load_alarms()
    
    # Filter alarm milik user ini saja
    user_alarms = [a['time'] for a in alarms if a['chat_id'] == chat_id]
    user_alarms.sort() # Urutkan jam
    
    if not user_alarms:
        await update.message.reply_text("📭 Kamu belum punya alarm aktif.")
    else:
        text = "📋 **Daftar Alarm Kamu:**\n" + "\n".join([f"- {t} WIB" for t in user_alarms])
        await update.message.reply_text(text)

async def test_alarm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command: /test (Bunyi dalam 10 detik)"""
    chat_id = update.effective_chat.id
    await update.message.reply_text("🧪 Tes dimulai! Alarm akan bunyi dalam 10 detik...")
    
    context.job_queue.run_once(
        send_alarm_message,
        when=10, # 10 detik dari sekarang
        data={'chat_id': chat_id, 'message': "🧪 INI TES ALARM! Bot berfungsi normal."},
        name=f"{chat_id}_test"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "👋 Halo! Saya Bot Alarm 2.0\n\n"
        "**Perintah:**\n"
        "/set HH:MM - Pasang alarm harian\n"
        "/stop HH:MM - Hapus alarm\n"
        "/list - Lihat daftar alarm\n"
        "/test - Cek bot hidup (bunyi dalam 10 detik)"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def restore_alarms(application):
    alarms = load_alarms()
    print(f"🔄 Mengembalikan {len(alarms)} alarm dari database...")
    for alarm in alarms:
        try:
            chat_id = alarm['chat_id']
            time_str = alarm['time']
            h, m = map(int, time_str.split(':'))
            job_name = f"{chat_id}_{time_str}"
            
            application.job_queue.run_daily(
                send_alarm_message,
                time=time(hour=h, minute=m, tzinfo=JAKARTA_TZ),
                data={'chat_id': chat_id},
                name=job_name
            )
        except Exception as e:
            print(f"Gagal restore alarm: {e}")

# --- MAIN PROGRAM ---
if __name__ == '__main__':
    if not TOKEN:
        print("❌ ERROR: BOT_TOKEN belum diset di Railway Variables!")
        exit()

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('set', set_alarm))
    application.add_handler(CommandHandler('stop', stop_alarm))
    application.add_handler(CommandHandler('list', list_alarms))
    application.add_handler(CommandHandler('test', test_alarm))

    async def post_init(app):
        await restore_alarms(app)
    application.post_init = post_init

    print("🚀 Bot Versi 2.0 berjalan...")
    application.run_polling()

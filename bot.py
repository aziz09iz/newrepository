import logging
import json
import os
from datetime import time, datetime, timedelta
import pytz

# Library Telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, 
    ContextTypes, 
    CommandHandler, 
    CallbackQueryHandler
)

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

def save_alarm_to_db(chat_id, time_str, message, alarm_type):
    alarms = load_alarms()
    # Hapus duplikat lama (update)
    alarms = [a for a in alarms if not (a['chat_id'] == chat_id and a['time'] == time_str)]
    
    alarms.append({
        "chat_id": chat_id, 
        "time": time_str,
        "message": message,
        "type": alarm_type # 'daily', 'workdays', atau 'once'
    })
    with open(FILE_DB, 'w') as f:
        json.dump(alarms, f, indent=4)

def remove_alarm_from_db(chat_id, time_str):
    alarms = load_alarms()
    new_alarms = [a for a in alarms if not (a['chat_id'] == chat_id and a['time'] == time_str)]
    with open(FILE_DB, 'w') as f:
        json.dump(new_alarms, f, indent=4)

# --- FITUR UTAMA ---

async def send_alarm_message(context: ContextTypes.DEFAULT_TYPE):
    """Saat alarm bunyi"""
    job = context.job
    chat_id = job.data['chat_id']
    pesan_custom = job.data.get('message', 'Waktunya aktivitas!')
    alarm_type = job.data.get('type', 'daily')
    time_str = job.data.get('time_str')

    # Tombol Snooze & Stop
    keyboard = [
        [
            InlineKeyboardButton("💤 5 Menit Lagi", callback_data="snooze"),
            InlineKeyboardButton("✅ Matikan", callback_data="stop_snooze")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Kirim Pesan
    try:
        await context.bot.send_message(
            chat_id=chat_id, 
            text=f"⏰ **ALARM!**\n\n📝 {pesan_custom}", 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"Gagal kirim ke {chat_id}: {e}")

    # KHUSUS ALARM SEKALI JALAN:
    # Setelah bunyi, langsung hapus dari database dan job queue
    if alarm_type == 'once':
        remove_alarm_from_db(chat_id, time_str)
        job.schedule_removal()
        print(f"Alarm sekali jalan ({time_str}) milik {chat_id} telah dihapus.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle tombol"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "stop_snooze":
        await query.edit_message_text(text=f"✅ Alarm dimatikan.")
        
    elif query.data == "snooze":
        await query.edit_message_text(text="💤 Oke, ditunda 5 menit.")
        # Buat job sementara untuk snooze (sekali jalan)
        context.job_queue.run_once(
            send_alarm_message,
            when=300, # 300 detik
            data={
                'chat_id': query.message.chat_id, 
                'message': "SNOOZE: Bangun woy!",
                'type': 'snooze', # Tipe snooze gak perlu disimpan ke DB
                'time_str': '00:00'
            }
        )

# Fungsi Pembuat Alarm (Core Logic)
async def create_alarm(update, context, alarm_type):
    chat_id = update.effective_chat.id
    try:
        if not context.args:
            raise ValueError("Argument kosong")
            
        time_input = context.args[0] # HH:MM
        # Ambil pesan custom
        custom_msg = " ".join(context.args[1:]) if len(context.args) > 1 else "Alarm!"

        hour, minute = map(int, time_input.split(':'))
        job_name = f"{chat_id}_{time_input}"
        
        # Simpan ke DB
        save_alarm_to_db(chat_id, time_input, custom_msg, alarm_type)
        
        # Hapus job lama kalau ada (agar tidak double)
        current_jobs = context.job_queue.get_jobs_by_name(job_name)
        for job in current_jobs: job.schedule_removal()

        # LOGIKA PENJADWALAN
        if alarm_type == 'once':
            # Hitung waktu target untuk alarm sekali jalan
            now = datetime.now(JAKARTA_TZ)
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target_time <= now:
                target_time += timedelta(days=1) # Kalau jam sudah lewat, set untuk besok
            
            context.job_queue.run_once(
                send_alarm_message,
                when=target_time,
                data={'chat_id': chat_id, 'message': custom_msg, 'type': 'once', 'time_str': time_input},
                name=job_name
            )
            tipe_teks = "Sekali Jalan"

        else:
            # Alarm Harian / Kerja
            # PERBAIKAN DI SINI:
            # Kita harus definisikan hari secara eksplisit.
            # 0-4 = Senin-Jumat
            # 0-6 = Senin-Minggu (Setiap Hari)
            if alarm_type == 'workdays':
                days_filter = (0, 1, 2, 3, 4)
            else:
                days_filter = (0, 1, 2, 3, 4, 5, 6) # <--- INI PERBAIKANNYA (Tidak boleh None)
            
            context.job_queue.run_daily(
                send_alarm_message,
                time=time(hour=hour, minute=minute, tzinfo=JAKARTA_TZ),
                days=days_filter, 
                data={'chat_id': chat_id, 'message': custom_msg, 'type': alarm_type, 'time_str': time_input},
                name=job_name
            )
            tipe_teks = "Senin-Jumat" if alarm_type == 'workdays' else "Setiap Hari"

        await update.message.reply_text(
            f"✅ Alarm **{tipe_teks}** diset jam `{time_input}`\n📝 Pesan: {custom_msg}",
            parse_mode='Markdown'
        )
        
    except (IndexError, ValueError):
        cmd_map = {'daily': '/set', 'workdays': '/kerja', 'once': '/sekali'}
        await update.message.reply_text(f"❌ Format: `{cmd_map[alarm_type]} HH:MM Pesan`")

# Wrapper Commands
async def set_daily(update, context): await create_alarm(update, context, 'daily')
async def set_workdays(update, context): await create_alarm(update, context, 'workdays')
async def set_once(update, context): await create_alarm(update, context, 'once')

async def list_alarms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    alarms = load_alarms()
    my_alarms = [a for a in alarms if a['chat_id'] == update.effective_chat.id]
    my_alarms.sort(key=lambda x: x['time'])
    
    if not my_alarms:
        await update.message.reply_text("📭 Belum ada alarm.")
    else:
        msg = "📋 **Daftar Alarm Kamu:**\n\n"
        for a in my_alarms:
            t = a.get('type', 'daily')
            if t == 'workdays': label = "🏢 Sen-Jum"
            elif t == 'once': label = "1️⃣ Sekali"
            else: label = "🔁 Tiap Hari"
            
            msg += f"• `{a['time']}` ({label}) - {a['message']}\n"
        await update.message.reply_text(msg, parse_mode='Markdown')

async def stop_alarm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        time_input = context.args[0]
        job_name = f"{update.effective_chat.id}_{time_input}"
        jobs = context.job_queue.get_jobs_by_name(job_name)
        
        if jobs:
            for job in jobs: job.schedule_removal()
            remove_alarm_from_db(update.effective_chat.id, time_input)
            await update.message.reply_text(f"🗑️ Alarm jam {time_input} dihapus.")
        else:
            await update.message.reply_text(f"❌ Tidak ketemu alarm jam {time_input}")
    except:
        await update.message.reply_text("Gunakan: `/stop HH:MM`", parse_mode='Markdown')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **Bot Alarm V5.0 (Final Pro)**\n\n"
        "1️⃣ `/set 07:00 [Pesan]` - Tiap Hari\n"
        "2️⃣ `/kerja 07:00 [Pesan]` - Senin-Jumat\n"
        "3️⃣ `/sekali 15:00 [Pesan]` - Cuma Hari Ini\n"
        "4️⃣ `/list` - Cek Jadwal\n"
        "5️⃣ `/stop 07:00` - Hapus Alarm\n"
        "6️⃣ `/test` - Tes Bunyi",
        parse_mode='Markdown'
    )

async def test_alarm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Tes bunyi dalam 5 detik...")
    context.job_queue.run_once(
        send_alarm_message, when=5, 
        data={'chat_id': update.effective_chat.id, 'message': "TESTING!", 'type': 'test', 'time_str': '00:00'}
    )

async def restore_alarms(application):
    alarms = load_alarms()
    print(f"🔄 Restore {len(alarms)} alarm...")
    for a in alarms:
        try:
            h, m = map(int, a['time'].split(':'))
            t = a.get('type', 'daily')
            chat_id = a['chat_id']
            msg = a.get('message', 'Alarm')
            time_str = a['time']
            job_name = f"{chat_id}_{time_str}"

            if t == 'once':
                # Restore alarm sekali jalan
                now = datetime.now(JAKARTA_TZ)
                target = now.replace(hour=h, minute=m, second=0, microsecond=0)
                if target <= now: target += timedelta(days=1)
                
                application.job_queue.run_once(
                    send_alarm_message, when=target,
                    data={'chat_id': chat_id, 'message': msg, 'type': t, 'time_str': time_str},
                    name=job_name
                )
            else:
                # Alarm harian/kerja
                if t == 'workdays':
                    days_filter = (0, 1, 2, 3, 4)
                else:
                    days_filter = (0, 1, 2, 3, 4, 5, 6) # <--- PERBAIKAN JUGA DI SINI

                application.job_queue.run_daily(
                    send_alarm_message,
                    time=time(hour=h, minute=m, tzinfo=JAKARTA_TZ),
                    days=days_filter,
                    data={'chat_id': chat_id, 'message': msg, 'type': t, 'time_str': time_str},
                    name=job_name
                )
        except Exception as e:
            print(f"Error restore: {e}")

if __name__ == '__main__':
    if not TOKEN: exit()
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('set', set_daily))
    application.add_handler(CommandHandler('kerja', set_workdays))
    application.add_handler(CommandHandler('sekali', set_once))
    application.add_handler(CommandHandler('stop', stop_alarm))
    application.add_handler(CommandHandler('list', list_alarms))
    application.add_handler(CommandHandler('test', test_alarm))
    application.add_handler(CallbackQueryHandler(button_handler))

    application.post_init = lambda app: restore_alarms(app)
    
    print("🚀 Bot V5.1 (Fixed Days Error) Running...")
    application.run_polling()

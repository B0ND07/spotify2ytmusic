import os
import sys
import time
import threading
from dotenv import load_dotenv

# Load any configurations from .env
load_dotenv()

# Global Lock to prevent multiple sync operations from running concurrently
sync_lock = threading.Lock()

# Telegram Bot configurations
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = None
if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
    try:
        import telebot
        bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
    except ImportError:
        print("[WARNING] pyTelegramBotAPI is not installed. Telegram features will be disabled.")

def send_telegram_message(message):
    if bot and TELEGRAM_CHAT_ID:
        try:
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        except Exception as e:
            print(f"[ERROR] Failed to send Telegram message: {e}")

def run_sync_cycle(triggered_by="Scheduled Loop"):
    # Attempt to acquire lock without blocking to immediately reject concurrent runs
    if not sync_lock.acquire(blocking=False):
        msg = f"⚠️ [{triggered_by}] A sync is already running. Request ignored."
        print(msg)
        send_telegram_message(msg)
        return False
        
    try:
        start_time = time.strftime('%Y-%m-%d %H:%M:%S')
        log_header = f"Starting Sync Cycle ({triggered_by}) at {start_time}"
        print("=" * 60)
        print(log_header)
        print("=" * 60)
        send_telegram_message(f"🔄 {log_header}")
        
        # 1. Download updated CSV from Exportify
        print("\n[Step 1/2] Downloading latest Spotify Liked Songs CSV...")
        from exportify_downloader import download_liked_songs
        success = download_liked_songs()
        
        if not success:
            fail_msg = "❌ [FAILED] Could not download Spotify CSV. Sync cancelled."
            print(fail_msg)
            send_telegram_message(fail_msg)
            return False
            
        # 2. Sync to YouTube Music
        print("\n[Step 2/2] Syncing to YouTube Music...")
        import yt_music_sync
        try:
            success_count, failed_count = yt_music_sync.main()
            
            success_msg = (
                f"✅ Sync Completed Successfully!\n"
                f"- Synced: {success_count}\n"
                f"- Failed: {failed_count}"
            )
            print(f"\n{success_msg}")
            send_telegram_message(success_msg)
            return True
        except Exception as e:
            err_msg = f"❌ [FAILED] YouTube Music sync failed: {e}"
            print(err_msg)
            send_telegram_message(err_msg)
            return False
            
    finally:
        sync_lock.release()

def scheduler_loop(interval_hours):
    interval_secs = float(interval_hours) * 3600
    print(f"Continuous Scheduler running in background. Interval: {interval_hours} hours.")
    
    # Run the first sync immediately on startup
    run_sync_cycle(triggered_by="Startup Sync")
    
    while True:
        print(f"\n[Scheduler] Waiting {interval_hours} hours before next cycle...")
        time.sleep(interval_secs)
        run_sync_cycle(triggered_by="Scheduled Loop")

def setup_telegram_handlers():
    @bot.message_handler(commands=['start', 'help'])
    def send_welcome(message):
        # Security check: only respond to the authorized chat ID
        if str(message.chat.id) != str(TELEGRAM_CHAT_ID):
            return
        welcome_text = (
            "🤖 Spotify to YT Music Sync Bot is active!\n\n"
            "Commands:\n"
            "/sync - Trigger a sync immediately\n"
            "/status - Check current sync status"
        )
        bot.reply_to(message, welcome_text)

    @bot.message_handler(commands=['sync'])
    def trigger_manual_sync(message):
        if str(message.chat.id) != str(TELEGRAM_CHAT_ID):
            return
            
        bot.reply_to(message, "🚀 Manual sync triggered. Starting...")
        # Run sync in a separate thread so it doesn't block Telegram polling
        sync_thread = threading.Thread(
            target=run_sync_cycle,
            kwargs={"triggered_by": f"Telegram /sync from {message.from_user.first_name}"}
        )
        sync_thread.start()

    @bot.message_handler(commands=['status'])
    def check_status(message):
        if str(message.chat.id) != str(TELEGRAM_CHAT_ID):
            return
            
        if sync_lock.locked():
            status_text = "🔄 Status: A sync is currently running."
        else:
            status_text = "😴 Status: Idle. Waiting for scheduled run or /sync command."
        bot.reply_to(message, status_text)

def main():
    interval_hours = os.getenv("SYNC_INTERVAL", "12")
    
    if bot:
        print("Telegram bot detected. Initializing bot handlers...")
        setup_telegram_handlers()
        
        # Start the scheduler loop in a background thread
        scheduler_thread = threading.Thread(
            target=scheduler_loop, 
            args=(interval_hours,), 
            daemon=True
        )
        scheduler_thread.start()
        
        print("Starting Telegram Bot Polling (blocks main thread)...")
        send_telegram_message("🤖 Sync Bot has started online!")
        bot.infinity_polling()
    else:
        # Standard Loop fallback (if Telegram is not configured)
        print("Telegram Bot config missing or incomplete. Running standard scheduler loop.")
        try:
            interval_secs = float(interval_hours) * 3600
            print(f"Continuous Sync Mode enabled. Running every {interval_hours} hours.")
            while True:
                run_sync_cycle(triggered_by="Scheduled Loop")
                print(f"\nSleeping for {interval_hours} hours...")
                time.sleep(interval_secs)
        except ValueError:
            print("Invalid SYNC_INTERVAL in .env. Running once and exiting.")
            run_sync_cycle(triggered_by="Manual Run")

if __name__ == "__main__":
    main()

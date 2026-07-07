import os
import sys
import time
from dotenv import load_dotenv

# Load any configurations from .env
load_dotenv()

def run_sync_cycle():
    print("=" * 60)
    print(f"Starting Sync Cycle at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. Download updated CSV from Exportify
    print("\n[Step 1/2] Downloading latest Spotify Liked Songs CSV...")
    # Dynamic import to ensure fresh execution context
    from exportify_downloader import download_liked_songs
    success = download_liked_songs()
    
    if not success:
        print("\n[FAILED] Could not download Spotify CSV. Skipping sync step.")
        return False
        
    # 2. Sync to YouTube Music
    print("\n[Step 2/2] Syncing to YouTube Music...")
    import yt_music_sync
    try:
        yt_music_sync.main()
    except Exception as e:
        print(f"\n[FAILED] Sync encountered an error: {e}")
        return False
        
    print("\nSync Cycle Completed successfully!")
    return True

def main():
    # To run continuously on a VPS, set SYNC_INTERVAL in hours (e.g. 12) in .env
    # Otherwise, it runs once and exits (ideal for cron jobs)
    interval_hours = os.getenv("SYNC_INTERVAL")
    
    if interval_hours:
        try:
            interval_secs = float(interval_hours) * 3600
            print(f"Continuous Sync Mode enabled. Running every {interval_hours} hours.")
            while True:
                run_sync_cycle()
                print(f"\nSleeping for {interval_hours} hours...")
                time.sleep(interval_secs)
        except ValueError:
            print("Invalid SYNC_INTERVAL in .env. Running once and exiting.")
            run_sync_cycle()
    else:
        run_sync_cycle()

if __name__ == "__main__":
    main()

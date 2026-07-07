# Spotify to YouTube Music Auto-Sync

An automated, lightweight sync tool designed to copy your Spotify Liked Songs library to YouTube Music. It runs headlessly at scheduled intervals on a VPS—**without requiring a Spotify Premium subscription**.

## How It Works
1. **Spotify Extraction**: Since Spotify restricts official API access for Free users, the script uses **Playwright** browser automation to navigate to [Exportify](https://exportify.app/). It mimics clicking the export button and downloads your Liked Songs CSV file (`spotify_liked_songs.csv`).
2. **YouTube Music Sync**: It reads the CSV, searches YouTube Music for matching tracks (favoring official songs over video matches), likes the found tracks (saving them to your library), and logs successfully synced track IDs to `synced_tracks.txt` to enable fast, incremental runs.
3. **VPS Orchestrator**: The script caches browser session states and uses loop timers to run completely headlessly in the background.

## Getting Started (Local Setup & Authorization)

You must run the script locally at least once to authorize both platforms and capture the session cache.

### 1. Installation
Clone the repository and install the dependencies:
```bash
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
playwright install chromium
```

### 2. Run and Authenticate
Start the sync:
```bash
python auto_sync.py
```
- **Spotify Login**: A browser window will open. Click "Get Started" on Exportify, log into your Spotify account, and click **Authorize**. The script will download the CSV and save your Spotify session in the `browser_profile/` folder.
- **YouTube Music Login**: When the terminal asks you for headers, follow these steps to link your account:
  1. Open your **Firefox browser** and go to [music.youtube.com](https://music.youtube.com) (make sure you are logged in).
  2. Press **F12** on your keyboard (or right-click anywhere on the page and select **Inspect**) to open the Developer Tools.
  3. Click on the **Network** tab at the top of the developer panel.
  4. Perform an action on the page (like searching for a song) to load some data.
  5. In the Network tab, look for a request named `search` or `browse` under the "Name" column and click it.
  6. Right-click the request, select **Copy Value**, and then click **Copy Request Headers**.
  7. Go back to your terminal, paste the copied text, press **Enter**, and then save it by pressing:
     - **Windows**: `Ctrl+Z` then `Enter`.
     - **Mac/Linux**: `Ctrl+D`.
  This will create your `browser.json` credentials file.

Once completed, the script will sync all your Liked Songs.

---

## Deployment to VPS (Fully Headless)

Once the local run completes and generates the cached sessions, you can migrate to your VPS:

### 1. Copy Files to VPS
Transfer these files and folders to your VPS:
- `auto_sync.py`
- `exportify_downloader.py`
- `yt_music_sync.py`
- `requirements.txt`
- **`browser_profile/`** (Contains your authenticated Spotify cookies)
- **`browser.json`** (Contains your authenticated YT Music headers)
- **`synced_tracks.txt`** (Optional, to keep your sync history)

### 2. Configure Environment
Create a `.env` file on your VPS:
```env
IS_VPS=true
# Sync interval in hours (e.g. 12 to run every 12 hours)
# Omit this variable if you prefer triggering it via a system cron job instead
SYNC_INTERVAL=12
```

### 3. Run on VPS
SSH into your VPS, install dependencies, and start the sync:
```bash
pip install -r requirements.txt
playwright install chromium
python auto_sync.py
```

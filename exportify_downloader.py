import os
import sys
import json
from playwright.sync_api import sync_playwright

def load_and_inject_cookies(context, cookie_file="spotify_cookies.json"):
    if not os.path.exists(cookie_file):
        return False
    try:
        with open(cookie_file, 'r', encoding='utf-8') as f:
            raw_cookies = json.load(f)
        
        cookies = []
        for c in raw_cookies:
            cookie = {
                "name": c.get("name"),
                "value": c.get("value"),
                "domain": c.get("domain"),
                "path": c.get("path", "/"),
                "secure": c.get("secure", True),
                "httpOnly": c.get("httpOnly", False),
            }
            if "expirationDate" in c:
                cookie["expires"] = int(c["expirationDate"])
            elif "expires" in c:
                cookie["expires"] = int(c["expires"])
            cookies.append(cookie)
            
        print(f"Injecting {len(cookies)} cookies from {cookie_file}...")
        context.add_cookies(cookies)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to load/inject cookies: {e}")
        return False

def download_liked_songs():
    profile_dir = os.path.abspath("browser_profile")
    csv_dest = "spotify_liked_songs.csv"
    
    # We check if we are running in VPS mode via an environment variable
    is_vps = os.getenv("IS_VPS", "false").lower() == "true"
    headless = is_vps
    
    print(f"Launching browser (headless={headless})...")
    
    with sync_playwright() as p:
        try:
            # Persistent context keeps cookies/session active across runs
            context = p.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                headless=headless,
                viewport={'width': 1280, 'height': 800}
            )
            
            page = context.new_page()
            
            print("Navigating to https://exportify.app/ ...")
            page.goto("https://exportify.app/")
            
            # Click "Get Started" if present
            get_started = page.locator("text=Get Started")
            if get_started.is_visible():
                get_started.click()
            
            print("Waiting for Liked Songs table to load...")
            try:
                # Wait for the Liked Songs entry to load (indicates logged in state)
                page.wait_for_selector("tr:has-text('Liked')", timeout=30000)
            except Exception:
                cookie_file = "spotify_cookies.json"
                if os.path.exists(cookie_file):
                    print("\n[INFO] Playlists did not load automatically. Attempting cookie import from spotify_cookies.json...")
                    if load_and_inject_cookies(context, cookie_file):
                        print("Reloading Exportify...")
                        page.goto("https://exportify.app/")
                        if get_started.is_visible():
                            get_started.click()
                        try:
                            page.wait_for_selector("tr:has-text('Liked')", timeout=30000)
                            print("[SUCCESS] Session successfully restored via imported cookies!")
                        except Exception:
                            if headless:
                                print("\n[ERROR] Playlists still did not load after importing cookies.")
                                context.close()
                                return False
                    else:
                        if headless:
                            context.close()
                            return False
                else:
                    if headless:
                        print("\n[ERROR] Playlists did not load automatically.")
                        print("This means the browser profile session has expired or is not logged in.")
                        print("Please run this script LOCALLY (non-headless) first to authenticate your Spotify account,")
                        print("or place a valid 'spotify_cookies.json' in this directory.")
                        context.close()
                        return False
                    else:
                        print("\n[INFO] Please log in to Spotify and authorize Exportify in the browser window...")
                        # Wait up to 5 minutes for the user to complete login in the opened browser window
                        page.wait_for_selector("tr:has-text('Liked')", timeout=300000)
            
            print("Found 'Liked' row. Starting export...")
            
            # Locate the specific row for Liked Songs (using .first to match the main 'Liked' row)
            liked_songs_row = page.locator("tr", has_text="Liked").first
            
            # Locate the Export button in that row
            export_button = liked_songs_row.locator("button:has-text('Export')")
            
            # Wait for download to start when button is clicked
            with page.expect_download(timeout=120000) as download_info:
                export_button.click()
                
            download = download_info.value
            download.save_as(csv_dest)
            
            print(f"Successfully downloaded latest liked songs to: {csv_dest}")
            context.close()
            return True
            
        except Exception as e:
            print(f"\n[ERROR] An error occurred during browser automation: {e}")
            return False

if __name__ == "__main__":
    download_liked_songs()

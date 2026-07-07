import os
import csv
import sys
import time
from ytmusicapi import YTMusic, setup

import re

def preprocess_headers(raw_input):
    # Header keywords we want to split on if they are squashed together
    keywords = [
        "Host", "User-Agent", "Accept", "Accept-Language", "Accept-Encoding",
        "Content-Type", "Content-Length", "Referer", "Content-Encoding",
        "X-Goog-Visitor-Id", "X-Youtube-Bootstrap-Logged-In", "X-Youtube-Client-Name",
        "X-Youtube-Client-Version", "X-Goog-AuthUser", "X-Origin", "Origin",
        "Sec-Fetch-Dest", "Sec-Fetch-Mode", "Sec-Fetch-Site", "Authorization",
        "Connection", "Alt-Used", "Cookie", "Priority", "TE"
    ]
    
    processed = raw_input
    # Insert newlines before headers if they are stuck together (e.g. "HTTP/3Host:" -> "\nHost:")
    for kw in keywords:
        processed = re.sub(rf'(?<!\n)({re.escape(kw)}:)', r'\n\1', processed)
    
    return processed

def authenticate_ytmusic():
    headers_file = "browser.json"
    if not os.path.exists(headers_file):
        print("Authentication credentials (browser.json) not found.")
        print("Starting YouTube Music Browser Headers setup...")
        print("Please follow these steps to get your request headers:")
        print("1. Open https://music.youtube.com in your web browser and ensure you are logged in.")
        print("2. Open Developer Tools (Press F12 or right-click -> Inspect).")
        print("3. Go to the Network tab.")
        print("4. Find a request to 'music.youtube.com' (e.g., search, browse) and click it.")
        print("5. In the Request Headers section, copy all the headers.")
        print("6. Paste them below and press Enter followed by Ctrl+Z (Windows) or Ctrl+D (Unix) to save:")
        
        # Read from stdin until EOF
        raw_headers = sys.stdin.read()
        preprocessed = preprocess_headers(raw_headers)
        
        try:
            # setup handles parsing the preprocessed headers and saving to browser.json
            setup(filepath=headers_file, headers_raw=preprocessed)
            print(f"\nAuthentication successful! Credentials saved to {headers_file}")
        except Exception as e:
            print(f"\nError during browser headers setup: {e}")
            sys.exit(1)
            
    return YTMusic(headers_file)

def find_song_video_id(yt, title, artists):
    query = f"{title} {artists}"
    
    # 1. Search for official songs first
    try:
        results = yt.search(query, filter="songs")
        if results and 'videoId' in results[0]:
            return results[0]['videoId']
    except Exception as e:
        print(f"  Error searching songs for query '{query}': {e}")

    # 2. Search for videos next
    try:
        results = yt.search(query, filter="videos")
        if results and 'videoId' in results[0]:
            return results[0]['videoId']
    except Exception as e:
        pass

    # 3. Fallback to general search
    try:
        results = yt.search(query)
        for res in results:
            if res.get('resultType') in ['song', 'video'] and 'videoId' in res:
                return res['videoId']
    except Exception as e:
        pass

    return None

def main():
    csv_file = "spotify_liked_songs.csv"
    sync_file = "synced_tracks.txt"
    
    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} not found.")
        print("Please export your Liked Songs from https://exportify.app/ and place the CSV in this directory.")
        return

    # Authenticate YTMusic
    print("Initializing YouTube Music client...")
    yt = authenticate_ytmusic()

    # Load already synced tracks to skip them
    synced_uris = set()
    if os.path.exists(sync_file):
        with open(sync_file, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                if " | " in line_str:
                    uri = line_str.split(" | ", 1)[0].strip()
                else:
                    uri = line_str
                synced_uris.add(uri)
    
    print(f"Loaded {len(synced_uris)} already synced tracks from cache.")

    # Read Spotify tracks from CSV
    tracks_to_sync = []
    with open(csv_file, mode="r", encoding="utf-8-sig") as f:
        # csv.DictReader handles headers automatically, utf-8-sig handles BOM if present
        reader = csv.DictReader(f)
        
        # Verify required columns are present (with case-insensitive fallback)
        headers = reader.fieldnames
        uri_col = next((h for h in headers if h.lower() in ["track uri", "uri"]), None)
        name_col = next((h for h in headers if h.lower() in ["track name", "name", "title"]), None)
        artists_col = next((h for h in headers if h.lower() in ["artist name(s)", "artist", "artists"]), None)
        
        if not (uri_col and name_col and artists_col):
            print("Error: The CSV file does not contain the required columns ('Track URI', 'Track Name', 'Artist Name(s)').")
            print(f"Found headers: {headers}")
            return
            
        for row in reader:
            uri = row[uri_col].strip()
            name = row[name_col].strip()
            artists = row[artists_col].strip()
            
            if uri not in synced_uris:
                tracks_to_sync.append({
                    'uri': uri,
                    'name': name,
                    'artists': artists
                })

    total_tracks = len(tracks_to_sync)
    if total_tracks == 0:
        print("All tracks from CSV are already synced! Nothing to do.")
        return

    print(f"Found {total_tracks} new tracks to sync.")
    
    success_count = 0
    failed_count = 0

    # Open sync file in append mode to update it live
    with open(sync_file, "a", encoding="utf-8") as cache_f:
        for idx, track in enumerate(tracks_to_sync, 1):
            name = track['name']
            artists = track['artists']
            uri = track['uri']
            
            print(f"[{idx}/{total_tracks}] Syncing: {name} - {artists} ...")
            
            # Find the song on YouTube Music
            video_id = find_song_video_id(yt, name, artists)
            
            if video_id:
                try:
                    # Rate the song as LIKE (adds to Liked Music library)
                    yt.rate_song(video_id, "LIKE")
                    success_count += 1
                    print("  -> Synced successfully!")
                    
                    # Update cache live so we don't lose progress if interrupted
                    cache_f.write(f"{uri} | {name}\n")
                    cache_f.flush()
                except Exception as e:
                    failed_count += 1
                    print(f"  -> Error liking song on YouTube Music: {e}")
            else:
                failed_count += 1
                print("  -> Could not find track on YouTube Music.")

            # Respect rate limits and sleep briefly
            time.sleep(0.5)

    print("\nSync summary:")
    print(f"- Successfully synced: {success_count}")
    print(f"- Failed to sync: {failed_count}")
    print(f"Done! Progression stored in {sync_file}")

if __name__ == "__main__":
    main()


import csv
import os
import requests
import subprocess
import time
import shutil
from collections import defaultdict
from rich.console import Console
from rich.progress import track as rich_track
from dotenv import load_dotenv

load_dotenv()
ARL = os.getenv('DEEZER_ARL')

# Ensure ARL is available for deemix (via config.json or env)
# Deemix looks for config.json in current dir if --portable
import json
config_data = {
    "arl": ARL,
    "downloadLocation": "Downloads",
    "tracknameTemplate": "%artist% - %title%",
    "createPlaylistFolder": False, # We handle folder structure manually via -p
    "createArtistFolder": False,
    "createAlbumFolder": False,
    "downloadArtwork": True,
    "fallbackBitrate": True,
}

# Write config only if ARL is present
if ARL:
    with open('config.json', 'w') as f:
        json.dump(config_data, f, indent=2)

console = Console()

def sanitize_filename(name):
    return "".join([c for c in name if c.isalnum() or c in " -_()."])

def search_deezer(query):
    try:
        # Search track
        url = f"https://api.deezer.com/search?q={query}&limit=1"
        r = requests.get(url) 
        data = r.json()
        if 'data' in data and len(data['data']) > 0:
            return data['data'][0]['link']
    except:
        pass
    return None

def download_youtube_batch(tracks, output_folder):
    # tracks is list of dictionaries (row)
    if not tracks: return
    
    console.print(f"[yellow]⚠️ Downloading {len(tracks)} tracks from YouTube...[/yellow]")
    
    for row in rich_track(tracks, description="YouTube Fallback..."):
        query = f"{row['Artist Name']} - {row['Track Name']}"
        # yt-dlp
        cmd = [
            "yt-dlp",
            "-x", "--audio-format", "mp3",
            "--embed-thumbnail", "--add-metadata",
            "--no-playlist",
            "-o", f"{output_folder}/%(artist)s - %(title)s.%(ext)s",
            f"ytsearch1:{query}"
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def main():
    if not os.path.exists("spotify_export.csv"):
        console.print("[red]❌ spotify_export.csv not found![/red]")
        return

    # 1. Group by Playlist
    playlists = defaultdict(list)
    with open("spotify_export.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            playlists[row['Playlist']].append(row)

    console.print(f"📦 Found {len(playlists)} playlists.")

    # 2. Process each playlist
    for pl_name, tracks in playlists.items():
        console.print(f"\n📂 Processing Playlist: [bold]{pl_name}[/bold] ({len(tracks)} tracks)")
        
        pl_folder = sanitize_filename(pl_name)
        download_path = os.path.join("Downloads", pl_folder)
        if not os.path.exists(download_path):
            os.makedirs(download_path)

        deezer_matches = [] # List of (row, link)
        fallback_tracks = []

        # Search Phase
        console.print("🔍 Searching Deezer...")
        for row in rich_track(tracks, description="Searching..."):
            query = f"{row['Artist Name']} - {row['Track Name']}"
            link = search_deezer(query)
            if link:
                deezer_matches.append((row, link))
            else:
                fallback_tracks.append(row)
        
        # Download Phase: Deemix
        if deezer_matches:
            console.print(f"[blue]⬇️ Downloading {len(deezer_matches)} tracks via Deemix...[/blue]")
            # Batch URLs (limit command line length)
            batch_size = 20 # Conservative batch
            for i in range(0, len(deezer_matches), batch_size):
                chunk = deezer_matches[i:i+batch_size]
                batch_urls = [x[1] for x in chunk]
                batch_rows = [x[0] for x in chunk]
                
                cmd = ["python", "-m", "deemix", "--portable", "-p", download_path] + batch_urls
                try:
                    # Add timeout to avoid hanging if auth fails
                    # Check=True to raise error on non-zero exit
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, timeout=45, check=True) 
                except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                    console.print("[red]⚠️ Deemix failed/timed out. Adding batch to YouTube fallback...[/red]")
                    fallback_tracks.extend(batch_rows)
                except Exception as e:
                    console.print(f"[red]Error running Deemix: {e}[/red]")
                    fallback_tracks.extend(batch_rows)
        
        # Download Phase: YouTube Fallback (only for failed searches)
        # Note: We don't verify if Deemix actually downloaded. 
        # Ideally we check file existence, but for now we assume Link -> Download.
        if fallback_tracks:
            download_youtube_batch(fallback_tracks, download_path)

    console.print("\n[bold green]✨ Batch Download Complete![/bold green]")

if __name__ == "__main__":
    main()

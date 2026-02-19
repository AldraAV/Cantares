
import csv
import os
import requests
import subprocess
import json
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

class BatchDownloader:
    def __init__(self, download_dir="Downloads"):
        self.arl = os.getenv('DEEZER_ARL')
        self.download_dir = download_dir
        self._setup_config()

    def _setup_config(self):
        # Config for Deemix
        config_data = {
            "arl": self.arl,
            "downloadLocation": self.download_dir,
            "tracknameTemplate": "%artist% - %title%",
            "createPlaylistFolder": False, 
            "createArtistFolder": False,
            "createAlbumFolder": False,
            "downloadArtwork": True,
            "fallbackBitrate": True,
        }
        if self.arl:
            with open('config.json', 'w') as f:
                json.dump(config_data, f, indent=2)

    def sanitize_filename(self, name):
        return "".join([c for c in name if c.isalnum() or c in " -_()."])

    def search_deezer(self, query):
        try:
            url = f"https://api.deezer.com/search?q={query}&limit=1"
            r = requests.get(url) 
            data = r.json()
            if 'data' in data and len(data['data']) > 0:
                return data['data'][0]['link']
        except:
            pass
        return None

    def download_youtube_batch(self, tracks, output_folder, callback=None):
        if not tracks: return
        
        for i, row in enumerate(tracks):
            query = f"{row['Artist Name']} - {row['Track Name']}"
            if callback: callback(f"YouTube Fallback: {query}")
            
            cmd = [
                "yt-dlp",
                "-x", "--audio-format", "mp3",
                "--embed-thumbnail", "--add-metadata",
                "--no-playlist",
                "-o", f"{output_folder}/%(artist)s - %(title)s.%(ext)s",
                f"ytsearch1:{query}"
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                if callback: callback(f"[red]Error: {result.stderr}[/red]")


    def process_csv(self, csv_path="spotify_export.csv", selected_playlists=None, range_config=None, callback=None):
        """
        selected_playlists: List of playlist names to process (None = All)
        range_config: {'offset': 0, 'limit': 100} (Per playlist)
        callback: function(message, progress_percent)
        """
        if not os.path.exists(csv_path):
            if callback: callback("CSV not found!", 0)
            return

        # 1. Load & Filter
        playlists = defaultdict(list)
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pl_name = row['Playlist']
                if selected_playlists and pl_name not in selected_playlists:
                    continue
                playlists[pl_name].append(row)

        total_playlists = len(playlists)
        current_pl_idx = 0

        # 2. Process
        for pl_name, tracks in playlists.items():
            current_pl_idx += 1
            if callback: callback(f"Playlist: {pl_name}", (current_pl_idx / total_playlists) * 100)

            # Apply Range
            offset = range_config.get('offset', 0) if range_config else 0
            limit = range_config.get('limit', len(tracks)) if range_config else len(tracks)
            
            tracks_slice = tracks[offset : offset + limit]
            
            pl_folder = self.sanitize_filename(pl_name)
            download_path = os.path.join(self.download_dir, pl_folder)
            if not os.path.exists(download_path):
                os.makedirs(download_path)

            deezer_matches = []
            fallback_tracks = []

            # Search
            for idx, row in enumerate(tracks_slice):
                if callback and idx % 5 == 0: 
                    callback(f"Searching: {row['Track Name']}", (current_pl_idx / total_playlists) * 100)
                
                query = f"{row['Artist Name']} - {row['Track Name']}"
                link = self.search_deezer(query)
                if link:
                    deezer_matches.append((row, link))
                else:
                    fallback_tracks.append(row)

            # Deemix
            if deezer_matches:
                if callback: callback(f"Downloading {len(deezer_matches)} via Deemix...", (current_pl_idx / total_playlists) * 100)
                batch_size = 20
                for i in range(0, len(deezer_matches), batch_size):
                    chunk = deezer_matches[i:i+batch_size]
                    batch_urls = [x[1] for x in chunk]
                    batch_rows = [x[0] for x in chunk]
                    
                    cmd = ["python", "-m", "deemix", "--portable", "-p", download_path] + batch_urls
                    try:
                        subprocess.run(cmd, stdout=subprocess.DEVNULL, timeout=45, check=True) 
                    except:
                        if callback: callback("Deemix timed out, using fallback...", (current_pl_idx / total_playlists) * 100)
                        fallback_tracks.extend(batch_rows)

            # YouTube
            if fallback_tracks:
                self.download_youtube_batch(fallback_tracks, download_path, lambda msg: callback(msg, (current_pl_idx / total_playlists) * 100))

        if callback: callback("Finished!", 100)

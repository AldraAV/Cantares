
import os
import csv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

# Load env variables (likely from root .env)
load_dotenv()

class SpotifyExporter:
    def __init__(self, update_callback=None):
        """
        Initialize Spotify Exporter.
        :param update_callback: Optional function(message) to report progress.
        """
        self.client_id = os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        self.redirect_uri = "https://nona-xi.vercel.app/callback"
        self.update_callback = update_callback or (lambda msg: print(msg))

    def authenticate(self):
        if not self.client_id or not self.client_secret:
            raise ValueError("❌ Missing credentials in .env (SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)")

        scope = "playlist-read-private user-library-read"
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope=scope,
            open_browser=True
        ))
        
        user = self.sp.current_user()
        self.update_callback(f"👤 Authenticated as: {user['display_name']}")
        return user

    def get_playlists(self):
        playlists = []
        results = self.sp.current_user_playlists(limit=50)
        playlists.extend(results['items'])
        while results['next']:
            results = self.sp.next(results)
            playlists.extend(results['items'])
        
        self.update_callback(f"📦 Found {len(playlists)} playlists.")
        return playlists

    def export_to_csv(self, filename="spotify_export.csv"):
        if not hasattr(self, 'sp'):
            self.authenticate()

        playlists = self.get_playlists()
        total_tracks = 0

        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Track Name", "Artist Name", "Album Name", "Playlist", "URI"])

            # 1. Export Playlists
            for pl in playlists:
                self.update_callback(f"🎵 Processing playlist: {pl['name']}...")
                results = self.sp.playlist_items(pl['id'])
                tracks = results['items']
                while results['next']:
                    results = self.sp.next(results)
                    tracks.extend(results['items'])
                
                for item in tracks:
                    track_data = item.get('track')
                    if not track_data: continue
                    
                    self._write_track(writer, track_data, pl['name'])
                    total_tracks += 1

            # 2. Export Liked Songs
            self.update_callback("💖 Processing 'Liked Songs'...")
            results = self.sp.current_user_saved_tracks(limit=50)
            tracks = results['items']
            while results['next']:
                results = self.sp.next(results)
                tracks.extend(results['items'])
            
            for item in tracks:
                track_data = item.get('track')
                if not track_data: continue
                self._write_track(writer, track_data, "Liked Songs")
                total_tracks += 1

        self.update_callback(f"✨ Export Complete! {total_tracks} tracks saved to {filename}")
        return total_tracks

    def _write_track(self, writer, track_data, playlist_name):
        name = track_data['name']
        artist = track_data['artists'][0]['name'] if track_data['artists'] else "Unknown"
        album = track_data['album']['name'] if track_data['album'] else "Unknown"
        uri = track_data['uri']
        writer.writerow([name, artist, album, playlist_name, uri])

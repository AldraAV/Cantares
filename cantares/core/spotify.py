
import os
import csv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class SpotifyExporter:
    def __init__(self):
        self.client_id = os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        self.redirect_uri = "https://nona-xi.vercel.app/callback"
        self.scope = "playlist-read-private user-library-read"
        self.sp = None
        self.user = None

    def authenticate(self):
        if not self.client_id or not self.client_secret:
            raise ValueError("Faltan credenciales de Spotify en .env")

        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope=self.scope,
            open_browser=True
        ))
        self.user = self.sp.current_user()
        return self.user

    def get_playlists(self):
        if not self.sp: self.authenticate()
        playlists = []
        results = self.sp.current_user_playlists(limit=50)
        playlists.extend(results['items'])
        while results['next']:
            results = self.sp.next(results)
            playlists.extend(results['items'])
        return playlists

    def get_playlist_tracks(self, playlist_id):
        if not self.sp: self.authenticate()
        tracks = []
        results = self.sp.playlist_items(playlist_id)
        tracks.extend(results['items'])
        while results['next']:
            results = self.sp.next(results)
            tracks.extend(results['items'])
        return tracks

    def get_liked_songs(self, limit=None):
        if not self.sp: self.authenticate()
        tracks = []
        results = self.sp.current_user_saved_tracks(limit=50)
        tracks.extend(results['items'])
        while results['next']:
            if limit and len(tracks) >= limit: break
            results = self.sp.next(results)
            tracks.extend(results['items'])
        return tracks[:limit] if limit else tracks

    def export_to_csv(self, playlists_to_export, include_liked=True, filename="spotify_export.csv", callback=None):
        """
        playlists_to_export: List of playlist dicts (or IDs)
        callback: function(current, total, message)
        """
        if not self.sp: self.authenticate()
        
        mode = "w" if not os.path.exists(filename) else "w" # Always overwrite for new batch? Or append? Let's overwrite for clean state if selected.
        
        total_steps = len(playlists_to_export) + (1 if include_liked else 0)
        current_step = 0

        with open(filename, mode, newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Track Name", "Artist Name", "Album Name", "Playlist", "URI"])

            for pl in playlists_to_export:
                current_step += 1
                if callback: callback(current_step, total_steps, f"Procesando: {pl['name']}")
                
                pl_tracks = self.get_playlist_tracks(pl['id'])
                for item in pl_tracks:
                    track_data = item.get('track')
                    if not track_data: continue
                    self._write_track(writer, track_data, pl['name'])

            if include_liked:
                current_step += 1
                if callback: callback(current_step, total_steps, "Procesando: Liked Songs")
                liked = self.get_liked_songs()
                for item in liked:
                    track_data = item.get('track')
                    if not track_data: continue
                    self._write_track(writer, track_data, "Liked Songs")

    def _write_track(self, writer, track_data, playlist_name):
        name = track_data['name']
        artist = track_data['artists'][0]['name'] if track_data['artists'] else "Unknown"
        album = track_data['album']['name'] if track_data['album'] else "Unknown"
        uri = track_data['uri']
        writer.writerow([name, artist, album, playlist_name, uri])

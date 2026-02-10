import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from ..config import Config

class SpotifyClient:
    def __init__(self):
        Config.validate()
        if Config.SPOTIFY_CLIENT_ID and Config.SPOTIFY_CLIENT_SECRET:
            auth_manager = SpotifyClientCredentials(
                client_id=Config.SPOTIFY_CLIENT_ID,
                client_secret=Config.SPOTIFY_CLIENT_SECRET
            )
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
        else:
            self.sp = None
            print("⚠️  Spotify credentials not found. Spotify search disabled.")

    def get_track_info(self, url):
        """Fetches metadata for a Spotify track URL."""
        if not self.sp:
            return None
        try:
            track = self.sp.track(url)
            artists = ", ".join([artist['name'] for artist in track['artists']])
            return {
                "title": track['name'],
                "artist": artists,
                "album": track['album']['name'],
                "cover_url": track['album']['images'][0]['url'] if track['album']['images'] else None,
                "duration_ms": track['duration_ms'],
                "release_date": track['album']['release_date'],
                "spotify_url": track['external_urls']['spotify']
            }
        except Exception as e:
            print(f"Error fetching track info: {e}")
            return None

    def search_track(self, query):
        """Searches for a track on Spotify."""
        if not self.sp:
            return None
        results = self.sp.search(q=query, type='track', limit=1)
        if results['tracks']['items']:
            track = results['tracks']['items'][0]
            artists = ", ".join([artist['name'] for artist in track['artists']])
            return {
                "title": track['name'],
                "artist": artists,
                "album": track['album']['name'],
                "cover_url": track['album']['images'][0]['url'] if track['album']['images'] else None,
                "duration_ms": track['duration_ms'],
                "release_date": track['album']['release_date'],
                "spotify_url": track['external_urls']['spotify']
            }
        return None

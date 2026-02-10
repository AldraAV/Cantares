
import requests
import re
from hashlib import md5
from binascii import a2b_hex, b2a_hex
from Crypto.Cipher import Blowfish, AES
from Crypto.Util import Counter
from rich.console import Console
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.oauth2 import SpotifyClientCredentials
import os
from dotenv import load_dotenv

load_dotenv()

console = Console()

class DeezSettings:
    # Hardcoded secrets from deezspot/deezloader
    SECRET_KEY = "g4el58wc0zvf9na1"
    SECRET_KEY_2 = b"jo6aey6haid2Teih"
    IDK_KEY = a2b_hex("0001020304050607")
    
    CLIENT_ID = 172365
    CLIENT_SECRET = "fb0bec7ccc063dab0417eb7b0d847f34"
    
    API_URL = "https://www.deezer.com/ajax/gw-light.php"
    MEDIA_URL = "https://media.deezer.com/v1/get_url"
    SONG_SERVER = "https://e-cdns-proxy-{}.dzcdn.net/mobile/1/{}"

    QUALITIES = {
        "MP3_128": {"n": "1", "s": "128", "f": ".mp3"},
        "MP3_320": {"n": "3", "s": "320", "f": ".mp3"},
        "FLAC":    {"n": "9", "s": "FLAC", "f": ".flac"},
    }

class DeezUtils:
    @staticmethod
    def md5hex(data: str) -> str:
        return md5(data.encode()).hexdigest()

    @staticmethod
    def calc_bf_key(song_id: str) -> str:
        h = DeezUtils.md5hex(song_id)
        return "".join(
            chr(ord(h[i]) ^ ord(h[i + 16]) ^ ord(DeezSettings.SECRET_KEY[i]))
            for i in range(16)
        )

    @staticmethod
    def blowfish_decrypt(data: bytes, key: str) -> bytes:
        cipher = Blowfish.new(key.encode(), Blowfish.MODE_CBC, DeezSettings.IDK_KEY)
        return cipher.decrypt(data)

    @staticmethod
    def gen_song_hash(md5_val, quality_n, song_id, media_version):
        data = b"\xa4".join(
            a.encode() for a in [md5_val, quality_n, song_id, media_version] if a
        )
        hashed = md5(data).hexdigest().encode()
        data = b"\xa4".join([hashed, data]) + b"\xa4"
        
        if len(data) % 16:
            data += b"\x00" * (16 - len(data) % 16)
            
        cipher = AES.new(DeezSettings.SECRET_KEY_2, AES.MODE_ECB)
        return b2a_hex(cipher.encrypt(data)).decode()

class DeezAPI:
    def __init__(self, arl=None):
        self.session = requests.Session()
        self.arl = arl
        self.token = None
        self.license_token = None
        
        # Load ARL from ENV if provided and not passed explicitly
        if not self.arl:
            self.arl = os.getenv("DEEZER_ARL")

        if self.arl:
            self.session.cookies['arl'] = self.arl
            self.refresh_session()

    def refresh_session(self):
        try:
            data = self.get_user_data()
            self.token = data.get('checkForm')
            self.license_token = data.get('USER', {}).get('OPTIONS', {}).get('license_token')
        except Exception as e:
            console.log(f"[yellow]Warning: Could not refresh session with ARL: {e}[/yellow]")
            self.token = "null"

    def gw_request(self, method, body=None):
        params = {
            "api_version": "1.0",
            "api_token": self.token if self.token else "null",
            "input": "3",
            "method": method
        }
        try:
            resp = self.session.post(DeezSettings.API_URL, params=params, json=body)
            resp.raise_for_status()
            resp_json = resp.json()
            if 'results' not in resp_json:
                 # If token is invalid/expired and we have an ARL, try to refresh once
                 if self.token != "null" and "error" in resp_json:
                    self.refresh_session()
                    params["api_token"] = self.token
                    resp = self.session.post(DeezSettings.API_URL, params=params, json=body)
                    return resp.json().get('results')
            return resp_json.get('results')
        except Exception as e:
            console.log(f"[red]API Request Error ({method}): {e}[/red]")
            return None

    def get_user_data(self):
        return self.gw_request("deezer.getUserData")

    def search_track(self, query):
        body = {"query": query, "start": 0, "nb": 5, "types": ["TRACK"]}
        return self.gw_request("search.music", body)

    def get_track_data(self, song_id):
        return self.gw_request("song.getData", {"sng_id": song_id})

    def get_track_url(self, track_data, quality="MP3_320"):
        # Check permissions and data
        md5_origin = track_data.get('MD5_ORIGIN')
        media_version = track_data.get('MEDIA_VERSION')
        sng_id = track_data.get('SNG_ID')
        
        if not (md5_origin and media_version and sng_id):
            return None, None

        # Determine quality
        q_settings = DeezSettings.QUALITIES.get(quality, DeezSettings.QUALITIES["MP3_128"])
        
        # Check if user can access this quality (simplified check)
        # In a real scenario, we check track_tokens or user rights, but here we try to gen URL
        
        # Method 1: Get single URL (Legacy) -> Usually works for MP3_128 without ARL, MP3_320/FLAC with ARL
        song_hash = DeezUtils.gen_song_hash(md5_origin, q_settings['n'], sng_id, media_version)
        url = DeezSettings.SONG_SERVER.format(md5_origin[0], song_hash)
        
        return url, q_settings['f']

class SpotifyResolver:
    def __init__(self):
        self.sp = None
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        if client_id and client_secret:
            self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=client_id, client_secret=client_secret))

    def resolve_track(self, url):
        if not self.sp:
            console.log("[yellow]Spotify credentials not found. Cannot resolve Spotify links using API.[/yellow]")
            return None
        
        try:
            track_id = self._extract_id(url)
            track = self.sp.track(track_id)
            query = f"{track['name']} {track['artists'][0]['name']}"
            return query
        except Exception as e:
            console.log(f"[red]Error resolving Spotify track: {e}[/red]")
            return None

    def _extract_id(self, url):
        # Extract ID from https://open.spotify.com/track/ID?si=...
        match = re.search(r'track/([a-zA-Z0-9]+)', url)
        return match.group(1) if match else url

import os
from yt_dlp import YoutubeDL
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error
import requests
from .deez_engine import DeezAPI, DeezUtils, console

class MusicDownloader:
    def __init__(self, output_dir="Music"):
        self.output_dir = output_dir
        self.deez_api = DeezAPI()

    def download(self, video_url, metadata):
        """Downloads audio from YouTube and tags it with metadata."""
        artist = metadata['artist']
        title = metadata['title']
        album = metadata['album']
        
        # Create artist/album directory structure
        save_path = os.path.join(self.output_dir, artist, album)
        os.makedirs(save_path, exist_ok=True)
        
        # File template
        filename = f"{artist} - {title}.mp3"
        output_template = os.path.join(save_path, f"{artist} - {title}.%(ext)s")

        # Check for local ffmpeg
        ffmpeg_local = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "bin", "ffmpeg.exe")
        ffmpeg_location = ffmpeg_local if os.path.exists(ffmpeg_local) else None

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'ffmpeg_location': ffmpeg_location,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'quiet': True,
        }

        if self.deez_api.token or self.deez_api.arl:
            try:
                if self._download_deezer(metadata, save_path, filename):
                     print(f"✅  [Deezer HQ] Done! Saved to: {os.path.join(save_path, filename)}")
                     return True
            except Exception as e:
                print(f"⚠️  Deezer download failed (falling back to YouTube): {e}")

        print(f"⬇️  [YouTube] Downloading: {title} by {artist}...")
        
        with YoutubeDL(ydl_opts) as ydl:
            try:
                ydl.download([video_url])
            except Exception as e:
                print(f"Error downloading: {e}")
                return False

    def _download_deezer(self, metadata, save_path, filename):
        track_data = None
        
        # 1. Try direct ID if available (from Interactive Search)
        if metadata.get('deezer_id'):
            print(f"🔗  Using direct Deezer ID: {metadata['deezer_id']}")
            track_data = self.deez_api.get_track_data(metadata['deezer_id'])
        
        # 2. Fallback to Search
        if not track_data:
            query = f"{metadata['artist']} - {metadata['title']}"
            print(f"🔎  Searching on Deezer: {query}")
            results = self.deez_api.search_track(query)
            if not results or not results['data']:
                raise Exception("Track not found on Deezer")
            
            # Get full data
            track_data = self.deez_api.get_track_data(results['data'][0]['id'])

        if not track_data:
             raise Exception("Could not retrieve track details")
        
        full_track = track_data

        # Try HQ first, then fallback
        url, ext = self.deez_api.get_track_url(full_track, "MP3_320")
        if not url:
             url, ext = self.deez_api.get_track_url(full_track, "MP3_128")
        
        if not url:
            raise Exception("Could not generate download URL")

        # Adjust filename ext
        filename = filename.rsplit('.', 1)[0] + ext
        filepath = os.path.join(save_path, filename)
        
        print(f"⬇️  Downloading from Deezer ({ext})...")
        
        try:
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                DeezUtils.decrypt_file(r.iter_content(2048), full_track['SNG_ID'], filepath)
            
            # Tagging
            self._tag_file(filepath, metadata)
            return True
        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            raise e

        # Tagging
        filepath = os.path.join(save_path, filename)
        if os.path.exists(filepath):
            self._tag_file(filepath, metadata)
            print(f"✅  Done! Saved to: {filepath}")
            return True
        return False

    def _tag_file(self, filepath, metadata):
        """Injects ID3 tags into the MP3 file."""
        try:
            audio = MP3(filepath, ID3=ID3)
            
            # Add ID3 tag if it doesn't exist
            try:
                audio.add_tags()
            except error:
                pass

            audio.tags.add(
                APIC(
                    encoding=3, # 3 is for utf-8
                    mime='image/jpeg', # image/jpeg or image/png
                    type=3, # 3 is for the cover image
                    desc=u'Cover',
                    data=requests.get(metadata['cover_url']).content
                )
            )
            audio.save()
            
            # EasyID3 for text tags
            audio = EasyID3(filepath)
            audio['title'] = metadata['title']
            audio['artist'] = metadata['artist']
            audio['album'] = metadata['album']
            audio['date'] = metadata['release_date'][:4]
            audio.save()
            
        except Exception as e:
            print(f"Error tagging file: {e}")

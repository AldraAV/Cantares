"""
test_engine.py — Test directo del motor de descarga de Cantares.
Descarga las 15 canciones mas recientes de Liked Songs usando el motor propio.
"""
import sys
import os

# Fix Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

from cantares.core.spotify import SpotifyExporter
from cantares.core.music_downloader import MusicDownloader, download_liked_songs

def progress(msg, percent=0, result=None):
    bar = "#" * (percent // 5) + "." * (20 - percent // 5)
    print(f"  [{bar}] {percent:3d}% | {msg}", flush=True)

def main():
    print("=" * 60, flush=True)
    print("CANTARES ENGINE TEST - 15 Liked Songs", flush=True)
    print("Motor: yt-dlp Python API (sin deemix)", flush=True)
    print("=" * 60, flush=True)
    
    # Auth
    print("\n[1] Spotify Auth...", flush=True)
    exp = SpotifyExporter()
    user = exp.authenticate()
    print(f"  OK: {user['display_name']}", flush=True)
    
    # Download
    print("\n[2] Descargando 15 liked songs...", flush=True)
    print("-" * 60, flush=True)
    
    result = download_liked_songs(
        exp, limit=15,
        output_dir=os.path.join(os.getcwd(), "Downloads"),
        callback=progress
    )
    
    # Summary
    print("\n" + "=" * 60, flush=True)
    print(f"RESULTADO FINAL:", flush=True)
    print(f"  Completadas: {result.completed}/{result.total}", flush=True)
    print(f"  Saltadas:    {result.skipped}", flush=True)
    print(f"  Fallidas:    {result.failed}", flush=True)
    print(f"  Tasa exito:  {result.success_rate:.0f}%", flush=True)
    print(f"  Tiempo:      {result.elapsed_sec:.0f}s", flush=True)
    
    if result.tracks:
        print(f"\nDetalle:", flush=True)
        for t in result.tracks:
            icon = "OK" if t.status.value == "complete" else ("SKIP" if t.status.value == "skipped" else "FAIL")
            extra = f"{t.file_size_mb:.1f}MB" if t.file_size_mb else (t.error or "")
            print(f"  [{icon:4s}] {t.artist} - {t.track_name} {extra}", flush=True)
    
    print("=" * 60, flush=True)

if __name__ == "__main__":
    main()

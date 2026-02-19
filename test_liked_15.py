"""
test_liked_15.py - Test: Exportar y descargar las 15 canciones mas recientes de Liked Songs.
"""
import os
import sys
import csv
from pathlib import Path
from dotenv import load_dotenv

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from cantares.core.spotify import SpotifyExporter
from cantares.core.batch_downloader import BatchDownloader


def main():
    print("=" * 60)
    print("CANTARES - Test: 15 Liked Songs mas recientes")
    print("=" * 60)
    
    # -- PASO 1: Exportar desde Spotify --
    print("\n[1/3] Conectando con Spotify...")
    exporter = SpotifyExporter()
    
    try:
        user = exporter.authenticate()
        print(f"  OK Autenticado como: {user['display_name']}")
    except Exception as e:
        print(f"  ERROR autenticando: {e}")
        return
    
    print("\n[2/3] Obteniendo 15 Liked Songs mas recientes...")
    try:
        liked = exporter.get_liked_songs(limit=15)
        print(f"  OK Obtenidas {len(liked)} canciones")
    except Exception as e:
        print(f"  ERROR obteniendo liked songs: {e}")
        return
    
    # Escribir CSV temporal solo con las 15 canciones
    test_csv = "test_liked_15.csv"
    with open(test_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Track Name", "Artist Name", "Album Name", "Playlist", "URI"])
        
        for i, item in enumerate(liked):
            track = item.get('track')
            if not track:
                continue
            name = track['name']
            artist = track['artists'][0]['name'] if track['artists'] else "Unknown"
            album = track['album']['name'] if track['album'] else "Unknown"
            uri = track['uri']
            print(f"  {i+1:2d}. {artist} - {name}")
            writer.writerow([name, artist, album, "Liked Songs", uri])
    
    print(f"\n  CSV generado: {test_csv}")
    
    # -- PASO 2: Descargar via BatchDownloader --
    print("\n[3/3] Iniciando descargas...")
    print("  Motor: Deezer (primario) -> YouTube (fallback)")
    print("-" * 60)
    
    download_dir = os.path.join(os.getcwd(), "Downloads", "Test_Liked_15")
    os.makedirs(download_dir, exist_ok=True)
    
    def progress_callback(msg, percent=0):
        bar_filled = int(percent / 5)
        bar = "#" * bar_filled + "." * (20 - bar_filled)
        print(f"  [{bar}] {percent:3d}% | {msg}")
    
    downloader = BatchDownloader(download_dir=download_dir, update_callback=progress_callback)
    
    downloader.process_csv(
        csv_path=test_csv,
        selected_playlists=["Liked Songs"],
        callback=progress_callback
    )
    
    # -- RESULTADO --
    print("\n" + "=" * 60)
    downloaded_files = list(Path(download_dir).rglob("*.*"))
    audio_files = [f for f in downloaded_files if f.suffix.lower() in ('.mp3', '.flac', '.m4a', '.ogg')]
    
    print(f"RESULTADO: {len(audio_files)} archivos de audio descargados")
    for f in audio_files:
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  >> {f.name} ({size_mb:.1f} MB)")
    
    if not audio_files:
        other = [f for f in downloaded_files if not f.is_dir()]
        if other:
            print("  Archivos encontrados (no audio):")
            for f in other:
                print(f"    -> {f.name}")
        else:
            print("  AVISO: No se descargo ningun archivo.")
            # Check if folder exists with subdirs
            sub_dirs = list(Path(download_dir).iterdir())
            if sub_dirs:
                print(f"  Subdirectorios: {[d.name for d in sub_dirs]}")
                for sd in sub_dirs:
                    files_in = list(sd.rglob("*.*"))
                    for f in files_in:
                        size_mb = f.stat().st_size / (1024 * 1024)
                        print(f"    >> {f.name} ({size_mb:.1f} MB)")
    
    print("=" * 60)


if __name__ == "__main__":
    main()

"""
Test de Estrategia Dual (Deezer -> YouTube).
Verifica que el MusicDownloader use correctamente la fuente primaria y secundaria.
"""
import os
import sys
import shutil
import io

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

from cantares.core.music_downloader import MusicDownloader, TrackResult

OUTPUT_DIR = "Downloads/Dual_Test"

def clean_dir():
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def test_deezer_primary():
    """Test 1: Deezer habilitado (deberia ser source='deezer')"""
    print("\n[TEST 1] Estrategia Dual (Deezer Habilitado)")
    clean_dir()
    
    dl = MusicDownloader(download_dir=OUTPUT_DIR, use_deezer=True)
    # Track que sabemos est en Deezer
    artist = "Reik"
    track = "Inolvidable"
    
    print(f"  Descargando: {artist} - {track}...")
    res = dl.download_single(artist, track)
    
    print(f"  Status: {res.status}")
    print(f"  Source: {res.source}")
    print(f"  File:   {res.file_path}")
    
    if res.source == "deezer":
        print("  -> PASS: Fuente correcta (Deezer)")
        if res.file_path and os.path.exists(res.file_path):
            print(f"  -> PASS: Archivo creado ({res.file_size_mb:.1f}MB)")
        else:
            print("  -> FAIL: Archivo no existe")
    else:
        print(f"  -> FAIL: Fuente incorrecta (esperaba deezer, obtuvo {res.source})")

def test_youtube_fallback():
    """Test 2: Deezer deshabilitado (simula fallback o ARL invalido)"""
    print("\n[TEST 2] YouTube Fallback (Deezer Deshabilitado)")
    clean_dir()
    
    # Forzamos use_deezer=False para simular que no se quiso usar o fall el login
    dl = MusicDownloader(download_dir=OUTPUT_DIR, use_deezer=False)
    
    artist = "Reik"
    track = "Noviembre Sin Ti"
    
    print(f"  Descargando: {artist} - {track}...")
    res = dl.download_single(artist, track)
    
    print(f"  Status: {res.status}")
    print(f"  Source: {res.source}")
    print(f"  File:   {res.file_path}")
    
    if res.source == "youtube":
        print("  -> PASS: Fuente correcta (YouTube)")
        if res.file_path and os.path.exists(res.file_path):
            print(f"  -> PASS: Archivo creado ({res.file_size_mb:.1f}MB)")
        else:
            print("  -> FAIL: Archivo no existe")
    else:
        print(f"  -> FAIL: Fuente incorrecta (esperaba youtube, obtuvo {res.source})")

def main():
    print("="*60)
    print("TEST DE ESTRATEGIA DUAL")
    print("="*60)
    
    test_deezer_primary()
    test_youtube_fallback()
    
    print("\nDone.")

if __name__ == "__main__":
    main()

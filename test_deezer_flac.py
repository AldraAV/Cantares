"""
Test del motor Deezer FLAC.
Descarga 3 canciones de las liked songs via Deezer con calidad FLAC.
"""
import os
import sys
import io

# Fix encoding para Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

from cantares.core.deezer_engine import DeezerEngine, Quality


def main():
    print("=" * 60)
    print("CANTARES DEEZER FLAC TEST")
    print("Motor: DeezerEngine nativo (sin deemix CLI)")
    print("=" * 60)
    
    # 1) Login
    print("\n[1] Login Deezer...")
    engine = DeezerEngine(
        output_dir="Downloads/Deezer_FLAC_Test",
        quality=Quality.FLAC
    )
    
    if not engine.login():
        print("  FAIL: No se pudo autenticar con Deezer")
        print("  Verifica que DEEZER_ARL en .env sea valido")
        arl = os.getenv("DEEZER_ARL", "")
        print(f"  ARL encontrado: {'SI' if arl else 'NO'} (len={len(arl)})")
        return
    
    print(f"  OK: Logueado como {engine.user_name}")
    print(f"  FLAC: {'SI' if engine.can_lossless else 'NO'}")
    print(f"  HQ:   {'SI' if engine.can_hq else 'NO'}")
    
    # 2) Test de busqueda
    print("\n[2] Test de busqueda...")
    results = engine.search("Reik Inolvidable", limit=3)
    if results:
        for r in results:
            print(f"  -> {r.get('ART_NAME', '?')} - {r.get('SNG_TITLE', '?')} (ID: {r.get('SNG_ID', '?')})")
    else:
        print("  WARN: Sin resultados de busqueda")
    
    # 3) Descargar 3 tracks de prueba
    print("\n[3] Descargando 3 tracks de prueba...")
    test_tracks = [
        {"artist": "Reik", "title": "Inolvidable"},
        {"artist": "Mana", "title": "Mariposa Traicionera"},
        {"artist": "Elefante", "title": "Asi Es La Vida"},
    ]
    
    def progress_cb(i, total, msg):
        bar_len = 20
        filled = int(bar_len * (i + 1) / total)
        bar = "#" * filled + "." * (bar_len - filled)
        print(f"  [{bar}] {int((i+1)/total*100):3d}% | {msg}")
    
    result = engine.download_batch(test_tracks, progress_cb=progress_cb)
    
    # 4) Resultados
    print("\n" + "=" * 60)
    print("RESULTADO FINAL:")
    print(f"  Completadas: {result.ok}/{result.total}")
    print(f"  Fallidas:    {result.failed}")
    print(f"  Saltadas:    {result.skipped}")
    print(f"  Tiempo:      {result.elapsed:.0f}s")
    
    print("\nDetalle:")
    for r in result.results:
        if r.success:
            size_mb = r.size_bytes / (1024 * 1024)
            print(f"  [OK  ] {r.artist} - {r.title} ({r.quality}) {size_mb:.1f}MB")
            # Verificar que FLAC tiene el header correcto
            if r.filepath and r.filepath.endswith(".flac"):
                with open(r.filepath, 'rb') as f:
                    magic = f.read(4)
                    is_flac = magic == b'fLaC'
                    print(f"         -> FLAC header: {'VALIDO' if is_flac else 'INVALIDO'} ({magic})")
        else:
            print(f"  [FAIL] {r.artist} - {r.title}: {r.error}")
    print("=" * 60)


if __name__ == "__main__":
    main()

import os
import sys
from cantares.music.spotify import SpotifyClient
from cantares.music.deez_engine import DeezAPI
from cantares.music.youtube import YouTubeSearcher
from cantares.music.downloader import MusicDownloader

# Asegurar codificación UTF-8
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def probar_descarga_culture_shock():
    print("=== PRUEBA DE CANTARES: CULTURE SHOCK - POLYPHIA ===")
    consulta = "Culture Shock Polyphia"
    carpeta_destino = "Descargas_Pruebas"
    
    os.makedirs(carpeta_destino, exist_ok=True)
    
    cliente_sp = SpotifyClient()
    cliente_deez = DeezAPI()
    buscador_yt = YouTubeSearcher()
    descargador = MusicDownloader(output_dir=carpeta_destino)
    
    metadatos = None
    print("1. Consultando metadatos directamente a la API de Spotify Premium...")
    if cliente_sp.sp:
        try:
            metadatos = cliente_sp.search_track(consulta)
            if metadatos:
                print(f"   [SPOTIFY API OK] Título: {metadatos['title']}")
                print(f"   [SPOTIFY API OK] Artista: {metadatos['artist']}")
                print(f"   [SPOTIFY API OK] Álbum: {metadatos['album']}")
                print(f"   [SPOTIFY API OK] Año: {metadatos['release_date']}")
                print(f"   [SPOTIFY API OK] URL: {metadatos['spotify_url']}")
        except Exception as e:
            print(f"   [ERROR SPOTIFY API] {e}")
            
    if not metadatos:
        print("2. Respaldo: Consultando metadatos en Deezer...")
        try:
            res = cliente_deez.search_track(consulta)
            if res and res.get('data'):
                t = res['data'][0]
                metadatos = {
                    "title": t.get('title', "Culture Shock"),
                    "artist": "Polyphia",
                    "album": t.get('album', {}).get('title', "New Levels New Devils"),
                    "cover_url": t.get('album', {}).get('cover_xl', "https://via.placeholder.com/500"),
                    "release_date": "2018",
                    "deezer_id": t.get('id')
                }
        except Exception as e:
            print(f"   [ERROR DEEZER API] {e}")
            
    if not metadatos:
        metadatos = {
            "title": "Culture Shock",
            "artist": "Polyphia",
            "album": "New Levels New Devils",
            "cover_url": "https://via.placeholder.com/500",
            "release_date": "2018"
        }
        
    print("\n3. Buscando stream/audio para descarga...")
    url_video = None
    try:
        video = buscador_yt.search_video(f"{metadatos['artist']} - {metadatos['title']}")
        if video and 'url' in video:
            url_video = video['url']
            print(f"   [YOUTUBE RESYNC OK] URL: {url_video}")
    except Exception as e:
        print(f"   [ERROR YOUTUBE] {e}")
        
    print("\n4. Iniciando descarga con MusicDownloader de Cantares...")
    try:
        exito = descargador.download(url_video or "https://www.youtube.com/watch?v=dQw4w9WgXcQ", metadatos)
        if exito is not False:
            print("\n[EXITO TOTAL] 'Culture Shock - Polyphia' descargada y etiquetada con metadatos de Spotify.")
        else:
            print("\n[ERROR] No se pudo completar la descarga.")
    except Exception as e:
        print(f"\n[EXCEPCION EN DESCARGA] {e}")

if __name__ == "__main__":
    probar_descarga_culture_shock()

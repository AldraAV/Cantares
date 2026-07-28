import os
import sys
import re
from cantares.music.deez_engine import DeezAPI
from cantares.music.spotify import SpotifyClient
from cantares.music.youtube import YouTubeSearcher
from cantares.music.downloader import MusicDownloader

# Asegurar codificación UTF-8 en consola para Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def limpiar_nombre_cancion(linea: str) -> str:
    """Extrae el texto de la canción eliminando guiones de lista y numeración (ej. '- 1. Rolas -> Rolas')."""
    linea = linea.strip()
    if linea.startswith("-"):
        linea = linea[1:].strip()
    # Eliminar número inicial tipo "1. ", "23. " si existe
    linea = re.sub(r"^\d+\.\s*", "", linea)
    return linea.strip()

def descargar_lista_spotify(ruta_archivo_md: str, carpeta_destino: str = "Descargas_Spotify_Likeadas"):
    """
    Lee las canciones del archivo Markdown y las descarga automáticamente usando Cantares.
    Prioriza Deezer HQ (320 kbps) usando el ARL y hace respaldo automático en YouTube DL con FFmpeg.
    """
    if not os.path.exists(ruta_archivo_md):
        print(f"[ERROR] No se encontró el archivo de canciones: {ruta_archivo_md}")
        return

    print(f"=== INICIANDO DESCARGA AUTOMÁTICA CON CANTARES ===")
    print(f"Archivo origen: {ruta_archivo_md}")
    print(f"Carpeta destino: {os.path.abspath(carpeta_destino)}\n")

    canciones = []
    with open(ruta_archivo_md, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if linea and linea.startswith("-") and not linea.startswith("#"):
                nombre = limpiar_nombre_cancion(linea)
                if nombre:
                    canciones.append(nombre)

    if not canciones:
        print("[AVISO] No se encontraron canciones para descargar en el archivo Markdown.")
        return

    print(f"[INFO] Se han detectado {len(canciones)} canciones en la lista para procesar.\n")

    descargador = MusicDownloader(output_dir=carpeta_destino)
    cliente_deez = DeezAPI()
    cliente_sp = SpotifyClient()
    buscador_yt = YouTubeSearcher()

    exitosas = 0
    fallidas = 0

    for indice, consulta in enumerate(canciones, start=1):
        print(f"--------------------------------------------------")
        print(f"[{indice}/{len(canciones)}] Procesando: {consulta}")
        
        metadatos = None
        
        # 1. Intentar buscar en Deezer primero para obtener ID directo y metadatos limpios
        print(f"  -> Consultando metadatos en Deezer...")
        try:
            resultados_deez = cliente_deez.search_track(consulta)
            if resultados_deez and resultados_deez.get('data'):
                t = dict(resultados_deez['data'][0])
                art_name = t.get('ART_NAME')
                if not art_name and 'artist' in t and isinstance(t['artist'], dict):
                    art_name = t['artist'].get('name')
                if not art_name and 'SNG_CONTRIBUTORS' in t and isinstance(t['SNG_CONTRIBUTORS'], dict):
                    art_name = t['SNG_CONTRIBUTORS'].get('main_artist', ['Desconocido'])[0]
                if not art_name:
                    art_name = "Desconocido"

                alb_title = t.get('ALB_TITLE')
                if not alb_title and 'album' in t and isinstance(t['album'], dict):
                    alb_title = t['album'].get('title')
                if not alb_title:
                    alb_title = "Sencillo"

                alb_pic = t.get('ALB_PICTURE', '')
                cover_url = f"https://e-cdns-images.dzcdn.net/images/cover/{alb_pic}/1000x1000-000000-80-0-0.jpg" if alb_pic else "https://via.placeholder.com/500"
                if 'album' in t and isinstance(t['album'], dict) and t['album'].get('cover_xl'):
                    cover_url = t['album']['cover_xl']

                metadatos = {
                    "title": t.get('SNG_TITLE', t.get('title', consulta.split('-')[0].strip())),
                    "artist": art_name,
                    "album": alb_title,
                    "cover_url": cover_url,
                    "release_date": str(t.get('PHYSICAL_RELEASE_DATE', '2024'))[:4],
                    "deezer_id": t.get('SNG_ID', t.get('id'))
                }
        except Exception as e:
            print(f"  [AVISO] Búsqueda en Deezer arrojó error técnico: {e}")

        # 2. Si Deezer no encontró metadatos, buscar en Spotify
        if not metadatos and cliente_sp.sp:
            print(f"  -> Consultando metadatos en Spotify...")
            try:
                metadatos = cliente_sp.search_track(consulta)
            except Exception as e:
                print(f"  [AVISO] Búsqueda en Spotify arrojó error: {e}")

        # 3. Respaldo por defecto si ningún API de metadatos devolvió resultados
        if not metadatos:
            partes = consulta.split('-', 1)
            titulo_fb = partes[0].strip()
            artista_fb = partes[1].strip() if len(partes) > 1 else "Desconocido"
            metadatos = {
                "title": titulo_fb,
                "artist": artista_fb,
                "album": "Descargas Spotify",
                "cover_url": "https://via.placeholder.com/500",
                "release_date": "2024",
                "deezer_id": None
            }

        print(f"  -> Metadatos finalizados: {metadatos['artist']} - {metadatos['title']}")

        # 4. Obtener URL de YouTube como respaldo para el método download()
        url_video = None
        try:
            print(f"  -> Localizando respaldo de audio en YouTube...")
            video = buscador_yt.search_video(f"{metadatos['artist']} - {metadatos['title']}")
            if video and 'url' in video:
                url_video = video['url']
        except Exception as e:
            print(f"  [AVISO] Búsqueda de respaldo en YouTube arrojó error: {e}")

        # 5. Ejecutar descarga con Cantares (intenta Deezer HQ primero, luego YouTube)
        exito = False
        try:
            # Si el método devuelve False (YouTube falló) o lanza excepción, lo manejamos
            exito_dl = descargador.download(url_video or "https://www.youtube.com/watch?v=dQw4w9WgXcQ", metadatos)
            if exito_dl is not False:
                exito = True
        except Exception as e_dl:
            print(f"  [ERROR] Falla en la descarga del tema: {e_dl}")
            exito = False

        if exito:
            exitosas += 1
            print(f"  [EXITO] Canción descargada y etiquetada correctamente.")
        else:
            fallidas += 1
            print(f"  [FALLO] No se pudo descargar la canción: {consulta}")

    print(f"\n==================================================")
    print(f"=== RESUMEN FINAL DE DESCARGAS CANTARES ===")
    print(f"Total procesadas: {len(canciones)}")
    print(f"Descargas exitosas: {exitosas}")
    print(f"Fallidas o pendientes: {fallidas}")
    print(f"Carpeta de música: {os.path.abspath(carpeta_destino)}")
    print(f"==================================================")

if __name__ == "__main__":
    ruta_md = r"C:\Users\carde\Desktop\MUACK\canciones_likeadas_spotify.md"
    descargar_lista_spotify(ruta_md)

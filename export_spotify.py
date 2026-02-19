
import os
import csv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import track

# Cargar variables de entorno
load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
# Redirect URI configurada en Spotify Apps (Nona fallback)
REDIRECT_URI = "https://nona-xi.vercel.app/callback"

console = Console()

def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        console.print("[red]❌ Faltan credenciales de Spotify en .env[/red]")
        return

    # Autenticación (scope para leer playlists privadas y biblioteca)
    # library-read no existe, user-library-read sí.
    scope = "playlist-read-private user-library-read"
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=scope,
        open_browser=True
    ))

    console.print("[green]✅ Conectado a Spotify[/green]")
    user = sp.current_user()
    console.print(f"👤 Usuario: [bold]{user['display_name']}[/bold]")

    # 1. Obtener Playlists
    playlists = []
    results = sp.current_user_playlists(limit=50)
    playlists.extend(results['items'])
    while results['next']:
        results = sp.next(results)
        playlists.extend(results['items'])

    console.print(f"📦 Encontradas [bold]{len(playlists)}[/bold] playlists.")

    # 2. Exportar Tracks
    with open("spotify_export.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Track Name", "Artist Name", "Album Name", "Playlist", "URI"])

        for pl in track(playlists, description="Procesando Playlists..."):
            pl_name = pl['name']
            
            # Paginación de tracks
            results = sp.playlist_items(pl['id'])
            tracks = results['items']
            while results['next']:
                results = sp.next(results)
                tracks.extend(results['items'])
                
            for item in tracks:
                track_data = item.get('track')
                if not track_data: continue
                
                name = track_data['name']
                artist = track_data['artists'][0]['name'] if track_data['artists'] else "Unknown"
                album = track_data['album']['name'] if track_data['album'] else "Unknown"
                uri = track_data['uri']
                
                writer.writerow([name, artist, album, pl_name, uri])

                writer.writerow([name, artist, album, pl_name, uri])

    # 3. Exportar "Dulces Wallpapers" (Liked Songs)
    console.print("[bold blue]💖 Procesando 'Liked Songs'...[/bold blue]")
    results = sp.current_user_saved_tracks(limit=50)
    tracks = results['items']
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])
    
    with open("spotify_export.csv", "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # No header, appending
        
        for item in track(tracks, description="Guardando Liked Songs..."):
            track_data = item.get('track')
            if not track_data: continue
            
            name = track_data['name']
            artist = track_data['artists'][0]['name'] if track_data['artists'] else "Unknown"
            album = track_data['album']['name'] if track_data['album'] else "Unknown"
            uri = track_data['uri']
            
            # Playlist name for Liked Songs
            writer.writerow([name, artist, album, "Liked Songs", uri])

    console.print(f"[green]✅ Añadas {len(tracks)} canciones de 'Liked Songs'.[/green]")
    console.print("[bold green]✨ Exportación completada: spotify_export.csv[/bold green]")

if __name__ == "__main__":
    main()

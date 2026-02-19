
import click
from rich.console import Console
from rich.table import Table
from .deez_engine import DeezAPI
from .spotify import SpotifyClient

console = Console()

def normalize_track(t):
    """Normalize GW API track object to standard keys."""
    if 'SNG_TITLE' in t:
        art_name = t.get('ART_NAME')
        if not art_name and 'SNG_CONTRIBUTORS' in t:
             art_name = t['SNG_CONTRIBUTORS'].get('main_artist', ['Unknown'])[0]
             
        return {
            'title': t.get('SNG_TITLE'),
            'artist': {'name': art_name},
            'album': {'title': t.get('ALB_TITLE'), 'cover_xl': f"https://e-cdns-images.dzcdn.net/images/cover/{t.get('ALB_PICTURE', '')}/1000x1000-000000-80-0-0.jpg"},
            'duration': int(t.get('DURATION', 0)),
            'id': t.get('SNG_ID'),
             # Persist needed internal keys for download (MD5_ORIGIN etc)
            'MD5_ORIGIN': t.get('MD5_ORIGIN'),
            'MEDIA_VERSION': t.get('MEDIA_VERSION'),
            'SNG_ID': t.get('SNG_ID')
        }
    return t

def interactive_search(query):
    # 1. If URL, return directly
    if "spotify.com" in query or "deezer.com" in query:
        return query, "url"

    cli_deez = DeezAPI()
    results = cli_deez.search_track(query)
    
    if not results or not results.get('data'):
        console.print("[red]❌ No results found.[/red]")
        return None, None

    raw_tracks = results['data']
    tracks = [normalize_track(t) for t in raw_tracks]
    
    # 2. Display Table
    table = Table(title=f"Resultados para: {query}")
    table.add_column("#", justify="right", style="cyan")
    table.add_column("Título", style="magenta")
    table.add_column("Artista", style="green")
    table.add_column("Álbum", style="yellow")
    table.add_column("Duración", style="blue")

    for idx, t in enumerate(tracks):
        dur_sec = int(t.get('duration', 0))
        duration = f"{dur_sec // 60}:{dur_sec % 60:02d}"
        table.add_row(str(idx + 1), t['title'], t['artist']['name'], t['album']['title'], duration)

    console.print(table)

    # 3. Interactive Selection
    choice = click.prompt("Selecciona una canción (0 para cancelar)", type=int, default=1)
    
    if choice < 1 or choice > len(tracks):
        console.print("[yellow]Operación cancelada.[/yellow]")
        return None, None
        
    selected = tracks[choice - 1]
    
    # Normalize metadata for downloader
    metadata = {
        "title": selected['title'],
        "artist": selected['artist']['name'],
        "album": selected['album']['title'],
        "cover_url": selected['album']['cover_xl'],
        "release_date": "Unknown", # Deezer search doesn't always provide this in shallow object
        "deezer_id": selected['id']
    }
    
    return metadata, "metadata"

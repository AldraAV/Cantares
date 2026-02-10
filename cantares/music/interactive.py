
import click
from rich.console import Console
from rich.table import Table
from .deez_engine import DeezAPI
from .spotify import SpotifyClient

console = Console()

def interactive_search(query):
    # 1. If URL, return directly
    if "spotify.com" in query or "deezer.com" in query:
        return query, "url"

    cli_deez = DeezAPI()
    results = cli_deez.search_track(query)
    
    if not results or not results.get('data'):
        console.print("[red]❌ No results found.[/red]")
        return None, None

    tracks = results['data']
    
    # 2. Display Table
    table = Table(title=f"Resultados para: {query}")
    table.add_column("#", justify="right", style="cyan")
    table.add_column("Título", style="magenta")
    table.add_column("Artista", style="green")
    table.add_column("Álbum", style="yellow")
    table.add_column("Duración", style="blue")

    for idx, t in enumerate(tracks):
        duration = f"{t['duration'] // 60}:{t['duration'] % 60:02d}"
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

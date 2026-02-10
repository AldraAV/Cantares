import click
import sys
import io

# Force UTF-8 encoding for Windows terminals
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

@click.group()
def main():
    """Cantares CLI - Porque lo bueno siempre se comparte"""
    pass

@main.command()
@click.argument("query")
def music(query):
    """Download music by Spotify URL or Search Query."""
    from .music.spotify import SpotifyClient
    from .music.youtube import YouTubeSearcher
    from .music.downloader import MusicDownloader
    from .music.interactive import interactive_search

    click.echo(f"🔍 Searching for: {query}...")
    
    metadata = None
    
    # Check for URL
    if "https://" in query or "http://" in query:
        # Existing URL logic (Spotify/Deezer)
        pass 
    else:
        # Interactive Search for text queries
        meta_result, source = interactive_search(query)
        if not meta_result:
            return # User cancelled or no results
        if source == "metadata":
            metadata = meta_result

    # 1. Get Metadata from Spotify/Url if not already set
    if not metadata:
        spotify = SpotifyClient()
        if "open.spotify.com" in query:
            metadata = spotify.get_track_info(query)
        else:
            # Fallback to non-interactive search if needed (or if interactive was bypassed)
            metadata = spotify.search_track(query)
    
    # Fallback to Deezer Search if Spotify failed/disabled
    if not metadata and "spotify.com" not in query:
        click.echo("⚠️  Spotify not configured or track not found. Searching on Deezer...")
        from .music.deez_engine import DeezAPI
        deez = DeezAPI()
        results = deez.search_track(query)
        if results and results['data']:
            t = results['data'][0]
            metadata = {
                "title": t['title'],
                "artist": t['artist']['name'],
                "album": t['album']['title'],
                "cover_url": t['album']['cover_xl'],
                "release_date": "Unknown" 
            }

    if not metadata:
        click.echo("❌ Track not found on Spotify or Deezer.")
        return

    click.echo(f"Found: 🎵 {metadata['title']} - 👤 {metadata['artist']}")

    # 2. Find on YouTube
    yt = YouTubeSearcher()
    video = yt.search_video(f"{metadata['artist']} - {metadata['title']}")
    
    if not video:
        click.echo("❌ Audio not found on YouTube.")
        return

    # 3. Download
    downloader = MusicDownloader()
    downloader.download(video['url'], metadata)

@main.command()
@click.argument("query")
def books(query):
    """Search and download books from Anna's Archive."""
    from .books.annas_archive import AnnasArchiveSearcher
    from .books.downloader import BookDownloader

    click.echo(f"🔍 Searching for: {query}...")
    searcher = AnnasArchiveSearcher()
    results = searcher.search(query)

    if not results:
        click.echo("❌ No books found.")
        return

    # List top 5
    click.echo(f"\nFound {len(results)} books. Top 5:")
    for i, r in enumerate(results[:5]):
        click.echo(f"{i+1}. {r['title']} - {r['author']} ({r['extension']})")
    
    # Ask to download first one
    if click.confirm(f"\nDownload '{results[0]['title']}'?", default=True):
        click.echo("Resolving download link...")
        dl_link = searcher.get_download_link(results[0]['link'])
        
        if dl_link:
            click.echo(f"Downloading from {dl_link}...")
            downloader = BookDownloader()
            try:
                path = downloader.download(dl_link, f"{results[0]['title']}.{results[0]['extension']}")
                click.echo(f"✅ Saved to: {path}")
            except Exception as e:
                click.echo(f"❌ Download failed: {e}")
        else:
            click.echo("❌ Could not resolve download link.")

@main.command()
def tui():
    """Launch the Terminal User Interface."""
    from cantares.ui.app import CantaresApp
    app = CantaresApp()
    app.run()

if __name__ == "__main__":
    main()

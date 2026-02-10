from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Input, Button, Label, RichLog
from textual.containers import Container, Vertical, Horizontal
from cantares.music.spotify import SpotifyClient
from cantares.music.youtube import YouTubeSearcher
from cantares.music.downloader import MusicDownloader

class MusicScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Label("🎵  Cantares Music Downloader", id="title"),
            Input(placeholder="Enter Spotify URL or Song Name...", id="search_input"),
            Horizontal(
                Button("Search & Download", variant="primary", id="download_btn"),
                classes="btn-container"
            ),
            RichLog(highlight=True, markup=True, id="log_output"),
            id="main_container"
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "download_btn":
            query = self.query_one("#search_input").value
            if query:
                self.download_music(query)

    def download_music(self, query):
        log = self.query_one("#log_output")
        log.write(f"[bold cyan]🔍 Searching for:[/bold cyan] {query}...")
        
        # This should ideally be async or threaded to not block UI
        # For MVP, we'll keep it simple but it might freeze UI briefly
        
        try:
            spotify = SpotifyClient()
            if "open.spotify.com" in query:
                metadata = spotify.get_track_info(query)
            else:
                metadata = spotify.search_track(query)
            
            if not metadata:
                log.write("[bold red]❌ Track not found on Spotify.[/bold red]")
                return

            log.write(f"[green]Found:[/green] 🎵 {metadata['title']} - 👤 {metadata['artist']}")

            yt = YouTubeSearcher()
            video = yt.search_video(f"{metadata['artist']} - {metadata['title']}")
            
            if not video:
                log.write("[bold red]❌ Audio not found on YouTube.[/bold red]")
                return

            log.write(f"[yellow]⬇️  Downloading from YouTube...[/yellow]")
            downloader = MusicDownloader()
            success = downloader.download(video['url'], metadata)
            
            if success:
                 log.write(f"[bold green]✅ Download Complete![/bold green] Saved to 'Music/{metadata['artist']}/{metadata['album']}'")
            else:
                 log.write("[bold red]❌ Download Failed.[/bold red]")

        except Exception as e:
            log.write(f"[bold red]❌ Error: {str(e)}[/bold red]")

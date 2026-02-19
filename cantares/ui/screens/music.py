import asyncio
from textual import work
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Input, Button, Label, RichLog, ProgressBar, DataTable
from textual.containers import Container, Vertical, Horizontal
from textual.worker import Worker, WorkerState

from cantares.core.music_downloader import MusicDownloader, TrackResult, DownloadStatus

class MusicScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Back")]

    CSS = """
    #results_table {
        height: 1fr;
        border: solid purple;
        display: none;
    }
    #log_output {
        height: 1fr;
        border: solid green;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Label("🎵  Cantares — Descarga de Música", id="title"),
            Label("Escribe 'Artista - Canción' o un término de búsqueda:", classes="help-text"),
            Input(placeholder="ej. Bad Bunny - Monaco (o pega un link)", id="search_input"),
            Horizontal(
                Button("Buscar", variant="primary", id="search_btn"),
                classes="btn-container"
            ),
            ProgressBar(total=100, show_eta=True, id="progress_bar"),
            DataTable(id="results_table", cursor_type="row"),
            RichLog(highlight=True, markup=True, id="log_output"),
            id="main_container"
        )
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#search_input").focus()
        self.log_write("[blue]Listo pa' la acción. Escribe algo arriba.[/blue]")
        
        # Configurar tabla
        table = self.query_one("#results_table", DataTable)
        table.add_columns("Título", "Artista", "Álbum", "Duración")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "search_btn":
            self.start_search()
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.start_search()

    def start_search(self):
        query = self.query_one("#search_input").value.strip()
        if not query:
            self.log_write("[red]Qué wewencha... faltó escribir la canción.[/red]")
            return
        
        self.query_one("#search_btn").disabled = True
        self.query_one("#search_input").disabled = True
        
        # Limpiar y preparar UI
        self.query_one("#log_output").clear()
        self.query_one("#results_table").clear()
        self.query_one("#results_table").display = "none"
        self.query_one("#log_output").display = "block"
        
        self.log_write(f"[bold cyan]🔍 Buscando en el pozo:[/bold cyan] {query}")
        self.run_search_worker(query)

    @work(exclusive=True, thread=True)
    def run_search_worker(self, query: str):
        downloader = MusicDownloader()
        
        # 1. Buscar
        results = downloader.search(query, limit=10)
        
        self.app.call_from_thread(self.show_results, results, query)

    def show_results(self, results, query):
        self.query_one("#search_btn").disabled = False
        self.query_one("#search_input").disabled = False
        
        if not results:
            self.log_write(f"[yellow]⚠️ No se encontró nada para: {query}. Intenta otra cosa.[/yellow]")
            return
            
        # Mostrar tabla
        table = self.query_one("#results_table", DataTable)
        table.clear()
        
        # Guardar resultados en memoria del widget para recuperarlos al seleccionar
        self.current_results = {str(r['id']): r for r in results}
        
        for r in results:
            dur = f"{r['duration']//60}:{r['duration']%60:02d}"
            # Usar ID como Row Key
            table.add_row(r['title'], r['artist'], r['album'], dur, key=str(r['id']))
            
        table.display = "block"
        self.query_one("#log_output").display = "none"
        table.focus()
        self.log_write(f"[green]¡Epa! Encontré {len(results)} rolas. Selecciona una.[/green]")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        row_key = event.row_key.value
        if row_key in self.current_results:
            track = self.current_results[row_key]
            self.start_download(track)

    def start_download(self, track_info):
        self.query_one("#results_table").display = "none"
        self.query_one("#log_output").display = "block"
        self.query_one("#progress_bar").display = True
        self.query_one("#progress_bar").update(total=100, progress=0)
        
        self.log_write(f"[bold green]👍 Arre. Bajando:[/bold green] {track_info['artist']} - {track_info['title']}")
        
        self.run_download_worker(track_info)

    @work(exclusive=True, thread=True)
    def run_download_worker(self, track_info):
        def progress_wrapper(msg, percent, result):
            self.app.call_from_thread(self.update_ui, msg, percent, result)
        
        downloader = MusicDownloader(callback=progress_wrapper)
        
        # Usar download_single con datos precisos
        result = downloader.download_single(track_info['artist'], track_info['title'])
            
        if result:
            self.app.call_from_thread(self.update_ui, "Finalizado", 100, result)
        
        self.app.call_from_thread(self.download_finished)

    def update_ui(self, msg: str, percent: int, result: TrackResult = None):
        """Update UI from the worker thread context."""
        bar = self.query_one("#progress_bar")
        bar.update(progress=percent)
        
        self.log_write(f"[{percent}%] {msg}")
        
        if result and result.status == DownloadStatus.COMPLETE:
            source_color = "green" if result.source == "deezer" else "yellow"
            source_icon = "🎹" if result.source == "deezer" else "📺"
            self.log_write(f"[{source_color}]  {source_icon} Fuente: {result.source.upper()} [/{source_color}]")
            quality_badge = f"[{'bold magenta' if 'FLAC' in result.quality else 'cyan'}]{result.quality}[/]"
            if result.duration_sec < 10: 
                self.log_write(f"[bold green]  ✓ ¡Listo, pa ayer! ({quality_badge}) Guardado en: {result.file_path}[/bold green]")
            else:
                 self.log_write(f"[bold green]  ✓ ¡Así está la calabaza! ({quality_badge}) Guardado en: {result.file_path}[/bold green]")
        elif result and result.status == DownloadStatus.FAILED:
            self.log_write(f"[bold red]❌ Algo tostó: {result.error}[/bold red]")
        elif result and result.status == DownloadStatus.SKIPPED:
             self.log_write(f"[yellow]⚠️ Iguanas ranas. Ya lo tenías descargado.[/yellow]")

    def download_finished(self):
        self.query_one("#search_btn").disabled = False
        self.query_one("#search_input").disabled = False
        self.query_one("#progress_bar").display = False
        self.log_write("[bold]¿Otra ronda? Dale al Search.[/bold]")
        self.query_one("#search_input").value = ""
        self.query_one("#search_input").focus()

    def log_write(self, message: str):
        log = self.query_one("#log_output")
        log.write(message)

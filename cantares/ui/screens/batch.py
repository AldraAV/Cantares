
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Button, Label, RichLog, TabbedContent, TabPane, Input, SelectionList, ContentSwitcher, ProgressBar
from textual.containers import Container, Vertical, Horizontal, Center
from textual.binding import Binding
from cantares.core.spotify_exporter import SpotifyExporter
from cantares.core.batch_downloader import BatchDownloader
import os
import csv
import threading

class BatchScreen(Screen):
    CSS = """
    BatchScreen {
        align: center middle;
    }
    
    #main_container {
        width: 95%;
        height: 95%;
        border: solid green;
        padding: 1;
        background: $surface;
    }

    .subtitle {
        text-align: center;
        color: $text-muted;
        margin-bottom: 1;
    }

    .options-row {
        height: auto;
        margin: 1 0;
        align: center middle;
    }
    
    .options-row Input {
        width: 20;
        margin: 0 1;
    }

    #playlist_selector {
        height: 1fr;
        border: solid gray;
    }

    #log_output {
        height: 1fr;
        border: solid gray;
        background: $surface-darken-1;
    }
    
    Button {
        margin: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("r", "refresh_csv", "Reload CSV"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Label("📦  Cantares — Operaciones por Lote", id="title"),
            
            TabbedContent(
                # --- TAB 1: EXPORT ---
                TabPane("🎵 Exportar de Spotify",
                    Vertical(
                        Label("Exporta tu librería y playlists a CSV", classes="subtitle"),
                        Label("Requiere SPOTIFY_CLIENT_ID en .env", classes="subtitle"),
                        
                        Center(
                            Button("🚀 Iniciar Exportación", id="btn_export", variant="primary"),
                        ),
                        RichLog(highlight=True, markup=True, id="log_export")
                    )
                ),

                # --- TAB 2: DOWNLOAD ---
                TabPane("⬇️ Descarga Masiva",
                    ContentSwitcher(
                        # View 1: Config
                        Container(
                            Label("Cargar playlists desde spotify_export.csv", classes="subtitle"),
                            Horizontal(
                                Button("🔄 Cargar CSV", id="btn_load_csv", variant="primary"),
                                Label("Selecciona Playlists:", classes="subtitle"),
                                classes="options-row"
                            ),
                            SelectionList(id="playlist_selector"),
                            
                            Label("Opciones de Rango (Opcional):", classes="subtitle"),
                            Horizontal(
                                Input(placeholder="Desde (Offset)", id="input_offset", type="integer"),
                                Input(placeholder="Límite (Max)", id="input_limit", type="integer"),
                                classes="options-row"
                            ),
                            
                            Center(
                                Button("🚀 Arrancar Descarga", id="btn_start_batch", variant="success"),
                            ),
                            id="selection_view"
                        ),

                        # View 2: Processing
                        Container(
                            Center(Label("Cocinando...", classes="subtitle")),
                            ProgressBar(total=100, show_eta=True, id="progress_bar"),
                            Label("Calentando motores...", id="status_label"),
                            RichLog(highlight=True, markup=True, id="log_download"),
                            Center(
                                Button("Aguanta un ratito...", disabled=True, id="btn_processing"),
                            ),
                            id="processing_view"
                        ),
                        
                        initial="selection_view", id="switcher"
                    )
                ),
            ),
            Button("🔙 Back to Menu", id="btn_back", variant="error"),
            id="main_container"
        )
        yield Footer()

    def on_mount(self):
        # Auto-load CSV if exists
        if os.path.exists("spotify_export.csv"):
            self.load_csv_playlists()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_back":
            self.dismiss()
        elif event.button.id == "btn_export":
            self.start_export()
        elif event.button.id == "btn_load_csv":
            self.load_csv_playlists()
        elif event.button.id == "btn_start_batch":
            self.start_batch_download()

    # --- EXPORT LOGIC ---
    def start_export(self):
        log = self.query_one("#log_export", RichLog)
        log.clear()
        log.write("[bold cyan]🚀 Arrancando exportación de Spotify... (Aguanta un ratito)[/bold cyan]")
        
        btn = self.query_one("#btn_export", Button)
        btn.disabled = True
        btn.label = "Exportando..."

        threading.Thread(target=self._run_export, daemon=True).start()

    def _run_export(self):
        def callback(msg):
            self.app.call_from_thread(self.query_one("#log_export", RichLog).write, msg)

        try:
            exporter = SpotifyExporter(update_callback=callback)
            exporter.export_to_csv()
            self.app.call_from_thread(self._on_export_finished, True)
        except Exception as e:
            self.app.call_from_thread(self.query_one("#log_export", RichLog).write, f"[red]❌ Algo tostó: {e}[/red]")
            self.app.call_from_thread(self._on_export_finished, False)

    def _on_export_finished(self, success):
        btn = self.query_one("#btn_export", Button)
        btn.disabled = False
        btn.label = "🚀 Iniciar Exportación"
        if success:
            self.notify("¡Así está la calabaza! Exportación lista. Ve a 'Descarga Masiva'.")
            self.load_csv_playlists()

    # --- DOWNLOAD LOGIC ---
    def load_csv_playlists(self):
        selector = self.query_one("#playlist_selector", SelectionList)
        
        if not os.path.exists("spotify_export.csv"):
            self.notify("spotify_export.csv not found. Run export first!", severity="warning")
            return

        playlists = set()
        try:
            with open("spotify_export.csv", "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    playlists.add(row['Playlist'])
            
            selector.clear_options()
            options = [(p, p) for p in sorted(playlists)]
            selector.add_options(options)
            self.notify(f"Loaded {len(options)} playlists")
            
        except Exception as e:
            self.notify(f"Error reading CSV: {e}", severity="error")

    def start_batch_download(self):
        selector = self.query_one("#playlist_selector", SelectionList)
        selected = selector.selected
        
        # If nothing selected, assume ALL
        if not selected:
             self.notify("No playlists selected! Processing ALL.", severity="information")
             selected = None

        offset_val = self.query_one("#input_offset", Input).value
        limit_val = self.query_one("#input_limit", Input).value
        
        offset = int(offset_val) if offset_val.isdigit() else 0
        limit = int(limit_val) if limit_val.isdigit() else None
        
        range_config = {"offset": offset, "limit": limit}
        
        # Switch View
        self.query_one("#switcher", ContentSwitcher).current = "processing_view"
        
        log = self.query_one("#log_download", RichLog)
        log.clear()
        log.write(f"[bold cyan]🚀 Arrancando motores... ¡Vámonos recio![/bold cyan]")
        
        threading.Thread(target=self._run_downloader, args=(selected, range_config), daemon=True).start()

    def _run_downloader(self, selected_playlists, range_config):
        def callback(msg, progress=None):
             self.app.call_from_thread(self._update_download_ui, msg, progress)

        try:
            downloader = BatchDownloader()
            downloader.process_csv(
                selected_playlists=list(selected_playlists) if selected_playlists else None,
                range_config=range_config,
                callback=callback
            )
            self.app.call_from_thread(self._on_download_finished)
        except Exception as e:
             self.app.call_from_thread(self._update_download_ui, f"[red]❌ Algo tostó muy feo: {e}[/red]", 0)

    def _update_download_ui(self, msg, progress):
        self.query_one("#log_download", RichLog).write(msg)
        self.query_one("#status_label", Label).update(msg)
        if progress is not None:
             self.query_one("#progress_bar", ProgressBar).update(progress=progress)

    def _on_download_finished(self):
        btn = self.query_one("#btn_processing", Button)
        btn.disabled = False
        btn.label = "¡Así está la calabaza! (Volver)"
        btn.variant = "success"
        # Temporarily make the button go back to selection
        # self.query_one("#switcher", ContentSwitcher).current = "selection_view"

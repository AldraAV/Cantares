from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Button, Label, Static
from textual.containers import Container, Vertical, Horizontal
from cantares.ui.screens.music import MusicScreen
# from cantares.ui.screens.books import BooksScreen # Placeholder
# from cantares.ui.screens.batch import BatchScreen # Placeholder

LOGO = """
   ______            __                         
  / ____/___ _____  / /_____ _________  _____   
 / /   / __ `/ __ \\/ __/ __ `/ ___/ _ \\/ ___/   
/ /___/ /_/ / / / / /_/ /_/ / /  /  __(__  )    
\\____/\\__,_/_/ /_/\\__/\\__,_/_/   \\___/____/     
                                                
"""

class CantaresApp(App):
    CSS_PATH = "styles.tcss"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "toggle_dark", "Toggle Dark Mode"),
        ("m", "screen_music", "Music Downloader")
    ]
    TITLE = "Cantares v2.0 - Porque lo bueno siempre se comparte"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Container(
            Static(LOGO, classes="logo", id="welcome_title"),
            Label("Porque lo bueno siempre se comparte", id="subtitle"),
            Vertical(
                Button("🎵  Descargar Música", id="btn_music", variant="success"),
                Button("📦  Descarga por Lote", id="btn_batch", variant="primary"),
                Button("📚  Descargar Libros", id="btn_books", variant="warning"),
                Button("❌  Salir", id="btn_exit", variant="error"),
                classes="menu_buttons"
            ),
            id="home_container"
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn_music":
            self.push_screen(MusicScreen())
        elif btn_id == "btn_batch":
            # self.push_screen(BatchScreen())
            pass
        elif btn_id == "btn_books":
            # self.push_screen(BooksScreen())
            pass
        elif btn_id == "btn_exit":
            self.exit()
    
    def action_screen_music(self):
        self.push_screen(MusicScreen())

if __name__ == "__main__":
    app = CantaresApp()
    app.run()

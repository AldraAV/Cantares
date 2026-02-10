from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Button, Label
from textual.containers import Container, Vertical
from cantares.ui.screens.music import MusicScreen
from cantares.ui.screens.books import BooksScreen

class CantaresApp(App):
    CSS_PATH = "styles.tcss"
    BINDINGS = [("q", "quit", "Quit"), ("d", "toggle_dark", "Dark mode")]
    TITLE = "Cantares - Porque lo bueno siempre se comparte"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Label("✨  Welcome to Cantares CLI  ✨", id="welcome_title"),
            Label("The Ultimate Downloader for Music & Books", id="subtitle"),
            Vertical(
                Button("🎵  Music Downloader", id="btn_music", variant="success"),
                Button("📚  Books Downloader", id="btn_books", variant="warning"),
                Button("❌  Exit", id="btn_exit", variant="error"),
                classes="menu_buttons"
            ),
            id="home_container"
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_music":
            self.push_screen(MusicScreen())
        elif event.button.id == "btn_books":
            self.push_screen(BooksScreen())
        elif event.button.id == "btn_exit":
            self.exit()

if __name__ == "__main__":
    app = CantaresApp()
    app.run()

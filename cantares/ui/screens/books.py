from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import Header, Footer, Input, Button, Label, DataTable, ProgressBar
from textual import on, work
from textual.reactive import reactive

from cantares.books.annas_archive import AnnasArchiveSearcher
from cantares.books.downloader import BookDownloader
import asyncio

class BooksScreen(Screen):
    """Screen for searching and downloading books."""
    
    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
    ]

    def compose(self) -> ComposeResult:
        with Container():
            yield Header()
            with Vertical(id="search-container"):
                yield Label("📚 Search for Books (Anna's Archive)", classes="title")
                with Horizontal():
                    yield Input(placeholder="Title, Author, or ISBN...", id="search-input")
                    yield Button("Search", id="search-btn", variant="primary")
            
            yield DataTable(id="results-table", cursor_type="row")
            
            with Vertical(id="download-status", classes="hidden"):
                yield Label("Waiting...", id="status-label")
                yield ProgressBar(total=100, show_eta=True, id="download-progress")
                
            yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Title", "Author", "Year", "Ext", "Link")
        # Hide the Link column if possible, or keep it last
        # table.show_cursor = False

    @on(Button.Pressed, "#search-btn")
    def on_search(self):
        query = self.query_one("#search-input").value
        if not query:
            self.notify("Please enter a search term.")
            return
            
        self.search_books(query)

    @on(Input.Submitted, "#search-input")
    def on_input_submit(self):
        self.on_search()

    @work(exclusive=True, thread=True)
    def search_books(self, query: str):
        table = self.query_one(DataTable)
        self.app.call_from_thread(table.clear)
        self.notify(f"Searching for '{query}'...")
        
        searcher = AnnasArchiveSearcher()
        results = searcher.search(query)
        
        if not results:
            self.notify("No books found.")
            return

        rows = []
        for r in results:
            rows.append((
                r['title'],
                r['author'],
                r['year'],
                r['extension'],
                r['link']
            ))
            
        self.app.call_from_thread(table.add_rows, rows)
        self.notify(f"Found {len(results)} books.")

    @on(DataTable.RowSelected)
    def on_row_selected(self, event: DataTable.RowSelected):
        # Get the row data
        row = self.query_one(DataTable).get_row_at(event.cursor_row)
        title = row[0]
        link = row[4]
        ext = row[3]
        
        self.download_book(title, link, ext)

    @work(exclusive=True, thread=True)
    def download_book(self, title, link, ext):
        self.query_one("#download-status").remove_class("hidden")
        status_label = self.query_one("#status-label")
        progress_bar = self.query_one("#download-progress")
        
        self.app.call_from_thread(status_label.update, f"Resolving download link for: {title}...")
        self.app.call_from_thread(progress_bar.update, progress=0, total=None) # Indeterminate
        
        searcher = AnnasArchiveSearcher()
        dl_link = searcher.get_download_link(link)
        
        if not dl_link:
            self.app.call_from_thread(self.notify, "Failed to get download link.", severity="error")
            self.app.call_from_thread(status_label.update, "Failed.")
            return

        self.app.call_from_thread(status_label.update, f"Downloading: {title}...")
        self.app.call_from_thread(progress_bar.update, progress=0, total=100) # Reset to determinate
        
        downloader = BookDownloader()
        # Clean filename
        safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '-', '_')]).strip()
        filename = f"{safe_title}.{ext}" if ext != "Unknown" else f"{safe_title}.pdf"
        
        def update_progress(current, total):
            if total > 0:
                percent = (current / total) * 100
                self.app.call_from_thread(progress_bar.update, progress=percent, total=100)
            else:
                # If total is unknown, maybe update indeterminate
                pass

        try:
            path = downloader.download(dl_link, filename, progress_callback=update_progress)
            self.app.call_from_thread(self.notify, f"Downloaded to {path}", severity="information")
            self.app.call_from_thread(status_label.update, f"Completed: {path}")
        except Exception as e:
            self.app.call_from_thread(self.notify, f"Error: {e}", severity="error")
            self.app.call_from_thread(status_label.update, "Error downloading.")

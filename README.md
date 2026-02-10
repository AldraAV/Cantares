# Cantares
> *"Porque lo bueno siempre se comparte"*
> Developed with love and written in Python. 🐍💖
---

**Cantares** is an open-source CLI/TUI application for downloading high-quality music and books. It integrates with Deezer APIs (via `deezspot` logic) and scraping sources for books.

## Features

- **Music Module**: 
  - Supports Deezer and Spotify links.
  - Downloads in **FLAC** or **MP3 (320kbps)** (requires ARL token).
  - Metadata handling (Cover Art, ID3 Tags).
  - Fallback to YouTube if Deezer download fails.
- **Books Module**: 
  - Search and download books from Anna's Archive / LibGen.
- **User Interface**: 
  - Terminal User Interface (TUI) powered by Textual.
  - Command Line Interface (CLI) for scripting.

## Installation

### Prerequisites
- Python 3.10+
- FFmpeg (for audio post-processing)

### Steps

1.  Clone the repository:
    ```bash
    git clone https://github.com/AldraAV/Cantares.git
    cd Cantares
    ```

2.  (Optional) Create a virtual environment:
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # Linux/Mac
    source .venv/bin/activate
    ```

3.  Install dependencies:
    ```bash
    pip install -e .
    ```

## Configuration

Create a `.env` file in the root directory to enable High Quality music downloads:

```ini
DEEZER_ARL=your_deezer_arl_token_here
# Optional:
SPOTIFY_CLIENT_ID=your_id
SPOTIFY_CLIENT_SECRET=your_secret
```

## Usage

### TUI Mode
Launch the interactive interface:
```bash
python -m cantares tui
```

### CLI Mode
**Music**:
```bash
python -m cantares music "Artist - Song Name"
# or
python -m cantares music https://open.spotify.com/track/...
```

**Books**:
```bash
python -m cantares books "Clean Code"
```

## Project Structure

- `cantares/`: Main package source.
- `cantares/music/`: Music download logic (DeezEngine, Spotify, YouTube).
- `cantares/books/`: Book scraping logic.
- `cantares/ui/`: Textual interface code.

## License

This project is for educational purposes only.

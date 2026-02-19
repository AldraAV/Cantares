"""
music_downloader.py — Motor de descarga propio de Cantares.

Estrategia dual:
  1) Deezer (primario) — calidad real FLAC/320/128 desde masters
  2) YouTube (fallback) — si Deezer falla, descarga MP3 via yt-dlp

Diseñado con la esencia de Nona: robusto, elegante, sin dependencias externas rotas.
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import List, Dict, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum

import yt_dlp


class DownloadStatus(Enum):
    PENDING = "pending"
    SEARCHING = "searching"
    DOWNLOADING = "downloading"
    COMPLETE = "complete"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TrackResult:
    """Resultado de descarga de un track."""
    track_name: str
    artist: str
    album: str
    status: DownloadStatus = DownloadStatus.PENDING
    file_path: Optional[str] = None
    error: Optional[str] = None
    duration_sec: float = 0.0
    file_size_mb: float = 0.0
    source: str = "youtube"  # 'deezer' or 'youtube'
    quality: str = "MP3"  # FLAC, MP3_320, etc


@dataclass 
class BatchResult:
    """Resultado de un batch de descargas."""
    total: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    tracks: List[TrackResult] = field(default_factory=list)
    elapsed_sec: float = 0.0
    
    @property
    def success_rate(self) -> float:
        return (self.completed / self.total * 100) if self.total > 0 else 0


# Callback type: (message: str, progress_percent: int, track_result: Optional[TrackResult])
ProgressCallback = Callable[[str, int, Optional[TrackResult]], None]


class MusicDownloader:
    """
    Motor de descarga de música de Cantares.
    
    Estrategia dual:
    1) Deezer (primario) — calidad FLAC/MP3_320/MP3_128 real
    2) YouTube (fallback) — MP3 320kbps via yt-dlp
    """
    
    # Configuración de calidad
    AUDIO_FORMAT = "mp3"
    AUDIO_QUALITY = "320"  # kbps
    
    @staticmethod
    def _find_ffmpeg() -> Optional[str]:
        """Auto-detectar ffmpeg: project bin/ > imageio-ffmpeg > PATH > None."""
        import shutil
        # 1. Project bin/ folder (custom copy)
        project_bin = Path(__file__).parent.parent.parent / "bin" / "ffmpeg.exe"
        if project_bin.exists():
            return str(project_bin.parent)
        # Also check generic name
        project_bin2 = Path(__file__).parent.parent.parent / "bin" / "ffmpeg"
        if project_bin2.exists():
            return str(project_bin2.parent)
        # 2. imageio-ffmpeg (bundled) — copy to project bin if found 
        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            if ffmpeg_exe and os.path.exists(ffmpeg_exe):
                # Copy to project bin/ so yt-dlp can find it as ffmpeg.exe
                bin_dir = Path(__file__).parent.parent.parent / "bin"
                bin_dir.mkdir(exist_ok=True)
                target = bin_dir / "ffmpeg.exe"
                if not target.exists():
                    import shutil as sh
                    sh.copy2(ffmpeg_exe, target)
                return str(bin_dir)
        except ImportError:
            pass
        # 3. System PATH
        sys_ffmpeg = shutil.which("ffmpeg")
        if sys_ffmpeg:
            return os.path.dirname(sys_ffmpeg)
        return None
    
    def __init__(self, download_dir: str = "Downloads", callback: Optional[ProgressCallback] = None,
                 use_deezer: bool = True):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.callback = callback or self._default_callback
        self._cancelled = False
        self._use_deezer = use_deezer
        self._deezer = None  # Lazy init
        
    def _default_callback(self, msg: str, percent: int = 0, result: Optional[TrackResult] = None):
        print(f"[{percent:3d}%] {msg}", flush=True)
    
    def cancel(self):
        """Cancelar descarga en progreso."""
        self._cancelled = True
    
    def _yt_dlp_options(self, output_dir: str, filename_template: str = "%(artist)s - %(title)s") -> dict:
        """Opciones optimizadas de yt-dlp."""
        ffmpeg_path = self._find_ffmpeg()
        
        opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': self.AUDIO_FORMAT,
                    'preferredquality': self.AUDIO_QUALITY,
                },
                {
                    'key': 'FFmpegMetadata',
                    'add_metadata': True,
                },
                {
                    'key': 'EmbedThumbnail',
                },
            ],
            'outtmpl': f'{output_dir}/{filename_template}.%(ext)s',
            'default_search': 'ytsearch1',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'writethumbnail': True,
            'embedthumbnail': True,
            'addmetadata': True,
            'socket_timeout': 30,
            'retries': 3,
            'fragment_retries': 3,
            'prefer_ffmpeg': True,
            'keepvideo': False,
        }
        
        if ffmpeg_path:
            opts['ffmpeg_location'] = ffmpeg_path
        
        return opts
    
    def _get_deezer(self, output_dir: str):
        """Lazy init del motor Deezer."""
        if self._deezer is None and self._use_deezer:
            try:
                from cantares.core.deezer_engine import DeezerEngine, Quality
                self._deezer = DeezerEngine(
                    output_dir=output_dir,
                    quality=Quality.FLAC  # Intentar FLAC, fallback automatico
                )
                if not self._deezer.login():
                    self._deezer = None  # ARL invalido, desactivar Deezer
            except Exception:
                self._deezer = None
        return self._deezer

    def search(self, query: str, limit: int = 15) -> List[Dict]:
        """
        Buscar tracks en Deezer.
        Returns: Lista de dicts con keys: id, title, artist, album, duration.
        """
        deezer = self._get_deezer(str(self.download_dir))
        if deezer:
            try:
                results = deezer.search(query, limit)
                normalized = []
                for t in results:
                    normalized.append({
                        'id': str(t.get('SNG_ID', '')),
                        'title': t.get('SNG_TITLE', 'Unknown'),
                        'artist': t.get('ART_NAME', 'Unknown'),
                        'album': t.get('ALB_TITLE', ''),
                        'duration': int(t.get('DURATION', 0)),
                        'source': 'deezer'
                    })
                return normalized
            except Exception:
                pass
        return []
    
    def download_single(self, artist: str, track_name: str, album: str = "",
                         output_dir: Optional[str] = None) -> TrackResult:
        """
        Descarga un solo track.
        Estrategia: Deezer primero (FLAC/320/128), YouTube como fallback.
        """
        result = TrackResult(
            track_name=track_name,
            artist=artist,
            album=album,
            status=DownloadStatus.SEARCHING
        )
        
        target_dir = output_dir or str(self.download_dir)
        os.makedirs(target_dir, exist_ok=True)
        
        safe_artist = self._sanitize(artist)
        safe_title = self._sanitize(track_name)
        
        # Verificar si ya existe (mp3 o flac)
        for ext in ['flac', 'mp3']:
            expected_file = Path(target_dir) / f"{safe_artist} - {safe_title}.{ext}"
            if expected_file.exists():
                result.status = DownloadStatus.SKIPPED
                result.file_path = str(expected_file)
                result.file_size_mb = expected_file.stat().st_size / (1024 * 1024)
                return result
        
        start = time.time()
        
        # ── INTENTO 1: Deezer (calidad real) ──
        deezer = self._get_deezer(target_dir)
        if deezer:
            try:
                deezer.output_dir = Path(target_dir)  # Actualizar directorio
                dz_result = deezer.download_track(artist, track_name)
                if dz_result.success and dz_result.filepath:
                    result.status = DownloadStatus.COMPLETE
                    result.file_path = dz_result.filepath
                    result.file_size_mb = dz_result.size_bytes / (1024 * 1024)
                    result.duration_sec = time.time() - start
                    result.source = "deezer"
                    result.quality = dz_result.quality  # Pass quality from Deezer
                    return result
            except Exception:
                pass  # Silencioso, caer a YouTube
        
        # ── INTENTO 2: YouTube (fallback) ──
        return self._download_youtube(artist, track_name, target_dir, safe_artist, safe_title, result, start)
    
    def _download_youtube(self, artist: str, track_name: str, target_dir: str,
                          safe_artist: str, safe_title: str,
                          result: TrackResult, start: float) -> TrackResult:
        """Descarga via YouTube (fallback)."""
        query = f"{artist} - {track_name}"
        expected_file = Path(target_dir) / f"{safe_artist} - {safe_title}.{self.AUDIO_FORMAT}"
        opts = self._yt_dlp_options(target_dir, f"{safe_artist} - {safe_title}")
        
        try:
            result.status = DownloadStatus.DOWNLOADING
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=True)
                
                if info and 'entries' in info:
                    info = info['entries'][0] if info['entries'] else None
                
                if info:
                    result.duration_sec = info.get('duration', 0)
                    actual_file = self._find_downloaded_file(target_dir, safe_artist, safe_title)
                    if actual_file:
                        result.file_path = str(actual_file)
                        result.file_size_mb = actual_file.stat().st_size / (1024 * 1024)
                        result.status = DownloadStatus.COMPLETE
                    else:
                        result.status = DownloadStatus.COMPLETE
                        result.file_path = str(expected_file)
                else:
                    result.status = DownloadStatus.FAILED
                    result.error = "No capeo nada con eso en YouTube"
            
            result.duration_sec = time.time() - start
        except Exception as e:
            result.status = DownloadStatus.FAILED
            result.error = str(e)[:200]
        
        return result
    
    def download_batch(self, tracks: List[Dict], playlist_name: str = "Downloads",
                       callback: Optional[ProgressCallback] = None) -> BatchResult:
        """
        Descarga un lote de tracks.
        
        Args:
            tracks: Lista de dicts con keys 'Track Name', 'Artist Name', 'Album Name'
            playlist_name: Nombre de la playlist (para crear carpeta)
            callback: Callback de progreso (msg, percent, track_result)
            
        Returns:
            BatchResult con estadísticas
        """
        cb = callback or self.callback
        self._cancelled = False
        
        batch = BatchResult(total=len(tracks))
        start_time = time.time()
        
        # Crear carpeta de playlist
        pl_folder = self._sanitize(playlist_name)
        output_dir = str(self.download_dir / pl_folder)
        os.makedirs(output_dir, exist_ok=True)
        
        cb(f"Playlist: {playlist_name} ({len(tracks)} tracks)", 0, None)
        
        for idx, track in enumerate(tracks):
            if self._cancelled:
                cb("⛔ Pfffff... descarga cancelada por el usuario", 
                   int((idx / batch.total) * 100), None)
                break
            
            artist = track.get('Artist Name', track.get('artist', 'Unknown'))
            name = track.get('Track Name', track.get('name', 'Unknown'))
            album = track.get('Album Name', track.get('album', ''))
            
            progress = int(((idx + 1) / batch.total) * 100)
            cb(f"[{idx+1}/{batch.total}] {artist} - {name}", progress, None)
            
            result = self.download_single(artist, name, album, output_dir)
            batch.tracks.append(result)
            
            if result.status == DownloadStatus.COMPLETE:
                batch.completed += 1
                cb(f"  OK: {result.file_size_mb:.1f} MB", progress, result)
            elif result.status == DownloadStatus.SKIPPED:
                batch.skipped += 1
                cb(f"  SKIP (ya existe): {name}", progress, result)
            else:
                batch.failed += 1
                batch.failed += 1
                cb(f"  ❌ Algo tostó: {result.error}", progress, result)
        
        batch.elapsed_sec = time.time() - start_time
        cb(f"¡Así está la calabaza! {batch.completed} OK, {batch.skipped} saltadas, {batch.failed} tostadas "
           f"({batch.elapsed_sec:.0f}s)", 100, None)
        
        return batch
    
    def download_from_csv(self, csv_path: str, selected_playlists: Optional[List[str]] = None,
                           range_config: Optional[Dict] = None,
                           callback: Optional[ProgressCallback] = None) -> BatchResult:
        """
        Descarga tracks desde un CSV exportado de Spotify.
        
        Args:
            csv_path: Ruta al CSV
            selected_playlists: Lista de playlists a procesar (None = todas)
            range_config: {'offset': int, 'limit': int}
            callback: Callback de progreso
        """
        import csv
        from collections import defaultdict
        
        cb = callback or self.callback
        
        if not os.path.exists(csv_path):
            cb(f"Otssss... CSV no encontrado: {csv_path}", 0, None)
            return BatchResult()
        
        # Leer y agrupar por playlist
        playlists = defaultdict(list)
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pl = row.get('Playlist', 'Unknown')
                if selected_playlists is None or pl in selected_playlists:
                    playlists[pl].append(row)
        
        # Flatten
        all_tracks = []
        for pl_name, tracks in playlists.items():
            for t in tracks:
                t['_playlist'] = pl_name
            all_tracks.extend(tracks)
        
        # Apply range
        offset = (range_config or {}).get('offset', 0)
        limit = (range_config or {}).get('limit', len(all_tracks))
        queue = all_tracks[offset:offset + limit]
        
        cb(f"Cola: {len(queue)} tracks de {len(playlists)} playlists. ¡Vámonos recio!", 0, None)
        
        # Agrupar por playlist para descargar en carpetas
        from collections import defaultdict
        by_playlist = defaultdict(list)
        for t in queue:
            by_playlist[t['_playlist']].append(t)
        
        # Descargar por playlist
        overall = BatchResult(total=len(queue))
        processed = 0
        
        for pl_name, tracks in by_playlist.items():
            sub_result = self.download_batch(tracks, pl_name, callback=cb)
            overall.completed += sub_result.completed
            overall.failed += sub_result.failed
            overall.skipped += sub_result.skipped
            overall.tracks.extend(sub_result.tracks)
            overall.elapsed_sec += sub_result.elapsed_sec
        
        return overall
    
    def _sanitize(self, name: str) -> str:
        """Sanitizar nombre de archivo."""
        invalid = '<>:"/\\|?*'
        result = ''.join(c for c in name if c not in invalid)
        return result.strip()[:200]  # Limitar longitud
    
    def _find_downloaded_file(self, directory: str, artist: str, title: str) -> Optional[Path]:
        """Busca el archivo descargado (yt-dlp puede variar el nombre)."""
        target_dir = Path(directory)
        expected = f"{artist} - {title}.{self.AUDIO_FORMAT}"
        
        # Búsqueda exacta
        exact = target_dir / expected
        if exact.exists():
            return exact
        
        # Buscar por patrón similar (yt-dlp a veces cambia caracteres)
        for f in target_dir.glob(f"*.{self.AUDIO_FORMAT}"):
            if artist.lower() in f.stem.lower() and title.lower()[:20] in f.stem.lower():
                return f
        
        # Buscar el archivo más reciente
        recent = sorted(target_dir.glob(f"*.{self.AUDIO_FORMAT}"), 
                       key=lambda p: p.stat().st_mtime, reverse=True)
        if recent:
            return recent[0]
        
        return None


# ── Quick API ─────────────────────────────────────────────

def download_track(artist: str, name: str, output_dir: str = "Downloads") -> TrackResult:
    """Función rápida para descargar un solo track."""
    dl = MusicDownloader(download_dir=output_dir)
    return dl.download_single(artist, name)


def download_liked_songs(spotify_exporter, limit: int = 15, 
                          output_dir: str = "Downloads",
                          callback: Optional[ProgressCallback] = None) -> BatchResult:
    """
    Descarga las canciones más recientes de Liked Songs.
    
    Args:
        spotify_exporter: Instancia autenticada de SpotifyExporter
        limit: Número de canciones a descargar
        output_dir: Directorio de salida
        callback: Callback de progreso
    """
    dl = MusicDownloader(download_dir=output_dir, callback=callback)
    
    # Obtener liked songs
    if callback:
        callback(f"Jalando {limit} canciones favoritas de Spotify (Aguanta un ratito)...", 0, None)
    
    liked = spotify_exporter.get_liked_songs(limit=limit)
    
    # Convertir a formato de tracks
    tracks = []
    for item in liked:
        t = item.get('track')
        if not t:
            continue
        tracks.append({
            'Track Name': t['name'],
            'Artist Name': t['artists'][0]['name'] if t['artists'] else 'Unknown',
            'Album Name': t['album']['name'] if t.get('album') else 'Unknown',
        })
    
    if callback:
        callback(f"Descargando {len(tracks)} tracks... ¡Arrancamos!", 5, None)
    
    return dl.download_batch(tracks, "Liked Songs", callback=callback)

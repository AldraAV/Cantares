
import os
from cantares.core.music_downloader import MusicDownloader, BatchResult, TrackResult

class BatchDownloader:
    """
    Wrapper para MusicDownloader que soporta operaciones batch.
    Reemplaza la antigua lógica basada en subprocess/deemix.
    """
    def __init__(self, download_dir="Downloads"):
        self.download_dir = download_dir
        self.downloader = MusicDownloader(download_dir=download_dir)

    def process_csv(self, csv_path="spotify_export.csv", selected_playlists=None, range_config=None, callback=None):
        """
        Descarga desde CSV usando MusicDownloader.
        
        Args:
            csv_path: Ruta al CSV.
            selected_playlists: Lista de nombres de playlists a filtrar.
            range_config: Configuración de offset/limit.
            callback: Función (msg: str, progress: int) para reportar progreso.
        """
        # Adaptador de callback: MusicDownloader espera (msg, percent, result)
        # BatchScreen espera (msg, percent)
        def adapter_callback(msg, percent, result):
            if callback:
                callback(msg, percent)

        # Actualizar callback del downloader
        self.downloader.callback = adapter_callback
        
        # Ejecutar descarga
        result = self.downloader.download_from_csv(
            csv_path=csv_path,
            selected_playlists=selected_playlists,
            range_config=range_config,
            callback=adapter_callback
        )
        
        return result

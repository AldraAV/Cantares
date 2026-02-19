import requests
import os

class BookDownloader:
    def download(self, url: str, filename: str, progress_callback=None) -> str:
        """
        Downloads a file from the given URL.
        
        Args:
            url: The direct download URL.
            filename: The target filename (path).
            progress_callback: Optional callback(current_bytes, total_bytes).
        
        Returns:
            Absolute path to the downloaded file.
        """
        # Ensure Books directory exists
        base_dir = "Books"
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
            
        filepath = os.path.join(base_dir, filename)
        
        # Stream download
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        progress_callback(downloaded, total_size)
                        
        return os.path.abspath(filepath)


import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cantares.core.downloader import BatchDownloader
from cantares.core.spotify import SpotifyExporter

def test_downloader_init():
    bd = BatchDownloader()
    print("DONE: BatchDownloader initialized")
    assert bd.download_dir == "Downloads"

def test_sanitize():
    bd = BatchDownloader()
    assert bd.sanitize_filename("My Playlist / 1") == "My Playlist  1"
    print("DONE: Sanitize working")

if __name__ == "__main__":
    try:
        test_downloader_init()
        test_sanitize()
        print("SUCCESS: Core tests passed!")
    except Exception as e:
        print(f"FAILED: Test failed: {e}")
        sys.exit(1)

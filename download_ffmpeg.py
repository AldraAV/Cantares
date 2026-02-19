import os
import requests
import zipfile
import shutil

URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
ZIP_NAME = "ffmpeg_final.zip"
EXTRACT_FOLDER = "ffmpeg_temp_final"
BIN_FOLDER = "bin"

def download_and_install():
    print(f"Downloading {URL}...")
    try:
        with requests.get(URL, stream=True) as r:
            r.raise_for_status()
            with open(ZIP_NAME, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print("Download complete.")
    except Exception as e:
        print(f"Download failed: {e}")
        return

    print("Extracting...")
    try:
        with zipfile.ZipFile(ZIP_NAME, 'r') as zip_ref:
            zip_ref.extractall(EXTRACT_FOLDER)
    except Exception as e:
        print(f"Extraction failed: {e}")
        return

    print("Locating binaries and installing...")
    if not os.path.exists(BIN_FOLDER):
        os.makedirs(BIN_FOLDER)

    for root, dirs, files in os.walk(EXTRACT_FOLDER):
        for file in files:
            if file in ["ffmpeg.exe", "ffprobe.exe"]:
                src = os.path.join(root, file)
                dst = os.path.join(BIN_FOLDER, file)
                shutil.copy2(src, dst)
                print(f"Installed {file}")

    print("Cleaning up...")
    try:
        os.remove(ZIP_NAME)
        shutil.rmtree(EXTRACT_FOLDER)
    except:
        pass

    print("Done! FFmpeg is ready.")

if __name__ == "__main__":
    download_and_install()

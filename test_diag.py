"""Quick diagnostic for Spotify + Download pipeline."""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

print("=== DIAGNOSTIC START ===", flush=True)

# 1. Test Spotify Auth
print("[1] Spotify Auth...", flush=True)
from cantares.core.spotify import SpotifyExporter
exp = SpotifyExporter()
try:
    user = exp.authenticate()
    print(f"  OK: {user['display_name']}", flush=True)
except Exception as e:
    print(f"  FAIL: {e}", flush=True)
    sys.exit(1)

# 2. Get 15 Liked Songs
print("[2] Get 15 Liked Songs...", flush=True)
liked = exp.get_liked_songs(limit=15)
print(f"  Got {len(liked)} songs", flush=True)
for i, item in enumerate(liked):
    t = item['track']
    art = t['artists'][0]['name'] if t['artists'] else '?'
    print(f"  {i+1:2d}. {art} - {t['name']}", flush=True)

# 3. Test Deezer Search (first song)
print("[3] Deezer Search...", flush=True)
from cantares.core.batch_downloader import BatchDownloader
bd = BatchDownloader(download_dir="Downloads/test_diag")
first = liked[0]['track']
query = f"{first['artists'][0]['name']} - {first['name']}"
link = bd.search_deezer(query)
print(f"  Query: {query}", flush=True)
print(f"  Result: {link}", flush=True)

# 4. Test Deemix (single track)
print("[4] Deemix single track test...", flush=True)
if link:
    import subprocess
    os.makedirs("Downloads/test_diag", exist_ok=True)
    cmd = [sys.executable, "-m", "deemix", "--portable", "-p", "Downloads/test_diag", link]
    print(f"  CMD: {' '.join(cmd)}", flush=True)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        print(f"  Return code: {result.returncode}", flush=True)
        if result.stdout: print(f"  STDOUT: {result.stdout[:200]}", flush=True)
        if result.stderr: print(f"  STDERR: {result.stderr[:200]}", flush=True)
    except subprocess.TimeoutExpired:
        print("  TIMEOUT after 60s", flush=True)
    except Exception as e:
        print(f"  ERROR: {e}", flush=True)

# 5. Check downloaded files
print("[5] Files in Downloads/test_diag:", flush=True)
from pathlib import Path
for f in Path("Downloads/test_diag").rglob("*.*"):
    size = f.stat().st_size / 1024
    print(f"  {f.name} ({size:.1f} KB)", flush=True)

print("=== DIAGNOSTIC END ===", flush=True)

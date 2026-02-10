from yt_dlp import YoutubeDL

class YouTubeSearcher:
    def __init__(self):
        self.ydl_opts = {
            'quiet': True,
            'default_search': 'ytsearch1',
            'no_warnings': True,
        }

    def search_video(self, query):
        """Searches for a best match video on YouTube."""
        # Add "Official Audio" to query to improve results for music
        search_query = f"{query} Official Audio"
        
        with YoutubeDL(self.ydl_opts) as ydl:
            try:
                info = ydl.extract_info(search_query, download=False)
                if 'entries' in info and info['entries']:
                    best_match = info['entries'][0]
                    return {
                        "video_id": best_match['id'],
                        "title": best_match['title'],
                        "duration": best_match['duration'],
                        "url": best_match['webpage_url']
                    }
            except Exception as e:
                print(f"Error searching YouTube: {e}")
                return None
        return None

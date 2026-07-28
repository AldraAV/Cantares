import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Config:
    SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "").strip() or None
    SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "").strip() or None

    @classmethod
    def validate(cls):
        # Optional validation
        pass

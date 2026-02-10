import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Config:
    SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
    SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

    @classmethod
    def validate(cls):
        # Optional validation
        pass

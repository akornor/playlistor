from django.conf import settings
from spotipy.oauth2 import SpotifyOAuth

oauth_manager = SpotifyOAuth(
    client_id=settings.SPOTIFY_CLIENT_ID,
    client_secret=settings.SPOTIFY_CLIENT_SECRET,
    redirect_uri=settings.SPOTIFY_REDIRECT_URI,
    scope="playlist-modify-public playlist-modify-private user-read-private",
    cache_path="token.json",
)

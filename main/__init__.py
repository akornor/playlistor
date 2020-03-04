from spotipy.oauth2 import SpotifyOAuth
from django.conf import settings

oauth = SpotifyOAuth(
    settings.SPOTIFY_CLIENT_ID, settings.SPOTIFY_CLIENT_SECRET, settings.SPOTIFY_REDIRECT_URI,
    scope='playlist-modify-public playlist-modify-private user-read-private',
    cache_path='token.json'
    )

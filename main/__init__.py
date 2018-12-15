from spotipy.oauth2 import SpotifyOAuth
from django.conf import settings

oauth = SpotifyOAuth(
    settings.CLIENT_ID, settings.CLIENT_SECRET, settings.REDIRECT_URI,
    scope='playlist-modify-public playlist-modify-private user-read-private',
    cache_path='token.json'
    )

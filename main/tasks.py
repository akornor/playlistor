from audible.celery import app
from celery import shared_task
from spotipy import Spotify, SpotifyException
from .utils import fetch_url, get_playlist_title, get_tracks, create_soup_obj
from main import oauth
from celery_progress.backend import ProgressRecorder

def get_access_token():
    return oauth.get_cached_token()['access_token']

def get_spotify_client(token):
    return Spotify(auth=token)

def grouper(n, iterable):
    return [iterable[i:i + n] for i in range(0, len(iterable), n)]

@shared_task(bind=True)
def generate_playlist(self, playlist_url):
    progress_recorder = ProgressRecorder(self)
    token = get_access_token()
    sp = get_spotify_client(token)
    uid = sp.current_user()['id']
    page = fetch_url(playlist_url)
    soup = create_soup_obj(page)
    playlist_title = get_playlist_title(soup)
    tracks = get_tracks(soup)
    n = len(tracks)
    playlist = sp.user_playlist_create(uid, playlist_title)
    playlist_id = playlist['id']
    tracks_uris = []
    for i, track in enumerate(tracks):
        try:
            results = sp.search(f'{track.title} {track.artist} {track.featuring}', limit=1)
            track_uri = results['tracks']['items'][0]["uri"]
            tracks_uris.append(track_uri)
            progress_recorder.set_progress(i+1, n)
        except IndexError:
            continue
    #You can add a maximum of 100 tracks per request.
    if len(tracks_uris) > 100:
        for chunk in grouper(100, tracks_uris):
            sp.user_playlist_add_tracks(uid, playlist_id, chunk)
    else:
        sp.user_playlist_add_tracks(uid, playlist_id, tracks_uris)
    url = playlist['external_urls']['spotify']
    return url

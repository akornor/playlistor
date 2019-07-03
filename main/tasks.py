from audible.celery import app
from celery import shared_task
from spotipy import Spotify, SpotifyException
from .parsers import fetch_url, AppleMusicParser
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
    html = fetch_url(playlist_url)
    data = AppleMusicParser(html).extract_data()
    playlist_title = data['playlist_title']
    tracks = data['tracks']
    creator = data['playlist_creator']
    n = len(tracks)
    playlist = sp.user_playlist_create(uid, playlist_title, description=f'Originally created by {creator} on Apple Music[{playlist_url}].')
    playlist_id = playlist['id']
    tracks_uris = []
    try:
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
    except SpotifyException as e:
        # Delete playlist if error occurs while adding songs
        sp.user_playlist_unfollow(uid, playlist_id)
        raise e
    url = playlist['external_urls']['spotify']
    return url

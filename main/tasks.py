from audible.celery import app
from celery import shared_task
from spotipy import Spotify, SpotifyException
from .parsers import fetch_url, AppleMusicParser, SpotifyParser
from main import oauth
from celery_progress.backend import ProgressRecorder
import requests
import json

def get_access_token():
    return oauth.get_cached_token()['access_token']

def get_spotify_client(token):
    return Spotify(auth=token)

def grouper(n, iterable):
    return [iterable[i:i + n] for i in range(0, len(iterable), n)]

@shared_task(bind=True)
def generate_spotify_playlist(self, playlist_url):
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

@shared_task(bind=True)
def generate_applemusic_playlist(self, playlist_url):
    progress_recorder = ProgressRecorder(self)
    html = fetch_url(playlist_url)
    data = SpotifyParser(html).extract_data()
    tracks = data['tracks']
    playlist_data = []
    print(tracks)
    n = len(tracks)
    headers = {
        'Authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiIsImtpZCI6IlEzNzlBOUtBUVYifQ.eyJpc3MiOiIyM05CNDlSRDM0IiwiZXhwIjoxNTYwODEzNDI4LCJpYXQiOjE1NjA3NzAyMjh9.0s1EBJkwuHcKBtIAR32ZS2bCjDWG0sw7ooH-_df8fJnQUSWCUwaAytl35J22Br3anlbvqpr5RgJlMwNKJ_lb7w',
        'Music-User-Token': 'AptLfToaSMg2Nfcal+VFwxnTQ3CQkcerw66NSQhGzfiMJTPmINrgkysUTns6HQn044cGExqJfF1iBeW9s8PGhWh8jVXuOKIGl/VeLg1QCzB+iYRioD4ZhHtf4baRk2MmBXBgrrwFxBS88/9OGDuiqetZ99LG1lBB5tW+TKiwGXoFeAU808ya/FBFypjHmooAWoGN/xVsGDqMRHy9ob2KdM1Dn80Ia7aunS4EYiIi5e8wfvFkxg=='
    }
    for i, track in enumerate(tracks):
        params = {
            'term': f'{track.title} {track.artist}',
            'limit': 1
        }
        response = requests.get('https://api.music.apple.com/v1/catalog/us/search', params=params, headers=headers)
        response.raise_for_status()
        results = response.json()
        song = results['results']['songs']['data'][0]
        playlist_data.append({"id": song['id'], "type": song["type"]})
        progress_recorder.set_progress(i+1, n)
    payload = {
       "attributes":{
          "name":"Some Playlist",
          "description":"My description"
       },
       "relationships":{
          "tracks":{
             "data": playlist_data
          }
       }
    }
    # create playlist here 
    response = requests.post('https://api.music.apple.com/v1/me/library/playlists', data=json.dumps(payload), headers=headers)
    response.raise_for_status()
    response = response.json()
    playlist_id = response['data'][0]['id']
    return f'https://music.apple.com/us/playlists/{playlist_id}'

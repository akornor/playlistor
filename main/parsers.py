from collections import namedtuple
import re
from .utils import (
    get_spotify_client,
    requests_retry_session,
    generate_auth_token,
    sanitize_track_name,
)

Track = namedtuple("Track", ["id", "name", "artists"])


SPOTIFY_PLAYLIST_URL_PAT = re.compile(
    r"http(s)?:\/\/open.spotify.com/(user\/.+\/)?playlist/(?P<playlist_id>.+)"
)
APPLE_MUSIC_PLAYLIST_URL_PAT = re.compile(
    r"https:\/\/(embed.)?music\.apple\.com\/(?P<storefront>.{2})\/playlist(\/.+)?\/(?P<playlist_id>.+)"
)


class BaseParser:
    def extract_data(self):
        raise NotImplementedError()


class AppleMusicParser(BaseParser):
    def __init__(self, playlist_url: str) -> None:

        mo = APPLE_MUSIC_PLAYLIST_URL_PAT.match(playlist_url)
        if mo is None:
            raise ValueError(
                "Expected playlist url in the form: https://music.apple.com/gh/playlist/pl.u-e98lGali2BLmkN"
            )
        self.session = session = requests_retry_session()
        token = generate_auth_token()
        self.headers = headers = {"Authorization": f"Bearer {token}"}
        storefront = "us"
        playlist_id = mo.group("playlist_id")
        self.BASE_URL = BASE_URL = "https://api.music.apple.com"
        response = session.get(
            f"{BASE_URL}/v1/catalog/{storefront}/playlists/{playlist_id}",
            headers=headers,
        )
        response.raise_for_status()
        self.data = response.json()["data"]

    def extract_data(self):
        return {
            "playlist_title": self._get_playlist_title(),
            "tracks": self._get_playlist_tracks(),
            "playlist_creator": self._get_playlist_creator(),
            "playlist_artwork_url": self._get_playlist_artwork_url(),
        }

    def _get_playlist_artwork_url(self):
        try:
            artwork_url = self.data[0]["attributes"]["artwork"]["url"]
            w = self.data[0]["attributes"]["artwork"]["width"]
            h = self.data[0]["attributes"]["artwork"]["height"]
            artwork_url = artwork_url.replace("{w}", str(w))
            artwork_url = artwork_url.replace("{h}", str(h))
            return artwork_url
        except Exception:
            return None

    def _get_playlist_title(self):
        return self.data[0]["attributes"]["name"]

    def _get_playlist_tracks(self):
        tracks = []
        track_items = []
        track_items += self.data[0]["relationships"]["tracks"]["data"]
        has_next = self.data[0]["relationships"]["tracks"].get("next")
        while has_next is not None:
            response = self.session.get(self.BASE_URL + has_next, headers=self.headers)
            response.raise_for_status()
            track_items += response.json()["data"]
            has_next = response.json().get("next")
        for track in track_items:
            try:
                artists = []
                track_id = track["id"]
                artists += (
                    track["attributes"]["artistName"]
                    .replace("featuring", ",")  # Lil' Scrappy featuring Young Buck
                    .replace("&", ",")  # Rah Digga & Missy Elliot
                    .replace(" x ", ",")  # Chloe x Halle
                    .split(",")
                )
                name = sanitize_track_name(track["attributes"]["name"])
                tracks.append(Track(id=track_id, name=name, artists=artists))
            except KeyError:
                continue
        return tracks

    def _get_playlist_creator(self):
        # Note: It's possible attribute doesn't contain curator name
        return self.data[0]["attributes"].get("curatorName")


class SpotifyParser(BaseParser):
    def __init__(self, playlist_url):
        mo = SPOTIFY_PLAYLIST_URL_PAT.match(playlist_url)
        if mo is None:
            raise ValueError(
                "Expected playlist url in the form: https://open.spotify.com/playlist/68QbTIMkw3Gl6Uv4PJaeTQ or https://open.spotify.com/user/333aaddaf/playlist/68QbTIMkw3Gl6Uv4PJaeTQ"
            )
        playlist_id = mo.group("playlist_id")
        self.sp = get_spotify_client()
        self.playlist = self.sp.playlist(playlist_id=playlist_id)

    def extract_data(self):
        return {
            "playlist_title": self._get_playlist_title(),
            "tracks": self._get_playlist_tracks(),
            "playlist_creator": self._get_playlist_creator(),
        }

    def _get_playlist_title(self):
        return self.playlist["name"]

    def _get_playlist_tracks(self):
        tracks = []
        items = [] + self.playlist["tracks"]["items"]
        next = self.playlist["tracks"]["next"]
        results = self.playlist["tracks"]
        while next is not None:
            results = self.sp.next(results)
            items += results["items"]
            next = results.get("next")
        for item in items:
            track = item["track"]
            if track is not None:
                track_id = track["id"]
                name = sanitize_track_name(track["name"])
                artists = [artist["name"] for artist in track["artists"]]
                tracks.append(Track(id=track_id, name=name, artists=artists))
        return tracks

    def _get_playlist_creator(self):
        return self.playlist["owner"]["display_name"]

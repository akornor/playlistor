from collections import namedtuple
import re
from .utils import get_spotify_client, requests_retry_session, generate_auth_token

Track = namedtuple("Track", ["id", "title", "artist", "featuring"])


class BaseParser:
    def extract_data(self):
        raise NotImplementedError()


class AppleMusicParser(BaseParser):
    def __init__(self, playlist_url: str) -> None:
        PAT = re.compile(
            r"https:\/\/music\.apple\.com\/(?P<storefront>.+)\/playlist(\/.+)?\/(?P<playlist_id>.+)",
            re.I
        )
        mo = PAT.match(playlist_url)
        if mo is None:
            raise ValueError(
                "Expected playlist url in the form: https://music.apple.com/gh/playlist/pl.u-e98lGali2BLmkN"
            )
        session = requests_retry_session()
        token = generate_auth_token()
        headers = {"Authorization": f"Bearer {token}"}
        storefront = mo.group("storefront")
        playlist_id = mo.group("playlist_id")
        response = session.get(
            f"https://api.music.apple.com/v1/catalog/{storefront}/playlists/{playlist_id}",
            headers=headers,
        )
        response.raise_for_status()
        self.data = response.json()["data"]

    def extract_data(self):
        return {
            "playlist_title": self._get_playlist_title(),
            "tracks": self._get_playlist_tracks(),
            "playlist_creator": self._get_playlist_creator(),
        }

    def _get_playlist_title(self):
        return self.data[0]["attributes"]["name"]

    def _get_playlist_tracks(self):
        tracks = []
        PAT = re.compile(r"\((.*?)\)")
        for track in self.data[0]["relationships"]["tracks"]["data"]:
            track_id = track["id"]
            artist = track["attributes"]["artistName"].replace("&", ",").replace(", ", " ")
            title = track["attributes"]["name"]
            featuring = ""
            if "feat." in title:
                title = title.replace("feat. ", "")
                mo = PAT.search(title)
                if mo is not None:
                    featuring = mo.group(1).replace("&", ",").replace(", ", " ")
                    title = PAT.sub("", title).strip()
            tracks.append(Track(id=track_id, title=title, artist=artist, featuring=featuring))
        return tracks

    def _get_playlist_creator(self):
        # Note: It's possible attribute doesn't contain curator name
        return self.data[0]["attributes"].get("curatorName")


class SpotifyParser(BaseParser):
    def __init__(self, playlist_url):
        PAT = re.compile(r"https:\/\/open.spotify.com/(user\/.+\/)?playlist/(?P<playlist_id>.+)", re.I)
        mo = PAT.match(playlist_url)
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
                title = track["name"]
                artist = track["artists"][0]["name"]
                tracks.append(Track(id=track_id, title=title, artist=artist, featuring=""))
        return tracks

    def _get_playlist_creator(self):
        return self.playlist["owner"]["display_name"]

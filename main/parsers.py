from collections import namedtuple
import re
from .utils import get_access_token, get_spotify_client

Track = namedtuple("Track", ["title", "artist", "featuring"])


class BaseParser:
    def __init__(self, html_source: str) -> None:
        from bs4 import BeautifulSoup

        self._soup = BeautifulSoup(html_source, "html.parser")

    def extract_data(self):
        raise NotImplementedError()


class AppleMusicParser(BaseParser):
    def extract_data(self):
        return {
            "playlist_title": self._get_playlist_title(),
            "tracks": self._get_playlist_tracks(),
            "playlist_creator": self._get_playlist_creator(),
        }

    def _get_playlist_title(self):
        return self._soup.find(class_="product-header__title").get_text().strip()

    def _get_playlist_tracks(self):
        soup = self._soup
        tracks = []
        tracklist = soup.find_all(class_="tracklist-item--song")
        for track in tracklist:
            title = (
                track.find(class_="tracklist-item__text__headline").get_text().strip()
            )
            artist = (
                track.find(class_="table__row__link table__row__link--secondary")
                .get_text()
                .strip()
                .replace("&", ",")
            )
            featuring = ""
            if "feat." in title:
                title = title.replace("feat. ", "")
                mo = re.search(r"\((.*?)\)", title)
                if mo:
                    featuring = mo.group(1).replace("&", ",")
                i = title.find("(")
                title = title[:i]
            tracks.append(Track(title=title, artist=artist, featuring=featuring))
        return tracks

    def _get_playlist_creator(self):
        return (
            self._soup.find(class_="product-header__identity album-header__identity")
            .get_text()
            .strip()
        )


class SpotifyParser:
    def __init__(self, playlist_url):
        PLAYLIST_RE = r"https://open.spotify.com/playlist/(.+)"
        mo = re.match(PLAYLIST_RE, playlist_url)
        if not mo:
            raise ValueError(
                "Expected playlist url in the form: https://open.spotify.com/playlist/68QbTIMkw3Gl6Uv4PJaeTQ"
            )
        playlist_id = mo.group(1)
        token = get_access_token()
        sp = get_spotify_client(token)
        self.playlist = sp.playlist(playlist_id=playlist_id)

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
        for track in self.playlist["tracks"]["items"]:
            title = track["track"]["name"]
            artist = track["track"]["artists"][0]["name"]
            tracks.append(Track(title=title, artist=artist, featuring=""))
        return tracks

    def _get_playlist_creator(self):
        return "Tyler, the creator."

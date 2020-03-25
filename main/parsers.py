from collections import namedtuple
import re
from .utils import get_spotify_client, fetch_url

Track = namedtuple("Track", ["title", "artist", "featuring"])


class BaseParser:
    def extract_data(self):
        raise NotImplementedError()


class AppleMusicParser(BaseParser):
    def __init__(self, playlist_url: str) -> None:
        html = fetch_url(playlist_url)
        from bs4 import BeautifulSoup

        self._soup = BeautifulSoup(html, "html.parser")

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
        PAT = re.compile(r"\((.*?)\)")
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
                mo = PAT.search(title)
                if mo is not None:
                    featuring = mo.group(1).replace("&", ",")
                    title = PAT.sub('', title).strip()
            tracks.append(Track(title=title, artist=artist, featuring=featuring))
        return tracks

    def _get_playlist_creator(self):
        return (
            self._soup.find(class_="product-header__identity album-header__identity")
            .get_text()
            .strip()
        )


class SpotifyParser(BaseParser):
    def __init__(self, playlist_url):
        PAT = r"(https:\/\/)?open.spotify.com/(user\/.+\/)?playlist/(?P<playlist_id>.+)"
        mo = re.match(PAT, playlist_url)
        if not mo:
            raise ValueError(
                "Expected playlist url in the form: https://open.spotify.com/playlist/68QbTIMkw3Gl6Uv4PJaeTQ or https://open.spotify.com/user/333aaddaf/playlist/68QbTIMkw3Gl6Uv4PJaeTQ"
            )
        playlist_id = mo.group('playlist_id')
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
        all_track_results = [] + self.playlist["tracks"]["items"]
        next = self.playlist["tracks"]["next"]
        results = self.playlist["tracks"]
        while next is not None:
            results = self.sp.next(results)
            all_track_results += results["items"]
            next = results.get("next")
        for track in all_track_results:
            title = track["track"]["name"]
            artist = track["track"]["artists"][0]["name"]
            tracks.append(Track(title=title, artist=artist, featuring=""))
        return tracks

    def _get_playlist_creator(self):
        return self.playlist["owner"]["display_name"]

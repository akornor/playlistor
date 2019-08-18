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
        title = self._soup.find(class_="product-header__title").get_text().strip()
        return title

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
        creator = self._soup.find(class_='product-header__identity album-header__identity').get_text().strip()
        return creator

class SpotifyParser(BaseParser):
    def extract_data(self):
        return {
            "playlist_title": self._get_playlist_title(),
            "tracks": self._get_playlist_tracks(),
            # "playlist_creator": self._get_playlist_creator(),
            "_get_playlist_creator": "Testing"
        }

    def _get_playlist_tracks(self):
        token = get_access_token()
        sp = get_spotify_client(token)
        # plid = urlparse(playlist_url).path.split('/')[-1]
        plid = '5aFz6ut5AhDfwmZ33J0ZVN'
        results = sp.playlist_tracks(playlist_id=plid)
        tracks = []
        for track in results['items']:
            title = track['track']['name']
            artist = track['track']['artists'][0]['name']
            tracks.append(Track(title=title, artist=artist, featuring=''))
        return tracks

    def _get_playlist_title(self):
        return self._soup.title.get_text()
        return (
            self._soup.find(class_="product-header__identity album-header__identity")
            .get_text()
            .strip()
        )

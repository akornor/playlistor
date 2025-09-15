from abc import ABC, abstractmethod
from typing import List, Optional
from urllib.parse import urljoin

from .data_models import Playlist, Track
from .utils import (
    generate_auth_token,
    get_applemusic_client,
    get_spotify_client,
    grouper,
    requests_retry_session,
)


class StreamingService(ABC):
    """Base class for streaming service implementations"""

    @abstractmethod
    def get_playlist(self, playlist_id: str, storefront: str = None) -> Playlist:
        """Fetch playlist data and return as unified Playlist object"""

    @abstractmethod
    def search_track(
        self, query: str, limit: int = 10, storefront: str = None
    ) -> List[Track]:
        """Search for a track and return matching results"""

    @abstractmethod
    def search_track_by_isrc(
        self, isrc: str, limit: int = 10, storefront: str = None
    ) -> List[Track]:
        """Search for a track by isrc"""

    @abstractmethod
    def create_playlist(
        self, name: str, description: str = None, track_ids: List[str] = None
    ) -> str:
        """Create a new playlist and return its ID"""


class AppleMusicService(StreamingService):
    """Apple Music streaming service implementation"""

    def __init__(self, access_token: Optional[str] = None):
        self.client = get_applemusic_client()
        if access_token:
            self.client.access_token = access_token

    def get_playlist(self, playlist_id: str, storefront: str = "us") -> Playlist:
        """Fetch Apple Music playlist data"""
        session = requests_retry_session()
        auth_token = generate_auth_token()
        headers = {"Authorization": f"Bearer {auth_token}"}
        API_BASE_URL = "https://api.music.apple.com"

        response = session.get(
            f"{API_BASE_URL}/v1/catalog/{storefront}/playlists/{playlist_id}",
            headers=headers,
        )
        response.raise_for_status()
        playlist_data = response.json()["data"][0]
        playlist_attrs = playlist_data["attributes"]

        # Get artwork URL
        artwork_url = None
        if "artwork" in playlist_attrs:
            artwork = playlist_attrs["artwork"]
            if "url" in artwork:
                w, h = artwork["width"], artwork["height"]
                artwork_url = (
                    artwork["url"].replace("{w}", str(w)).replace("{h}", str(h))
                )

        # Get tracks with pagination
        tracks = []
        track_items = []
        track_items.extend(playlist_data["relationships"]["tracks"]["data"])
        next_url = playlist_data["relationships"]["tracks"].get("next")

        while next_url is not None:
            response = session.get(urljoin(API_BASE_URL, next_url), headers=headers)
            data = response.json()
            track_items.extend(data["data"])
            next_url = data.get("next")
        tracks = [self.raw_to_track(raw) for raw in track_items]

        return Playlist(
            id=playlist_id,
            name=playlist_attrs["name"],
            tracks=tracks,
            creator=playlist_attrs.get("curatorName"),
            description=playlist_attrs.get("description", {}).get("short"),
            artwork_url=artwork_url,
            url=playlist_attrs.get("url"),
        )

    def search_track(
        self, query: str, limit: int = 10, storefront: str = "us"
    ) -> List[Track]:
        results = self.client.search(query=query, limit=limit, storefront=storefront)

        if not results or "results" not in results or "songs" not in results["results"]:
            return []

        return [
            self.raw_to_track(raw)
            for raw in results["results"]["songs"].get("data", [])
        ]

    def search_track_by_isrc(
        self, isrc: str, limit: int = 10, storefront: str = "us"
    ) -> List[Track]:
        results = self.client.get_songs_by_isrc([isrc], storefront=storefront)
        return [self.raw_to_track(raw) for raw in results.get("data", [])]

    def create_playlist(
        self, name: str, description: str = None, track_ids: List[str] = None
    ) -> str:
        if len(track_ids) > 100:
            # Create playlist with first 100 tracks
            playlist_data = self.client.user_playlist_create(
                name=name, description=description, track_ids=track_ids[:100]
            )
            playlist_id = playlist_data["data"][0]["id"]

            # Add remaining tracks in chunks
            remaining_tracks = track_ids[100:]
            for chunk in grouper(100, remaining_tracks):
                self.client.user_playlist_add_tracks(playlist_id, chunk)

            return playlist_id
        else:
            playlist_data = self.client.user_playlist_create(
                name=name, description=description, track_ids=track_ids
            )
            return playlist_data["data"][0]["id"]

    def raw_to_track(self, raw: dict) -> Track:
        attrs = raw["attributes"]
        artists = []
        artist_name = attrs.get("artistName", "")
        artists.extend(
            artist_name.replace("featuring", ",")
            .replace("&", ",")
            .replace(" x ", ",")
            .split(",")
        )
        artists = [artist.strip() for artist in artists if artist.strip()]

        return Track(
            id=raw["id"],
            name=attrs.get("name"),
            artists=artists,
            album=attrs.get("albumName"),
            duration_ms=attrs.get("durationInMillis"),
            isrc=attrs.get("isrc"),
            release_date=attrs.get("releaseDate"),
        )

    def __str__(self):
        return "apple-music"


class SpotifyService(StreamingService):

    def __init__(self):
        self.client = get_spotify_client()

    def get_playlist(self, playlist_id: str, storefront: str = None) -> Playlist:
        playlist = self.client.playlist(playlist_id=playlist_id)

        # Get all tracks with pagination
        tracks = []
        items = []
        items.extend(playlist["tracks"]["items"])
        track_results = playlist["tracks"]
        has_next = track_results.get("next")

        while has_next is not None:
            track_results = self.client.next(track_results)
            items.extend(track_results["items"])
            has_next = track_results.get("next")

        for i, item in enumerate(items):
            track = item["track"]
            if track is not None:
                tracks.append(self.raw_to_track(track))

        return Playlist(
            id=playlist_id,
            name=playlist["name"],
            tracks=tracks,
            creator=playlist["owner"]["display_name"],
            description=playlist["description"],
            url=playlist["external_urls"]["spotify"],
        )

    def search_track(
        self, query: str, limit: int = 10, storefront: str = None
    ) -> List[Track]:
        results = self.client.search(query, limit=limit, type="track")["tracks"][
            "items"
        ]
        return [self.raw_to_track(track) for track in results]

    def search_track_by_isrc(
        self, isrc: str, limit: int = 10, storefront: str = None
    ) -> List[Track]:
        query = f"isrc:{isrc}"
        return self.search_track(query, limit)

    def create_playlist(
        self, name: str, description: str = None, track_ids: List[str] = None
    ) -> str:

        user_id = self.client.current_user()["id"]
        playlist = self.client.user_playlist_create(
            user_id, name, description=description
        )
        playlist_id = playlist["id"]

        if track_ids:
            track_uris = [f"spotify:track:{track_id}" for track_id in track_ids]

            # Add tracks in chunks of 100 (Spotify's limit)
            if len(track_uris) > 100:
                for chunk in grouper(100, track_uris):
                    self.client.playlist_add_items(playlist_id, chunk)
            else:
                self.client.playlist_add_items(playlist_id, track_uris)

        return playlist_id

    def raw_to_track(self, raw: dict) -> Track:
        return Track(
            id=raw["id"],
            name=raw["name"],
            artists=[artist["name"] for artist in raw["artists"]],
            album=raw["album"]["name"],
            duration_ms=raw["duration_ms"],
            isrc=raw.get("external_ids", {}).get("isrc"),
            release_date=raw["album"]["release_date"],
        )

    def __str__(self):
        return "spotify"

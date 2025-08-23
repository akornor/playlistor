from dataclasses import asdict, dataclass
from typing import List, Optional


@dataclass
class Track:
    """
    Unified Track representation for cross-platform compatibility.
    Combines fields from all previous Track implementations.
    """

    id: str
    name: str
    artists: List[str]

    # Optional fields
    album: Optional[str] = None
    duration_ms: Optional[int] = None
    isrc: Optional[str] = None
    release_date: Optional[str] = None
    position: Optional[int] = None

    # Computed properties
    @property
    def length(self) -> Optional[int]:
        """Duration in seconds"""
        return self.duration_ms // 1000 if self.duration_ms else None

    @property
    def albums(self) -> List[str]:
        """Return album as list for compatibility with similarity functions"""
        return [self.album] if self.album else []

    @property
    def sanitized_name(self) -> str:
        """Sanitized track name for search purposes"""
        from .utils import sanitize_track_name

        return sanitize_track_name(self.name)

    def to_dict(self) -> dict:
        """Convert to dictionary, useful for serialization"""
        return asdict(self)


@dataclass
class Playlist:
    """
    Unified Playlist representation for cross-platform compatibility.
    """

    id: str
    name: str
    tracks: List[Track]

    # Optional fields
    creator: Optional[str] = None
    description: Optional[str] = None
    artwork_url: Optional[str] = None
    url: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary with tracks as dicts"""
        return {
            "id": self.id,
            "name": self.name,
            "tracks": [track.to_dict() for track in self.tracks],
            "creator": self.creator,
            "description": self.description,
            "artwork_url": self.artwork_url,
            "url": self.url,
        }


def parse_artist_names(artist_string: str) -> List[str]:
    """
    Parse artist string into list of individual artist names.
    Handles common separators like 'featuring', '&', ' x '.
    """
    if not artist_string:
        return []

    artists = []
    for artist in (
        artist_string.replace("featuring", ",")
        .replace("&", ",")
        .replace(" x ", ",")
        .split(",")
    ):
        clean_artist = artist.strip()
        if clean_artist:
            artists.append(clean_artist)

    return artists

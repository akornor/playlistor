import re
from dataclasses import asdict

import requests
from celery import shared_task
from celery.utils.log import get_task_logger
from celery_progress.backend import ProgressRecorder

from playlistor.celery import app  # noqa

from .counters import Counters
from .matching import are_tracks_same, track_similarity
from .services import AppleMusicService, SpotifyService
from .utils import parse_track_info, strip_qs

logger = get_task_logger(__name__)

counters = Counters()

SPOTIFY_PLAYLIST_URL_PAT = re.compile(
    r"http(s)?:\/\/open.spotify.com/(user\/.+\/)?playlist/(?P<playlist_id>[^\s?]+)"
)
APPLE_MUSIC_PLAYLIST_URL_PAT = re.compile(
    r"https:\/\/(embed.)?music\.apple\.com\/(?P<storefront>.{2})\/playlist(\/.+)?\/(?P<playlist_id>[^\s?]+)"
)


def search_with_isrc(service, track):
    if track.isrc:
        return service.search_track_by_isrc(track.isrc, limit=10)
    return []


def search_with_full_metadata(service, track):
    clean_title = parse_track_info(track.name)["title"]
    return service.search_track(f"track:{clean_title} artist:{track.artists}", limit=10)


def search_with_primary_artist(service, track):
    clean_title = parse_track_info(track.name)["title"]
    if track.artists:
        return service.search_track(f"{clean_title} {track.artists[0]}", limit=10)
    return service.search_track(clean_title, limit=10)


def search_with_fuzzy_name(service, track):
    clean_title = parse_track_info(track.name)["title"]
    return service.search_track(clean_title, limit=20)


def find_best_match(source_track, search_results):
    if not search_results:
        return None

    matches = sorted(
        search_results,
        key=lambda result_track: track_similarity(source_track, result_track),
        reverse=True,
    )
    return matches[0] if matches else None


def search_with_quality_fallbacks(service, source_track):
    search_strategies = [
        ("ISRC", search_with_isrc),
        ("Full metadata", search_with_full_metadata),
        ("Primary artist", search_with_primary_artist),
        ("Fuzzy name", search_with_fuzzy_name),
    ]

    for strategy_name, strategy_func in search_strategies:
        results = strategy_func(service, source_track)
        if not results:
            continue

        best_match = find_best_match(source_track, results)

        if best_match and are_tracks_same(source_track, best_match):
            logger.info(
                f"Found good match using {strategy_name} strategy for '{source_track.name}'"
            )
            return best_match

        if best_match:
            similarity = track_similarity(source_track, best_match)
            logger.info(
                f"{strategy_name} strategy: best similarity {similarity:.3f} (below threshold) for '{source_track.name}'"
            )

    logger.info(
        f"No quality matches found across all strategies for '{source_track.name}'"
    )
    return None


@shared_task(bind=True)
def generate_spotify_playlist(self, url):
    url = strip_qs(url)
    logger.info(f"Generating spotify equivalent of apple music playlist:{url}")
    progress_recorder = ProgressRecorder(self)

    source_service = AppleMusicService()
    destination_service = SpotifyService()

    playlist_id = APPLE_MUSIC_PLAYLIST_URL_PAT.match(url).group("playlist_id")
    storefront = APPLE_MUSIC_PLAYLIST_URL_PAT.match(url).group("storefront")
    source_playlist = source_service.get_playlist(playlist_id, storefront=storefront)

    track_ids = []
    missed_tracks = []
    n = len(source_playlist.tracks)

    for i, source_track in enumerate(source_playlist.tracks):
        try:
            best_match = search_with_quality_fallbacks(
                destination_service, source_track
            )

            if best_match:
                track_ids.append(best_match.id)
            else:
                missed_tracks.append(asdict(source_track))

        except Exception as e:
            missed_tracks.append(asdict(source_track))
            logger.error(f"Error processing track {source_track.name}: {e}")
            continue
        finally:
            progress_recorder.set_progress(i + 1, n)

    destination_playlist_id = destination_service.create_playlist(
        name=source_playlist.name,
        description=f"Made with Playlistor (https://playlistor.io) :)",
        track_ids=track_ids,
    )

    playlist_url = f"https://open.spotify.com/playlist/{destination_playlist_id}"

    counters.incr_playlist_counter()
    logger.info(f"Missed {len(missed_tracks)} in {n} track(s)")

    return {
        "playlist_url": playlist_url,
        "number_of_tracks": n,
        "missed_tracks": missed_tracks,
        "source": "apple-music",
        "destination": "spotify",
    }


@shared_task(bind=True)
def generate_applemusic_playlist(self, url, access_token):
    url = strip_qs(url)
    logger.info(f"Generating apple music equivalent of spotify playlist:{url}")
    progress_recorder = ProgressRecorder(self)
    playlist_id = SPOTIFY_PLAYLIST_URL_PAT.match(url).group("playlist_id")
    source_service = SpotifyService()
    destination_service = AppleMusicService(access_token=access_token)

    source_playlist = source_service.get_playlist(playlist_id)

    track_ids = []
    missed_tracks = []
    n = len(source_playlist.tracks)
    for i, source_track in enumerate(source_playlist.tracks):
        try:
            # Use functional fallback search approach
            best_match = search_with_quality_fallbacks(
                destination_service, source_track
            )

            if best_match:
                track_ids.append(best_match.id)
            else:
                missed_tracks.append(asdict(source_track))
        except Exception as e:
            logger.error(f"Error processing track {source_track.name}: {e}")
            missed_tracks.append(asdict(source_track))
            continue
        finally:
            progress_recorder.set_progress(i + 1, n)
    try:
        destination_playlist_id = destination_service.create_playlist(
            name=source_playlist.name,
            description=f"Made with Playlistor (https://playlistor.io) :)",
            track_ids=track_ids,
        )

    except requests.exceptions.HTTPError as e:
        response = e.response
        if response.status_code >= 500:
            raise self.retry(exc=e, countdown=30)
        else:
            raise e
    counters.incr_playlist_counter()
    logger.info(f"Missed {len(missed_tracks)} in {n} track(s)")
    return {
        "playlist_url": None,
        "number_of_tracks": n,
        "missed_tracks": missed_tracks,
        "source": "spotify",
        "destination": "apple-music",
    }

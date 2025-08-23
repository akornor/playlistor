from dataclasses import asdict

import requests
from celery import shared_task
from celery.utils.log import get_task_logger
from celery_progress.backend import ProgressRecorder

from playlistor.celery import app  # noqa

from .counters import Counters
from .matching import are_tracks_same, track_similarity
from .parsers import (
    APPLE_MUSIC_PLAYLIST_URL_PAT,
    SPOTIFY_PLAYLIST_URL_PAT,
)
from .services import AppleMusicService, SpotifyService
from .utils import (
    strip_qs,
)

logger = get_task_logger(__name__)

counters = Counters()


@shared_task(bind=True)
def generate_spotify_playlist(self, url):
    url = strip_qs(url)
    logger.info(f"Generating spotify equivalent of apple music playlist:{url}")
    progress_recorder = ProgressRecorder(self)

    # Use services for consistent Track objects
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
            # Search for matching tracks using Spotify service
            if source_track.isrc is not None:
                query = f"isrc:{source_track.isrc}"
            else:
                query = f"track:{source_track.name} artist:{source_track.artists}"
            search_results = destination_service.search_track(query, limit=10)
            if not search_results:
                logger.info(
                    f"Couldn't find a match for {source_track.name}. Skipping...."
                )
                missed_tracks.append(asdict(source_track))
                continue

            # Find the best matching track using similarity algorithm
            matches = sorted(
                search_results,
                key=lambda result_track: track_similarity(source_track, result_track),
                reverse=True,
            )
            best_match = matches[0] if matches else None

            # Only use the match if it meets the similarity threshold
            if best_match and are_tracks_same(source_track, best_match):
                track_ids.append(best_match.id)
            else:
                missed_tracks.append(asdict(source_track))

        except Exception as e:
            missed_tracks.append(asdict(source_track))
            logger.error(f"Error processing track {source_track.name}: {e}")
            continue
        finally:
            progress_recorder.set_progress(i + 1, n)

    # Create Spotify playlist
    # destination_playlist_id = destination_service.create_playlist(
    #     name=source_playlist.name,
    #     description=f"Made with Playlistor (https://playlistor.io) :)",
    #     track_ids=track_ids
    # )

    destination_playlist_id = "0jDsrf34K5Ga1y1ueHmq1l"

    # Get playlist URL
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
            # use single artist as it's observed to improve search accuracy.
            query = f"{source_track.name} {source_track.artists[0]}"
            search_results = destination_service.search_track(query)
            if not search_results:
                logger.info(
                    f"Couldn't find a match for {source_track.name}. Skipping...."
                )
                missed_tracks.append(asdict(source_track))
                continue
            # Find the best matching track using similarity algorithm
            matches = sorted(
                search_results,
                key=lambda result_track: track_similarity(source_track, result_track),
                reverse=True,
            )
            best_match = matches[0] if matches else None

            # Only use the match if it meets the similarity threshold
            if best_match and are_tracks_same(source_track, best_match):
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
        # Create Spotify playlist
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

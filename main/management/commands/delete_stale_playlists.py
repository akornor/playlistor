from main.utils import get_spotify_client
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        sp = get_spotify_client()
        # number of playlists -- we should make this configurable at some point in the future
        N = 500
        playlists = []
        while N > 0:
            playlists.extend(
                sp.current_user_playlists(offset=4000 + N, limit=50)["items"]
            )
            N -= 50
        for playlist in playlists:
            sp.current_user_unfollow_playlist(playlist["id"])
        self.stdout.write(self.style.SUCCESS("Successfully deleted playlists."))

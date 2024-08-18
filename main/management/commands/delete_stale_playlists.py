from django.core.management.base import BaseCommand

from main.utils import get_spotify_client


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("-n", type=int, default=500)
        # make offset required ?
        parser.add_argument("--offset", type=int, default=4000)

    def handle(self, *args, **options):
        sp = get_spotify_client()
        N = options["n"]
        offset = options["offset"]
        playlists = []
        while N > 0:
            playlists.extend(
                sp.current_user_playlists(offset=offset + N, limit=50)["items"]
            )
            N -= 50
        for playlist in playlists:
            sp.current_user_unfollow_playlist(playlist["id"])
        self.stdout.write(self.style.SUCCESS("Successfully deleted playlists."))

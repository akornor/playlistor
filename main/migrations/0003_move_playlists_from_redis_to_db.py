import json

from django.db import migrations
from django.db.backends.sqlite3.schema import DatabaseSchemaEditor
from django.db.migrations.state import StateApps

from main.utils import get_redis_client


def move_playlists_to_database(apps: StateApps, schema_editor: DatabaseSchemaEditor):
    # redis_client = get_redis_client()
    # Playlist = apps.get_model('main', 'Playlist')
    # n = redis_client.llen('playlists')
    # if n > 0:
    #     playlists = redis_client.lrange('playlists', 0, -1)
    #     playlists = [json.loads(playlist) for playlist in playlists[::-1]]
    #     playlists = [Playlist(name=playlist['name'], spotify_url=playlist['spotify_url'], applemusic_url=playlist['applemusic_url']) for playlist in playlists]
    #     Playlist.objects.bulk_create(playlists)
    #     # redis_client.delete('playlists')
    #     redis_client.incrby('counter:playlists', n)
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0002_playlist_created_at"),
    ]

    operations = [
        migrations.RunPython(
            move_playlists_to_database, reverse_code=migrations.RunPython.noop
        ),
    ]

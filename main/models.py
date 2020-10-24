from django.db import models
from bulk_update_or_create import BulkUpdateOrCreateQuerySet


class Playlist(models.Model):
    name = models.CharField(max_length=200)
    spotify_url = models.URLField()
    applemusic_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Playlist({self.name})"

class Track(models.Model):
	MAX_LENGTH = 255
	name = models.CharField(max_length=MAX_LENGTH, null=True, db_index=True)
	artists = models.CharField(max_length=MAX_LENGTH, null=True, db_index=True)
	spotify_id = models.CharField(max_length=MAX_LENGTH, null=True, unique=True)
	apple_music_id = models.CharField(max_length=MAX_LENGTH, null=True, unique=True)
	isrc = models.CharField(max_length=MAX_LENGTH, null=True)

	objects = BulkUpdateOrCreateQuerySet.as_manager()

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=['spotify_id', 'apple_music_id'], name='unique_spotify_id_apple_music_id')
		]

	def __str__(self):
		return f"Track({self.name})"

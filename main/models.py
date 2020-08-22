from django.db import models


class Playlist(models.Model):
    name = models.CharField(max_length=200)
    spotify_url = models.URLField()
    applemusic_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Playlist({self.name})"

class Track(models.Model):
	MAX_LENGTH = 255
	name = models.CharField(max_length=MAX_LENGTH, null=True)
	artist = models.CharField(max_length=MAX_LENGTH, null=True)
	featuring = models.CharField(max_length=MAX_LENGTH, null=True)
	spotify_id = models.CharField(max_length=MAX_LENGTH, null=True)
	apple_music_id = models.CharField(max_length=MAX_LENGTH, null=True)
	isrc = models.CharField(max_length=MAX_LENGTH, null=True)

	def __str__(self):
		return f"Track({self.name})"

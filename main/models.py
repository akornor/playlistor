from django.db import models


class Playlist(models.Model):
    name = models.CharField(max_length=200)
    spotify_url = models.URLField()
    applemusic_url = models.URLField()

    def __str__(self):
        return f"Playlist({self.name})"

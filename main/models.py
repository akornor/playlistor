from django.db import models


class Playlist(models.Model):
    name = models.CharField(max_length=200)
    spotify_url = models.URLField()
    applemusic_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Playlist({self.name})"

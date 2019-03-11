import os
from django.test import TestCase
from django.conf import settings
from main.parsers import AppleMusicParser

class TestParser(TestCase):
	def setUp(self):
		playlist = os.path.join(settings.BASE_DIR, 'main/tests/playlist.html')
		with open(playlist) as f:
			self.html = f.read()

	def test_apple_music_parser(self):
		data = AppleMusicParser(self.html).extract_data()
		self.assertEqual(data['playlist_title'], "It's Lit!!!")
		self.assertEqual(len(data['tracks']), 75)
		self.assertEqual(data['playlist_creator'], 'Apple Music Hip-Hop')
		

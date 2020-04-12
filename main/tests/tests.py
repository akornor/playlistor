import os
from unittest.mock import patch, Mock
from django.test import TestCase
from django.conf import settings
from main.parsers import AppleMusicParser

class TestParser(TestCase):
	def setUp(self):
		playlist = os.path.join(settings.BASE_DIR, 'main/tests/playlist.html')
		with open(playlist) as f:
			self.html = f.read()

	@patch('requests.get')
	def test_apple_music_parser(self, get):
		get.return_value = response = Mock()
		response.headers = {'content-type': 'application/json'}
		response.ok = True
		response.text = self.html
		url = 'https://music.apple.com/gh/playlist/pl.u-e98lGali2BLmkN'
		data = AppleMusicParser(url).extract_data()
		self.assertEqual(data['playlist_title'], "It's Lit!!!")
		self.assertEqual(len(data['tracks']), 75)
		self.assertEqual(data['playlist_creator'], 'Apple Music Hip-Hop')
		

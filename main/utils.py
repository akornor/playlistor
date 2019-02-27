import requests
from bs4 import BeautifulSoup
from collections import namedtuple

Track = namedtuple('Track', ['title', 'artist', 'featuring'])

def get_tracks(soup):
    rv = []
    tracklist = soup.find_all(class_='tracklist-item--song')
    for track in tracklist:
        title = track.find(class_='tracklist-item__text__headline').get_text().strip()
        artist = track.find(class_='table__row__link table__row__link--secondary').get_text().strip()
        featuring = ''
        if 'feat.' in title:
            t = title.replace('feat. ', '')
            i = t.index('(')
            featuring = t[i+1:-1]
        rv.append(Track(title=title, artist=artist, featuring=featuring))
    return rv

def fetch_url(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.text

def create_soup_obj(html):
    soup = BeautifulSoup(html, 'html.parser')
    return soup

def get_playlist_title(soup):
    title = soup.find(class_='product-header__title').get_text().strip()
    return title
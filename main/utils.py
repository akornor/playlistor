import requests

def fetch_url(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.text

def grouper(n, iterable):
    return [iterable[i:i + n] for i in range(0, len(iterable), n)]
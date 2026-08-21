import requests
import json

query = """
[out:json];
(
  node["railway"="station"](9.8,76.2,10.2,76.5);
  node["station"="subway"](9.8,76.2,10.2,76.5);
  node["station"="light_rail"](9.8,76.2,10.2,76.5);
);
out body;
"""
url = 'https://overpass-api.de/api/interpreter'
response = requests.post(url, data={'data': query}, headers={'User-Agent': 'MetGoApp/1.0'})
try:
    data = response.json()
    for e in data['elements']:
        if 'tags' in e and 'name' in e['tags']:
            print(f"{e['tags']['name']}: {e['lat']}, {e['lon']}")
except Exception as e:
    print('Error:', e)
    print(response.text)

import urllib.request, json
url = 'https://nominatim.openstreetmap.org/search?q=Vyttila+Metro+Station+Kochi&format=json'
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        if len(data) > 0:
            print(data[0]['lat'], data[0]['lon'])
except Exception as e:
    print('Error:', e)

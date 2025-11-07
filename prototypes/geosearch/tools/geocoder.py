from pathlib import Path
import json
import time
import urllib
import urllib.request

CACHE_NAME = 'nominatim_cache.json'
# boost candidates within that box, 
# see https://nominatim.org/release-docs/develop/api/Search/#result-restriction
VIEW_BOX = "-9.602050781250002,53.44880116583745,-3.5925292968750004,56.36524486372141"

class GeoCoder:

    def __init__(self):
        self.cache_path = Path(__file__).parent / CACHE_NAME
        if self.cache_path.exists():
            self.cache = json.loads(self.cache_path.read_text())
        else:
            self.cache = {}

    def find_first(self, query):
        ret = None
        res = self.search(query)
        if res['features']:
            ret = res['features'][0]
        return ret

    def search(self, query):
        # look up the response cache
        ret = self._get_from_cache(query)
        if not ret:
            # send a request
            time.sleep(1.5)
            ret = self._request_from_nominatim(query)
            self._add_to_cache(query, ret)
        ret = json.loads(ret)
        return ret

    def _get_from_cache(self, query):
        return self.cache.get(query, None)

    def _request_from_nominatim(self, query):
        print(f'REQUEST: {query}')
        url = f'https://nominatim.openstreetmap.org/search?q={urllib.parse.quote_plus(query)}&viewbox={VIEW_BOX}&format=geojson'
        res = urllib.request.urlopen(url)
        # TODO: error management
        ret = res.read().decode('utf-8')
        return ret

    def _add_to_cache(self, query, response):
        self.cache[query] = response
        self.save_cache()

    def save_cache(self):
        self.cache_path.write_text(json.dumps(self.cache, indent=2))

# coder = GeoCoder()
# # print(coder.search('london eye'))
# print(coder.find_first('london eye'))


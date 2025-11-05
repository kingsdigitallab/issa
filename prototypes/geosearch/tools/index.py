from pathlib import Path
import json
from geocoder import GeoCoder

PLACE_QUESTION_KEY = 'place_names'
INDEX_NAME = 'index.json'
FEATURES_QUESTION_KEY = 'features'

class Index:
    def __init__(self):
        self.index_path = Path(__file__).parent / INDEX_NAME
        if self.index_path.exists():
            self.index = json.loads(self.index_path.read_text())
        else:
            self.index = {}

    def build(self):
        self.index = []

        geocoder = GeoCoder()

        collections_folder_path = Path('../data/collections/')

        for answers_file_path in collections_folder_path.glob("**/transcription_answers.json"):
            answers_file_content = json.loads(answers_file_path.read_text())
            place_names = answers_file_content.get('data', {}).get(PLACE_QUESTION_KEY, {}).get('answer', [])
            features = answers_file_content.get('data', {}).get(FEATURES_QUESTION_KEY, {}).get('answer', [])

            if not isinstance(place_names, list):
                print(f'WARN: {answers_file_path} doesn\'t contain a list of place names')
                continue

            print(f'{answers_file_path}: {len(place_names)} place names')
            for place_name in place_names:
                query = f'{place_name["locality"]} {place_name["place"]}'
                geocode = geocoder.find_first(query)
                print(f'  {query} {'found' if geocode else 'NOT FOUND'}')
                if geocode:
                    geocode['video_place'] = place_name["place"]
                    geocode['video_locality'] = place_name["locality"]
                    geocode['video_start'] = place_name['start']
                    geocode['video_summary'] = features['summary']
                    geocode['video_sport'] = bool(features.get('sport', 0))
                    geocode['video_politics'] = bool(features.get('politics', 0))
                    geocode['video_path'] = str(answers_file_path.parent / str(answers_file_path.parent.name + '.mp4'))
                    # todo: include summary of that unit
                    self.index.append(geocode)

        index_content = {
            'meta': {},
            'data': self.index,
        }

        self.index_path.write_text(json.dumps(index_content, indent=2))

index = Index()

index.build()

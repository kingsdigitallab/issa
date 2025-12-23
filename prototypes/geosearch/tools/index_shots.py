from pathlib import Path
import json
import csv
import re
from functools import lru_cache

PLACE_QUESTION_KEY = 'place_names'
INDEX_NAME = 'index_shots.json'
INDEX_NAME_VECTORS = 'index_shots_vectors.json'
FEATURES_QUESTION_KEY = 'features'
COLLECTION_FOLDER_PATH = Path('../data/collections/')

class Index:
    def __init__(self):
        self.index_path = Path(__file__).parent / INDEX_NAME
        if self.index_path.exists():
            self.index = json.loads(self.index_path.read_text())
        else:
            self.index = {}

    def get_shot_start_time(self, video_name, clip_name, shot_index):
        start_times = self.get_shots_start_times(video_name, clip_name)
        return re.sub(r'\..*$', '', start_times[int(shot_index) - 1]['Start Timecode'])

    @lru_cache(maxsize=10)
    def get_shots_start_times(self, video_name, clip_name):
        ret = []
        with open(COLLECTION_FOLDER_PATH / 'NI' / video_name / clip_name / 'shots' / 'shots.csv', 'r') as file:
            next(file)  # Skip the first line
            reader = csv.DictReader(file)
            ret = list(reader)
        return ret

    def build(self):
        self.index = []
        
        stats = {
            'found': 0,
            'failed': 0,
        }

        questions = [
            'short_description',
            'subject_type',
            'background',
            'indoor',
            'above',
            'subject',
            'colour'
        ]

        for answers_file_path in COLLECTION_FOLDER_PATH.glob("**/frames.json"):
            answers_file_content = json.loads(answers_file_path.read_text())
            middle_props = answers_file_content.get('data', {}).get('middle.jpg', {})
            if not middle_props:
                continue
            print(answers_file_path)

            entry = {
                'video': answers_file_path.parent.parent.parent.parent.name,
                'clip': answers_file_path.parent.parent.parent.name,
                'shot': answers_file_path.parent.name,
            }

            entry['start'] = self.get_shot_start_time(entry['video'], entry['clip'], entry['shot'])

            for question in questions:
                entry[question] = middle_props[question]['value']

            title_data = middle_props['title']['value']
            entry['has_title'] = 1 if title_data  else 0
            if title_data:
                entry['title'] = title_data['title']
                entry['year'] = title_data['year']
                entry['productionCompany'] = title_data['productionCompany']
            else:
                entry['title'] = ''
                entry['year'] = ''
                entry['productionCompany'] = ''

            self.index.append(entry)

        index_content = {
            'meta': {},
            'data': self.index,
        }

        self.index_path.write_text(json.dumps(index_content, indent=2))

        print(f'total: {stats["found"] + stats["failed"]}; found: {stats["found"]} ; not found: {stats["failed"]}')

    def build_vectors(self):
        index = []
        
        stats = {
            'found': 0,
            'failed': 0,
        }

        for answers_file_path in COLLECTION_FOLDER_PATH.glob("**/frames.json"):
            answers_file_content = json.loads(answers_file_path.read_text())
            middle_props = answers_file_content.get('data', {}).get('middle.jpg', {})
            stats['found'] += 1
            if not middle_props:
                stats['failed'] += 1
                continue
            print(answers_file_path)

            entry = {
                'video': answers_file_path.parent.parent.parent.parent.name,
                'clip': answers_file_path.parent.parent.parent.name,
                'shot': answers_file_path.parent.name,
                'vector': middle_props['embedding']['value']
            }

            index.append(entry)

        index_content = {
            'meta': {},
            'data': index,
        }

        # Path(INDEX_NAME_VECTORS).write_text(json.dumps(index_content, indent=2))
        Path(INDEX_NAME_VECTORS).write_text(json.dumps(index_content))

        print(f'total: {stats["found"] + stats["failed"]}; found: {stats["found"]} ; not found: {stats["failed"]}')

index = Index()

# index.build()
index.build_vectors()

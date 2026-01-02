from pathlib import Path
import json
import csv
import re

SOURCE_PATH = Path('source.ml')

class Comparer:

    def compare(self):
        self.group_files()

        self.compare_partitions()

        # self.compare_place_names()

    def group_files(self):
        clips_models_answer = {}

        if not SOURCE_PATH.exists():
            print(f'ERROR: {SOURCE_PATH} not found')
            exit()
            return

        for path in SOURCE_PATH.glob('**/*.json'):
            model = path.parts[1]
            clip_path = '/'.join(path.parts[2:])

            if clip_path not in clips_models_answer:
                clips_models_answer[clip_path] = {}

            if model not in clips_models_answer[clip_path]:
                clips_models_answer[clip_path][model] = path
        
        self.clips_models_answer = clips_models_answer

    def compare_partitions(self):
        stats = {}

        clips_models_answer = self.clips_models_answer

        for clip in clips_models_answer:
            print(clip)
            for model in clips_models_answer[clip]:

                if model not in stats:
                    stats[model] = {
                        'max': 0,
                        'min': 0,
                        'avg': 0,
                        'sum': 0,
                        'err': 0,
                        'hal': [],
                    }

                content = clips_models_answer[clip][model].read_text()
                data = json.loads(content)

                parts = data['data']['parts']['answer']
                parts_count = len(parts)
                parts_valid = 1
                if not isinstance(parts, list):
                    parts_count = 0
                    parts_valid = 0
                    stats[model]['err'] += 1

                stats[model]['max'] = max(stats[model]['max'], parts_count)
                stats[model]['min'] = min(stats[model]['min'], parts_count)
                stats[model]['sum'] += parts_count
                stats[model]['avg'] = stats[model]['sum'] / len(clips_models_answer)

                print(f'  {model:>15}: {parts_count} parts {'   ' if parts_valid else 'ERR '}')
        
        self.show_stats(stats)

    def compare_place_names(self):
        stats = {}

        clips_models_answer = self.clips_models_answer

        for clip in clips_models_answer:
            print(clip)

            transcription_path = (Path('data/input/NI') / Path(clip)).parent / 'transcription.json'
            trans_content = transcription_path.read_text().lower()

            for model in clips_models_answer[clip]:

                hallucinations = []

                if model not in stats:
                    stats[model] = {
                        'max': 0,
                        'min': 0,
                        'avg': 0,
                        'sum': 0,
                        'err': 0,
                        'hal': [],
                    }

                content = clips_models_answer[clip][model].read_text()
                data = json.loads(content)

                parts = data['data']['place_names']['answer']
                parts_count = len(parts)
                parts_valid = 1
                if not isinstance(parts, list):
                    parts_count = 0
                    parts_valid = 0
                    stats[model]['err'] += 1
                else:
                    for part in parts:
                        place = part['place']
                        place = re.sub(r'\s*\([^)]*\)', '', place)
                        if place.lower() not in trans_content:
                            hallucinations.append(place)

                stats[model]['max'] = max(stats[model]['max'], parts_count)
                stats[model]['min'] = min(stats[model]['min'], parts_count)
                stats[model]['sum'] += parts_count
                stats[model]['avg'] = stats[model]['sum'] / len(clips_models_answer)
                stats[model]['hal'].extend(hallucinations)

                print(f'  {model:>15}: {parts_count} parts {'   ' if parts_valid else 'ERR '} {hallucinations}')
        
        self.show_stats(stats)

    def show_stats(self, stats):
        print(f'{'':<15} {'min':>4} {'max':>4} {'avg':>4} {'err':>4} {'hal':>4}')
        for model in stats:
            stat = stats[model]
            print(f'{model:<15} {stat['min']:>4} {stat['max']:>4} {int(stat['avg']):>4} {stat['err']:>4} {len(stat['hal']):>4}')

comparer = Comparer()
comparer.compare()
print('done')

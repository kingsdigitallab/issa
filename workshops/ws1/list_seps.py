from pathlib import Path
import json
from collections import Counter

# Replace 'path/to/your/folder' with your actual directory path
base_dir = Path('batches')

# Find all files ending in .y (e.g., X.y) recursively
files = base_dir.rglob('video_answers.json')

print(f'{"file":40s} {"sep":3s} {"err":3s}')

sep_types = Counter()

for file_path in files:
    data = json.loads(file_path.read_text())['data']
    sep1 = data['sep1']
    seps = sep1['answer']
    errors = [c['error'] for c in sep1['stats']['chunks'] if c['error']]

    sep_types.update([s.get('tag', '') for s in seps])
    
    if len(seps) or errors:
        err_count_str = len(errors)
        err_count_str = str(err_count_str) if err_count_str else ''
        print(f'{str(file_path):40s} {len(seps):3d} {err_count_str:3s}')

print()

for type_count in sep_types.most_common(50):
    print(f'{type_count[1]} {type_count[0]}')

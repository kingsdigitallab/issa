from pathlib import Path
import json
from collections import Counter

# Replace 'path/to/your/folder' with your actual directory path
base_dir = Path('batches')

# Find all files ending in .y (e.g., X.y) recursively
files = base_dir.rglob('video_answers.json')

sep_types = Counter()

missing_progs = 0

files_count = 0
for file_path in sorted(list(files)):
    data = json.loads(file_path.read_text())['data']
    sep1 = data['sep1']
    seps = sep1['answer']
    errors = [c['error'] for c in sep1['stats']['chunks'] if c['error']]
    
    prog_paths = file_path.parent.rglob('*-prog.mp4')
    progs_count = len(list(prog_paths))

    sep_types.update([s.get('tag', '') for s in seps])
    
    if len(seps) or errors:
        err_count_str = len(errors)
        err_count_str = str(err_count_str) if err_count_str else ''
        print(f'{str(file_path):40s}  {progs_count:3d} progs  {len(seps):3d} segs  {err_count_str:3s} errs')
    
    if progs_count == 0:
        missing_progs += 1

    files_count += 1

print()

for type_count in sep_types.most_common(100):
    print(f'{type_count[1]} {type_count[0]}')

print()

print(f'{files_count} files; {missing_progs} missing progs')
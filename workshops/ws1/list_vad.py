from pathlib import Path
import json
from collections import Counter

# Replace 'path/to/your/folder' with your actual directory path
base_dir = Path('batches')

# Find all files ending in .y (e.g., X.y) recursively
files = base_dir.rglob('voice_segments.json')

print(f'{"file":40s} {"sep":3s} {"err":3s}')

files_count = 0
silent_count = 0
for file_path in files:
    segs = json.loads(file_path.read_text())

    print(f'{str(file_path):60s} {len(segs):4d}')
    
    files_count += 1
    if len(segs) < 1:
        silent_count += 1

print()

print(f'{files_count} files; {silent_count} silent')

'''
Script created by opencode:e-research/arc:apex
Randomly sample N items from a file and print them as a pipe-separated string.
'''

import random
import sys
from pathlib import Path

DEFAULT_INPUT = 'batches/all-files.txt'
DEFAULT_SAMPLE_SIZE = 50
SEPARATOR = '|'


def sample_lines(input_path: str, sample_size: int, seed=None) -> str:
    ret = ''
    lines = [line.strip() for line in Path(input_path).read_text().splitlines() if line.strip()]
    if sample_size > len(lines):
        sys.exit(f'ERROR: requested {sample_size} items but {input_path} only has {len(lines)}')
    rng = random.Random(seed)
    ret = SEPARATOR.join(rng.sample(lines, sample_size))
    return ret


if __name__ == '__main__':
    input_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INPUT
    count = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_SAMPLE_SIZE
    print(sample_lines(input_file, count))

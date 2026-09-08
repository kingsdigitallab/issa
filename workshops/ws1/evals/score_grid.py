'''
Script created by opencode:opencode/big-pickle
Reads evals/video_answers.json, computes compare_segments_v2 scores against ground truth,
and produces a CSV with fps x vctx grids stacked per seed.

scp hpc:/scratch/prj/dh_issa/is
sa/workshops/ws1/evals/video_answers.json video_answers_234.json

python3 score_grid.py 234552207.32

'''
import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from segments import compare_segments

DEFAULT_VIDEO = '234552207.32'
# DEFAULT_VIDEO = '139329389.32'
SEGMENTS_TRUE_DIR = Path(__file__).resolve().parent.parent / 'segments_true'
ANSWERS_FILE = Path(__file__).resolve().parent / 'video_answers_DEFAULT_VIDEO.json'
DEFAULT_METRIC_VERSION = 4

VCTX_DIVISOR = 2048 * 1024


def parse_answer(answer):
    if isinstance(answer, list):
        return answer
    if isinstance(answer, str):
        match = re.search(r'```JSON\n(.*?)\n```', answer, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        return json.loads(answer)
    return []


def get_entry_params(entry):
    options = entry.get('options', {})
    fps = options.get('media_io_kwargs', {}).get('video', {}).get('fps')
    seed = options.get('seed')
    longest_edge = (options.get('mm_processor_kwargs') or
                    options.get('extra_body', {}).get('mm_processor_kwargs', {}))
    if isinstance(longest_edge, dict):
        longest_edge = longest_edge.get('size', {}).get('longest_edge')
    vctx = longest_edge // VCTX_DIVISOR if longest_edge else None
    return fps, vctx, seed


def main():
    parser = argparse.ArgumentParser(
        description='Produce fps x vctx score grids from video_answers.json')
    parser.add_argument('video', nargs='?', default=DEFAULT_VIDEO,
                        help=f'video ID for ground truth (default: {DEFAULT_VIDEO})')
    parser.add_argument('-o', '--out', default=None,
                        help='output CSV path (default: evals/score_grid_<video>.csv)')
    parser.add_argument('-l', '--log', default=None,
                        help='output log path (default: evals/evals_<video>.txt)')
    parser.add_argument('-s', '--sep', action='store_true',
                        help='prediction timecodes are for separators (not programmes)')
    parser.add_argument('-m', '--metric', default=DEFAULT_METRIC_VERSION, type=int,
                        help='comparison metric version')
    args = parser.parse_args()

    gt_path = SEGMENTS_TRUE_DIR / f'{args.video}.json'
    if not gt_path.exists():
        sys.exit(f'ERROR: ground truth not found: {gt_path}')
    ground_truth = json.loads(gt_path.read_text())

    answer_file = str(ANSWERS_FILE).replace('DEFAULT_VIDEO', args.video[:3])
    print(f'READ {answer_file}')
    with open(answer_file) as f:
        answers = json.load(f)

    log_path = Path(args.log) if args.log else (
        Path(__file__).resolve().parent / f'evals_{args.video}.txt')

    grids = defaultdict(dict)
    fps_set = set()
    vctx_set = set()

    with open(log_path, 'w') as log:
        for key, entry in answers.items():
            fps, vctx, seed = get_entry_params(entry)
            if fps is None or vctx is None or seed is None:
                print(f'WARNING: skipping {key} (missing params)', file=sys.stderr)
                continue

            predicted = parse_answer(entry.get('answer', []))
            result = compare_segments(ground_truth, predicted, is_separator=args.sep, version=args.metric)
            score = result.get('score', 0.0)
            grids[(seed, vctx, fps)] = score
            fps_set.add(fps)
            vctx_set.add(vctx)

            matched = result.get('matched', 0)
            expected = result.get('expected', len(ground_truth))
            missing = expected - matched
            beyond = result.get('beyond', 1)
            diff = result.get('diff', '')

            log.write(f'=== {key} ===  (fps={fps} vctx={vctx} seed={seed})\n')
            log.write(f'score:  {score*100:.0f}%\n')
            log.write(f'missing: {missing} / expected {expected}'
                      f'   (extra: {result.get("extra", 0)})\n')
            log.write(f'beyond:  {beyond:.4f}\n')
            if diff:
                log.write('diff:\n')
                for line in diff.splitlines():
                    log.write(f'  {line}\n')
            else:
                log.write('diff: (none)\n')
            log.write('\n')

    print(f'WRITTEN {log_path}')

    fps_sorted = sorted(fps_set)
    vctx_sorted = sorted(vctx_set)
    seeds = sorted({k[0] for k in grids})

    out_path = Path(args.out) if args.out else (
        Path(__file__).resolve().parent / f'score_grid_{args.video}.csv')

    with open(out_path, 'w', newline='') as f:
        writer = csv.writer(f)
        for seed in seeds:
            writer.writerow([f'seed={seed}',f'metric={args.metric}'])
            writer.writerow(['vctx\\fps'] + [str(fps) for fps in fps_sorted])
            for vctx in vctx_sorted:
                row = [str(vctx)]
                for fps in fps_sorted:
                    score = grids.get((seed, vctx, fps), None)
                    row.append(f'{score:.4f}' if score is not None else '')
                writer.writerow(row)
            writer.writerow([])

    print(f'WRITTEN {out_path}')


if __name__ == '__main__':
    main()

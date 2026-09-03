'''
Script created by opencode:e-research/arc:apex
Runs answer_videos_vlm.bash followed by cp_answer.py for every combination of
fps and video_tokens, so each settings variation gets answered and aggregated.
'''

from itertools import product
from pathlib import Path
import subprocess

# FPS_VALUES = [0.5, 1.0, 1.5, 2.0]
FPS_VALUES = [1.5]
VIDEO_TOKENS_VALUES = ['12k', '32k', '64k', '96k', '128k']
# VIDEO_TOKENS_VALUES = ['12k', '32k', '64k', '96k', '128k']
ANSWER_SCRIPT = 'answer_videos_vlm.bash'
COPY_SCRIPT = 'cp_answer.py'
SEEDS=["43", "1234"]
# SEEDS=["43"]
VIDEO="234"

BASE_DIR = Path(__file__).resolve().parent


def run_answer(fps: float, video_tokens: str, seed: str) -> int:
    cmd = ['bash', ANSWER_SCRIPT, '--fps', str(fps), '--video-tokens', video_tokens, '--seed', seed, '--video', VIDEO]
    print(f'RUNNING: {" ".join(cmd)}')
    ret = subprocess.run(cmd, cwd=BASE_DIR).returncode
    return ret


def run_copy() -> int:
    print(f'RUNNING: {COPY_SCRIPT}')
    ret = subprocess.run(['python', COPY_SCRIPT], cwd=BASE_DIR).returncode
    return ret


def run_combo(fps: float, video_tokens: str, seed: str) -> int:
    ret = run_answer(fps, video_tokens, seed)
    if ret == 0:
        ret = run_copy()
    return ret


def main() -> int:
    ret = 0
    for fps, video_tokens, seed in product(FPS_VALUES, VIDEO_TOKENS_VALUES, SEEDS):
        print(f'=== fps={fps} video_tokens={video_tokens} seed={seed} ===')
        ret = run_combo(fps, video_tokens, seed)
        if ret != 0:
            print(f'FAILED at fps={fps} video_tokens={video_tokens} (exit code {ret}), aborting remaining combinations')
            break
    print('All combinations completed successfully.')
    return ret


if __name__ == '__main__':
    raise SystemExit(main())

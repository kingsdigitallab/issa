'''
Script created by opencode:e-research/arc:apex
Runs answer_videos_vlm.bash followed by cp_answer.py for every combination of
fps and video_tokens, so each settings variation gets answered and aggregated.
'''

from itertools import product
from pathlib import Path
import subprocess

FPS_VALUES = (0.5, 1.0, 2.0)
VIDEO_TOKENS_VALUES = ('12k', '32k', '64k', '128k')
ANSWER_SCRIPT = 'answer_videos_vlm.bash'
COPY_SCRIPT = 'cp_answer.py'

BASE_DIR = Path(__file__).resolve().parent


def run_answer(fps: float, video_tokens: str) -> int:
    cmd = ['bash', ANSWER_SCRIPT, '--fps', str(fps), '--video-tokens', video_tokens]
    print(f'RUNNING: {" ".join(cmd)}')
    ret = subprocess.run(cmd, cwd=BASE_DIR).returncode
    return ret


def run_copy() -> int:
    print(f'RUNNING: {COPY_SCRIPT}')
    ret = subprocess.run(['python', COPY_SCRIPT], cwd=BASE_DIR).returncode
    return ret


def run_combo(fps: float, video_tokens: str) -> int:
    ret = run_answer(fps, video_tokens)
    if ret == 0:
        ret = run_copy()
    return ret


def main() -> int:
    ret = 0
    for fps, video_tokens in product(FPS_VALUES, VIDEO_TOKENS_VALUES):
        print(f'=== fps={fps} video_tokens={video_tokens} ===')
        ret = run_combo(fps, video_tokens)
        if ret != 0:
            print(f'FAILED at fps={fps} video_tokens={video_tokens} (exit code {ret}), aborting remaining combinations')
            break
    print('All combinations completed successfully.')
    return ret


if __name__ == '__main__':
    raise SystemExit(main())

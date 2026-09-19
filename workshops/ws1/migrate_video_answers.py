# Script created by opencode:e-research/arc:apex
# Prompt: standalone migration script moving each legacy video_answers.json into the
# clip_answers.json of the -full clip folder next to it.

import argparse
import shutil
from pathlib import Path

ANSWERS_FILE_NAME = 'video_answers.json'
TARGET_FILE_NAME = 'clip_answers.json'
FULL_CLIP_FOLDER_SUFFIX = '-full'


def get_full_clip_folder_path(video_folder_path: Path):
    '''Returns the -full clip folder directly inside the video folder, None if there is none or several'''
    ret = None

    full_clip_folder_paths = [
        p for p in sorted(video_folder_path.iterdir())
        if p.is_dir() and p.name.endswith(FULL_CLIP_FOLDER_SUFFIX)
    ]
    if len(full_clip_folder_paths) == 1:
        ret = full_clip_folder_paths[0]

    return ret


def migrate_video_answers(root_path: Path, force=False, dry_run=False) -> dict:
    '''Moves every video_answers.json found under the root path into the clip_answers.json of the -full clip folder next to it.
    Returns the moved answers paths and the skipped ones with the reason of the skip'''
    ret = {'moved': [], 'skipped': []}

    for answers_path in sorted(root_path.rglob(ANSWERS_FILE_NAME)):
        full_clip_folder_path = get_full_clip_folder_path(answers_path.parent)

        if full_clip_folder_path is None:
            ret['skipped'].append((str(answers_path), 'no single -full clip folder next to it'))
            continue

        target_path = full_clip_folder_path / TARGET_FILE_NAME
        if target_path.exists() and not force:
            ret['skipped'].append((str(answers_path), f'target already exists: {target_path}'))
            continue

        if dry_run:
            print(f'would move {answers_path} -> {target_path}')
        else:
            print(f'move {answers_path} -> {target_path}')
            shutil.move(answers_path, target_path)

        ret['moved'].append(str(answers_path))

    return ret


def main():
    parser = argparse.ArgumentParser(description='Move each video_answers.json into the clip_answers.json of the -full clip folder next to it')
    parser.add_argument('root_paths', nargs='+', type=Path, help='root folders to scan')
    parser.add_argument('--force', action='store_true', help='overwrite an existing clip_answers.json in the target folder')
    parser.add_argument('--dry-run', action='store_true', help='only print the moves, do not perform them')
    args = parser.parse_args()

    for root_path in args.root_paths:
        stats = migrate_video_answers(root_path, force=args.force, dry_run=args.dry_run)
        print(f'{root_path}: moved: {len(stats["moved"])}; skipped: {len(stats["skipped"])}')
        for skipped_path, reason in stats['skipped']:
            print(f'skipped {skipped_path}: {reason}')


if __name__ == '__main__':
    main()

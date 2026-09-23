'''
Script created by opencode:e-research/arc:apex
Prompt summary: group the separators recorded in batches/<VIDEOID>/<CLIP>-full/
clip_answers.json (data.sep1.answer) by tag; select one random separator per group
among those with an available video, write the evals/seps/seps.json manifest of the
groups; extract its middle frame into evals/seps/<TAG_SLUG>-<COUNT>-<VIDEOID>-
<HH-MM-SS>.jpg with ffmpeg; render an SVG grid of the frames whose cell sizes scale
with the group counts.
'''

import argparse
import base64
import io
import json
import math
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape

try:
    from PIL import Image as PilImage
except ImportError:
    PilImage = None

sys.path.append(str(Path(__file__).resolve().parent))
from segments import get_hms_from_secs

SOURCE_DIR = Path('./batches')
OUT_DIR = Path('./evals')
SEPS_DIR = OUT_DIR / 'seps'
MANIFEST_PATH = SEPS_DIR / 'seps.json'
DEFAULT_SVG_PATH = OUT_DIR / 'seps.svg'

ANSWERS_FILE_NAME = 'clip_answers.json'
FULL_CLIP_FOLDER_SUFFIX = '-full'
ANSWERS_KEY = 'sep1'
VIDEO_EXTENSION = '.mp4'
JPEG_EXTENSION = '.jpg'
JSON_INDENT = 2

DEFAULT_SEED = 1234
DEFAULT_SCALING = 'clamped'
SCALING_CHOICES = ('clamped', 'linear', 'sqrt')

FFMPEG_LOG_LEVEL = 'error'
FFMPEG_STRICT_COMPLIANCE = 'unofficial'
JPEG_QUALITY = '2'
JPEG_SOI_MARKER = b'\xff\xd8'
MISSING_FLAG = 'missing'
MISSING_VALUE = 1
SECS_PER_HOUR = 3600
SECS_PER_MINUTE = 60
FALLBACK_MAX_COUNT = 1
FALLBACK_ASPECT = 4 / 3

TIMECODE_REGEX = r'^(\d?\d?):(\d\d):(\d\d)$'
TIMECODE_PATTERN = re.compile(TIMECODE_REGEX)
TIMECODE_DASH = '-'

SLUG_FILLER = '-'
SLUG_TRIM = '-'
SLUG_REGEX = r'[^a-z0-9]+'
SLUG_PATTERN = re.compile(SLUG_REGEX)
SLUG_MAX_LEN = 80
SLUG_COLLISION_START = 2
SLUG_EMPTY_FALLBACK = 'untagged'

EMBED_MAX_WIDTH = 640
EMBED_JPEG_QUALITY = 85

SVG_WIDTH = 2400
SVG_MARGIN = 24
SVG_ROW_GAP = 28
SVG_COL_GAP = 16
TITLE_TEXT = 'Separator tag groups — sampled mid-frames'
TITLE_SIZE = 20
TITLE_COLOR = '#333333'
TITLE_BASELINE = SVG_MARGIN + TITLE_SIZE
SUBTITLE_SIZE = 13
SUBTITLE_COLOR = '#666666'
SUBTITLE_GAP = 8
SUBTITLE_BASELINE = TITLE_BASELINE + SUBTITLE_GAP + SUBTITLE_SIZE
HEADER_GAP = 26
HEADER_HEIGHT = SUBTITLE_BASELINE + HEADER_GAP
BACKGROUND_COLOR = '#ffffff'
TINY_CELL_WIDTH = 60
MIN_CELL_WIDTH = 140
MAX_CELL_WIDTH = 640
CAPTION_FONT_SIZE = 13
CAPTION_MIN_FONT_SIZE = 7
CAPTION_CHAR_WIDTH_RATIO = 0.58
CAPTION_LINE_SPACING = 1.25
CAPTION_LINE_COUNT = 2
CAPTION_TOP_GAP = 6
CAPTION_TAG_COLOR = '#333333'
CAPTION_META_COLOR = '#666666'
CAPTION_TAG_WEIGHT = 'bold'
CAPTION_ELLIPSIS = '…'
TEXT_SEPARATOR = ' · '
IMAGE_HREF_PREFIX = 'data:image/jpeg;base64,'


def find_exe(name: str) -> str:
    ret = shutil.which(name)
    if not ret:
        sys.exit(f'ERROR: {name} not found on PATH')
    return ret


def get_secs_from_hms(time_code) -> float | None:
    '''Seconds for a HH:MM:SS (or H:MM:SS) code, None when it does not parse.'''
    ret = None
    match = TIMECODE_PATTERN.match(str(time_code or ''))
    if match:
        ret = (int(match.group(1)) * SECS_PER_HOUR +
               int(match.group(2)) * SECS_PER_MINUTE + int(match.group(3)))
    return ret


def get_timecode_string(mid_sec: float) -> str:
    '''Mid-point seconds as a HH-MM-SS timecode string (for filenames).'''
    ret = get_hms_from_secs(int(mid_sec)).replace(':', TIMECODE_DASH)
    return ret


def make_slug(text: str) -> str:
    '''Lowercase slug: runs of non-alphanumerics collapsed to one dash,
    optionally truncated to SLUG_MAX_LEN.'''
    ret = SLUG_PATTERN.sub(SLUG_FILLER, text.lower()).strip(SLUG_TRIM)
    if len(ret) > SLUG_MAX_LEN:
        ret = ret[:SLUG_MAX_LEN].rstrip(SLUG_TRIM)
    return ret


def get_unique_slug(tag: str, used: dict) -> str:
    '''Unique slug for tag, warning and shifting it with a dash and an increment
    when another distinct tag already produced the same slug.'''
    ret = make_slug(tag)
    if not ret:
        ret = SLUG_EMPTY_FALLBACK
    if used.get(ret, tag) != tag:
        print(f'WARNING: slug collision on {ret!r}, shifting tag {tag!r}', file=sys.stderr)
        suffix = SLUG_COLLISION_START
        while used.get(f'{ret}{SLUG_FILLER}{suffix}', tag) != tag:
            suffix += 1
        ret = f'{ret}{SLUG_FILLER}{suffix}'
    used[ret] = tag
    return ret


def make_separator(entry: dict, clip_dir: Path, videoid: str) -> dict | None:
    '''Record for one answer entry: tag, videoid, clip folder, video path and
    mid-point seconds, None when the tag or the timecodes are unusable.'''
    ret = None
    tag = entry.get('tag')
    start = get_secs_from_hms(entry.get('start'))
    end = get_secs_from_hms(entry.get('end'))
    if not tag or start is None or end is None or end < start:
        print(f'WARNING: unusable separator {entry} in {clip_dir}', file=sys.stderr)
    else:
        ret = {
            'tag': tag,
            'videoid': videoid,
            'clip': clip_dir.name,
            'video': clip_dir / (clip_dir.name + VIDEO_EXTENSION),
            'mid': (start + end) / 2,
        }
    return ret


def collect_separators(batches_dir: Path) -> list:
    '''Records for every usable separator entry across all -full clip folders
    (batches/<VIDEOID>/<CLIP>-full/clip_answers.json, data.sep1.answer).'''
    ret = []
    for video_dir in sorted(p for p in batches_dir.iterdir() if p.is_dir()):
        clip_dirs = [p for p in video_dir.iterdir()
                     if p.is_dir() and p.name.endswith(FULL_CLIP_FOLDER_SUFFIX)]
        for clip_dir in sorted(clip_dirs):
            answers_path = clip_dir / ANSWERS_FILE_NAME
            if not answers_path.exists():
                continue
            try:
                answers = json.loads(answers_path.read_text())
            except json.JSONDecodeError as e:
                print(f'WARNING: skipping {answers_path} ({e})', file=sys.stderr)
                continue
            answer = answers.get('data', {}).get(ANSWERS_KEY, {}).get('answer', [])
            if not isinstance(answer, list):
                print(f'WARNING: no {ANSWERS_KEY} separator list in {answers_path}',
                      file=sys.stderr)
                continue
            for entry in answer:
                separator = make_separator(entry, clip_dir, video_dir.name)
                if separator is not None:
                    ret.append(separator)
    return ret


def group_separators(separators: list) -> dict:
    '''Separators grouped in a dict keyed by their exact tag.'''
    ret = {}
    for separator in separators:
        ret.setdefault(separator['tag'], []).append(separator)
    return ret


def get_selections(groups: list, rng: random.Random) -> list:
    '''(manifest entry, selection or None) pairs for the tag groups in the given
    (count desc, tag asc) order. A group with at least one existing video gets
    a manifest entry recording its randomly selected separator plus a selection
    holding the details needed for the frame extraction; a group without any
    existing video gets a null-videoid entry flagged as missing and no
    selection.'''
    ret = []
    used_slugs = {}
    for tag, group in groups:
        available = [separator for separator in group if separator['video'].exists()]
        count = len(group)
        selection = None
        if available:
            separator = rng.choice(available)
            timecode = get_timecode_string(separator['mid'])
            entry = {
                'videoid': separator['videoid'],
                'count': count,
                'timecode': timecode,
                'tag': tag,
            }
            selection = {
                'tag': tag,
                'count': count,
                'videoid': separator['videoid'],
                'timecode': timecode,
                'video': separator['video'],
                'mid': separator['mid'],
                'out_path': (SEPS_DIR /
                             f'{get_unique_slug(tag, used_slugs)}-{count}-'
                             f"{separator['videoid']}-{timecode}{JPEG_EXTENSION}"),
            }
        else:
            entry = {
                'videoid': None,
                'count': count,
                'timecode': None,
                'tag': tag,
                MISSING_FLAG: MISSING_VALUE,
            }
        ret.append((entry, selection))
    return ret


def extract_frame(video_path: Path, mid_sec: float, out_path: Path,
                  ffmpeg_exe: str) -> bool:
    '''Full-resolution JPEG of the frame at mid_sec; True on success, otherwise
    warn on stderr and remove any partial output.'''
    ret = False
    proc = subprocess.run(
        [ffmpeg_exe, '-v', FFMPEG_LOG_LEVEL, '-ss', f'{mid_sec:.2f}', '-i', str(video_path),
         '-frames:v', '1', '-q:v', JPEG_QUALITY, '-strict', FFMPEG_STRICT_COMPLIANCE,
         '-y', str(out_path)],
        capture_output=True)
    jpeg_ok = False
    if out_path.exists():
        with open(out_path, 'rb') as f:
            jpeg_ok = f.read(len(JPEG_SOI_MARKER)) == JPEG_SOI_MARKER
    if proc.returncode == 0 and jpeg_ok:
        ret = True
    else:
        out_path.unlink(missing_ok=True)
        print(f'WARNING: could not extract a frame at {mid_sec:.0f}s from {video_path}: '
              f'{proc.stderr.decode(errors="replace").strip()}', file=sys.stderr)
    return ret


def get_frame_data(jpeg: bytes) -> tuple:
    '''(aspect ratio, JPEG bytes for the SVG embedding) of a sampled frame: the
    original bytes when PIL is unavailable, otherwise a copy downscaled to
    EMBED_MAX_WIDTH recompressed to keep the SVG lean.'''
    ret = (FALLBACK_ASPECT, jpeg)
    if PilImage is not None:
        image = PilImage.open(io.BytesIO(jpeg))
        if image.width > EMBED_MAX_WIDTH:
            image = image.resize((EMBED_MAX_WIDTH,
                                  round(image.height * EMBED_MAX_WIDTH / image.width)))
        buffer = io.BytesIO()
        image.convert('RGB').save(buffer, format='JPEG', quality=EMBED_JPEG_QUALITY)
        ret = (image.width / image.height, buffer.getvalue())
    return ret


def get_cell_width(count: int, max_count: int, scaling: str) -> float:
    '''Cell width in px for a group of `count` separators, relative to the largest
    displayed group; linear starts at a tiny floor, clamped and sqrt stay between
    the min and max cell widths.'''
    ret = MIN_CELL_WIDTH
    ratio = count / max_count if max_count else 0.0
    if scaling == 'linear':
        ret = max(TINY_CELL_WIDTH, MAX_CELL_WIDTH * ratio)
    elif scaling == 'sqrt':
        ret = MIN_CELL_WIDTH + (MAX_CELL_WIDTH - MIN_CELL_WIDTH) * math.sqrt(ratio)
    else:
        ret = MIN_CELL_WIDTH + (MAX_CELL_WIDTH - MIN_CELL_WIDTH) * ratio
    return ret


def get_caption_font_size(width: float, lines: list) -> float:
    '''Caption font size fitting both lines in the cell width, at least
    CAPTION_MIN_FONT_SIZE.'''
    ret = CAPTION_FONT_SIZE
    longest = max(len(line) for line in lines)
    if longest:
        ret = min(ret, width / (CAPTION_CHAR_WIDTH_RATIO * longest))
    ret = max(CAPTION_MIN_FONT_SIZE, ret)
    return ret


def get_caption_chars_fit(width: float, size: float) -> int:
    ret = int(width / (CAPTION_CHAR_WIDTH_RATIO * size))
    return max(ret, 1)


def truncate_caption(text: str, max_chars: int) -> str:
    ret = text
    if len(ret) > max_chars:
        ret = ret[:max_chars - len(CAPTION_ELLIPSIS)] + CAPTION_ELLIPSIS
    return ret


def svg_text(x: float, y: float, content: str, color: str, size: float,
             anchor: str = 'start', weight: str = '') -> str:
    ret = (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size:.1f}" fill="{color}" '
           f'text-anchor="{anchor}"')
    if weight:
        ret += f' font-weight="{weight}"'
    ret += f'>{escape(content)}</text>'
    return ret


def svg_image(x: float, y: float, width: float, height: float, jpeg: bytes) -> str:
    href = IMAGE_HREF_PREFIX + base64.b64encode(jpeg).decode('ascii')
    ret = (f'<image x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" '
           f'href="{href}" xlink:href="{href}"/>')
    return ret


def build_svg(frames: list, group_count: int, missing_count: int, scaling: str) -> str:
    '''Grid SVG of the sampled frames sorted by group size desc: one cell per
    frame, the cell width scaled by the group count, with the tag, count, videoid
    and timecode captioned at the bottom of each frame. Cells flow left to right
    and wrap when they would cross the canvas margin.'''
    ret = []
    body = []
    max_count = max([frame['count'] for frame in frames] or [FALLBACK_MAX_COUNT])
    x = SVG_MARGIN
    y = HEADER_HEIGHT
    row_height = 0.0
    for frame in frames:
        width = get_cell_width(frame['count'], max_count, scaling)
        if body and x + width > SVG_WIDTH - SVG_MARGIN:
            x = SVG_MARGIN
            y += row_height + SVG_ROW_GAP
            row_height = 0.0
        img_height = width / frame['aspect']
        meta_line = (f"{frame['count']}{TEXT_SEPARATOR}{frame['videoid']}"
                     f"{TEXT_SEPARATOR}{frame['timecode']}")
        size = get_caption_font_size(width, [frame['tag'], meta_line])
        chars_fit = get_caption_chars_fit(width, size)
        tag_y = y + img_height + CAPTION_TOP_GAP + size
        meta_y = tag_y + size * CAPTION_LINE_SPACING
        body.append(svg_image(x, y, width, img_height, frame['jpeg']))
        body.append(svg_text(x, tag_y, truncate_caption(frame['tag'], chars_fit),
                             CAPTION_TAG_COLOR, size, 'start', CAPTION_TAG_WEIGHT))
        body.append(svg_text(x, meta_y, truncate_caption(meta_line, chars_fit),
                             CAPTION_META_COLOR, size))
        row_height = max(row_height, img_height + CAPTION_TOP_GAP +
                         size * CAPTION_LINE_SPACING * CAPTION_LINE_COUNT)
        x += width + SVG_COL_GAP
    svg_height = y + row_height + SVG_MARGIN
    subtitle = (f'{group_count} tag groups{TEXT_SEPARATOR}{missing_count} without '
                f'an available video{TEXT_SEPARATOR}{len(frames)} sampled frames'
                f'{TEXT_SEPARATOR}scaling: {scaling}')
    ret.append(f'<svg xmlns="http://www.w3.org/2000/svg" '
               f'xmlns:xlink="http://www.w3.org/1999/xlink" width="{SVG_WIDTH:.0f}" '
               f'height="{svg_height:.0f}" viewBox="0 0 {SVG_WIDTH:.0f} '
               f'{svg_height:.0f}" font-family="sans-serif">')
    ret.append(f'<rect x="0" y="0" width="{SVG_WIDTH:.0f}" height="{svg_height:.0f}" '
               f'fill="{BACKGROUND_COLOR}"/>')
    ret.append(svg_text(SVG_MARGIN, TITLE_BASELINE, TITLE_TEXT, TITLE_COLOR, TITLE_SIZE))
    ret.append(svg_text(SVG_MARGIN, SUBTITLE_BASELINE, subtitle, SUBTITLE_COLOR,
                        SUBTITLE_SIZE))
    ret.extend(body)
    ret.append('</svg>')
    ret = '\n'.join(ret)
    return ret


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Sample the middle frame of one random separator per tag group '
                    'from the separator answers recorded in the -full clip folders, '
                    'save the frames and a seps.json manifest under evals/seps/, and '
                    'render an SVG grid of the sampled frames.')
    parser.add_argument('--seed', type=int, default=DEFAULT_SEED,
                        help=f'random seed for the per-group separator selection '
                             f'(default: {DEFAULT_SEED})')
    parser.add_argument('--scaling', choices=SCALING_CHOICES, default=DEFAULT_SCALING,
                        help='how the SVG cell size scales with the group count: '
                             'clamped = between fixed min and max cell widths, '
                             'linear = strictly proportional with a tiny floor, '
                             'sqrt = square-root compressed '
                             f'(default: {DEFAULT_SCALING})')
    parser.add_argument('-o', '--out', default=str(DEFAULT_SVG_PATH),
                        help=f'output SVG path (default: {DEFAULT_SVG_PATH})')
    args = parser.parse_args()

    ffmpeg_exe = find_exe('ffmpeg')
    if not SOURCE_DIR.is_dir():
        sys.exit(f'ERROR: batches directory not found: {SOURCE_DIR}')
    SEPS_DIR.mkdir(parents=True, exist_ok=True)

    groups = sorted(group_separators(collect_separators(SOURCE_DIR)).items(),
                    key=lambda item: (-len(item[1]), item[0]))
    missing_count = 0
    entries = []
    selections = []
    for entry, selection in get_selections(groups, random.Random(args.seed)):
        entries.append(entry)
        if selection is None:
            missing_count += 1
        else:
            selections.append(selection)

    MANIFEST_PATH.write_text(json.dumps(entries, indent=JSON_INDENT) + '\n')
    print(f'Written {MANIFEST_PATH} ({len(entries)} groups, {missing_count} without '
          f'an available video)')

    frames = []
    failures = 0
    for selection in selections:
        if not extract_frame(selection['video'], selection['mid'], selection['out_path'],
                             ffmpeg_exe):
            failures += 1
            continue
        jpeg = selection['out_path'].read_bytes()
        aspect, embed_jpeg = get_frame_data(jpeg)
        frames.append({
            'tag': selection['tag'],
            'count': selection['count'],
            'videoid': selection['videoid'],
            'timecode': selection['timecode'],
            'jpeg': embed_jpeg,
            'aspect': aspect,
        })
    print(f'Saved {len(frames)} frames under {SEPS_DIR} ({failures} extraction failures)')

    svg = build_svg(frames, len(entries), missing_count, args.scaling)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(svg)
    print(f'Written {out_path} ({len(frames)} frames, {len(entries)} groups, '
          f'scaling: {args.scaling})')


if __name__ == '__main__':
    main()

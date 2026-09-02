'''
Script created by opencode:e-research/arc:apex
For a given answer key and video, render an SVG timeline of the programme intervals:
ground-truth bars (segments_true/<video>.json) with vertical start/end timecodes,
medium frame thumbnails at the midpoints of ground-truth segments above the track,
medium frame thumbnails of the gaps between ground-truth segments in a band between
the tracks, and the predicted bars from sample11/<video>/video_answers.json data[<key>].
'''
import argparse
import base64
import io
import json
import shutil
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape

try:
    from PIL import Image as PilImage
except ImportError:
    PilImage = None

sys.path.append(str(Path(__file__).resolve().parent.parent))
from segments import convert_segments_to_seconds, load_segments

SOURCE_DIR = Path('./sample11')
SEGMENTS_TRUE_DIR = Path('./segments_true')
OUT_DIR = Path('./evals')

SVG_WIDTH = 1600
LEFT_MARGIN = 50
TITLE_SIZE = 20
TITLE_BASELINE = TITLE_SIZE + 4
TITLE_HEIGHT = 34
FRAME_GAP = 10
MEDIUM_FRAME_WIDTH = 96
MIDDLE_GAP = 10
FRAME_PAD = 4
MIN_EXTRACTION_WIDTH = 4
BAR_HEIGHT = 10
BOTTOM_MARGIN = 14
LABEL_SIZE = 9
LABEL_CHAR_WIDTH = 5.2
LABEL_PAD = 4
LABEL_GAP = 2
LABEL_COLUMN_WIDTH = 7
MIN_LABEL_SIZE = 4
MIN_BAR_WIDTH_IN_PX = 0.5
MIN_VISIBLE_BAR_WIDTH = 1.0
CLIP_TOLERANCE_IN_SECS = 0.5
MID_CLAMP_IN_SECS = 0.1
JPEG_QUALITY = '5'
NOTE_SIZE = 12
NOTE_GAP = 6
FALLBACK_ASPECT = 4 / 3
BACKGROUND_COLOR = '#ffffff'
TRACK_BG_COLOR = '#f0f0f0'
TRUE_COLOR = '#3f6fa3'
TRUE_LABEL_COLOR = '#28507a'
PRED_COLOR = '#d98a3d'
PRED_LABEL_COLOR = '#9c5c1e'
TITLE_COLOR = '#333333'
NOTE_COLOR = '#999999'

LABEL_BAND_HEIGHT = 48


def find_exe(name: str) -> str:
    ret = shutil.which(name)
    if not ret:
        sys.exit(f'ERROR: {name} not found on PATH')
    return ret


def get_video_duration(video_path: Path, ffprobe_exe: str) -> float:
    '''Video duration in seconds, 0.0 when ffprobe fails to report it.'''
    ret = 0.0
    proc = subprocess.run(
        [ffprobe_exe, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0',
         str(video_path)],
        capture_output=True, text=True)
    if proc.returncode == 0:
        try:
            ret = float(proc.stdout.strip().splitlines()[0])
        except (ValueError, IndexError):
            ret = 0.0
    return ret


def extract_frame_jpeg(video_path: Path, time_sec: float, width_px: float,
                       ffmpeg_exe: str) -> bytes:
    '''Single JPEG frame at time_sec scaled to width_px, empty bytes on failure.'''
    ret = b''
    scale_width = max(int(round(width_px)), MIN_EXTRACTION_WIDTH)
    proc = subprocess.run(
        [ffmpeg_exe, '-v', 'error', '-ss', f'{time_sec:.2f}', '-i', str(video_path),
         '-frames:v', '1', '-vf', f'scale={scale_width}:-2', '-q:v', JPEG_QUALITY,
         '-f', 'image2', '-'],
        capture_output=True)
    if proc.returncode == 0 and proc.stdout.startswith(b'\xff\xd8'):
        ret = proc.stdout
    else:
        print(f'WARNING: could not extract a frame at {time_sec:.0f}s: '
              f'{proc.stderr.decode(errors="replace").strip()}', file=sys.stderr)
    return ret


def get_jpeg_aspect(jpeg_bytes: bytes) -> float:
    '''Width/height ratio of a JPEG image, 4:3 when PIL is unavailable.'''
    ret = FALLBACK_ASPECT
    if PilImage is not None:
        w, h = PilImage.open(io.BytesIO(jpeg_bytes)).size
        ret = w / h
    return ret


def extract_frame(video_path: Path, mid: float, frame_width: float, ffmpeg_exe: str) -> tuple:
    '''(mid, width, jpeg) for one frame, or None when extraction fails.'''
    ret = None
    frame_width = max(int(round(frame_width)), MIN_EXTRACTION_WIDTH)
    jpeg = extract_frame_jpeg(video_path, mid, frame_width, ffmpeg_exe)
    if jpeg:
        ret = (mid, frame_width, jpeg)
    return ret


def load_predictions(video_dir: Path, key: str) -> tuple:
    '''(raw predicted segments, model name) for the answer key, empty when absent.'''
    ret = []
    model = ''
    answers_file = video_dir / 'video_answers.json'
    if answers_file.exists():
        with open(answers_file) as f:
            data = json.load(f)
        entry = data.get('data', {}).get(key, {})
        model = entry.get('model', '')
        answer = entry.get('answer', [])
        if isinstance(answer, list):
            ret = answer
    return ret, model


def svg_rect(x: float, y: float, width: float, height: float, color: str, title: str = '') -> str:
    ret = (f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(width, 0):.1f}" '
           f'height="{height:.1f}" fill="{color}"')
    if title:
        ret += f'><title>{escape(title)}</title></rect>'
    else:
        ret += '/>'
    return ret


def svg_text(x: float, y: float, content: str, color: str, size: float = LABEL_SIZE,
             anchor: str = 'start', style: str = '', rotation: int = 0) -> str:
    ret = (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size:.1f}" fill="{color}" '
           f'text-anchor="{anchor}"')
    if style:
        ret += f' font-style="{style}"'
    if rotation:
        ret += f' transform="rotate({rotation} {x:.1f} {y:.1f})"'
    ret += f'>{escape(content)}</text>'
    return ret


def svg_image(x: float, y: float, width: float, height: float, jpeg_bytes: bytes) -> str:
    href = 'data:image/jpeg;base64,' + base64.b64encode(jpeg_bytes).decode('ascii')
    ret = (f'<image x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" '
           f'href="{href}" xlink:href="{href}"/>')
    return ret


def get_label_width(text: str) -> float:
    ret = len(text) * LABEL_CHAR_WIDTH + LABEL_PAD
    return ret


def get_label_size(bar_width: float, codes: list) -> float:
    '''Font size at which both vertical timecodes fit beside each other and in the band.'''
    ret = LABEL_SIZE
    ret = min(ret, LABEL_SIZE * bar_width / (2 * LABEL_COLUMN_WIDTH))
    max_len = max(get_label_width(code) for code in codes)
    ret = min(ret, LABEL_SIZE * (LABEL_BAND_HEIGHT - LABEL_GAP) / max_len)
    ret = max(MIN_LABEL_SIZE, ret)
    return ret


def place_column(placed: list, x_left: float, width: float) -> float:
    '''Column left edge, nudged to the right past any earlier overlapping column.'''
    ret = x_left
    for p_left, p_right in placed:
        if ret < p_right and ret + width > p_left:
            ret = p_right
    placed.append((ret, ret + width))
    return ret


def render_track(segs: list, duration: float, y_bar: float, color: str, label_color: str,
                 labels_above: bool) -> str:
    '''SVG for one interval track: background, bars, and vertical start/end timecodes.'''
    ret = []
    x0 = LEFT_MARGIN
    x1 = SVG_WIDTH - LEFT_MARGIN
    px_per_sec = (x1 - x0) / duration
    ret.append(svg_rect(x0, y_bar, x1 - x0, BAR_HEIGHT, TRACK_BG_COLOR))
    placed = []
    for seg in segs:
        start_s = seg.get('startTime')
        end_s = seg.get('endTime')
        if not seg.get('valid', 0) or start_s is None or end_s is None or end_s <= start_s:
            continue
        x_start = x0 + start_s * px_per_sec
        x_end = x0 + min(end_s, duration) * px_per_sec
        if x_end - x_start < MIN_BAR_WIDTH_IN_PX:
            print(f'WARNING: segment outside the timeline skipped: '
                  f'{seg.get("start", "")} - {seg.get("end", "")}', file=sys.stderr)
            continue
        clipped = end_s > duration + CLIP_TOLERANCE_IN_SECS
        ret.append(svg_rect(x_start, y_bar, max(x_end - x_start, MIN_VISIBLE_BAR_WIDTH),
                            BAR_HEIGHT, color, seg.get('desc', '')))
        start_code = str(seg.get('start', ''))
        end_code = str(seg.get('end', ''))
        if clipped:
            end_code += ' »'
        size = get_label_size(x_end - x_start, [start_code, end_code])
        col_width = LABEL_COLUMN_WIDTH * size / LABEL_SIZE
        rotation = -90 if labels_above else 90
        label_y = y_bar if labels_above else y_bar + BAR_HEIGHT
        anchor_shift = col_width if labels_above else 0
        start_x = place_column(placed, x_start, col_width)
        end_x = place_column(placed, x_end - col_width, col_width)
        ret.append(svg_text(start_x + anchor_shift, label_y, start_code, label_color, size,
                            'start', '', rotation))
        ret.append(svg_text(end_x + anchor_shift, label_y, end_code, label_color, size,
                            'start', '', rotation))
    ret = '\n'.join(ret)
    return ret


def build_svg(video: str, key: str, model: str, duration: float, segs_true: list,
              segs_pred: list, seg_frames: list, gap_frames: list) -> str:
    '''Assemble the complete SVG document. Both frame lists are (mid_time, width, jpeg).'''
    ret = []
    x0 = LEFT_MARGIN
    x1 = SVG_WIDTH - LEFT_MARGIN
    px_per_sec = (x1 - x0) / duration
    seg_items = [(mid, width, width / get_jpeg_aspect(jpeg), jpeg)
                 for mid, width, jpeg in seg_frames]
    gap_items = [(mid, width, width / get_jpeg_aspect(jpeg), jpeg)
                 for mid, width, jpeg in gap_frames]
    seg_frames_height = max([height for _, _, height, _ in seg_items] or [0])
    gap_frames_height = max([height for _, _, height, _ in gap_items] or [0])
    frames_top = TITLE_HEIGHT + FRAME_GAP
    seg_frames_bottom = frames_top + seg_frames_height
    true_bar_y = seg_frames_bottom + LABEL_BAND_HEIGHT
    middle_top = true_bar_y + BAR_HEIGHT + MIDDLE_GAP
    pred_bar_y = middle_top + gap_frames_height + MIDDLE_GAP
    svg_height = pred_bar_y + BAR_HEIGHT + LABEL_BAND_HEIGHT + BOTTOM_MARGIN

    title = f'{video} — {key}'
    if model:
        title += f'   ({model})'
    ret.append(f'<svg xmlns="http://www.w3.org/2000/svg" '
               f'xmlns:xlink="http://www.w3.org/1999/xlink" width="{SVG_WIDTH}" '
               f'height="{svg_height:.0f}" viewBox="0 0 {SVG_WIDTH} {svg_height:.0f}" '
               f'font-family="sans-serif">')
    ret.append(svg_rect(0, 0, SVG_WIDTH, svg_height, BACKGROUND_COLOR))
    ret.append(svg_text(x0, TITLE_BASELINE, title, TITLE_COLOR, TITLE_SIZE))
    for mid, width, height, jpeg in seg_items:
        cx = x0 + mid * px_per_sec
        ret.append(svg_image(cx - width / 2, seg_frames_bottom - height, width, height, jpeg))
    ret.append(render_track(segs_true, duration, true_bar_y, TRUE_COLOR, TRUE_LABEL_COLOR, True))
    for mid, width, height, jpeg in gap_items:
        cx = x0 + mid * px_per_sec
        ret.append(svg_image(cx - width / 2, middle_top + (gap_frames_height - height) / 2,
                            width, height, jpeg))
    ret.append(render_track(segs_pred, duration, pred_bar_y, PRED_COLOR, PRED_LABEL_COLOR, False))
    if not segs_pred:
        ret.append(svg_text((x0 + x1) / 2, pred_bar_y + BAR_HEIGHT + NOTE_GAP + NOTE_SIZE,
                            f"no prediction for '{key}'", NOTE_COLOR, NOTE_SIZE, 'middle',
                            'italic'))
    ret.append('</svg>')
    ret = '\n'.join(ret)
    return ret


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Render an SVG timeline of true vs predicted programme intervals in a video.')
    parser.add_argument('key', help="answer key in video_answers.json, e.g. prg1")
    parser.add_argument('video', help='video filename without extension, e.g. 139329389.32')
    parser.add_argument('-o', '--out', default=None,
                        help=f'output SVG path (default: {OUT_DIR}/<video>_<key>.svg)')
    args = parser.parse_args()

    ffmpeg_exe = find_exe('ffmpeg')
    ffprobe_exe = find_exe('ffprobe')

    video_path = SOURCE_DIR / args.video / f'{args.video}.mp4'
    if not video_path.exists():
        sys.exit(f'ERROR: video not found: {video_path}')

    segs_true = [s for s in convert_segments_to_seconds(load_segments(args.video, SEGMENTS_TRUE_DIR))
                 if s.get('valid')]
    preds_raw, model = load_predictions(SOURCE_DIR / args.video, args.key)
    segs_pred = [s for s in convert_segments_to_seconds(preds_raw) if s.get('valid')]

    duration = get_video_duration(video_path, ffprobe_exe)
    if duration <= 0:
        duration = max([s['endTime'] for s in segs_true + segs_pred if 'endTime' in s] or [0])
    if duration <= 0:
        sys.exit('ERROR: could not determine the video duration')

    px_per_sec = (SVG_WIDTH - 2 * LEFT_MARGIN) / duration

    seg_frames = []
    for seg in segs_true:
        start_s = seg['startTime']
        end_s = min(seg['endTime'], duration)
        mid = max(MID_CLAMP_IN_SECS, min((start_s + end_s) / 2, duration - MID_CLAMP_IN_SECS))
        seg_width = (end_s - start_s) * px_per_sec
        frame = extract_frame(video_path, mid, min(MEDIUM_FRAME_WIDTH,
                                                   seg_width - 2 * FRAME_PAD), ffmpeg_exe)
        if frame:
            seg_frames.append(frame)

    gap_mids = []
    for seg, next_seg in zip(segs_true, segs_true[1:]):
        if next_seg['startTime'] > seg['endTime']:
            gap_mids.append((seg['endTime'] + next_seg['startTime']) / 2)

    gap_frames = []
    for idx, gap_mid in enumerate(gap_mids):
        mid = max(MID_CLAMP_IN_SECS, min(gap_mid, duration - MID_CLAMP_IN_SECS))
        cx = LEFT_MARGIN + mid * px_per_sec
        frame_width = MEDIUM_FRAME_WIDTH
        if idx > 0:
            frame_width = min(frame_width,
                              (gap_mid - gap_mids[idx - 1]) * px_per_sec - 2 * FRAME_PAD)
        if idx < len(gap_mids) - 1:
            frame_width = min(frame_width,
                              (gap_mids[idx + 1] - gap_mid) * px_per_sec - 2 * FRAME_PAD)
        frame = extract_frame(video_path, mid,
                              min(frame_width, 2 * cx, 2 * (SVG_WIDTH - cx)), ffmpeg_exe)
        if frame:
            gap_frames.append(frame)

    svg = build_svg(args.video, args.key, model, duration, segs_true, segs_pred,
                    seg_frames, gap_frames)

    out_path = Path(args.out) if args.out else OUT_DIR / f'{args.video}_{args.key}.svg'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(svg)
    print(f'Written {out_path} ({len(segs_true)} true / {len(segs_pred)} predicted segments, '
          f'{len(seg_frames)} segment / {len(gap_frames)} gap frames, '
          f'duration {int(duration)}s)')


if __name__ == '__main__':
    main()

from pathlib import Path
import json
import re
import sys

def print_dict(dic):
    print(json.dumps(dic, indent=2))

def load_segments(filename, dir):
    ret = []
    filepath = Path(dir) / f'{filename}.json'
    try:
        ret = json.loads(filepath.read_text())
    except json.decoder.JSONDecodeError as e:
        print(f'ERROR: {filepath} ({e})')
        sys.exit(1)        
    return ret

def get_hms_from_secs(time_in_seconds):
    ret = []
    parts = [60, 60, 24]
    res = time_in_seconds
    for p in parts:
        ret.append(res % p)
        res = res // p
    return f'{int(ret[2]):02d}:{int(ret[1]):02d}:{int(ret[0]):02d}'

def convert_segments_to_seconds(segments):
    ret = json.loads(json.dumps(segments))
    if isinstance(segments, dict):
        ret = ret.get('programs', [])
    if not(isinstance(ret, list)):
        return []
    for i, s in enumerate(ret):
        s['valid'] = 1
        for p in ['startTime', 'endTime']:
            time_code = s.get(p, None)
            if time_code is None:
                # cope with models that insist on using 'start_time'
                time_code = s.get(p.replace('Time', '_time'), None)
            if time_code is None:
                # support for start/end
                time_code = s.get(p.replace('Time', ''), None)
            matches = None
            if time_code is not None:
                time_code = str(time_code)
                matches = re.match(r'^[\d.]+$', time_code)
                if matches:
                    s[p] = float(time_code)
                else:                    
                    matches = re.match(r'^(\d?\d\d):(\d\d)$', time_code)
                    if matches:
                        time_code = '00:' + time_code
                    matches = re.match(r'^(\d\d):(\d?\d\d):(\d\d)$', time_code)
                    if matches:
                        s[p] = (int(matches.group(1)) * 60 + int(matches.group(2))) * 60 + int(matches.group(3))
                        # print(time_code, s[p])
            if not matches:
                print(f'WARNING: wrong time format in segment {i+1}.{p}, {time_code}')
                s['valid'] = 0
    
    return ret

def convert_segments_from_programs_to_separators(segments):
    ret = []
    last_end = 0
    for s in segments:
        ret.append({
            'startTime': last_end,
            'endTime': s['startTime'],
            'valid': 1
        })
        last_end = s['endTime']
    return ret

def get_segs_intersection(seg1, seg2):
    startTime = max(seg1['startTime'], seg2['startTime'])
    endTime = min(seg1['endTime'], seg2['endTime'])
    return [startTime, endTime]

def compare_segments(segments_true, segments_predict, is_separator=False):
    '''
    This method is based on proportionality of coverage of matching segment.
    It penalises distance to true boundaries proportionally to the length of the true segment
    But it has a few flaws:
    1. If only one perfect prediction covering 50% of a 10-segs video, score is 50%
    2. If buggy predictor repeats the same first match, it can get 100%
    It has advantages as well:
    1. deals well with two predictions covering different parts of the same segment
    2. penalise too early or too late matches consistently and proportionally
    '''
    segments_true = convert_segments_to_seconds(segments_true)
    if is_separator:
        segments_true = convert_segments_from_programs_to_separators(segments_true)
    segments_predict = convert_segments_to_seconds(segments_predict)

    ret = get_default_comparison(segments_true)

    # 1. score all combinations of segments
    for sp in segments_predict:
        # best_true_segment = None
        sp['score'] = -1e6
        for st in segments_true:
            score = score_segment_pair(st, sp)
            if score > sp['score']:
                sp['score'] = score
                sp['true'] = st
                # best_true_segment = st
        length = sp['true']['endTime'] - sp['true']['startTime']
        sp['score'] = max(0, sp['score'])
        ret['score'] += sp['score'] * length

    ret['score'] /= sum([st['endTime'] - st['startTime'] for st in segments_true])
    ret['matched'] = len({sp['true']['startTime'] for sp in segments_predict})

    extra = len(segments_predict) - len(segments_true)
    if extra > 0:
        # necessary? extra predictions are already penalised with above method
        ret['score'] = ret['score'] / len(segments_predict) * len(segments_true)
        ret['extra'] = extra

    if segments_predict:
        beyond = segments_predict[-1]['endTime'] / segments_true[-1]['endTime']
        if beyond > 1:
            ret['score'] /= beyond
            ret['beyond'] = beyond
            ret['duration_diff_ratio'] = beyond

    # 2. generate difference report
    diff = []
    for st in segments_true:
        st_str = f'{get_hms_from_secs(st["startTime"])} - {get_hms_from_secs(st["endTime"])}'
        score = ''
        for sp in segments_predict:
            if sp['true'] == st:
                diff.append(f'{int(sp["score"]*100):>3d}% {get_hms_from_secs(sp["startTime"])} - {get_hms_from_secs(sp["endTime"])}  /  {st_str}')
                st_str = ''
        if st_str:
            diff.append(f'{" "*24}  /  {st_str}')
    ret['diff'] = '\n'.join(diff)

    return ret

def score_segment_pair(segment_true, segment_predict):
    ret = 0.5
    length = segment_true['endTime'] - segment_true['startTime']
    ret = 1 - abs(segment_true['startTime'] - segment_predict['startTime']) / length - abs(segment_true['endTime'] - segment_predict['endTime']) / length
    # ret = max(0, ret)
    return ret

def get_default_comparison(segments_true):
    return {
        "score": 0.0,
        "summary": "invalid input format",
        "valid": True,
        "beyond": 1,
        "matched": 0,
        "expected": len(segments_true),
        "duration_diff_ratio": 1,
        "extra": 0
    }

def compare_segments_old(segments_true, segments_predict, is_separator=False):
    '''
    Scoring based on number of prog covered by at least one prediction.
    Tends to be too generous in individual scoring for partial overlap.
    '''
    segments_true = convert_segments_to_seconds(segments_true)
    if is_separator:
        segments_true = convert_segments_from_programs_to_separators(segments_true)
    segments_predict = convert_segments_to_seconds(segments_predict)

    ret = get_default_comparison(segments_true)

    if not(isinstance(segments_predict, list)):
        ret["valid"] = False
        return ret

    score = 0.0
    matched_count = 0

    true_matched = []

    # find the best match for each true seg
    # mtach largest segments first
    segments_true_longest_first = sorted(segments_true, key=lambda s: s['endTime'] - s['startTime'], reverse=True)
    for seg_true in segments_true_longest_first:
        largest_overlap = 0
        best_pred = None

        # select the predicted segment with largest overlap over the true seg
        for seg_pred in segments_predict:
            already_matched = seg_pred.get('true', None)
            if already_matched: continue   
            if seg_pred['valid'] == 0: continue
                
            if is_separator:
                # reject prediction if overlaps surrounding programs by X secs.
                SEPARATOR_TOLERANCE_IN_SECS = 4
                if (seg_pred['startTime'] < (seg_true['startTime'] - SEPARATOR_TOLERANCE_IN_SECS) or
                    seg_pred['endTime'] > (seg_true['endTime'] + SEPARATOR_TOLERANCE_IN_SECS)
                    ):
                    continue
            
            inter = get_segs_intersection(seg_true, seg_pred)
            overlap = inter[1] - inter[0]
            if overlap > largest_overlap:
                largest_overlap = overlap
                best_pred = seg_pred

        if best_pred:
            best_pred['true'] = seg_true
            true_matched.append(seg_true)
            if is_separator:
                # score is intersection / union
                if 0:
                    union = [
                        min(seg_true['startTime'], best_pred['startTime']),
                        max(seg_true['endTime'], best_pred['endTime'])
                    ]
                    pred_score = largest_overlap / (union[1] - union[0])
                else:
                    # rationale: prediction need to capture title before next prog
                    # not really an issue if it captures a bit of separator after last
                    BEFORE_NEXT_PROG_IN_SECS = 5
                    before_next_prog = {
                        'startTime': max(seg_true['startTime'], seg_true['endTime'] - BEFORE_NEXT_PROG_IN_SECS),
                        'endTime': seg_true['endTime']
                    }
                    inter = get_segs_intersection(before_next_prog, best_pred)
                    overlap = inter[1] - inter[0]
                    # TODO: But pred going a bit over programs will also get 100%...
                    pred_score = overlap / (before_next_prog['endTime'] - before_next_prog['startTime'])
            else:
                # score is the proportion of true segmment covered by predicted
                pred_score = largest_overlap / (seg_true['endTime'] - seg_true['startTime'])

            best_pred['score'] = int(pred_score * 100) / 100
            score += pred_score
            matched_count += 1
            
        # score = 0 otherwise

    if score:
        # penalty for any missing segment or excess prediction
        # Flaw = missing a tiny prog has same penalty as a major one..
        ret['score'] = score / max(len(segments_true), len(segments_predict))            
    else:
        ret['score'] = score

    ret['score'] = int(ret['score'] * 100) / 100

    # summary
    ret['summary'] = f'{matched_count} / {len(segments_true)} matched'
    excess = len(segments_predict) - len(segments_true)
    if excess > 0:
        ret['summary'] += f' ; {excess} extra predictions'
    else:
        excess = 0
    
    ret['predicted'] = len(segments_predict)
    ret['matched'] = matched_count
    ret['extra'] = excess
    # Strong indicator of hallucinated times
    ret['duration_diff_ratio'] = segments_predict[-1]['endTime'] / segments_true[-1]['endTime']
    if ret['duration_diff_ratio'] > 1.5:
        ret['summary'] += f' ; hallucinated end {ret["duration_diff_ratio"]:.2}'
        ret['score'] /= ret['duration_diff_ratio']

    # diff: display all (matched and unmatched) segments
    diff_lines = []
    last_pred_start = 0
    for pred in segments_predict:
        # display all unmatched true segment before this and previous
        if pred['valid']:
            for t in segments_true:
                if t in true_matched: continue
                if t['startTime'] >= last_pred_start and t['startTime'] < pred['startTime']:
                    diff_lines.append(f'                            /  {get_hms_from_secs(t["startTime"])} - {get_hms_from_secs(t["endTime"])}')

        pred_readable = f'{int(pred.get("score", 0) * 100):3d}%  '
        if pred['valid']:
            pred_readable += f'{get_hms_from_secs(pred["startTime"])} - {get_hms_from_secs(pred["endTime"])} '
        else:
            pred_readable += f'invalid format '
        if pred.get('true', None):
            pred_readable += f'  /  {get_hms_from_secs(pred["true"]["startTime"])} - {get_hms_from_secs(pred["true"]["endTime"])}'
        if pred['valid']:
            last_pred_start = pred["startTime"]
        diff_lines.append(pred_readable)

    ret['diff'] = '\n'.join(diff_lines)

    return ret

def validate_segments(segments):
    '''Returns an array of validation errors'''
    ret = []
    segs_in_seconds = convert_segments_to_seconds(segments)
    lastEnd = 0
    for idx, s in enumerate(segs_in_seconds):
        error = ''
        if s['startTime'] > s['endTime']:
            error = f'start > end'
        if lastEnd > s['startTime']:
            error = f'end of last segment > start of this segment'
        if error:
            ret.append({
                'index': idx,
                'error': error,
                'segment': segments[idx]
            })
        lastEnd = s['endTime']
    return ret


if __name__ == '__main__':
    INPUT_FILE_NAME = 'aobbu34200001'
    # INPUT_FILE_NAME = 'DVC43313'

    segments_true = load_segments(INPUT_FILE_NAME, 'segments_true')
    segments_predict = load_segments(INPUT_FILE_NAME, 'segments_predict')

    # res = compare_segments(segments_true, segments_predict, False)
    res = compare_segments(segments_true, segments_predict)
    print(print_dict(res))


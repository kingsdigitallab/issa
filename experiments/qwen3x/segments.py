from pathlib import Path
import json
import re

def print_dict(dic):
    print(json.dumps(dic, indent=2))

def load_segments(filename, dir):
    ret = Path(dir) / f'{filename}.json'
    ret = json.loads(ret.read_text())
    return ret

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
            if not time_code:
                # cope with models that insist on using 'start_time'
                time_code = s.get(p.replace('Time', '_time'), None)
            if not time_code:
                # support for start/end
                time_code = s.get(p.replace('Time', ''), None)
            matches = None
            if time_code:
                time_code = str(time_code)
                matches = re.match(r'^[\d.]+$', time_code)
                if matches:
                    s[p] = float(time_code)
                else:                    
                    matches = re.match(r'^(\d\d):(\d\d)$', time_code)
                    if matches:
                        time_code = '00:' + time_code
                    matches = re.match(r'^(\d\d):(\d\d):(\d\d)$', time_code)
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
    segments_true = convert_segments_to_seconds(segments_true)
    if is_separator:
        segments_true = convert_segments_from_programs_to_separators(segments_true)
    segments_predict = convert_segments_to_seconds(segments_predict)

    ret = {
        "score": 0.0,
        "summary": "invalid input format",
        "diff": [] 
    }

    if not(isinstance(segments_predict, list)):
        return ret

    score = 0.0
    matched_count = 0

    # find the best match for each true seg
    for seg_true in segments_true:
        largest_overlap = 0
        best_pred = None

        # select the predicted segment with largest overlap over the true seg
        for seg_pred in segments_predict:
            match = seg_pred.get('true', None)
            if match: continue   
            if seg_pred['valid'] == 0: continue
                
            if is_separator:
                # predicted separator can't go over programs
                TOLERANCE = 3
                if (seg_pred['startTime'] < (seg_true['startTime'] - TOLERANCE) or
                    seg_pred['endTime'] > (seg_true['endTime'] + TOLERANCE)
                    ):
                    continue
            
            inter = get_segs_intersection(seg_true, seg_pred)
            overlap = inter[1] - inter[0]
            if overlap > largest_overlap:
                largest_overlap = overlap
                best_pred = seg_pred

        # score for that prediction is the ratio of the true seg covered by it
        # So 1.0 if covered fully (or over), 0.5 if only cover half
        if best_pred:
            best_pred['true'] = seg_true
            if is_separator:
                # score is intersection / union
                union = [
                    min(seg_true['startTime'], best_pred['startTime']),
                    max(seg_true['endTime'], best_pred['endTime'])
                ]
                pred_score = largest_overlap / (union[1] - union[0])
            else:
                pred_score = largest_overlap / (seg_true['endTime'] - seg_true['startTime'])
            best_pred['score'] = int(pred_score * 100) / 100
            print(best_pred)
            score += pred_score
            matched_count += 1
            
        # score = 0 otherwise

    if score:
        # penalty for any missing segment or excess prediction
        ret['score'] = score / max(len(segments_true), len(segments_predict))            
    else:
        ret['score'] = score

    ret['score'] = int(ret['score'] * 100) / 100

    # summary
    ret['summary'] = f'{matched_count} / {len(segments_true)} matched'
    excess = len(segments_predict) - len(segments_true)
    if excess > 0:
        ret['summary'] += f' ; {excess} extra predictions'

    # ret['missing'] = segments_predict

    return ret

if 0:
    INPUT_FILE_NAME = 'v1'

    segments_true = load_segments(INPUT_FILE_NAME, 'segments_true')
    segments_predict = load_segments(INPUT_FILE_NAME, 'segments_predict')

    res = compare_segments(segments_true, segments_predict)
    print(print_dict(res))

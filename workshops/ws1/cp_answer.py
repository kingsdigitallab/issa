'''
Copy vlm answer about a video into an aggregated json file.
So we can create more systematic perf stats based on variations of settings.
'''

from pathlib import Path
import json

SRC_PATH = 'sample11/234552207.32/video_answers.json'
DST_PATH = 'evals/video_answers.json'
QST_NAME = 'prg1'

dst_path = Path(DST_PATH)
dst_path.parent.mkdir(exist_ok=1)

content_in = json.loads(Path(SRC_PATH).read_text())
answer = content_in['data'][QST_NAME]
options = answer['options']

answer_key =  f"fps-{options['media_io_kwargs']['video']['fps']}-vctx-{int(options['mm_processor_kwargs']['size']['longest_edge']/1024/2048)}-re-{options['reasoning_effort']}-s-{options['seed']}"

content_out = {}
if dst_path.exists():
    content_out = json.loads(dst_path.read_text())

content_out[answer_key] = answer

dst_path.write_text(json.dumps(content_out, indent=2))

print(f'COPIED answer "{answer_key}" to {dst_path}')


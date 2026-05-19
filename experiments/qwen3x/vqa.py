from openai import OpenAI
import json
import csv
from datetime import datetime
import subprocess
from pathlib import Path
from segments import compare_segments, load_segments
import re

# VIDEO_FILENAME = 'DVC43998.mp4'
# VIDEO_FILENAME = 'S1964_2.mp4'

API_URL = "http://localhost:8000/v1"
MODELID = "Qwen/Qwen3.5-4B"
MODELID = "Qwen/Qwen3.5-2B"
MODELID = "cyankiwi/Qwen3.5-4B-AWQ-4bit"
# MODELID = "cyankiwi/Qwen3.5-9B-AWQ-4bit"
SEEDS = [42, 54]
SEED = SEEDS[0]
PROMPT = "Summarize the video content in one sentence."
PROMPT = '''This video contains one or more TV programs. 
Each program should be preceded by a special, full screen visual separator such as a large count down, a large clock, a black screen, color bars or a production card with title. The visual separators are not intended for public television, only for production team. A separator may last between a few seconds to a few minutes. They are distinct from title screens within a program.
Detect all programs in the video. 
Then returns only a json array with one item per program. 
Each item is a dictionary with `startTime` and `endTime` keys in 'HH:MM:SS' format.
No need to analyse or describe programs.
'''
CSV_FILE = 'evaluations.csv'
CSV_COLUMNS = ['experiment_time', 'duration_seconds', 'model_id', 'video', 'comparison_summary', 'comparison_score', 'vram_gb', 'seed', 'comments']
CSV_COMMENTS = 'no-reasoning'

VIDEO_FILENAMES = ['aobbu34200001', 'DVC43998', 'DVC43313', '90D2335_A']
# VIDEO_FILENAMES = ['DVC43998', 'DVC43313', '90D2335_A']
# True to run only the first experiment (first video, first model seed).
SINGLE_TEST = False

def parse_dirty_json(dirty_json):
    'Convert dirty json to a pythons structure. Handles different formattings.'
    ret = dirty_json
    if isinstance(dirty_json, str):
        json_blocks = re.sub(r'(?s)```json\b(.*)```', r'\1', dirty_json)
        clean_json = json_blocks.strip(' \n')
        if (clean_json.startswith('{') and clean_json.endswith('}')) or (clean_json.startswith('[') and clean_json.endswith(']')):
            try:
                ret = json.loads(clean_json)
            except json.decoder.JSONDecodeError:
                self._warn(f'Invalid JSON format: {ret}')
                pass
    return ret

def format_time(delta):
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"    

def print_dict(d):
    print('')
    print('```json')
    print(json.dumps(d, indent=2))
    print('```')
    print('')
    
def print_system_vram_usage():
    used, total = get_system_vram_used()
    print(f'* VRAM used: {used:.2f} GB out of {total:.1f} GB')
    
def get_system_vram_used():
    # Query GPU memory usage in MiB
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
        capture_output=True, text=True
    )
    
    # Parse the output (e.g., "1024, 8192")
    used_mib, total_mib = map(int, result.stdout.strip().split(", "))
        
    return [used_mib / 1024, total_mib / 1024]
    
    
def log_to_csv(experiment_time, duration_seconds, model_id, video, comparison_summary, comparison_score, vram_gb, seed):
    ret = Path(CSV_FILE)
    needs_header = not ret.exists()
    with open(CSV_FILE, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if needs_header:
            writer.writeheader()
        writer.writerow({
            'experiment_time': experiment_time,
            'duration_seconds': duration_seconds,
            'model_id': model_id,
            'video': video,
            'comparison_summary': comparison_summary,
            'comparison_score': comparison_score,
            'vram_gb': vram_gb,
            'seed': seed,
            'comments': CSV_COMMENTS
        })

    
def run_experiment(video_filename, seed=None):
        
    if seed is None:
        seed = SEED
    
    # Configured by environment variables
    client = OpenAI(
        api_key="whatever",
        base_url=API_URL    
    )
    
    video_filename_with_ext = video_filename + '.mp4'
    
    experiment_time = datetime.now().isoformat()
    vram_gb, vram_total = get_system_vram_used()
    
    print('---')
    print(f'* TIME = {experiment_time}')
    print(f'* VIDEO = {video_filename_with_ext}')
    print(f'* VRAM used: {vram_gb:.2f} GB out of {vram_total:.1f} GB')
    t0 = datetime.now()
    
    if 1:            
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "video_url",
                        "video_url": {
                            "url": f"file:///home/gnoel/src/prj/issa/experiments/qwen3x/videos/{video_filename_with_ext}"
                        }
                    },
                    {
                        "type": "text",
                        "text": PROMPT
                    }
                ]
            }
        ]
                    
        # When vLLM is launched with `--media-io-kwargs '{"video": {"num_frames": -1}}'`,
        # video frame sampling can be configured via `extra_body` (e.g., by setting `fps`).
        # This feature is currently supported only in vLLM.
        #
        # By default, `fps=2` and `do_sample_frames=True`.
        # With `do_sample_frames=True`, you can customize the `fps` value to set your desired video sampling rate.
        
        options = {
            'model': MODELID,
            'messages': messages,
            'max_tokens': 15*1024,
            'temperature': 0.6,
            'top_p': 0.95,
            'presence_penalty': 1.0,
            'seed': seed,
            'extra_body': {
                "top_k": 20,
                "mm_processor_kwargs": {"fps": 2, "do_sample_frames": True},
                "enable_thinking": False,            
            }
        }
    
        print('* REQUEST =')
        print_dict(options)
        
        res = client.chat.completions.create(**options)
        
        answer = None
        first_choice = res.choices[0]
        if first_choice:
            if first_choice.finish_reason == 'stop':
                answer = first_choice.message.content
                if not answer:
                    # qwen3.5 2b via vllm will respond in reasoning field
                    answer = first_choice.message.reasoning
        
        comparison = None
        if answer:
            print(f'\n* ANSWER = \n{answer}\n')
            
            # compare segments
            segments_true = load_segments(video_filename, 'segments_true')
            segments_predict = parse_dirty_json(answer)
            comparison = compare_segments(segments_true, segments_predict)
            
            print(f'\n* COMPARISON = ')
            print_dict(comparison)
        
    
    t1 = datetime.now()
    duration = t1 - t0
        
    print('* RESPONSE =')
    print_dict(json.loads(res.model_dump_json()))

    vram_gb, vram_total = get_system_vram_used()    
    print(f'* VRAM used: {vram_gb:.2f} GB out of {vram_total:.1f} GB')
    
    print(f'* TIME = {datetime.now().isoformat()}')
    
    if duration:
        print(f'* DURATION = {format_time(duration)}')
    
    comparison_summary = comparison.get('summary', '') if comparison else ''
    comparison_score = comparison.get('score', 0.0) if comparison else 0.0
    log_to_csv(experiment_time, duration.total_seconds(), MODELID, video_filename, comparison_summary, comparison_score, round(vram_gb, 2), seed)
    
    print('\n')
    print('-' * 3)
    print('\n')


for video_filename in VIDEO_FILENAMES:
    for seed in SEEDS:
        run_experiment(video_filename, seed)
        if SINGLE_TEST:
            break
    if SINGLE_TEST:
        break


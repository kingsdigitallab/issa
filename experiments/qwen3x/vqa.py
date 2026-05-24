from openai import OpenAI
import json
from datetime import datetime
from pathlib import Path
from segments import compare_segments, load_segments
from utils import parse_dirty_json, format_time, print_dict, print_system_vram_usage, get_system_vram_used, get_first_gpu_name, log_to_csv, get_first_model_name
import re

ENGINE_API_URL = "http://localhost:8000/v1"
ENGINE_TIMEOUT = 20*60.0 # 
ENGINE_CLIENT = OpenAI(
    api_key="whatever",
    base_url=ENGINE_API_URL,
    timeout=ENGINE_TIMEOUT
)

MODELID = get_first_model_name(ENGINE_CLIENT)

# Qwen3.5
# MODELID = "Qwen/Qwen3.5-2B"
# MODELID = "Qwen/Qwen3.5-4B"
# MODELID = 'Qwen/Qwen3.5-9B'
# MODELID = "cyankiwi/Qwen3.5-4B-AWQ-4bit"

# See Qwen3.5 Model Card on Huggingface
# https://huggingface.co/Qwen/Qwen3.5-27B

TEMP = 1.0    # 0.7 - 1.0 (2B -> 27B); 2B best with 0.6
TOP_P = 0.95  # 0.8 to 0.95 for Qwen3.5 2-27B
TOP_K = 20    # 

# MODELID = "OpenGVLab/InternVL3-14B"

# for Qwen3-VL
if 'Qwen3-VL' in MODELID:
    # MODELID = "Qwen/Qwen3-VL-32B_Instruct"
    TEMP = 0.7
    TOP_P = 0.8
    TOP_K = 20

# False for benchmarking on multiple video with 2 seeds
# True to test with one video and 2-4 seeds (to tune hyperparams)
IS_TUNING = False
# IS_TUNING = True
    
if IS_TUNING:
    SEEDS = [106, 23, 86, 12] # ONLY for tuning params
    SEEDS = [12, 23]
else:
    SEEDS = [42, 54] # For multi-video benchmarking
        
PROMPT = "Summarize the video content in one sentence."
PROMPT = '''This video contains one or more TV programs. 
Each program should be preceded by a special, full screen visual separator such as a large count down, a large clock, a black screen, color bars or a production card with title. The visual separators are not intended for public television, only for production team. A separator may last between a few seconds to a few minutes. They are distinct from title screens within a program.
Detect all programs in the video. 
Then returns only a json array with one item per program. 
Each item is a dictionary with `startTime` and `endTime` keys in 'HH:MM:SS' format.
No need to analyse or describe programs.
'''
PROMPT = '''This video contains one or more TV programs. 
Each program is be preceded by a special, full screen visual separator.
A visual separator looks like a large count down, a large clock, a black screen, color bars or a production card with title. 
The visual separators are not intended for public television, only for production team. 
A separator may last between a few seconds to a few minutes. They are very distinct from title screens within a program.
Detect all programs in the video.
Then returns only a json array program timecodes.
Follow exactly this format:

[
    {
        "start": "00:01:14",
        "end": "00:06:23"
    },
    {
        "start": "00:10:45",
        "end": "00:24:32"
    }
]
'''

# Disable model reasoning => much faster processing, but possibly less accurate
DONT_THINK = True
# DONT_THINK = False

## That prompting technique doesn't seem to make any difference on Qwen3.5:
# if not DONT_THINK:
#     # not sure if models will follow that... 
#     PROMPT += '\nThink step by step, but keep your reasoning brief. Then give the final answer. Do not explain anything beyond what is necessary.'

VIDEO_FILENAMES = ['aobbu34200001', 'DVC43998', 'DVC43313', '90D2335_A']

if IS_TUNING:
    VIDEO_FILENAMES = ['DVC43998'] # smallest video; faster for fine-tuning
    # VIDEO_FILENAMES = ['90D2335_A'] # Qwen3.5 tends to overthink it

# True to run only the first experiment (first video, first model seed).
SINGLE_TEST = False
# SINGLE_TEST = True
ENGINE = 'sglang'
ENGINE_ATTENTION_BACKEND = 'fa3'
GPU = get_first_gpu_name()

# WRITE_TO_CSV = False
WRITE_TO_CSV = not IS_TUNING

CSV_COMMENTS = f't={TEMP} top_p={TOP_P} {ENGINE_ATTENTION_BACKEND} {ENGINE} {GPU}'

if DONT_THINK:
    CSV_COMMENTS += ' no-reasoning'

# will be populated by each run and displayed at the end of the series
stats = {
    'runs': [],
    'options': {},
}

   
   
def run_experiment(video_filename, seed):
            
    client = ENGINE_CLIENT
    
    video_filename_with_ext = video_filename + '.mp4'
    
    experiment_time = datetime.now().isoformat()
    vram_gb, vram_total = get_system_vram_used()
    
    print('---')
    print(f'* TIME = {experiment_time}')
    print(f'* VIDEO = {video_filename_with_ext}')
    print(f'* VRAM used: {vram_gb:.2f} GB out of {vram_total:.1f} GB')
    t0 = datetime.now()
    
    if 1:    
        video_path = Path.cwd().absolute() / 'videos' / video_filename_with_ext        
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "video_url",
                        "video_url": {
                            "url": f"file://{video_path}"
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
            'max_tokens': 15*1024, # maximum OUTPUT tokens (add ~15k for video+prompt input context)
            'temperature': TEMP,
            'top_p': TOP_P, 
            'presence_penalty': 1.5, # low for better json output; but will make thinking loop/repeat; Qwen3.5 recommends 1.5
            # 'frequency_penalty': 0.9, # same here?
            'seed': seed,
#             'response_format': {
#                 'type': 'json_object'
#             },
            'extra_body': {
                "top_k": TOP_K,
                "mm_processor_kwargs": {"fps": 2, "do_sample_frames": True}, # see Qwen3.5 card
            }
        }

        if DONT_THINK:
            # not sure which engine respect this one
            options['extra_body']['enable_thinking'] = False
            # sglang will respect that
            options['extra_body']['chat_template_kwargs'] = {"enable_thinking": False}
            
        stats['options'] = options

        print('* REQUEST =')
        print_dict(options)
        
        res = client.chat.completions.create(**options)

        print('* RESPONSE =')
        print_dict(json.loads(res.model_dump_json()))
                
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
        
    vram_gb, vram_total = get_system_vram_used()    
    print(f'* VRAM used: {vram_gb:.2f} GB out of {vram_total:.1f} GB')
    
    print(f'* TIME = {datetime.now().isoformat()}')
    
    if duration:
        print(f'* DURATION = {format_time(duration)}')
    
    comparison_summary = comparison.get('summary', '') if comparison else ''
    comparison_score = comparison.get('score', 0.0) if comparison else 0.0
    if WRITE_TO_CSV:
        log_to_csv(experiment_time, duration.total_seconds(), MODELID, video_filename, comparison_summary, comparison_score, round(vram_gb, 2), seed, CSV_COMMENTS)
    
    print('\n')
    print('-' * 3)
    print('\n')

    stats['runs'].append({
        'video': video_filename,
        'score': comparison_score,
        'seed': seed,
        'time': duration.total_seconds(),
    })
    
if __name__ == '__main__':
    for video_filename in VIDEO_FILENAMES:
        for seed in SEEDS:
            run_experiment(video_filename, seed)
            if SINGLE_TEST:
                break
        if SINGLE_TEST:
            break

print('---')  

print('SUMMARY')  
            
print_dict(stats)

print(CSV_COMMENTS)

avg_score = sum([s['score'] for s in stats['runs']]) / len(stats['runs'])

print(f'Avg score: {avg_score:0.2f} over {len(stats['runs'])} runs')

print()


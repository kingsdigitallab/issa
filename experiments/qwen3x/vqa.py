from openai import OpenAI
import json
from datetime import datetime
import subprocess

# VIDEO_FILENAME = 'DVC43998.mp4'
VIDEO_FILENAME = 'S1964_2.mp4'

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
    
    # Convert MiB to GiB
#     used_gib = used_mib / 1024
#     total_gib = total_mib / 1024
    
    return [used_mib / 1024, total_mib / 1024]
    
    # print(f"VRAM used: {used_gib:.2f} GB out of {total_gib:.1f} GB")

    
# Configured by environment variables
client = OpenAI(
    api_key="whatever",
    base_url="http://localhost:8000/v1"    
)

print('---')
print(f'* TIME = {datetime.now().isoformat()}')
print(f'* VIDEO = {VIDEO_FILENAME}')
print_system_vram_usage()
t0 = datetime.now()


if 0:

    messages = [
        {"role": "user", "content": "Just say Hello world in reverse. Do not output reasoning. Only output the final answer."},
    ]
    
    print('PROMPT =')
    print(json.dumps(messages, indent=2))
    
    res = client.chat.completions.create(
        model="Qwen/Qwen3.5-4B",
        messages=messages,
        max_tokens=32768,
        temperature=1.0,
        top_p=1.0,
        presence_penalty=2.0,
        # reasoning_effort="none",
        extra_body={
            "top_k": 20,
            "enable_thinking": False
        }, 
    )
    # print("Chat response:", chat_response)

if 1:
    '''
    vllm serve Qwen/Qwen3.5-2B --port 8000 --tensor-parallel-size 1 --max-model-len 262144 --reasoning-parser qwen3 --allowed-local-media-path /home/gnoel/src/prj/issa/experiments/ --media-io-kwargs '{"video": {"num_frames": -1}}'
    '''
    
    PROMPT = "Summarize the video content in one sentence."
    PROMPT = '''This video contains one or more TV programs. 
Each program is normally preceded by a visual separator such as a large count down, a clock, a black screen, color bars or a production card with title.
Detect all programs in the video. Only return the starting and ending timecode for each program (e.g. 00:13, 01:45). One line per program.
No need to analyse or describe programs.
'''
        
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "video_url",
                    "video_url": {
                        "url": f"file:///home/gnoel/src/prj/issa/experiments/qwen3x/{VIDEO_FILENAME}"
                    }
                },
                {
                    "type": "text",
                    "text": PROMPT
                }
            ]
        }
    ]
    
#     print('PROMPT =')
#     print(json.dumps(messages, indent=2))
        
    # When vLLM is launched with `--media-io-kwargs '{"video": {"num_frames": -1}}'`,
    # video frame sampling can be configured via `extra_body` (e.g., by setting `fps`).
    # This feature is currently supported only in vLLM.
    #
    # By default, `fps=2` and `do_sample_frames=True`.
    # With `do_sample_frames=True`, you can customize the `fps` value to set your desired video sampling rate.
    
    options = {
        'model': "Qwen/Qwen3.5-4B",
        'messages': messages,
        'max_tokens': 5*1024,
        'temperature': 0.6,
        'top_p': 0.95,
        'presence_penalty': 1.0,
        'extra_body': {
            "top_k": 20,
            "mm_processor_kwargs": {"fps": 2, "do_sample_frames": True},
            "enable_thinking": False,            
        }
    }

    print('* REQUEST =')
    print_dict(options)
    
    res = client.chat.completions.create(**options)
#         model="Qwen/Qwen3.5-2B",
#         messages=messages,
#         max_tokens=5*1024,
#         temperature=0.7,
#         top_p=0.8,
#         presence_penalty=1.5,
#         extra_body={
#             "top_k": 20,
#             "mm_processor_kwargs": {"fps": 2, "do_sample_frames": True},
#         }, 
#     )

t1 = datetime.now()
duration = t1 - t0
    
print('* RESPONSE =')
print_dict(json.loads(res.model_dump_json()))

print_system_vram_usage()

print(f'* TIME = {datetime.now().isoformat()}')

if duration:
    print(f'* DURATION = {format_time(duration)}')

print('\n')
print('-' * 3)
print('\n')

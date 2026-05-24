from openai import OpenAI
import json
import csv
from datetime import datetime
import subprocess
from pathlib import Path
# from segments import compare_segments, load_segments
import re

CSV_FILE = 'evaluations.csv'
CSV_COLUMNS = ['experiment_time', 'duration_seconds', 'model_id', 'video', 'comparison_summary', 'comparison_score', 'vram_gb', 'seed', 'comments']


def parse_dirty_json(dirty_json):
    'Convert dirty json to a pythons structure. Handles different formattings.'
    ret = dirty_json
    if isinstance(ret, str):
        json_blocks = re.sub(r'(?s)^.*?```json\b(.*)```.*?$', r'\1', ret)
        clean_json = json_blocks.strip(' \n')
        if (clean_json.startswith('{') and clean_json.endswith('}')) or (clean_json.startswith('[') and clean_json.endswith(']')):
            try:
                ret = json.loads(clean_json)
            except json.decoder.JSONDecodeError:
                print(f'Invalid JSON format: {ret}')
    
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
    
def get_first_model_name(openai_client):
    # Returns the name (ID) of the first available model from the OpenAI API.
    
    # Retrieve the list of models
    models = openai_client.models.list()
    
    # Check if there are any models available
    if models.data:
        return models.data[0].id
    else:
        return None
            
def get_first_gpu_name():
    # Returns 1st GPU name, e.g. "a100_80g""
    result = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'], 
                          capture_output=True, text=True)
    # 'NVIDIA A100 80GB PCIe''
    ret = result.stdout.strip()
    ret = re.sub(r'NVIDIA|PCIe', '', ret)
    ret = ret.strip().replace(' ', '_').lower()
    return ret
    
def log_to_csv(experiment_time, duration_seconds, model_id, video, comparison_summary, comparison_score, vram_gb, seed, comments):
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
            'comments': comments
        })

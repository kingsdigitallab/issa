from pathlib import Path 
import json

def write_json(data, path):
    content = json.dumps(data, indent=2)
    Path(path).write_text(content)
    print(f'WRITTEN {path} ({int(len(content)/1024/1024)} MB)')

def to_bool(v):
    ret = False

    if v:
        false_strings = ['0', 'false', 'no']
        if v not in false_strings:
            ret = True

    return ret
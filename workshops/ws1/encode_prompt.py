'''
Convert a multi line string into a format 
that can be added to a params.json file 
in Framesense
'''

import json 

PROMPT = """
```json
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
```
"""

lines = PROMPT.split('\n')

print(json.dumps(lines, indent=2))


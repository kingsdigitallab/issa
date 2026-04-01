import json 

# This script generates a 'clips' entry array 
# to be inserted in a framesense annotation file.

# time codes of a black screen separating two programmes in a video.
black_screens = '''
00:00
01:47
03:33
04:56
06:56
08:52
10:36
12:01
13:23
14:50
16:10
17:42
19:11
21:01
22:53
24:36
26:06
27:40
29:17
30:32
32:05
33:30
34:48
'''

ret = []

i = 0
last_time_code = None
for time_code in black_screens.split('\n'):
    time_code = time_code.strip()
    if not time_code:
        continue
    if last_time_code is None:
        last_time_code = time_code
        continue
    i += 1
    ret.append({
      "sequenceNumber": f'{i}',
      "startTime": f'00:{last_time_code}',
      "endTime": f'00:{time_code}',
      "srt": [
      ],
      "description": ""
    })
    last_time_code = time_code

print(json.dumps(ret, indent=2))


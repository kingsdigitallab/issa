TEMPLATES = {
    "prog1": {
        "text": '''This video contains one or more TV programs. 
Each program should be preceded by a special, full screen visual separator such as a large count down, a large clock, a black screen, color bars or a production card with title. The visual separators are not intended for public television, only for production team. A separator may last between a few seconds to a few minutes. They are distinct from title screens within a program.
Detect all programs in the video. 
Then returns only a json array with one item per program. 
Each item is a dictionary with `startTime` and `endTime` keys in 'HH:MM:SS' format.
No need to analyse or describe programs.
        ''',
        "find_separators": 0
    },
    "prog2": {
        "desc": "exact new prompt used with 46% score on Qwen3.5-2B",
        "text": '''This video contains one or more TV programs. 
Each program should be preceded by a special, full screen visual separator.
A visual separator looks like a large count down, a large clock, a black screen, color bars or a production card with title. 
The visual separators are not intended for public television, only for production team. 
A separator may last between a few seconds to a few minutes. They are very distinct from title screens within a program.
Detect all programs in the video.
Then returns only a json array with the time each detected progream starts and ends.
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
        ''',
        "find_separators": 0
    },
    "prog3": {
        "text": '''This video contains one or more TV programs. 
Each program is preceded by a special, full screen visual separator.
A visual separator usually looks like a large count down, a large clock, a black screen, color bars or a production card with title. 
The visual separators are not meant for public audience, only for production team. 
A separator may last between a few seconds to a few minutes. They are very distinct from title screens within a program.
Detect all programs in the video.
Then returns a JSON with an array of program timecodes. Timecode format is 'HH:MM:SS'.
The structure of your reponse must follow this example:
    
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
        ''',
        "find_separators": 0
    },
    "prog3{}": {
        "text": '''This video contains one or more TV programs. 
Each program is be preceded by a special, full screen visual separator.
A visual separator looks like a large count down, a large clock, a black screen, color bars or a production card with title. 
The visual separators are not intended for public television, only for production team. 
A separator may last between a few seconds to a few minutes. They are very distinct from title screens within a program.
Detect all programs in the video.
Then return only a JSON response of all programs in the video, in exactly the following structure (timecode format is 'HH:MM:SS')

```json
{
    "reasoning": "< your brief analysis of content and reasoning about program separation (max 1000 words) >",
    "programs": [
        {
            "start": "00:01:14",
            "end": "00:06:23"
        },
        {
            "start": "00:10:45",
            "end": "00:24:32"
        }
    ]
}
````
        ''',
        "find_separators": 0
    },  
    "sep0": {
        "desc": "exact prompt used by experiments/qwen3-vl in Nov 2025",
        "text": '''The video is a broadcast television recording from Northern Ireland. 
It contains one or more programmes visually preceded by a clear separator screen.
A separator screen has the following properties:
* usually just a silent image without movement or a large count down
* often contains the title or the producer of the upcoming programme
* often looks like a large clock or countdown, but not always
* it can last from a few seconds to a couple of minutes
* it is never part of the programme itself and not meant for public viewing
* its visual style is normally very different from the upcoming programme
* it is never an advertisement

Usually all separator screens in a video look very similar.

Please only mention separators before a new programme, not those within programmes.

Return a valid JSON Array with a list of all the times a separator appears.

Each entry should have those keys:
* start_time
* end_time
* title: all the text written on the separator screen
* year: if the year is visible on screen
* producer: if the channel name or producer is visible on screen
* visual: maximum three words describing what the separator screen looks like
        ''',
        "find_separators": 1
    },
    "sep1": {
        "text": '''This video contains one or more TV programs. 
Each program should be preceded by a special, full screen visual separator.
A visual separator looks like a large count down, a large clock, a black screen, color bars or a production card with title. 
The visual separators are not intended for public television, only for production team. 
A separator may last between a few seconds to a few minutes. They are very distinct from title screens within a program.
Detect all programs and separators in the video.
Then returns a JSON with an array of separators timecodes. Timecode format is 'HH:MM:SS'.
Your reponse must follow exactly this structure:
    
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
        ''',
        "find_separators": 1
    },
    "sep2": {
        "desc": "example from Brave AI",
        "text": '''You are an expert video analysis AI. Your task is to identify program separators in the provided video. 

A "program separator" is defined as a distinct visual break between content, such as:
- A fade to black or white screen lasting more than 2 seconds.
- A static title card or end slate.
- A hard cut to a black screen.

Tasks:
1. Scan the video and identify all timestamps where a separator occurs.
2. For each separator, provide the start and end timestamps in "HH:MM:SS" format.
3. Describe the type of separator (e.g., "fade to black," "title card").
4. Output the results in JSON format with keys "start_time", "end_time", and "description".

Do not include transitions within the same program (e.g., scene changes). Only identify breaks between distinct programs or segments.
''',
        "find_separators": 1,
    }
}

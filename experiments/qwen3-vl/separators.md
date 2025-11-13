Try a variety of models to detect seprators, preferably:
* outer ones only
* with low VRAM
* reliably

Experiments

1. 4B on 10mins gets all the seperators right and right metadata; but also inner seps
    1. (same with different seed find three then loops.)
    2. (4B killed (OOM?) on full video (35m).)
3. 4b perfect result on 10m video with better prompt
4. 4b perfect results on a different 16m video

---

1.

* Time: 2025-11-08T13:26:47.210140
* Video: v-10.mp4
* Model: Qwen/Qwen3-VL-4B-Instruct
* Device: NVIDIA GeForce RTX 4090
* VRAM used: 8.65 GB

PROMPT:

The video is a broadcast television recording from Northern Ireland. 
It contains one or more programmes visually preceded by a clear separator screen.
A separator screen is usually just a silent image without movement.
It can last from a few seconds to a couple of minutes. 
It often contains a title of the upcoming programme.
Please only mention separators before a new programme, not those within programmes.

Return a valid JSON Array with a list of all the times a separator appears.

Each entry should have those keys:
* start_time
* end_time
* title: all the text written on the separator screen
* year: if the year is visible on screen
* producer: if the channel name or producer is visible on screen


ANSWER:

```json
[
    {
        "start_time": "0:06",
        "end_time": "0:10",
        "title": "UTV LIVE",
        "producer": "UTV",
        "year": "2017"
    },
    {
        "start_time": "2:33",
        "end_time": "2:35",
        "title": "UTV LIVE",
        "producer": "UTV",
        "year": "2017"
    },
    {
        "start_time": "4:30",
        "end_time": "4:32",
        "title": "UTV WEATHER",
        "producer": "UTV",
        "year": "2017"
    },
    {
        "start_time": "4:42",
        "end_time": "4:44",
        "title": "UTV LIVE",
        "producer": "UTV",
        "year": "2017"
    }
]
```


* VRAM used: 13.17 GB

1 min 8s

---

2.

Loading checkpoint shards: 100%|██████████████████████████████████████████████████████| 2/2 [00:05<00:00,  2.67s/it]

* Time: 2025-11-08T13:58:00.660850
* Video: v-10.mp4
* Model: Qwen/Qwen3-VL-4B-Instruct
* Device: NVIDIA GeForce RTX 4090
* VRAM used: 8.65 GB

PROMPT:

The video is a broadcast television recording from Northern Ireland. 
It contains one or more programmes visually preceded by a clear separator screen.
A separator screen is usually just a silent image without movement that is not part of the programme and never shown to the viewers.
It can last from a few seconds to a couple of minutes. 
It often contains a title of the upcoming programme.
It's visual style is normally very different from the following programme.
Please only mention separators before a new programme, not those within programmes.

Return a valid JSON Array with a list of all the times a separator appears.

Each entry should have those keys:
* start_time
* end_time
* title: all the text written on the separator screen
* year: if the year is visible on screen
* producer: if the channel name or producer is visible on screen

ANSWER:

```json
[
    {
        "start_time": "0:06",
        "end_time": "0:10",
        "title": "UTV LIVE",
        "producer": "UTV",
        "year": "2017"
    },
    {
        "start_time": "2:35",
        "end_time": "3:34",
        "title": "UTV LIVE",
        "producer": "UTV",
        "year": "2017"
    }
]
```

* VRAM used: 13.17 GB

real    1m9.801s

---

3.

* Time: 2025-11-08T14:04:06.670651
* Video: DVC43998.mp4
* Model: Qwen/Qwen3-VL-4B-Instruct
* Device: NVIDIA GeForce RTX 4090
* VRAM used: 8.65 GB

PROMPT:

The video is a broadcast television recording from Northern Ireland. 
It contains one or more programmes visually preceded by a clear separator screen.
A separator screen is usually just a silent image without movement that is not part of the programme and never shown to the viewers.
It can last from a few seconds to a couple of minutes. 
It often contains a title of the upcoming programme.
It's visual style is normally very different from the following programme.
Please only mention separators before a new programme, not those within programmes.

Return a valid JSON Array with a list of all the times a separator appears.

Each entry should have those keys:
* start_time
* end_time
* title: all the text written on the separator screen
* year: if the year is visible on screen
* producer: if the channel name or producer is visible on screen


ANSWER:

```json
[
    {
        "start_time": "00:00",
        "end_time": "00:23",
        "title": "DRUGS (NATASHA)",
        "producer": "UTV LIVE AT SIX",
        "year": "2017"
    },
    {
        "start_time": "02:33",
        "end_time": "02:35",
        "title": "SLAUGHTNEIL (GARETH)",
        "producer": "UTV LIVE AT SIX",
        "year": "2017"
    },
    {
        "start_time": "04:13",
        "end_time": "04:15",
        "title": "SIROCCO E01 (VICKI)",
        "producer": "UTV LIVE AT SIX",
        "year": "2017"
    },
    {
        "start_time": "06:37",
        "end_time": "06:40",
        "title": "PRISONER NO8 (JUDITH)",
        "producer": "UTV LIVE AT SIX",
        "year": "2017"
    },
    {
        "start_time": "08:17",
        "end_time": "08:20",
        "title": "LIONS E18 (RUTH)",
        "producer": "UTV LIVE AT SIX",
        "year": "2017"
    },
    {
        "start_time": "10:33",
        "end_time": "10:36",
        "title": "GAA E31 (DENISE)",
        "producer": "UTV LIVE AT SIX",
        "year": "2017"
    }
]
```

* VRAM used: 13.17 GB

real    1m46.380s
user    1m14.413s
sys     0m39.173s

# 1. Experimental context

## Objectives

Try a variety of Qwen3-VL models to zero-shot detection of seperators from full-length video, preferably:
* "outer" ones only (i.e. not title screen within a programme)
* with low VRAM (see it can run om consumer GPU, 24GB max, instead of queueing for HPC)
* reliably (high recall; false positive are less important than ommisions b/c we can exclude them during post-processing; e.g. detecting inner separators or adverts is ok if they can be weed out)

## Experiments

See all the detailed outputs in the main Experiments section below.

1. 4B on 10mins gets all the seperators right and right metadata; but also inner seps
    1. (same with different seed find three then loops.)
    2. (4B killed (OOM?) on full video (35m).)
3. 4b perfect result on 10m video with better prompt
4. 4b perfect results on a different 16m video
5. 32b and better prompt
6. 32b
7. 32b 

## Resource usage
* 4b on 35mins video: 13GB VRAM (23GB with FrameSense)
* 8b on 35mins video: ?         (40GB with FrameSense)
* 32b on 35min video: 72GB VRAM (OOM! with FrameSense, WHY??)

## TODO
* 30b-3ba with transformers
* 32b-fp8 with vllm

## Questions
* what is the minimim model size for robust results on all videos?
* what is the maximum video length qwen3-vl can analyse well?
* is VRAM usage dependent on video length or output length?
* Why is VRAM usage higher with FrameSense containers?

## Videos

| Video - mins| Results with 4b/8b models (FrameSense)         | w/ 32B model |
|-------------|------------------------------------------------|--------------|
| DVC43998 16 | No issues                                      | looks good   |
| DVC43313 35 | rep loop                                       | looks good   |
| 32594    33 | rep loop, goes beyond 1h                       | looks good   |
| 90SP2284 90 | reps loop; missed 27:30, 51:10, 01:10:06       | excellent    |
| S1963_8  28 | processing error with FrameSense               |              |
| S1963_12 37 |                                                |              |
| S1964_2  32 | missed 20:34, 25:48, 29:23, 30:28              |              |
| 55300_A  25 |                                                |              |

---

# 2. Experimental results

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

---

4.

* Time  : 2025-11-14T00:11:23.208875
* Video : DVC43313.mp4
* Model : Qwen/Qwen3-VL-32B-Instruct
* Device: NVIDIA H100 NVL
* Seed  : 3407
* VRAM  : 62.70 GB

PROMPT:

The video is a broadcast television recording from Northern Ireland. 
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

ANSWER:

```json
[
  {
    "start_time": "00:05",
    "end_time": "00:10",
    "title": "UTV LIVE TX HEADS/AL505 RX/TX: 01/03/2017",
    "year": "2017",
    "producer": "UTV",
    "visual": "clock, black, white"
  },
  {
    "start_time": "02:38",
    "end_time": "03:32",
    "title": "UTV LIVE TX HEADS/AL505 RX/TX: 01/03/2017",
    "year": "2017",
    "producer": "UTV",
    "visual": "clock, black, white"
  },
  {
    "start_time": "11:21",
    "end_time": "11:28",
    "title": "VOTE 17 UTV LIVE Friday 1:35pm & 8pm Saturday 10:20am Sunday 1:35pm",
    "year": null,
    "producer": "UTV",
    "visual": "text, white, blue"
  },
  {
    "start_time": "17:37",
    "end_time": "17:42",
    "title": "UTV LIVE",
    "year": null,
    "producer": "UTV",
    "visual": "text, white, blue"
  }
]
```


* VRAM  : 71.81 GB


---

5.

* Time  : 2025-11-14T00:18:00.732143
* Video : ../../../framesense/data/NI/32594/32594.mp4
* Model : Qwen/Qwen3-VL-32B-Instruct
* Device: NVIDIA H100 NVL
* Seed  : 3407
* VRAM  : 62.70 GB

PROMPT:

The video is a broadcast television recording from Northern Ireland. 
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

ANSWER:

```json
[
  {
    "start_time": "0:00",
    "end_time": "0:14",
    "title": "Ulster Television ENG UNIT",
    "year": null,
    "producer": "Ulster Television",
    "visual": "clock, logo, blue"
  },
  {
    "start_time": "2:38",
    "end_time": "2:54",
    "title": "Ulster Television ENG UNIT",
    "year": null,
    "producer": "Ulster Television",
    "visual": "clock, logo, blue"
  },
  {
    "start_time": "6:07",
    "end_time": "6:23",
    "title": "Ulster Television ENG UNIT",
    "year": null,
    "producer": "Ulster Television",
    "visual": "clock, logo, blue"
  },
  {
    "start_time": "11:49",
    "end_time": "11:58",
    "title": "Ulster Television ENG UNIT",
    "year": null,
    "producer": "Ulster Television",
    "visual": "clock, logo, blue"
  },
  {
    "start_time": "16:24",
    "end_time": "16:34",
    "title": "Ulster Television ENG UNIT",
    "year": null,
    "producer": "Ulster Television",
    "visual": "clock, logo, blue"
  },
  {
    "start_time": "21:19",
    "end_time": "21:28",
    "title": "Ulster Television ENG UNIT",
    "year": null,
    "producer": "Ulster Television",
    "visual": "clock, logo, blue"
  },
  {
    "start_time": "23:23",
    "end_time": "23:33",
    "title": "Ulster Television ENG UNIT",
    "year": null,
    "producer": "Ulster Television",
    "visual": "clock, logo, blue"
  }
]
```

* VRAM  : 71.60 GB

---

6.

* Time  : 2025-11-14T00:26:11.079051
* Video : ../../../framesense/data/NI/90D2335_A/90D2335_A.mp4
* Model : Qwen/Qwen3-VL-32B-Instruct
* Device: NVIDIA H100 NVL
* Seed  : 3407
* VRAM  : 62.70 GB

PROMPT:

The video is a broadcast television recording from Northern Ireland. 
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


ANSWER:

```json
[
  {
    "start_time": "01:42",
    "end_time": "02:00",
    "title": "Yamal Productions Our Century Programme: 28 59/1582 'The Stars of Co. Down' Fo: 73.74 Stereo: 1/2 1.05 (44) 00:00:00 Yellow Moon Park Production 01232 421826",
    "year": "1999",
    "producer": "Yamal Productions",
    "visual": "clock, black, white"
  },
  {
    "start_time": "06:42",
    "end_time": "07:00",
    "title": "Yamal Productions Our Century Programme: 31 59/1583 'The Pill' Fo: 73.74 Stereo: 1/2 1.05 (44) 00:00:00 Yellow Moon Park Production 01232 421826",
    "year": "1999",
    "producer": "Yamal Productions",
    "visual": "clock, black, white"
  },
  {
    "start_time": "11:42",
    "end_time": "12:00",
    "title": "Yamal Productions Our Century Programme: 31 59/1584 'Best' Fo: 73.74 Stereo: 1/2 1.05 (44) 00:00:00 Yellow Moon Park Production 01232 421826",
    "year": "1999",
    "producer": "Yamal Productions",
    "visual": "clock, black, white"
  },
  {
    "start_time": "16:42",
    "end_time": "17:00",
    "title": "Yamal Productions Our Century Programme: 32 59/1585 'Housing' Fo: 73.74 Stereo: 1/2 1.05 (44) 00:00:00 Yellow Moon Park Production 01232 421826",
    "year": "1999",
    "producer": "Yamal Productions",
    "visual": "clock, black, white"
  },
  {
    "start_time": "21:42",
    "end_time": "22:00",
    "title": "Yamal Productions Our Century Programme: 33 59/1586 'Van Morrison' Fo: 73.74 Stereo: 1/2 1.05 (44) 00:00:00 Yellow Moon Park Production 01232 421826",
    "year": "1999",
    "producer": "Yamal Productions",
    "visual": "clock, black, white"
  },
  {
    "start_time": "26:42",
    "end_time": "27:00",
    "title": "Yamal Productions Our Century Programme: 34 59/1587 'Building Bridges' Fo: 73.74 Stereo: 1/2 1.05 (44) 00:00:00 Yellow Moon Park Production 01232 421826",
    "year": "1999",
    "producer": "Yamal Productions",
    "visual": "clock, black, white"
  },
  {
    "start_time": "31:42",
    "end_time": "32:00",
    "title": "Yamal Productions Our Century Programme: 35 59/1588 'Girona' Fo: 73.74 Stereo: 1/2 1.05 (44) 00:00:00 Yellow Moon Park Production 01232 421826",
    "year": "1999",
    "producer": "Yamal Productions",
    "visual": "clock, black, white"
  }
]
```

* VRAM  : 72.36 GB


---


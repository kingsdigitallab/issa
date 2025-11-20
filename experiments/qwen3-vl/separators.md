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
...
see Video section below for reference to experiment number for each video.

## Resource usage
* 4b on 35mins video: 13GB VRAM (23GB with FrameSense)
* 8b on 35mins video: ?         (40GB with FrameSense)
* 32b on 35min video: 72GB VRAM (OOM! with FrameSense, WHY??)

On our 4090 GPU loading 32b models only takes 19GB instead of 62GB on HPC, why?

## TODO
* 30b-3ba with transformers
* 32b-fp8 with vllm

## Questions
* what is the minimim model size for robust results on all videos?
* what is the maximum video length qwen3-vl can analyse well?
* is VRAM usage dependent on video length or output length?
* Why is VRAM usage higher with FrameSense containers?

## Videos

| Video     | mins| Results with 4b/8b models (FrameSense)         | w/ 32B model   | Exp.|
|-----------|-----|------------------------------------------------|----------------|-----|
| DVC43998  | 16  | No issues                                      | looks good     |  3  |
| DVC43313  | 35  | rep loop                                       | looks good     |  4  |
| 32594     | 33  | rep loop, goes beyond 1h                       | looks good     |  5  |
| 90SP2284  | 90  | reps loop; Missed 27:30, 51:10, 01:10:06       | TO BE CHECKED  | 10  |
| 90D2335_A | 36  |                                                | excellent      |  6  |
| S1963_8   | 28  | processing error with FrameSense               | TO BE CHECKED  |  9  |
| S1963_12  | 37  | M 1:13,12:46; H 2:30,4:55,7:46; G 34:39,...    | better         |  8  |
| S1964_2   | 32  | missed 20:34, 25:48, 29:23, 30:28              | only 1st       |  7  |
| 55300_A   | 25  | finds opening and closing title                | title, credits | 11  |

Why did the processing of S1963_8 take 1h20m ! 

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

7.

* Time  : 2025-11-17T11:02:52.483131
* Video : ../../../framesense/data/NI/S1964_2/S1964_2.mp4
* Model : Qwen/Qwen3-VL-32B-Instruct
* Device: NVIDIA A100 80GB PCIe
* Seed  : 3407
* VRAM  : 62.60 GB

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
    "start_time": "00:00",
    "end_time": "00:04",
    "title": "4",
    "year": null,
    "producer": null,
    "visual": "countdown number"
  }
]
```

* VRAM  : 70.53 GB
Duration: 00:03:34 (exclude model loading)


---

8.

* Time  : 2025-11-18T17:10:53.514817
* Video : ../../../framesense/data/NI/S1963_12/S1963_12.mp4
* Model : Qwen/Qwen3-VL-32B-Instruct
* Device: NVIDIA H100 NVL
* Seed  : 3407
* VRAM  : 62.70 GB

PROMPT:

The video is a broadcast television recording from Northern Ireland. 
It contains one or more programmes visually preceded by a clear separator screen.
A separator screen has the following properties:
* usually just a silent image without movement or a large (flickering) count down
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
    "end_time": "0:07",
    "title": "5",
    "year": null,
    "producer": null,
    "visual": "countdown number"
  },
  {
    "start_time": "0:36",
    "end_time": "0:45",
    "title": null,
    "year": null,
    "producer": null,
    "visual": "crosshair target"
  },
  {
    "start_time": "1:12",
    "end_time": "1:18",
    "title": null,
    "year": null,
    "producer": null,
    "visual": "crosshair target"
  },
  {
    "start_time": "1:51",
    "end_time": "2:02",
    "title": null,
    "year": null,
    "producer": null,
    "visual": "crosshair target"
  },
  {
    "start_time": "3:11",
    "end_time": "3:18",
    "title": "3",
    "year": null,
    "producer": null,
    "visual": "countdown number"
  },
  {
    "start_time": "13:08",
    "end_time": "13:14",
    "title": null,
    "year": null,
    "producer": null,
    "visual": "crosshair target"
  },
  {
    "start_time": "15:20",
    "end_time": "15:26",
    "title": null,
    "year": null,
    "producer": null,
    "visual": "crosshair target"
  },
  {
    "start_time": "22:34",
    "end_time": "22:40",
    "title": "3",
    "year": null,
    "producer": null,
    "visual": "countdown number"
  },
  {
    "start_time": "27:47",
    "end_time": "27:53",
    "title": "11",
    "year": null,
    "producer": null,
    "visual": "countdown number"
  },
  {
    "start_time": "30:41",
    "end_time": "30:47",
    "title": null,
    "year": null,
    "producer": null,
    "visual": "crosshair target"
  },
  {
    "start_time": "35:45",
    "end_time": "35:51",
    "title": "3",
    "year": null,
    "producer": null,
    "visual": "countdown number"
  },
  {
    "start_time": "37:35",
    "end_time": "37:41",
    "title": null,
    "year": null,
    "producer": null,
    "visual": "crosshair target"
  }
]
```

* VRAM  : 70.71 GB
Duration: 00:05:19 (exclude model loading)


---

9.

* Time  : 2025-11-20T08:40:04.259785
* Video : ../../../framesense/data/NI/S1963_8/S1963_8.mp4
* Model : Qwen/Qwen3-VL-32B-Instruct
* Device: NVIDIA H100 NVL
* Seed  : 3407
* VRAM  : 62.70 GB

PROMPT:

The video is a broadcast television recording from Northern Ireland. 
It contains one or more programmes visually preceded by a clear separator screen.
A separator screen has the following properties:
* usually just a silent image without movement or a large (flickering) count down
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
    "end_time": "0:09",
    "title": "1000 MILES 91 CIRCUIT OF IRELAND TRIAL",
    "year": null,
    "producer": null,
    "visual": "black and white sign"
  },
  {
    "start_time": "0:11",
    "end_time": "0:29",
    "title": "Ulster Automobile Club 1000 MILES CIRCUIT OF IRELAND TRIAL",
    "year": null,
    "producer": null,
    "visual": "hand-drawn map"
  },
  {
    "start_time": "0:31",
    "end_time": "0:43",
    "title": "1951",
    "year": "1951",
    "producer": null,
    "visual": "black screen with white text"
  },
  {
    "start_time": "5:26",
    "end_time": "5:32",
    "title": "Ulster Trophy Races 1952 Preliminary events for the Small Fry",
    "year": "1952",
    "producer": null,
    "visual": "chalkboard"
  },
  {
    "start_time": "7:41",
    "end_time": "7:47",
    "title": "Ulster Trophy Races 1952 The Big Stuff Winner: Fartace in an Alfa",
    "year": "1952",
    "producer": null,
    "visual": "chalkboard"
  },
  {
    "start_time": "11:30",
    "end_time": "11:36",
    "title": "PRACTICE AT CRAIGANTLET SEPT. 1951",
    "year": "1951",
    "producer": null,
    "visual": "black screen with white text"
  },
  {
    "start_time": "12:01",
    "end_time": "12:09",
    "title": "R.A.C. TOURIST TROPHY RACE SEPT. 1951 JAGUAR FIRST MOSS DRIVING",
    "year": "1951",
    "producer": null,
    "visual": "black screen with white text"
  },
  {
    "start_time": "13:55",
    "end_time": "14:03",
    "title": "CIRCUIT OF IRELAND TRIAL EASTER 1952",
    "year": "1952",
    "producer": null,
    "visual": "chalkboard"
  },
  {
    "start_time": "14:51",
    "end_time": "14:58",
    "title": "1000 MILES 96 CIRCUIT OF IRELAND TRIAL",
    "year": null,
    "producer": null,
    "visual": "black and white sign"
  },
  {
    "start_time": "22:49",
    "end_time": "22:55",
    "title": "ASCENDING TIM HEALY PASS",
    "year": null,
    "producer": null,
    "visual": "black screen with white text"
  },
  {
    "start_time": "26:10",
    "end_time": "26:17",
    "title": "LEAVING KILLARNEY",
    "year": null,
    "producer": null,
    "visual": "black screen with white text"
  }
]
```

* VRAM  : 70.69 GB

Duration: 01:20:27 (exclude model loading)

---

10.

* Time  : 2025-11-20T10:14:10.599941
* Video : ../../../framesense/data/NI/90SP2284/90SP2284.mp4
* Model : Qwen/Qwen3-VL-32B-Instruct
* Device: NVIDIA H100 NVL
* Seed  : 3407
* VRAM  : 62.70 GB

PROMPT:

The video is a broadcast television recording from Northern Ireland. 
It contains one or more programmes visually preceded by a clear separator screen.
A separator screen has the following properties:
* usually just a silent image without movement or a large (flickering) count down
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
    "start_time": "00:00",
    "end_time": "00:04",
    "title": "KELLY\nTX 17 9 99\n99/0 516",
    "year": "1999",
    "producer": "KELLY",
    "visual": "clock, black, white"
  },
  {
    "start_time": "00:13",
    "end_time": "00:16",
    "title": "KELLY TITLES\nGOF4",
    "year": null,
    "producer": "KELLY",
    "visual": "clock, black, white"
  },
  {
    "start_time": "01:00",
    "end_time": "01:03",
    "title": "FRIDAY NIGHT\nwith\nGaltee",
    "year": null,
    "producer": "Galtee",
    "visual": "text, colorful, logo"
  },
  {
    "start_time": "02:00",
    "end_time": "02:03",
    "title": "KELLY BREAKS\nOUT OF BREAK -\nFREEDOM!",
    "year": null,
    "producer": "KELLY",
    "visual": "clock, silver, logo"
  },
  {
    "start_time": "03:56",
    "end_time": "03:59",
    "title": "KELLY BREAKS\nOUT OF BREAK -\nAUSTIN IN",
    "year": null,
    "producer": "KELLY",
    "visual": "clock, silver, logo"
  },
  {
    "start_time": "05:36",
    "end_time": "05:39",
    "title": "KELLY BREAKS\nINTO BREAK -\nTARTAN - UNFINISHED",
    "year": null,
    "producer": "KELLY",
    "visual": "clock, silver, logo"
  },
  {
    "start_time": "06:56",
    "end_time": "06:59",
    "title": "The Mugs Game\nUVF\nOrmeau Road\nBelfast BT7 1EB",
    "year": null,
    "producer": "UVF",
    "visual": "text, red, logo"
  }
]
```

* VRAM  : 72.39 GB
Duration: 00:10:43 (exclude model loading)


---

11.

* Time  : 2025-11-20T11:13:09.130525
* Video : ../../../framesense/data/NI/55300_A/55300_A.mp4
* Model : Qwen/Qwen3-VL-32B-Instruct
* Device: NVIDIA H100 NVL
* Seed  : 3407
* VRAM  : 62.70 GB

PROMPT:

The video is a broadcast television recording from Northern Ireland. 
It contains one or more programmes visually preceded by a clear separator screen.
A separator screen has the following properties:
* usually just a silent image without movement or a large (flickering) count down
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
    "start_time": "0.0",
    "end_time": "8.0",
    "title": "LESSER SPOTTED ULSTER",
    "year": null,
    "producer": null,
    "visual": "black background, white text, title"
  },
  {
    "start_time": "1512.0",
    "end_time": "1525.0",
    "title": "Thanks to: RITA MEWALL JEFFEREY CUPPLES BERTIE MCKAY PHILLIP WATSON MICHAEL FERGUSON LORNA FERGUSON JULIAN FRIERS JILL FRIERS and the people of Ballintoy",
    "year": null,
    "producer": null,
    "visual": "black background, white text, credits"
  },
  {
    "start_time": "1526.0",
    "end_time": "1531.0",
    "title": "A NORTHLAND Production for UTV",
    "year": null,
    "producer": "UTV",
    "visual": "black background, white and colored text, logo"
  }
]
```


* VRAM  : 70.68 GB

Duration: 00:03:10 (exclude model loading)

---


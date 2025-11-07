
Task: find separators in a 35 min video

Observations: 
* with a simple prompt, Qwen3-vl 32b find all the separator but hallucinate a couple and doesn't read all the titles.
* with a more advanced prompt to only detect separators outside programmes, it detects teh first two then hallucinate in a loop.

---

* Time: 2025-11-07T09:43:51.449677
* Video: DVC43313.mp4
* Model: Qwen/Qwen3-VL-32B-Instruct
* Device: NVIDIA H100 NVL
* VRAM used: 62.70 GB

PROMPT:

The video is a broadcast television recording from Northern Ireland. 
It contains one or more programmes visually preceded by a clear separator screen.
A separator screen is usually just a silent image without movement.
It can last from a few seconds to a couple of minutes. 
It often contains a title of the upcoming programme.

Return a valid JSON Array with a list of all the times a separator appears.

Each entry should have those keys:
* start_time
* end_time
* title

ANSWER:

```json
[
  {
    "start_time": "0:00",
    "end_time": "0:10",
    "title": "UTV LIVE",
    "@annotation": "correct, that a clock, but there's more written on that screen",
  },
  {
    "start_time": "2:37",
    "end_time": "3:35",
    "title": "UTV LIVE",
    "@annotation": "correct, that a clock, but there's more written on that screen",
  },
  {
    "start_time": "4:38",
    "end_time": "4:41",
    "title": "UTV LIVE",
    "@annotation": "correct, but that's an inner separator",
  },
  {
    "start_time": "14:05",
    "end_time": "14:08",
    "title": "VOTE 17",
    "@annotation": "correct, that a clock, but that's an inner separator, also missing titles cming gradually",
  },
  {
    "start_time": "17:09",
    "end_time": "17:12",
    "title": "UTV LIVE",
    "@annotation": "Hallucination",
  },
  {
    "start_time": "21:14",
    "end_time": "21:17",
    "title": "UTV LIVE",
    "@annotation": "correct, but that's an inner separator",
  },
  {
    "start_time": "27:27",
    "end_time": "27:30",
    "title": "UTV LIVE",
    "@annotation": "Hallucination",
  },
  {
    "start_time": "28:15",
    "end_time": "28:18",
    "title": "UTV LIVE"
    "@annotation": "Hallucination",
  }
]
```

* VRAM used: 71.77 GB


---



* Time: 2025-11-07T10:48:58.094926
* Video: DVC43313.mp4
* Model: Qwen/Qwen3-VL-32B-Instruct
* Device: NVIDIA H100 NVL
* VRAM used: 62.70 GB

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


/cephfs/volumes/hpc_data_usr/k1217897/307a0abf-03e6-4bc1-9da9-436d2eb93196/prj/issa/experiments/qwen3-vl/venv/lib/python3.11/site-packages/transformers/video_processing_utils.py:879: UserWarning: `torchcodec` is not installed and cannot be used to decode the video by default. Falling back to `torchvision`. Note that `torchvision` decoding is deprecated and will be removed in future versions. 
  warnings.warn(
/cephfs/volumes/hpc_data_usr/k1217897/307a0abf-03e6-4bc1-9da9-436d2eb93196/prj/issa/experiments/qwen3-vl/venv/lib/python3.11/site-packages/transformers/video_utils.py:529: UserWarning: Using `torchvision` for video decoding is deprecated and will be removed in future versions. Please use `torchcodec` instead.
  warnings.warn(
/cephfs/volumes/hpc_data_usr/k1217897/307a0abf-03e6-4bc1-9da9-436d2eb93196/prj/issa/experiments/qwen3-vl/venv/lib/python3.11/site-packages/torchvision/io/_video_deprecation_warning.py:5: UserWarning: The video decoding and encoding capabilities of torchvision are deprecated from version 0.22 and will be removed in version 0.24. We recommend that you migrate to TorchCodec, where we'll consolidate the future decoding/encoding capabilities of PyTorch: https://github.com/pytorch/torchcodec
  warnings.warn(

ANSWER:

```json
[
  {
    "start_time": "00:05",
    "end_time": "00:10",
    "title": "UTV LIVE TX HEADS/AL505 RX/TX: 01/03/2017",
    "year": "2017",
    "producer": "UTV"
  },
  {
    "start_time": "02:39",
    "end_time": "03:32",
    "title": "UTV LIVE TX HEADS/AL505 RX/TX: 01/03/2017",
    "year": "2017",
    "producer": "UTV"
  },
  {
    "start_time": "03:32",
    "end_time": "03:34",
    "title": "",
    "year": "",
    "producer": ""
  },
  {
    "start_time": "03:34",
    "end_time": "03:44",
    "title": "",
    "year": "",
    "producer": ""
  },
  {
    "start_time": "03:44",
    "end_time": "03:49",
    "title": "",
    "year": "",
    "producer": ""
  },
  {
    "start_time": "03:49",
    "end_time": "03:50",
    "title": "",
    "year": "",
    "producer": ""
  },
  {
    "start_time": "03:50",
    "end_time": "03:54",
    "title": "",
    "year": "",
    "producer": ""
  },
  {
    "start_time": "03:54",
    "end_time": "03:55",
    "title": "",
    "year": "",
    "producer": ""
  },
  {
    "start_time": "03:55",
    "end_time": "03:57",
    "title": "",
    "year": "",
    "producer": ""
  },
  {
    "start_time": "03:57",
    "end_time": "04:00",
    "title": "",
    "year": "",
    "producer": ""
  },
  {
    "start_time": "04:00",
    "end_time": "04:03",
    "title": "",
    "year": "",
    "producer": ""
  },
  {
    "start_time": "04:03",
    "end_time": "04:04",
    "title": "",
    "year": "",
    "producer": ""
  },
  {
    "start_time": "04:04",
    "end_time": "04:05",
    "title": "",
    "year": "",
    "producer": ""
  },
  {
    "start_time": "04:05",
    "end_time": "04:06",
    "title": "",
    "year": "",
    "producer": ""
  },
  {
    "start_time": "04:06",
    "end_time": "04:07",
    "title": "",
    "year": "",
    "producer": ""
  },
  {
    "start_time": "04:07",
    "end_time": "04:08",
    "title": "",
    "year": "",
    "producer": ""
  },
  {
    "start_time": "04:08",
    "end_time": "04:09",
    "title": "",
    "year": "",
    "producer": ""
  },
  {
    "start_time": "04:09",
    "end_time": "04:10",
    "title": "",
    "year": "",
    "producer": ""
  },
  {
    "start_time": "04:10",
    "end_time": "04:11",
    "title": "",
    "year": "",
    "producer": ""
  },
  {
    "start_time": "04:11",
    "end_time": "04:12",
    "title": "",
    "year": "",
    "producer": ""
  },
  {
    "start_time": "04:12",
    "end_time": "04:13",
    "title": "",
    "year": "",
    "producer": ""
  },
  {
    "start_time": "04:13",
    "end_time": "04:14",
```


* VRAM used: 71.78 GB


---



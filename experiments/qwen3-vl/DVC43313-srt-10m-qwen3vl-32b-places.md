Experiment related to MVP 2 to extract place names 
and types directly from video file using a VLM.

Observations:
* hit and miss, some location are rights, others not accurate
* some notable hallucinations, including about teh subtitles
* promising but only if there's a way to make it more reliable
* categorisation of place could be more consistent

TODO:
* change prompt to insist on the place name being taken from the subtitle
* compare the extarcted subs aith the video
* tweak temperature

---

* Time: 2025-10-25T10:37:10.582158
* Video: v-10-srt.mp4
* Model: Qwen/Qwen3-VL-32B-Instruct
* Device: NVIDIA A100 80GB PCIe
* VRAM used: 62.60 GB

PROMPT:

The video is a broadcast television recording from Northern Ireland.
List all moments where a particular place in Northern Ireland is shown visually and/or mentioned in the subtitles.
Answer as a valid JSON Array.
Each item in the list should have the following fields:
* time: the timestamp of the ocurrence in the video
* locality: name of a city, district, town or village
* name: the actual short name of the place
* type: the type of place (e.g. church, townhall, football pitch)
* subtitle: exactly how the place is mentioned in the subtitle or 'NONE' if not mentioned
* view: briefly characterise, in a few words, the way the place is shown on screen or 'NONE' if not shown
* indoor: 'yes' if the view is from indoor, 'no' if from outdoor, 'NONE' if not shown


ANSWER:

```json
[
  {
    "time": "4:03",
    "locality": "Belfast",
    "name": "Sailor's Row",
    "type": "commercial building complex",
    "subtitle": "the new office development in Northern Ireland, Sailor's Row",
    "view": "wide aerial shot of modern glass buildings with people walking in courtyard",
    "indoor": "no"
  },
  {
    "time": "4:10",
    "locality": "Belfast",
    "name": "Belfast",
    "type": "city",
    "subtitle": "I hope, with East Belfast basically and the rest of the city, which is what we really want.",
    "view": "man speaking outdoors in front of modern buildings",
    "indoor": "no"
  },
  {
    "time": "4:19",
    "locality": "Belfast",
    "name": "Belfast",
    "type": "city",
    "subtitle": "We're actually part of Belfast.",
    "view": "wide shot of classical stone building with columns",
    "indoor": "no"
  },
  {
    "time": "5:47",
    "locality": "Belfast",
    "name": "Belfast",
    "type": "city",
    "subtitle": "A lawyer acting for the Renewable Heat Association said the case was brought to the High Court in Belfast.",
    "view": "exterior shot of large classical building with flagpole and graveyard",
    "indoor": "no"
  },
  {
    "time": "5:50",
    "locality": "Belfast",
    "name": "Royal Courts of Justice",
    "type": "court building",
    "subtitle": "Royal Courts of Justice",
    "view": "close-up of sign on building with arrow pointing left",
    "indoor": "no"
  },
  {
    "time": "5:54",
    "locality": "Belfast",
    "name": "Belfast",
    "type": "city",
    "subtitle": "The case has been heard, and the judgment handed down, in the High Court in Belfast.",
    "view": "close-up of ornate black lantern with crown on top",
    "indoor": "no"
  },
  {
    "time": "9:37",
    "locality": "Belfast",
    "name": "Belfast City Centre",
    "type": "urban area",
    "subtitle": "it's 16 acres of prime development land close to Belfast City Centre",
    "view": "wide shot of construction site with crane and piles of earth",
    "indoor": "no"
  },
  {
    "time": "9:50",
    "locality": "Belfast",
    "name": "Belfast",
    "type": "city",
    "subtitle": "The development, though, was cleared in the way for a major regeneration plan in 2005",
    "view": "wide shot of large cleared field with city skyline in background",
    "indoor": "no"
  }
]
```

* VRAM used: 71.55 GB


---

* Time: 2025-10-25T10:58:50.411958
* Video: v-10-srt.mp4
* Model: Qwen/Qwen3-VL-32B-Instruct
* Device: NVIDIA A100 80GB PCIe
* VRAM used: 62.60 GB

PROMPT:

The video is a broadcast television recording from Northern Ireland.
List all moments where a particular place in Northern Ireland is shown visually and/or mentioned in the subtitles.
Answer as a valid JSON Array.
Each item in the list should have the following fields:
* time: the timestamp of the ocurrence in the video
* locality: name of a city, district, town or village (e.g. Armagh)
* name: the exact place name, without the locality (e.g. St. Chatherine's College)
* type: the type of place (e.g. church, townhall, football pitch)
* subtitle: exactly how the place is mentioned in the subtitle or 'NONE' if not mentioned
* view: briefly characterise, in a few words, the way the place is shown on screen or 'NONE' if not shown
* indoor: 'yes' if the view is from indoor, 'no' if from outdoor, 'NONE' if not shown

The values of `locality` and `name` together should be enough to uniquely pinpoint the location on a map.

ANSWER:

```json
[
  {
    "time": "4:04",
    "locality": "Belfast",
    "name": "Sewerby Road",
    "type": "commercial complex",
    "subtitle": "this large office complex in Northern Ireland's Sewerby Road",
    "view": "Aerial view of a modern glass office complex with people walking in the courtyard.",
    "indoor": "no"
  },
  {
    "time": "4:10",
    "locality": "Belfast",
    "name": "Sewerby Road",
    "type": "commercial complex",
    "subtitle": "I hope when East Belfast basically and the rest of the city, which is what we really want, will be part of the city. We're not some independent bit of it. We're actually part of Belfast.",
    "view": "Close-up of a man speaking outdoors in front of a building with reflective windows.",
    "indoor": "no"
  },
  {
    "time": "4:19",
    "locality": "Belfast",
    "name": "Royal Courts of Justice",
    "type": "court building",
    "subtitle": "The Royal Courts of Justice, where the case was heard.",
    "view": "Exterior shot of a large classical building with columns and a flagpole.",
    "indoor": "no"
  },
  {
    "time": "5:48",
    "locality": "Belfast",
    "name": "Royal Courts of Justice",
    "type": "court building",
    "subtitle": "The case was heard in Belfast, and the judge said the case was not only about the individual claimant, but the wider principle that the Department for the Economy could not be forced to publish the names.",
    "view": "Exterior shot of the same classical building with a sign reading 'Royal Courts of Justice'.",
    "indoor": "no"
  },
  {
    "time": "5:50",
    "locality": "Belfast",
    "name": "Royal Courts of Justice",
    "type": "court building",
    "subtitle": "Royal Courts of Justice",
    "view": "Close-up of a street sign pointing to the Royal Courts of Justice.",
    "indoor": "no"
  },
  {
    "time": "5:55",
    "locality": "Belfast",
    "name": "Royal Courts of Justice",
    "type": "court building",
    "subtitle": "The case was heard in Belfast, and the judge said the case was not only about the individual claimant, but the wider principle that the Department for the Economy could not be forced to publish the names.",
    "view": "Close-up of a decorative black lantern with a crown on top.",
    "indoor": "no"
  },
  {
    "time": "9:38",
    "locality": "Belfast",
    "name": "Sewerby Road",
    "type": "commercial complex",
    "subtitle": "It's 16 acres of prime development land close to Belfast City centre.",
    "view": "Wide shot of a construction site with cranes and excavated earth.",
    "indoor": "no"
  },
  {
    "time": "9:50",
    "locality": "Belfast",
    "name": "Sewerby Road",
    "type": "commercial complex",
    "subtitle": "The development, in fact, was cleared in the way for a major regeneration plan in 2005.",
    "view": "Panoramic view of a large open field with construction equipment and buildings in the distance.",
    "indoor": "no"
  },
  {
    "time": "9:58",
    "locality": "Belfast",
    "name": "Sewerby Road",
    "type": "commercial complex",
    "subtitle": "The new masterplan for the site will be understood the Law",
    "view": "Aerial view of the modern glass office complex with people walking in the courtyard.",
    "indoor": "no"
  }
]
```

* VRAM used: 70.86 GB


---

* Time: 2025-10-25T11:32:34.750092
* Video: v-10-srt.mp4
* Model: Qwen/Qwen3-VL-32B-Instruct
* Device: NVIDIA A100 80GB PCIe
* VRAM used: 62.60 GB

PROMPT:

The video is a broadcast television recording from Northern Ireland.
List all moments an identifiable landmark in Northern Ireland is shown on screen.
Use the subtitles to figure out the actual place name and the broader context.
Answer as a valid JSON Array.
Each item in the list should have the following fields:
* time: the timestamp when the landmark is shown in the video
* locality: name of a city, district, town or village (e.g. Armagh)
* name: the exact place name, without the locality (e.g. St. Chatherine's College)
* type: the type of place (e.g. church, townhall, football pitch)
* subtitle: exactly how the place is mentioned in the subtitle or 'NONE' if not mentioned
* view: briefly characterise, in a few words, the way the place is shown on screen
* indoor: 'yes' if the view is from indoor, 'no' if from outdoor

The values of `locality` and `name` together should be enough to uniquely pinpoint the location on a map.


ANSWER:

```json
[
  {
    "time": "4:04",
    "locality": "Belfast",
    "name": "Saxons Way",
    "type": "commercial development",
    "subtitle": "the new office development in Belfast city centre, Saxons Way",
    "view": "Aerial view of a modern glass office complex with people walking in the courtyard.",
    "indoor": "no"
  },
  {
    "time": "4:19",
    "locality": "Belfast",
    "name": "Belfast City Hall",
    "type": "townhall",
    "subtitle": "Belfast City Hall, the city's most prominent building",
    "view": "Exterior shot of the grand neoclassical building with columns and a dome.",
    "indoor": "no"
  },
  {
    "time": "5:47",
    "locality": "Belfast",
    "name": "Belfast Crown Court",
    "type": "court building",
    "subtitle": "The case was brought before the High Court in Belfast, and the judge said the Economy Minister's decision to publish the names was not legally justified.",
    "view": "Exterior shot of a large classical building with a cross and a statue in front.",
    "indoor": "no"
  },
  {
    "time": "5:50",
    "locality": "Belfast",
    "name": "Royal Courts of Justice",
    "type": "court building",
    "subtitle": "The case was brought before the High Court in Belfast, and the judge said the Economy Minister's decision to publish the names was not legally justified.",
    "view": "Close-up of a sign on a building that reads 'Royal Courts of Justice'.",
    "indoor": "no"
  },
  {
    "time": "7:11",
    "locality": "Belfast",
    "name": "Belfast Crown Court",
    "type": "court building",
    "subtitle": "The lawyer acting for the Renewable Heat Association said the case was brought to be a test of the law, and the association wanted to see if the judge would rule that the names of the companies involved in the RHI scheme could be published.",
    "view": "Exterior shot of the same classical building as at 5:47.",
    "indoor": "no"
  },
  {
    "time": "9:58",
    "locality": "Belfast",
    "name": "The Lanyon Building",
    "type": "public building",
    "subtitle": "the new university campus at the Lanyon Building",
    "view": "Aerial view of a modern campus with a large glass and steel structure.",
    "indoor": "no"
  }
]
```

* VRAM used: 70.86 GB


real    2m54.411s
user    1m27.150s
sys     0m49.871s

---

* Time: 2025-10-25T22:33:51.407135
* Video: v-10-srt.mp4
* Model: Qwen/Qwen3-VL-32B-Instruct
* Device: NVIDIA A100 80GB PCIe
* VRAM used: 62.60 GB

PROMPT:

The video is a broadcast television recording from Northern Ireland.
By using the context in the video subtitles and other text visible on screen, 
spot all specific places in Northern Ireland. 
A specific place is a clearly specified small area or structure smaller than a province or a city (e.g. a town hall, a village, a school, a city district or borough)
which can be uniquely named and precisely pinpointed on a map.
List, as a JSON array, all occurences of a specific place in the video.
Each item in the list should have the following fields:
* time: the timestamp when the place is shown in the video
* locality: name of a city, district, town or village where this place is located (e.g. Armagh)
* name: the exact place name, without the locality (e.g. St. Chatherine's College)
* type: the type of place (e.g. church, townhall, football pitch)
* subtitle: exactly how the place is named in the subtitle or on screen text
* view: briefly characterise, in a few words, the way the place is shown on screen
* indoor: 'yes' if the view is from indoor, 'no' if from outdoor

The values of `locality` and `name` together should be enough to uniquely pinpoint the location on a map.


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
    "time": "4:04",
    "locality": "Belfast",
    "name": "Sailors' Home",
    "type": "building",
    "subtitle": "the Sailors' Home in the city centre",
    "view": "exterior aerial view of a modern glass building complex",
    "indoor": "no"
  },
  {
    "time": "4:18",
    "locality": "Belfast",
    "name": "Belfast City Hall",
    "type": "city hall",
    "subtitle": "Belfast City Hall",
    "view": "exterior shot of a large classical-style building with columns and a clock tower",
    "indoor": "no"
  },
  {
    "time": "5:48",
    "locality": "Belfast",
    "name": "Royal Courts of Justice",
    "type": "courthouse",
    "subtitle": "Royal Courts of Justice",
    "view": "exterior shot of a large classical-style building with columns and a clock tower",
    "indoor": "no"
  },
  {
    "time": "9:38",
    "locality": "Belfast",
    "name": "Belfast City Centre",
    "type": "city centre",
    "subtitle": "Belfast City Centre",
    "view": "aerial view of a construction site with cranes and buildings in the background",
    "indoor": "no"
  },
  {
    "time": "9:58",
    "locality": "Belfast",
    "name": "The Lanyon Building",
    "type": "building",
    "subtitle": "The Lanyon Building",
    "view": "aerial view of a modern building complex with a large courtyard and people walking around",
    "indoor": "no"
  }
]
```


* VRAM used: 70.87 GB


---

* Time: 2025-10-25T22:51:41.529765
* Video: v-10-srt.mp4
* Model: Qwen/Qwen3-VL-32B-Instruct
* Device: NVIDIA A100 80GB PCIe
* VRAM used: 62.60 GB

PROMPT:

The video is a broadcast television recording from Northern Ireland.
Spot explicit mentions or reliable depictions of identifiable place names in the subtitles and the visuals. 
TV studios or large areas the size of a city should be ignored.
List, as a valid JSON array, all occurences of the place names.
Each item in the list should have the following fields:
* time: the timestamp when the place is shown in the video
* locality: name of a city, district, town or village where this place is located (e.g. Armagh)
* name: the exact place name, without the locality (e.g. St. Chatherine's College)
* type: the type of place (e.g. church, townhall, football pitch)
* subtitle: exactly how the place is named in the subtitle or on screen text
* view: briefly characterise, in a few words, the way the place is shown on screen
* indoor: 'yes' if the view is from indoor, 'no' if from outdoor

The values of `locality` and `name` together should be enough to uniquely pinpoint the location on a map.

ANSWER:

```json
[
  {
    "time": "4:05",
    "locality": "Belfast",
    "name": "Savoy Place",
    "type": "building complex",
    "subtitle": "Savoy Place",
    "view": "Aerial view of a modern glass building complex with a courtyard",
    "indoor": "no"
  },
  {
    "time": "4:19",
    "locality": "Belfast",
    "name": "Belfast City Hall",
    "type": "town hall",
    "subtitle": "Belfast City Hall",
    "view": "Exterior shot of a large classical building with columns and a dome",
    "indoor": "no"
  },
  {
    "time": "5:47",
    "locality": "Belfast",
    "name": "Belfast Crown Court",
    "type": "court building",
    "subtitle": "Belfast Crown Court",
    "view": "Exterior shot of a large classical building with a flagpole and cross",
    "indoor": "no"
  },
  {
    "time": "5:50",
    "locality": "Belfast",
    "name": "Royal Courts of Justice",
    "type": "court building",
    "subtitle": "Royal Courts of Justice",
    "view": "Close-up of a street sign pointing to the Royal Courts of Justice",
    "indoor": "no"
  },
  {
    "time": "9:18",
    "locality": "Belfast",
    "name": "Belfast City Centre",
    "type": "urban area",
    "subtitle": "Belfast City Centre",
    "view": "Aerial view of a construction site with cranes and a large open area",
    "indoor": "no"
  },
  {
    "time": "9:31",
    "locality": "Belfast",
    "name": "Belfast City Centre",
    "type": "urban area",
    "subtitle": "Belfast City Centre",
    "view": "Aerial view of a construction site with cranes and a large open area",
    "indoor": "no"
  },
  {
    "time": "9:57",
    "locality": "Belfast",
    "name": "The Linen Quarter",
    "type": "urban area",
    "subtitle": "The Linen Quarter",
    "view": "Aerial view of a modern urban area with buildings and people",
    "indoor": "no"
  }
]
```

* VRAM used: 70.86 GB





real    5m50.947s
user    1m41.997s
sys     0m56.532s

---

PROMPT:

The video is a broadcast television recording. List all the high-level segments in the video. Don't be too granular. A segment length can vary between 2 and 30 minutes. They are usually clearly separated by blank or count down screens. Answer as a JSON array with starting time, any text in the separation screen preceding the segment, and a few words describing the content of teh segment.

```json
[
  {
    "start_time": "0:00",
    "separator_text": "",
    "segment_description": "Intro screen with UTV LIVE logo and date."
  },
  {
    "start_time": "0:11",
    "separator_text": "",
    "segment_description": "News anchors at desk discussing current events."
  },
  {
    "start_time": "2:31",
    "separator_text": "UTV LIVE TX HEADS/ALS05 RX/TX: 01/03/2017",
    "segment_description": "Black screen with UTV LIVE logo and technical details."
  },
  {
    "start_time": "3:35",
    "separator_text": "",
    "segment_description": "Montage of various scenes including construction, people, and cityscapes."
  },
  {
    "start_time": "3:50",
    "separator_text": "",
    "segment_description": "News anchors back in studio discussing topics."
  },
  {
    "start_time": "4:04",
    "separator_text": "",
    "segment_description": "Interview with a man in front of a building and exterior shots of buildings."
  },
  {
    "start_time": "4:30",
    "separator_text": "UTV WEATHER",
    "segment_description": "Weather segment with a man in a suit standing in front of a rainy background."
  },
  {
    "start_time": "4:45",
    "separator_text": "",
    "segment_description": "Return to news anchors in studio with various visuals on screen."
  },
  {
    "start_time": "5:11",
    "separator_text": "",
    "segment_description": "Footage of industrial equipment and machinery."
  },
  {
    "start_time": "5:47",
    "separator_text": "",
    "segment_description": "Reporter Jane Loughrey reporting live from outside a building."
  },
  {
    "start_time": "6:34",
    "separator_text": "STATEMENT",
    "segment_description": "Statement from Mr Justice Deeny displayed on screen."
  },
  {
    "start_time": "7:35",
    "separator_text": "",
    "segment_description": "Reporter Jane Loughrey in studio discussing the case with another anchor."
  },
  {
    "start_time": "9:18",
    "separator_text": "",
    "segment_description": "Anchor discussing urban development with visuals of construction sites and cityscapes."
  }
]
```

VRAM used: 70.99 GB

real    3m34.626s

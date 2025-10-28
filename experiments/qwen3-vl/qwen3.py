'''Observations:

Qwen-VL-2B with flash attention requires 8GB for a small response to a 10 mins video.
1 minute.
!!! 2B seems to only describe the action and not the sound or spoken words

4B, takes 43GB!
4B unable to response qst about sound & speech!
It also repeats.

8B uses 57GB

'''
import os
from transformers import Qwen3VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
import torch
from datetime import datetime

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
# MAX_NEW_TOKENS = 128
# MAX_NEW_TOKENS = 4000
MAX_NEW_TOKENS = 5000

### MVP1 - Semantic Segmentation
# original from DC:
PROMPT = '''The video is a broadcast television recording. Analyse the video. First, identify from the text in the title plate(s), ident(s), or transmission card(s), how many programmes are in this recording, and any relevant metadata about the programmes, including network, name, channel, and transmission date if available. Then break down each programme into meaningful segments, for example, if it is a news programme identify each of the news stories. Output an index of the segments with a timestamp and a detailed summary of each segment, focusing on subjects, places and actions, and including any relevant information from the visuals, sound, text or speech. Return this index as a valid JSON array.'''
# original w/ request for brevity & absence of audio processing capabilities => repetitive loops
# PROMPT = '''The video is a broadcast television recording. Analyse the video. First, identify from the text in the title plate(s), ident(s), or transmission card(s), how many programmes are in this recording, and any relevant metadata about the programmes, including network, name, channel, and transmission date if available. Then break down each programme into meaningful segments, for example, if it is a news programme identify each of the news stories. Output an index of the segments with a timestamp and a short summary (one short sentence maximum) of each segment, focusing on subjects, places and actions, and including any relevant information from the visuals, texts and subtitles. Return this index as a valid JSON array.'''
# PROMPT = '''The video is a broadcast television recording. List all the separate programmes. If a programme contains multiple news stories, list the stories as well. For each item in the list provide the timecode and one short sentence summary.'''
# PROMPT = '''The video is a broadcast television recording. Spot the visual separation between programmes, like a clock, a countdown, a blank screen or a title screen. List all the programmes longer than a one minute (don't be too granular), with their starting time and any text visible on the visual separation preceding the programme. Also describe the topic of each programme with a few words. Answer in JSON only.'''
# Used to compare most qwen models
# PROMPT = '''The video is a broadcast television recording. List all the high-level segments in the video. Don't be too granular. A segment length can vary between 2 and 30 minutes. They are usually clearly separated by blank or count down screens. Answer as a JSON array with starting time, any text in the separation screen preceding the segment, and a few words describing the content of teh segment.'''
# Improved
# PROMPT = '''The video is a broadcast television recording from Northern Ireland. List all the high-level programmes in the video. A programme length can vary between 2 and 30 minutes. It is usually clearly preceded by a blank or count-down screen serving as a separator. Answer with a JSON array with starting time, any text in the separation screen preceding the segment, and a few words summary of the content (mentioning place(s), people and main event/action).'''

### MVP2 - Place Names
PROMPT = '''The video is a broadcast television recording from Northern Ireland. Transcribe all the subtitles with high accuracy. One sentence per line. Don't make things up.'''

# VIDEO_PATH = "v-10-srt.mp4"
VIDEO_PATH = "v-10-srt.mp4"
# VIDEO_PATH = "DVC43313-srt.mp4"

# MODEL = "Qwen/Qwen3-VL-4B-Instruct" # unreliable
# MODEL = "Qwen/Qwen3-VL-8B-Instruct" # 
# MODEL = "Qwen/Qwen3-VL-8B-Thinking" # very verbose, need to increase MAX_NEW_TOKENS >> 1k to catch the actual response
# MODEL = "Qwen/Qwen3-VL-32B-Instruct-FP8" # NOT working; transforms package doesn't support it yet
# MODEL = "Qwen/Qwen3-VL-30B-A3B-Instruct" # NOT working; Transforms doesn't support it yet
MODEL = "Qwen/Qwen3-VL-32B-Instruct" # v. good quality for 20mins video; ~72GB VRAM!

def show_vram():
    free, total = torch.cuda.mem_get_info()
    used = total - free
    print(f"* VRAM used: {used / 1024**3:.2f} GB")

# default: Load the model on the available device(s)
# model = Qwen3VLForConditionalGeneration.from_pretrained(
#     "Qwen/Qwen3-VL-2B-Instruct", dtype="auto", device_map="auto"
# )

# We recommend enabling flash_attention_2 for better acceleration and memory saving, especially in multi-image and video scenarios.
model = Qwen3VLForConditionalGeneration.from_pretrained(
    MODEL,
    dtype=torch.bfloat16,
    # dtype="auto",
    attn_implementation="flash_attention_2",
    device_map="auto",
)

device_name = torch.cuda.get_device_name(torch.cuda.current_device())

print('')
print(f'* Time: {datetime.now().isoformat()}')
print(f'* Video: {VIDEO_PATH}')
print(f'* Model: {MODEL}')
print(f'* Device: {device_name}')
show_vram()

print(f'\nPROMPT:\n\n{PROMPT}\n')

processor = AutoProcessor.from_pretrained(MODEL)

messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "video",
                "video": VIDEO_PATH,
            },
            {"type": "text", "text": PROMPT},
        ],
    }
]

if 1:
    # from HF model card

    # Preparation for inference
    inputs = processor.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt"
    )
    inputs = inputs.to(model.device)

    # Inference: Generation of the output
    generated_ids = model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS)
    generated_ids_trimmed = [
        out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    output_text = processor.batch_decode(
        generated_ids_trimmed, 
        skip_special_tokens=True, 
        clean_up_tokenization_spaces=False
    )
else:
    # This code is much slower to load than the alternative above and often goes OOM after
    # https://github.com/QwenLM/Qwen3-VL/blob/main/cookbooks/video_understanding.ipynb
    text = processor.apply_chat_template(
        messages, 
        tokenize=False, 
        add_generation_prompt=True
    )
    image_inputs, video_inputs, video_kwargs = process_vision_info(
        [messages], 
        return_video_kwargs=True, 
        # image_patch_size=processor.image_processor.patch_size,
        image_patch_size= 16,
        return_video_metadata=True
    )
    if video_inputs is not None:
        video_inputs, video_metadatas = zip(*video_inputs)
        video_inputs, video_metadatas = list(video_inputs), list(video_metadatas)
    else:
        video_metadatas = None

    inputs = processor(
        text=[text], 
        images=image_inputs, 
        videos=video_inputs, 
        video_metadata=video_metadatas, 
        **video_kwargs, 
        do_resize=False, 
        return_tensors="pt"
    )
    inputs = inputs.to('cuda')

    output_ids = model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS)
    generated_ids = [output_ids[len(input_ids):] for input_ids, output_ids in zip(inputs.input_ids, output_ids)]
    output_text = processor.batch_decode(generated_ids, skip_special_tokens=True, clean_up_tokenization_spaces=True)

print(f'\nANSWER:\n')
print(output_text[0])
print('\n')

show_vram()

print('\n')
print('-' * 3)
print('\n')

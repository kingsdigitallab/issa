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

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
# MAX_NEW_TOKENS = 128
MAX_NEW_TOKENS = 1000
PROMPT = '''How long is this video and what are the topics covered?'''
# original:
PROMPT = '''The video is a broadcast television recording. Analyse the video. First, identify from the text in the title plate(s), ident(s), or transmission card(s), how many programmes are in this recording, and any relevant metadata about the programmes, including network, name, channel, and transmission date if available. Then break down each programme into meaningful segments, for example, if it is a news programme identify each of the news stories. Output an index of the segments with a timestamp and a detailed summary of each segment, focusing on subjects, places and actions, and including any relevant information from the visuals, sound, text or speech. Return this index as a valid JSON array.'''
PROMPT = '''The video is a broadcast television recording. List all the separate programmes. If a programme contains multiple news stories, list the stories as well. For each item in the list provide the timecode and one short sentence summary.'''
PROMPT = '''Transcribe what is being said in the video.'''
PROMPT = '''The video is a broadcast television recording. Spot the visual separation between programmes, like a clock, a countdown, a blank screen or a title screen. List all the programmes, with their starting time and any text visible on the visual separation preceding the programme.'''
# PROMPT = '''Transcribe all that is being said in this video; ignore the images.'''
VIDEO_PATH = "v-10.mp4"
# MODEL = "Qwen/Qwen3-VL-4B-Instruct"
MODEL = "Qwen/Qwen3-VL-8B-Instruct"

def show_vram():
    free, total = torch.cuda.mem_get_info()
    used = total - free
    print(f"VRAM used: {used / 1024**3:.2f} GB")

# default: Load the model on the available device(s)
# model = Qwen3VLForConditionalGeneration.from_pretrained(
#     "Qwen/Qwen3-VL-2B-Instruct", dtype="auto", device_map="auto"
# )

# We recommend enabling flash_attention_2 for better acceleration and memory saving, especially in multi-image and video scenarios.
model = Qwen3VLForConditionalGeneration.from_pretrained(
    MODEL,
    dtype=torch.bfloat16,
    attn_implementation="flash_attention_2",
    device_map="auto",
)

show_vram()

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

print(PROMPT)

if 0:
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
    # https://github.com/QwenLM/Qwen3-VL/blob/main/cookbooks/video_understanding.ipynb
    text = processor.apply_chat_template(
        messages, 
        tokenize=False, 
        add_generation_prompt=True
    )
    image_inputs, video_inputs, video_kwargs = process_vision_info([messages], return_video_kwargs=True, 
                                                                   image_patch_size= 16,
                                                                   return_video_metadata=True)
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

print(output_text[0])

show_vram()

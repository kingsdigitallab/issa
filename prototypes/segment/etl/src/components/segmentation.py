import json
import os
from pathlib import Path

import torch
from tqdm import tqdm
from transformers import AutoModelForCausalLM, AutoProcessor

from . import utils

PROMPT_SMALL = {
    "role": "system",
    "content": [
        {
            "type": "text",
            "text": """
You are an expert broadcast segmentation system. Your input is a JSON sequence of frame
captions and audio transcriptions from a broadcast television recording. Each item in
the sequence has a `timestamp`, `caption` and `transcription`.

Your task is to analyze this sequence and output a valid JSON array of all meaningful
segments.

1.  A new segment is defined by a significant change in topic, location, or speakers.
2.  Group consecutive commercials into a single "Commercial Break" segment.
3.  For each segment, generate a concise one-sentence description and a 1-2 word topic.

Output your response as a valid JSON array. Each object in the array **must** follow
this exact structure:

{
  "start": "Timestamp of the segment's start (e.g., 00:01:23)",
  "end": "Timestamp of the segment's end (e.g., 00:04:10)",
  "category": "A general category (e.g., regional-news, national-news, weather, sports,
  commercial-break, show-intro, show-content)",
  "description": "A 1-2 sentence summary of this segment, focusing on the main subject
  and action.",
  "topic": "A 1-2 word topic in lowercase (e.g., politics, transportation, health)"
}

CRITICAL: Your entire output must be *only* the valid JSON array, starting with `[` and
ending with `]`. Do not write any other text, explanation, or greeting.
""",
        }
    ],
}


def generate_segments(
    video_path: str,
    input_folder: str,
    model_name: str,
    prompt_path: str,
    output_folder: str,
):
    """
    Generate semantic segments for a video using frame captions and audio transcription.

    Args:
        video_path (str): Path to the input video file.
        input_folder (str): Path to the input folder containing captions and audio data.
        model_name (str): Name of the model to use for segment generation.
        prompt_path (str): Path to the prompt file.
        output_folder (str): Path to the output folder where segments will be saved.
    """
    video_name = Path(video_path).name
    captions_path = Path(input_folder) / video_name / "captions.json"
    transcription_path = Path(input_folder) / video_name / "transcription.json"
    output_path = utils.create_output_path(video_path, output_folder)

    with open(captions_path, "r") as f:
        captions = json.load(f)
    with open(transcription_path, "r") as f:
        transcriptions = json.load(f)
    with open(prompt_path, "r") as f:
        system_prompt = f.read()

    aligned_data = align_captions_with_transcription(captions, transcriptions)

    messages = [
        {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
        {
            "role": "user",
            "content": [{"type": "text", "text": aligned_data}],
        },
    ]

    prompt_filepath = os.path.join(output_path, "prompt.json")
    with open(prompt_filepath, "w") as f:
        json.dump(messages, f, indent=4)

    print(f"Prompt saved to {prompt_filepath}")

    device = utils.get_torch_device()

    model = AutoModelForCausalLM.from_pretrained(model_name)
    model.to(device)
    model.eval()

    processor = AutoProcessor.from_pretrained(model_name, use_fast=True)

    print(f"Model {model_name} loaded")

    inputs = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    ).to(device)
    input_len = inputs["input_ids"].shape[-1]

    with torch.inference_mode():
        generation = model.generate(**inputs, max_new_tokens=4096, do_sample=False)
        generation = generation[0][input_len:]

    decoded = processor.decode(generation, skip_special_tokens=True)

    output_filepath = os.path.join(output_path, "segments.txt")
    with open(output_filepath, "w") as f:
        f.write(decoded)

    response_json = json.loads(
        decoded.replace("```json", "").replace("```", "").strip()
    )

    output_filepath = os.path.join(output_path, "segments.json")
    with open(output_filepath, "w") as f:
        json.dump(response_json, f, indent=4)

    print(f"Segments saved to {output_filepath}")


def align_captions_with_transcription(captions: list, transcriptions: dict) -> list:
    """
    Align frame captions with audio transcription segments.

    Args:
        captions (list): List of caption dictionaries with 'timestamp' and 'caption' keys.
        transcriptions (dict): Transcription dictionary with 'segments' list containing
                              'start', 'end', and 'text' keys.

    Returns:
        list: List of aligned data dictionaries with 'timestamp', 'caption', and
              'transcription' keys.
    """
    aligned_data = []

    for caption in tqdm(captions, desc="Aligning captions with audio transcription"):
        timestamp = caption["timestamp"]
        transcription = []

        segments = filter(
            lambda x: x["start"] <= timestamp < x["end"], transcriptions["segments"]
        )

        for segment in segments:
            transcription.append(segment["text"])

        aligned_data.append(
            {
                "timestamp": timestamp,
                "caption": caption["caption"],
                "transcription": " ".join(transcription),
            }
        )

    return aligned_data

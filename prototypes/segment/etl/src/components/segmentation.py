import json
import os
from pathlib import Path

import torch

from . import utils


def generate_segments(
    video_path: str,
    input_folder: str,
    model_name: str,
    prompt_folder: str,
    prompt_only: bool,
    output_folder: str,
):
    """
    Generate semantic segments for a video using frame captions and audio transcription.

    Args:
        video_path (str): Path to the input video file.
        input_folder (str): Path to the input folder containing captions and audio data.
        model_name (str): Name of the model to use for segment generation.
        prompt_folder (str): Path to the folder containing system prompt files.
        prompt_only (bool): Whether to generate only the prompt without generating segments.
        output_folder (str): Path to the output folder where segments will be saved.
    """
    video_name = Path(video_path).name
    aligned_data_path = Path(input_folder) / video_name / "aligned_data.json"
    segmentation_prompt = Path(prompt_folder) / "segmentation.md"
    output_path = utils.create_output_path(video_path, output_folder)

    with open(aligned_data_path, "r") as f:
        aligned_data = json.load(f)
    with open(segmentation_prompt, "r") as f:
        system_prompt = f.read()

    messages = [
        {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
        {
            "role": "user",
            "content": [{"type": "text", "text": aligned_data}],
        },
    ]

    prompt_filepath = os.path.join(output_path, "segmentation_prompt.json")
    with open(prompt_filepath, "w") as f:
        json.dump(messages, f, indent=4)

    print(f"Prompt saved to {prompt_filepath}")

    if prompt_only:
        return

    model, processor, device = utils.get_llm_model(model_name)

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

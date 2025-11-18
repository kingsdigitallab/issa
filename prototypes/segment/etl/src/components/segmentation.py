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

    print("Detecting boundaries...")
    detect_boundaries(aligned_data, model_name, prompt_folder, output_path)

    return

    messages = [
        {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
        {
            "role": "user",
            "content": [{"type": "text", "text": aligned_data[:5]}],
        },
    ]

    prompt_filepath = os.path.join(output_path, "segmentation_prompt.json")
    with open(prompt_filepath, "w") as f:
        json.dump(messages, f, indent=4)

    print(f"Prompt saved to {prompt_filepath}")

    if prompt_only:
        return

    model, processor, device = utils.get_llm_model(model_name)

    decoded = utils.generate_text_from_messages(model, processor, device, messages)

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


def detect_boundaries(segments, model_name, prompt_folder, output_path):
    """
    Detects boundaries between segments using a language model.

    Args:
        segments (list): A list of segment dictionaries.
        model_name (str): The name of the model to use.
        prompt_folder (str): The path to the folder containing the prompt file.
        output_path (str): The path to save the output file.
    """
    boundary_detection_prompt_path = Path(prompt_folder) / "boundary_detection.md"
    with open(boundary_detection_prompt_path, "r") as f:
        system_prompt = f.read()

    model, processor, device = utils.get_llm_model(model_name)

    boundaries = []
    for i in range(len(segments) - 1):
        current_segment = segments[i]
        next_segment = segments[i + 1]

        user_content = (
            f"Current:\n{json.dumps(current_segment, indent=2)}\n\n"
            f"Next:\n{json.dumps(next_segment, indent=2)}"
        )

        messages = [
            {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
            {"role": "user", "content": [{"type": "text", "text": user_content}]},
        ]

        response = utils.generate_text_from_messages(model, processor, device, messages)

        is_boundary = "YES" in response.upper()
        boundaries.append(is_boundary)
        print(f"Comparison {i + 1}/{len(segments) - 1}: Is boundary? {is_boundary}")

    # The first segment is always a boundary.
    # The last segment comparison is not possible, so we have one less boundary result.
    final_boundaries = [True] + boundaries

    for i, segment in enumerate(segments):
        if i < len(final_boundaries):
            segment["is_boundary"] = final_boundaries[i]
        else:
            segment["is_boundary"] = False

    output_filepath = os.path.join(output_path, "segments_with_boundaries.json")
    with open(output_filepath, "w") as f:
        json.dump(segments, f, indent=4)

    print(f"Segments with boundaries saved to {output_filepath}")

    return segments

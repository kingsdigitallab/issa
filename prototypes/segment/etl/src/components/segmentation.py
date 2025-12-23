import json
import os
from pathlib import Path

from tqdm import tqdm

from . import utils


def detect_boundaries(
    video_path: str,
    input_folder: str,
    model_name: str,
    prompt_folder: str,
    output_folder: str,
):
    """
    Detects boundaries between segments using a language model.

    Args:
    video_path (str): Path to the input video file.
    input_folder (str): Path to the input folder containing aligned_data.json.
    model_name (str): Name of the model to use for boundary detection.
    prompt_folder (str): Path to the folder containing system prompt files.
    output_folder (str): Path to the output folder where segments will be saved.
    """
    video_name = Path(video_path).name
    aligned_data_path = Path(input_folder) / video_name / "aligned_data.json"
    boundary_detection_prompt_path = Path(prompt_folder) / "boundary_detection.md"
    output_path = utils.create_output_path(video_path, output_folder)

    with open(aligned_data_path, "r") as f:
        segments = json.load(f)
    with open(boundary_detection_prompt_path, "r") as f:
        system_prompt = f.read()

    model, processor, device = utils.get_llm_model(model_name)

    full_prompt = system_prompt

    boundaries = []
    for i in tqdm(range(len(segments) - 1), desc="Detecting boundaries"):
        previous_segment = segments[i - 1] if i > 0 else segments[i]
        current_segment = segments[i]
        next_segment = segments[i + 1]

        user_content = (
            "[Previous Frame Context (T-1)]\n"
            f"{json.dumps(previous_segment, indent=2)}\n\n"
            "[Current Frame Context (T)]\n"
            f"{json.dumps(current_segment, indent=2)}\n\n"
            "[Next Frame Context (T+1)]\n"
            f"{json.dumps(next_segment, indent=2)}"
        )

        full_prompt += "\n\n" + user_content

        messages = [
            {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
            {"role": "user", "content": [{"type": "text", "text": user_content}]},
        ]

        response = utils.generate_text_from_messages(model, processor, device, messages)

        is_boundary = "YES" in response.upper()
        boundaries.append(is_boundary)

    final_boundaries = [True] + boundaries

    for i, segment in tqdm(
        enumerate(segments), desc="Updating segments with boundary information"
    ):
        if i < len(final_boundaries):
            segment["is_boundary"] = final_boundaries[i]
        else:
            segment["is_boundary"] = False

    output_filepath = os.path.join(output_path, "boundaries_prompt.txt")
    with open(output_filepath, "w") as f:
        f.write(full_prompt)

    output_filepath = os.path.join(output_path, "boundaries.json")
    with open(output_filepath, "w") as f:
        json.dump(segments, f, indent=4)

    print(f"Segments with boundaries saved to {output_filepath}")

    return segments


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


def merge_segments(
    video_path: str,
    input_folder: str,
    output_folder: str,
):
    """
    Merges segments based on boundary detection data.

    Args:
        video_path (str): Path to the input video file.
        input_folder (str): Path to the folder containing boundaries.json.
        output_folder (str): Path to the output folder where merged_segments.json will be saved.
    """
    video_name = Path(video_path).name
    boundaries_path = Path(input_folder) / video_name / "boundaries.json"
    output_path = utils.create_output_path(video_path, output_folder)

    with open(boundaries_path, "r") as f:
        segments = json.load(f)

    if not segments:
        print("No segments found to merge.")
        return

    boundary_indices = [i for i, seg in enumerate(segments) if seg.get("is_boundary")]

    if not boundary_indices:
        print("No boundaries found in segments.")
        return

    merged_segments = []
    for i in tqdm(range(len(boundary_indices)), desc="Merging segments"):
        start_index = boundary_indices[i]

        segment_group = []
        end_timestamp = 0.0

        if i + 1 < len(boundary_indices):
            end_index = boundary_indices[i + 1]
            segment_group = segments[start_index:end_index]
            end_timestamp = segments[end_index]["timestamp"]
        else:
            segment_group = segments[start_index:]
            end_timestamp = segments[-1]["timestamp"]

        if not segment_group:
            continue

        start_timestamp = segment_group[0]["timestamp"]
        captions = [s["caption"] for s in segment_group if "caption" in s]
        transcriptions = [
            s["transcription"] for s in segment_group if "transcription" in s
        ]

        merged_segments.append(
            {
                "start_timestamp": start_timestamp,
                "end_timestamp": end_timestamp,
                "captions": captions,
                "transcriptions": list(dict.fromkeys(transcriptions)),
            }
        )

    output_filepath = os.path.join(output_path, "merged_segments.json")
    with open(output_filepath, "w") as f:
        json.dump(merged_segments, f, indent=4)

    print(f"Merged segments saved to {output_filepath}")


def summarise_segments(
    video_path: str,
    input_folder: str,
    model_name: str,
    caption_chunk_size: int,
    prompt_folder: str,
    output_folder: str,
):
    """
    Generates summaries for each merged segment using an LLM.

    Args:
        video_path (str): Path to the input video file.
        input_folder (str): Path to the folder containing merged_segments.json.
        model_name (str): Name of the model to use for summarisation.
        caption_chunk_size (int): Number of captions to include in each chunk.
        prompt_folder (str): Path to the folder containing the summarisation prompt.
        output_folder (str): Path to the output folder where summaries.json will be saved.
    """
    video_name = Path(video_path).name
    merged_segments_path = Path(input_folder) / video_name / "merged_segments.json"
    summarisation_prompt_path = Path(prompt_folder) / "summarisation.md"
    output_path = utils.create_output_path(video_path, output_folder)

    with open(merged_segments_path, "r") as f:
        merged_segments = json.load(f)

    with open(summarisation_prompt_path, "r") as f:
        system_prompt = f.read()

    model, processor, device = utils.get_llm_model(model_name)

    for segment in tqdm(merged_segments, desc="Summarising segments"):
        captions = segment.get("captions", [])

        if len(captions) > caption_chunk_size:
            caption_summaries = []
            for i in range(0, len(captions), caption_chunk_size):
                chunk = captions[i : i + caption_chunk_size]
                chunk_payload = {"captions": chunk, "transcriptions": []}

                messages = [
                    {
                        "role": "system",
                        "content": [{"type": "text", "text": system_prompt}],
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": json.dumps(chunk_payload)}
                        ],
                    },
                ]
                chunk_summary = utils.generate_text_from_messages(
                    model, processor, device, messages
                )
                caption_summaries.append(chunk_summary)

            segment["captions"] = caption_summaries

        user_content = json.dumps(segment)
        messages = [
            {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
            {"role": "user", "content": [{"type": "text", "text": user_content}]},
        ]

        summary = utils.generate_text_from_messages(model, processor, device, messages)
        segment["summary"] = summary

    output_filepath = os.path.join(output_path, "summaries.json")
    with open(output_filepath, "w") as f:
        json.dump(merged_segments, f, indent=4)

    print(f"Segments with summaries saved to {output_filepath}")


def classify_segments(
    video_path: str,
    input_folder: str,
    model_name: str,
    prompt_folder: str,
    output_folder: str,
):
    """
    Classify summaries for each merged segment using an LLM.

    Args:
        video_path (str): Path to the input video file.
        input_folder (str): Path to the folder containing merged_segments.json.
        model_name (str): Name of the model to use for classification.
        prompt_folder (str): Path to the folder containing the classification prompt.
        output_folder (str): Path to the output folder where summaries.json will be saved.
    """
    video_name = Path(video_path).name
    merged_segments_path = Path(input_folder) / video_name / "summaries.json"
    classification_prompt_path = Path(prompt_folder) / "classification.md"
    output_path = utils.create_output_path(video_path, output_folder)

    with open(merged_segments_path, "r") as f:
        merged_segments = json.load(f)

    with open(classification_prompt_path, "r") as f:
        system_prompt = f.read()

    model, processor, device = utils.get_llm_model(model_name)

    for segment in tqdm(merged_segments, desc="Classifying segments"):
        user_content = json.dumps(segment)
        messages = [
            {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
            {"role": "user", "content": [{"type": "text", "text": user_content}]},
        ]

        generated = utils.generate_text_from_messages(
            model, processor, device, messages
        )
        classification = json.loads(generated.replace("```json", "").replace("```", ""))

        segment["topic"] = classification["topic"]
        segment["channel"] = classification["channel"]
        segment["program_name"] = classification["program_name"]
        segment["transmission_date"] = classification["transmission_date"]

    output_filepath = os.path.join(output_path, "classifications.json")
    with open(output_filepath, "w") as f:
        json.dump(merged_segments, f, indent=4)

    print(f"Segments with classification saved to {output_filepath}")

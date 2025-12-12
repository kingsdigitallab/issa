import json
import time
from pathlib import Path

from tqdm import tqdm

from . import metadata, utils


def align(
    video_path: str,
    input_folder: str,
    merge_duplicates: bool,
    output_folder: str,
):
    """
    Aligns frame captions with audio transcription and saves the result.

    Args:
        video_path (str): Path to the input video file.
        input_folder (str): Path to the folder containing captions.json and transcription.json.
        merge_duplicates (bool): Whether to merge duplicate transcriptions.
        output_folder (str): Path to the folder where aligned_data.json will be saved.
    """
    start_time = time.time()

    video_name = Path(video_path).name
    captions_path = Path(input_folder) / video_name / "captions.json"
    transcription_path = Path(input_folder) / video_name / "transcription.json"
    output_path = utils.create_output_path(video_path, output_folder)

    with open(captions_path, "r") as f:
        captions_file = json.load(f)
    with open(transcription_path, "r") as f:
        transcriptions_file = json.load(f)

    captions = captions_file.get("data", captions_file)
    transcriptions = transcriptions_file.get("data", transcriptions_file)

    aligned_data = align_captions_with_transcription(
        captions, transcriptions, merge_duplicates
    )

    processing_time = time.time() - start_time

    output = {
        "_meta": metadata.create_metadata(
            component="aligning",
            input_file=video_path,
            items_processed=len(aligned_data),
            processing_time_seconds=processing_time,
            parameters={"merge_duplicate_transcriptions": merge_duplicates},
        ),
        "data": aligned_data,
    }

    output_filepath = Path(output_path) / "aligned_data.json"
    with open(output_filepath, "w") as f:
        json.dump(output, f, indent=4)

    print(f"Aligned data saved to {output_filepath}")


def align_captions_with_transcription(
    captions: list, transcriptions: dict, merge_duplicates: bool
) -> list:
    """
    Align frame captions with audio transcription segments.

    Args:
        captions (list): List of caption dictionaries with 'timestamp' and 'caption' keys.
        transcriptions (dict): Transcription dictionary with 'segments' list containing
                              'start', 'end', and 'text' keys.
        merge_duplicates (bool): Whether to merge duplicate transcriptions.

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
            transcription.append(segment["text"].strip())

        aligned_data.append(
            {
                "timestamp": timestamp,
                "caption": caption["caption"],
                "transcription": " ".join(transcription),
            }
        )

    if merge_duplicates:
        aligned_data = merge_duplicate_transcriptions(aligned_data)

    return aligned_data


def merge_duplicate_transcriptions(aligned_data: list) -> list:
    """
    Merge duplicate transcriptions in aligned data.

    Args:
        aligned_data (list): List of aligned data dictionaries with 'timestamp', 'caption', and
                             'transcription' keys.

    Returns:
        list: List of merged aligned data dictionaries.
    """
    merged_data = []

    for data in aligned_data:
        if merged_data and data["transcription"] == merged_data[-1]["transcription"]:
            merged_data[-1]["caption"].append(data["caption"])
        else:
            merged_data.append(
                {
                    "timestamp": data["timestamp"],
                    "caption": [data["caption"]],
                    "transcription": data["transcription"],
                }
            )

    return merged_data

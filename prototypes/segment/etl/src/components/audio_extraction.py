import json
import os
import time

import whisper

from . import metadata, utils


def extract_audio(
    video_path: str,
    language: str = "en",
    model_size: str = "small",
    output_folder: str = "../data/1_interim",
):
    """
    Extract audio using Whisper from a video and save it into a folder.

    Args:
        video_path (str): Path to the input video.
        language (str): The language of the audio. Default is "en".
        model_size (str): The size of the Whisper model to use. Default is "small".
        output_folder (str): Path to the output folder where the audion will be saved. Default is "../data/1_interim".
    """
    start_time = time.time()

    output_path = utils.create_output_path(video_path, output_folder)

    print(f"Extracting audio from {video_path} and saving to {output_folder}...")

    device = utils.get_torch_device()
    is_fp16 = device not in ["mps", "cpu"]

    model = whisper.load_model(model_size, device=device)
    result = model.transcribe(video_path, fp16=is_fp16, language=language, verbose=True)

    processing_time = time.time() - start_time

    output = {
        "_meta": metadata.create_metadata(
            component="audio_extraction",
            input_file=video_path,
            items_processed=len(result.get("segments", [])),
            processing_time_seconds=processing_time,
            parameters={"language": language},
            model_name=f"whisper-{model_size}",
            backend="local",
            device=device,
        ),
        "data": result,
    }

    with open(os.path.join(output_path, "transcription.json"), "w") as f:
        json.dump(output, f, indent=4)

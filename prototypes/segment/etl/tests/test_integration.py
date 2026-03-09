import json
import os
from unittest.mock import MagicMock

import cv2
from typer.testing import CliRunner

from components import (
    aligning,
    audio_extraction,
    frame_captioning,
    segmentation,
)

runner = CliRunner()


def test_full_pipeline_integration(tmp_path, mocker):
    """
    Test the full data flow of the ETL pipeline by running every step sequentially
    with aggressively mocked models and file handlers.
    """
    # 1. Setup directories and dummy inputs
    video_path = str(tmp_path / "dummy_integration.mp4")
    (tmp_path / "dummy_integration.mp4").touch()

    interim_folder = str(tmp_path / "data" / "1_interim")
    final_folder = str(tmp_path / "data" / "2_final")
    prompt_folder = str(tmp_path / "data" / "0_prompts")

    os.makedirs(interim_folder, exist_ok=True)
    os.makedirs(final_folder, exist_ok=True)
    os.makedirs(prompt_folder, exist_ok=True)

    # Create dummy prompt files
    for prompt_name in [
        "boundary_detection.md",
        "segmentation.md",
        "summarisation.md",
        "classification.md",
    ]:
        with open(os.path.join(prompt_folder, prompt_name), "w") as f:
            f.write(f"Dummy {prompt_name}")

    # --- Mocks ---

    # 1. frame_extraction mocks
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True

    def mock_get(prop_id):
        if prop_id == cv2.CAP_PROP_FPS:
            return 30.0
        if prop_id == cv2.CAP_PROP_FRAME_COUNT:
            return 60  # 2 seconds
        return 0

    mock_cap.get.side_effect = mock_get
    mock_cap.read.side_effect = [
        (True, "fake_frame"),
        (True, "fake_frame"),
        (False, None),
    ]
    mocker.patch("cv2.VideoCapture", return_value=mock_cap)
    mocker.patch("cv2.imwrite")

    # Create the fake extracted frames manually on disk for the next step to find them
    frames_dir = tmp_path / "data" / "1_interim" / "dummy_integration.mp4" / "frames"
    frames_dir.mkdir(parents=True)
    (frames_dir / "frame_0000_0.00.png").touch()
    (frames_dir / "frame_0030_1.00.png").touch()

    # 2. audio_extraction mocks
    mock_whisper = MagicMock()
    mock_whisper.transcribe.return_value = {
        "text": "Hello world. Goodbye.",
        "segments": [
            {"start": 0.0, "end": 1.0, "text": "Hello world."},
            {"start": 1.0, "end": 2.0, "text": " Goodbye."},
        ],
    }
    mocker.patch("whisper.load_model", return_value=mock_whisper)
    mocker.patch("components.utils.get_torch_device", return_value="cpu")

    # 3. frame_captioning mocks
    mocker.patch(
        "components.utils.get_model_client", return_value=("model", "processor", "cpu")
    )
    mocker.patch(
        "components.utils.generate_caption", side_effect=["Caption 1", "Caption 2"]
    )

    # 4. segmentation models mock (for detect_boundaries, summarise, classify)
    mocker.patch(
        "components.utils.generate_text_from_messages",
        side_effect=[
            # detect_boundaries (2 frames minus 1 = 1 call)
            "YES",
            # summarise_segments (2 segments = 2 calls)
            "Summary of seg 1",
            "Summary of seg 2",
            # classify_segments (2 summaries = 2 calls)
            json.dumps(
                {
                    "topic": "T1",
                    "channel": "C1",
                    "program_name": "P1",
                    "transmission_date": "D1",
                }
            ),
            json.dumps(
                {
                    "topic": "T2",
                    "channel": "C2",
                    "program_name": "P2",
                    "transmission_date": "D2",
                }
            ),
        ],
    )

    # --- Execute Pipeline sequentially ---

    print("Running audio_extraction...")
    audio_extraction.extract_audio(video_path, output_folder=interim_folder)

    print("Running frame_captioning...")
    frame_captioning.caption_frames(video_path, "mock1", True, interim_folder)

    print("Running aligning...")
    aligning.align(video_path, interim_folder, True, interim_folder)

    print("Running detect_boundaries...")
    segmentation.detect_boundaries(
        video_path, interim_folder, "mock2", prompt_folder, final_folder
    )

    print("Running merge_segments...")
    segmentation.merge_segments(video_path, final_folder, final_folder)

    print("Running summarise_segments...")
    segmentation.summarise_segments(
        video_path, final_folder, "mock3", 25, prompt_folder, final_folder
    )

    print("Running classify_segments...")
    segmentation.classify_segments(
        video_path, final_folder, "mock4", prompt_folder, final_folder
    )

    # --- Assertions ---

    # 1. Did we write all interim outputs?
    interim_out_dir = tmp_path / "data" / "1_interim" / "dummy_integration.mp4"
    assert (interim_out_dir / "transcription.json").exists()
    assert (interim_out_dir / "captions.json").exists()
    assert (interim_out_dir / "aligned_data.json").exists()

    # 2. Did we write all final outputs?
    final_out_dir = tmp_path / "data" / "2_final" / "dummy_integration.mp4"
    assert (final_out_dir / "boundaries.json").exists()
    assert (final_out_dir / "merged_segments.json").exists()
    assert (final_out_dir / "summaries.json").exists()
    assert (final_out_dir / "classifications.json").exists()

    # 3. Quick sanity check on final classifications shape
    with open(final_out_dir / "classifications.json", "r") as f:
        class_data = json.load(f)["data"]

    assert len(class_data) == 2
    assert class_data[0]["summary"] == "Summary of seg 1"
    assert class_data[0]["topic"] == "T1"
    assert class_data[1]["summary"] == "Summary of seg 2"
    assert class_data[1]["channel"] == "C2"

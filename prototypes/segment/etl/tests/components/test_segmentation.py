import json
import os
import shutil
from pathlib import Path

import pytest

from components import segmentation


@pytest.fixture
def fixtures_dir():
    return Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def setup_segmentation_environment(tmp_path, fixtures_dir):
    """Sets up a temporary directory structure mimicking the real ETL inputs."""
    video_path = tmp_path / "dummy_video.mp4"
    video_path.touch()

    input_folder = tmp_path / "input"
    output_folder = tmp_path / "output"
    video_input_dir = input_folder / "dummy_video.mp4"
    video_input_dir.mkdir(parents=True)

    # Copy fixtures
    shutil.copy(
        fixtures_dir / "aligned_data.json", video_input_dir / "aligned_data.json"
    )
    shutil.copy(fixtures_dir / "boundaries.json", video_input_dir / "boundaries.json")
    shutil.copy(
        fixtures_dir / "merged_segments.json", video_input_dir / "merged_segments.json"
    )

    # Prompts folder
    prompt_folder = fixtures_dir / "prompts"

    return {
        "video_path": str(video_path),
        "input_folder": str(input_folder),
        "output_folder": str(output_folder),
        "prompt_folder": str(prompt_folder),
        "video_output_dir": output_folder / "dummy_video.mp4",
    }


def test_detect_boundaries(mocker, setup_segmentation_environment):
    env = setup_segmentation_environment

    # Mock get_model_client and generate_text_from_messages
    mocker.patch(
        "components.utils.get_model_client",
        return_value=("mock_model", "mock_processor", "mock_device"),
    )
    mock_generate = mocker.patch(
        "components.utils.generate_text_from_messages",
        side_effect=["YES", "NO", "YES", "NO"],
    )

    result_segments = segmentation.detect_boundaries(
        video_path=env["video_path"],
        input_folder=env["input_folder"],
        model_name="mock-model",
        prompt_folder=env["prompt_folder"],
        output_folder=env["output_folder"],
        backend="local",
    )

    assert mock_generate.call_count == 4
    assert len(result_segments) == 5

    # Check first is always True
    assert result_segments[0]["is_boundary"] is True
    # Check side effects mapped to segments
    assert result_segments[1]["is_boundary"] is True  # "YES"
    assert result_segments[2]["is_boundary"] is False  # "NO"
    assert result_segments[3]["is_boundary"] is True  # "YES"
    assert result_segments[4]["is_boundary"] is False  # "NO"

    assert (env["video_output_dir"] / "boundaries.json").exists()


def test_merge_segments(setup_segmentation_environment):
    env = setup_segmentation_environment

    # Run merge_segments, which should read from boundaries.json and output merged_segments.json
    segmentation.merge_segments(
        video_path=env["video_path"],
        input_folder=env["input_folder"],
        output_folder=env["output_folder"],
    )

    output_path = env["video_output_dir"] / "merged_segments.json"
    assert output_path.exists()

    with open(output_path, "r") as f:
        merged_file = json.load(f)

    data = merged_file["data"]
    # Looking at boundaries.json dummy fixture, boundaries are at index 0, 2, 4
    # This means segments should be grouped: [0, 1], [2, 3], [4]
    assert len(data) == 3

    assert data[0]["start_timestamp"] == 0.0
    assert data[0]["end_timestamp"] == 4.0
    assert len(data[0]["captions"]) == 2

    assert data[1]["start_timestamp"] == 4.0
    assert data[1]["end_timestamp"] == 8.0

    assert data[2]["start_timestamp"] == 8.0
    assert data[2]["end_timestamp"] == 8.0


def test_summarise_segments(mocker, setup_segmentation_environment):
    env = setup_segmentation_environment

    mocker.patch(
        "components.utils.get_model_client",
        return_value=("mock_model", "mock_processor", "mock_device"),
    )
    # The merged_segments has 3 segments. We will mock the summary return values.
    # No chunking occurs since caption_chunk_size is larger than our dummy captions lengths
    mock_generate = mocker.patch(
        "components.utils.generate_text_from_messages",
        side_effect=["Summary 1", "Summary 2", "Summary 3"],
    )

    segmentation.summarise_segments(
        video_path=env["video_path"],
        input_folder=env["input_folder"],
        model_name="mock-model",
        caption_chunk_size=10,
        prompt_folder=env["prompt_folder"],
        output_folder=env["output_folder"],
    )

    assert mock_generate.call_count == 3

    output_path = env["video_output_dir"] / "summaries.json"
    assert output_path.exists()

    with open(output_path, "r") as f:
        result = json.load(f)["data"]

    assert len(result) == 3
    assert result[0]["summary"] == "Summary 1"
    assert result[1]["summary"] == "Summary 2"
    assert result[2]["summary"] == "Summary 3"


def test_classify_segments(mocker, setup_segmentation_environment):
    env = setup_segmentation_environment
    # We need to test classification. It reads summaries.json, so we need a dummy file.
    # We can write one quickly.
    summaries_data = {
        "data": [
            {"summary": "Summary 1"},
            {"summary": "Summary 2"},
        ]
    }
    with open(
        Path(env["input_folder"]) / "dummy_video.mp4" / "summaries.json", "w"
    ) as f:
        json.dump(summaries_data, f)

    mocker.patch(
        "components.utils.get_model_client",
        return_value=("mock_model", "mock_processor", "mock_device"),
    )

    class_response = json.dumps(
        {
            "topic": "News",
            "channel": "BBC",
            "program_name": "Evening News",
            "transmission_date": "2024-01-01",
        }
    )

    mock_generate = mocker.patch(
        "components.utils.generate_text_from_messages", return_value=class_response
    )

    segmentation.classify_segments(
        video_path=env["video_path"],
        input_folder=env["input_folder"],
        model_name="mock-model",
        prompt_folder=env["prompt_folder"],
        output_folder=env["output_folder"],
    )

    assert mock_generate.call_count == 2
    output_path = env["video_output_dir"] / "classifications.json"
    assert output_path.exists()


def test_detect_boundaries_malformed_response(mocker, setup_segmentation_environment):
    env = setup_segmentation_environment

    mocker.patch(
        "components.utils.get_model_client",
        return_value=("mock_model", "mock_processor", "mock_device"),
    )
    # LLM might return conversational junk, but we only check for "YES" in response.upper()
    mocker.patch(
        "components.utils.generate_text_from_messages",
        side_effect=[
            "I am sorry, I cannot answer that.",
            "YES",
            "No, this is a continuation",
            "garbage...yes...more garbage",
        ],
    )

    result_segments = segmentation.detect_boundaries(
        video_path=env["video_path"],
        input_folder=env["input_folder"],
        model_name="mock-model",
        prompt_folder=env["prompt_folder"],
        output_folder=env["output_folder"],
        backend="local",
    )

    # The first boundary is always forced to True in the code
    assert result_segments[0]["is_boundary"] is True
    # "I am sorry, I cannot answer that." -> False
    assert result_segments[1]["is_boundary"] is False
    # "YES" -> True
    assert result_segments[2]["is_boundary"] is True
    # "No, this is a continuation" -> False (NO yes in it)
    assert result_segments[3]["is_boundary"] is False
    # "garbage...yes...more garbage" -> True ("YES" is in upper)
    assert result_segments[4]["is_boundary"] is True


def test_merge_segments_empty(tmp_path):
    video_path = str(tmp_path / "dummy_empty.mp4")
    (tmp_path / "dummy_empty.mp4").touch()
    input_folder = str(tmp_path / "in")
    output_folder = str(tmp_path / "out")

    video_input_dir = tmp_path / "in" / "dummy_empty.mp4"
    video_input_dir.mkdir(parents=True)

    with open(video_input_dir / "boundaries.json", "w") as f:
        json.dump({"data": []}, f)

    segmentation.merge_segments(video_path, input_folder, output_folder)

    assert not (tmp_path / "out" / "dummy_empty.mp4" / "merged_segments.json").exists()


def test_merge_segments_no_boundaries(tmp_path):
    video_path = str(tmp_path / "dummy_no_bound.mp4")
    (tmp_path / "dummy_no_bound.mp4").touch()
    input_folder = str(tmp_path / "in")
    output_folder = str(tmp_path / "out")

    video_input_dir = tmp_path / "in" / "dummy_no_bound.mp4"
    video_input_dir.mkdir(parents=True)

    data = [
        {"timestamp": 0.0, "is_boundary": False},
        {"timestamp": 2.0, "is_boundary": False},
    ]
    with open(video_input_dir / "boundaries.json", "w") as f:
        json.dump({"data": data}, f)

    segmentation.merge_segments(video_path, input_folder, output_folder)

    assert not (
        tmp_path / "out" / "dummy_no_bound.mp4" / "merged_segments.json"
    ).exists()


def test_merge_segments_single_boundary_entire_video(tmp_path):
    video_path = str(tmp_path / "dummy_single.mp4")
    (tmp_path / "dummy_single.mp4").touch()
    input_folder = str(tmp_path / "in")
    output_folder = str(tmp_path / "out")

    video_input_dir = tmp_path / "in" / "dummy_single.mp4"
    video_input_dir.mkdir(parents=True)

    data = [
        {"timestamp": 0.0, "caption": "A", "transcription": "B", "is_boundary": True},
        {"timestamp": 2.0, "caption": "C", "transcription": "D", "is_boundary": False},
        {"timestamp": 4.0, "caption": "E", "transcription": "F", "is_boundary": False},
    ]
    with open(video_input_dir / "boundaries.json", "w") as f:
        json.dump({"data": data}, f)

    segmentation.merge_segments(video_path, input_folder, output_folder)

    output_path = tmp_path / "out" / "dummy_single.mp4" / "merged_segments.json"
    assert output_path.exists()

    with open(output_path, "r") as f:
        result = json.load(f)["data"]

    assert len(result) == 1
    assert result[0]["start_timestamp"] == 0.0
    assert result[0]["end_timestamp"] == 4.0
    assert len(result[0]["captions"]) == 3
    assert len(result[0]["transcriptions"]) == 3

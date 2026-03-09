import json
import os

from components import frame_captioning


def test_caption_frames(mocker, tmp_path):
    video_path = str(tmp_path / "dummy.mp4")
    output_folder = str(tmp_path / "out")

    # Mocking frames existence
    frames_path = tmp_path / "out" / "dummy.mp4" / "frames"
    frames_path.mkdir(parents=True)
    (frames_path / "frame_0000_0.00.png").touch()
    (frames_path / "frame_0030_1.00.png").touch()
    (frames_path / "frame_0060_2.00.png").touch()

    mocker.patch(
        "components.utils.get_model_client", return_value=("model", "processor", "cpu")
    )

    # We will generate duplicates to test the duplicate removal logic
    mock_generate = mocker.patch(
        "components.utils.generate_caption",
        side_effect=["Caption A", "Caption B", "Caption B"],
    )

    frame_captioning.caption_frames(
        video_path=video_path,
        model_name="test-model",
        remove_duplicates=True,
        output_folder=output_folder,
    )

    assert mock_generate.call_count == 3

    captions_file = tmp_path / "out" / "dummy.mp4" / "captions.json"
    assert captions_file.exists()

    with open(captions_file, "r") as f:
        data = json.load(f)

    # Since we remove duplicates, "Caption B" should only appear once
    assert len(data["data"]) == 2
    assert data["data"][0]["caption"] == "Caption A"
    assert data["data"][1]["caption"] == "Caption B"


def test_caption_frames_no_frames(mocker, tmp_path, capsys):
    video_path = str(tmp_path / "dummy.mp4")
    output_folder = str(tmp_path / "out")
    frames_path = tmp_path / "out" / "dummy.mp4" / "frames"
    frames_path.mkdir(parents=True)

    frame_captioning.caption_frames(video_path, "model", True, output_folder)

    captured = capsys.readouterr()
    assert "No frames found" in captured.out

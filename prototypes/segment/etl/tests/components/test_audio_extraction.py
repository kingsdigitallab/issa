import json
import os

from components import audio_extraction


def test_extract_audio(mocker, tmp_path):
    video_path = str(tmp_path / "dummy.mp4")
    output_folder = str(tmp_path / "out")

    # Needs to be created by utils.create_output_path
    (tmp_path / "out" / "dummy.mp4").mkdir(parents=True)

    mock_model = mocker.MagicMock()
    mock_model.transcribe.return_value = {
        "text": "Hello world",
        "segments": [{"start": 0.0, "end": 2.0, "text": "Hello world"}],
    }

    mocker.patch("whisper.load_model", return_value=mock_model)
    mocker.patch("components.utils.get_torch_device", return_value="cpu")

    audio_extraction.extract_audio(
        video_path=video_path,
        language="en",
        model_size="small",
        output_folder=output_folder,
    )

    output_file = tmp_path / "out" / "dummy.mp4" / "transcription.json"
    assert output_file.exists()

    with open(output_file, "r") as f:
        data = json.load(f)

    assert data["data"]["text"] == "Hello world"
    assert len(data["data"]["segments"]) == 1
    assert data["_meta"]["component"] == "audio_extraction"

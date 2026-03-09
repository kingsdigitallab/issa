import json

from components import aligning


def test_align(tmp_path):
    video_path = str(tmp_path / "dummy.mp4")
    input_folder = str(tmp_path / "in")
    output_folder = str(tmp_path / "out")

    video_input_dir = tmp_path / "in" / "dummy.mp4"
    video_input_dir.mkdir(parents=True)

    # Mock captions.json
    captions_data = {
        "data": [
            {"timestamp": 0.0, "caption": "Scene 1"},
            {"timestamp": 2.0, "caption": "Scene 2"},
            {"timestamp": 4.0, "caption": "Scene 3"},
        ]
    }
    with open(video_input_dir / "captions.json", "w") as f:
        json.dump(captions_data, f)

    # Mock transcription.json
    transcription_data = {
        "data": {
            "segments": [
                {"start": 0.0, "end": 2.5, "text": "Hello world."},
                {"start": 2.5, "end": 5.0, "text": " Goodbye world."},
            ]
        }
    }
    with open(video_input_dir / "transcription.json", "w") as f:
        json.dump(transcription_data, f)

    aligning.align(
        video_path=video_path,
        input_folder=input_folder,
        merge_duplicates=True,
        output_folder=output_folder,
    )

    aligned_file = tmp_path / "out" / "dummy.mp4" / "aligned_data.json"
    assert aligned_file.exists()

    with open(aligned_file, "r") as f:
        data = json.load(f)

    # 0.0 overlaps with segment 1 -> Hello world.
    # 2.0 overlaps with segment 1 -> Hello world.
    # Because merge_duplicates=True, "Scene 1" and "Scene 2" should be merged
    # 4.0 overlaps with segment 2 -> Goodbye world.

    assert len(data["data"]) == 2
    assert data["data"][0]["transcription"] == "Hello world."
    assert data["data"][0]["caption"] == ["Scene 1", "Scene 2"]

    assert data["data"][1]["transcription"] == "Goodbye world."
    assert data["data"][1]["caption"] == ["Scene 3"]


def test_align_no_merge(tmp_path):
    video_path = str(tmp_path / "dummy.mp4")
    input_folder = str(tmp_path / "in")
    output_folder = str(tmp_path / "out")

    video_input_dir = tmp_path / "in" / "dummy.mp4"
    video_input_dir.mkdir(parents=True)

    captions_data = {
        "data": [
            {"timestamp": 0.0, "caption": "Scene 1"},
            {"timestamp": 2.0, "caption": "Scene 2"},
        ]
    }
    with open(video_input_dir / "captions.json", "w") as f:
        json.dump(captions_data, f)

    transcription_data = {
        "data": {"segments": [{"start": 0.0, "end": 5.0, "text": "Hello."}]}
    }
    with open(video_input_dir / "transcription.json", "w") as f:
        json.dump(transcription_data, f)

    aligning.align(
        video_path=video_path,
        input_folder=input_folder,
        merge_duplicates=False,
        output_folder=output_folder,
    )

    aligned_file = tmp_path / "out" / "dummy.mp4" / "aligned_data.json"
    assert aligned_file.exists()

    with open(aligned_file, "r") as f:
        data = json.load(f)

    assert len(data["data"]) == 2
    assert data["data"][0]["transcription"] == "Hello."
    assert data["data"][0]["caption"] == "Scene 1"
    assert data["data"][1]["transcription"] == "Hello."
    assert data["data"][1]["caption"] == "Scene 2"

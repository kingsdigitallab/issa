import pytest
from typer.testing import CliRunner

from main import app

runner = CliRunner()


def test_extract_frames_command(mocker):
    # Mock the underlying function
    mock_func = mocker.patch("main.frame_extraction.extract_frames")

    result = runner.invoke(
        app,
        [
            "extract-frames",
            "dummy.mp4",
            "--sample-rate",
            "2.0",
            "--output-folder",
            "out",
        ],
    )

    assert result.exit_code == 0
    mock_func.assert_called_once_with("dummy.mp4", 2.0, "out")


def test_extract_audio_command(mocker):
    mock_func = mocker.patch("main.audio_extraction.extract_audio")

    result = runner.invoke(
        app,
        [
            "extract-audio",
            "dummy.mp4",
            "--language",
            "fr",
            "--model-size",
            "base",
            "--output-folder",
            "out",
        ],
    )

    assert result.exit_code == 0
    mock_func.assert_called_once_with("dummy.mp4", "fr", "base", "out")


def test_caption_frames_command(mocker):
    mock_func = mocker.patch("main.frame_captioning.caption_frames")

    result = runner.invoke(
        app,
        [
            "caption-frames",
            "dummy.mp4",
            "--model-name",
            "test-model",
            "--no-remove-duplicates",
            "--output-folder",
            "out",
            "--backend",
            "api",
        ],
    )

    assert result.exit_code == 0
    mock_func.assert_called_once_with("dummy.mp4", "test-model", False, "out", "api")


def test_align_command(mocker):
    mock_func = mocker.patch("main.aligning.align")

    result = runner.invoke(
        app,
        [
            "align",
            "dummy.mp4",
            "--input-folder",
            "in",
            "--no-merge-duplicate-transcriptions",
            "--output-folder",
            "out",
        ],
    )

    assert result.exit_code == 0
    mock_func.assert_called_once_with("dummy.mp4", "in", False, "out")


def test_detect_boundaries_command(mocker):
    mock_func = mocker.patch("main.segmentation.detect_boundaries")

    result = runner.invoke(
        app,
        [
            "detect-boundaries",
            "dummy.mp4",
            "--model-name",
            "test",
            "--input-folder",
            "in",
            "--prompt-folder",
            "prompts",
            "--output-folder",
            "out",
            "--backend",
            "api",
        ],
    )

    assert result.exit_code == 0
    mock_func.assert_called_once_with(
        "dummy.mp4", "in", "test", "prompts", "out", "api"
    )


def test_merge_segments_command(mocker):
    mock_func = mocker.patch("main.segmentation.merge_segments")

    result = runner.invoke(
        app,
        [
            "merge-segments",
            "dummy.mp4",
            "--input-folder",
            "in",
            "--output-folder",
            "out",
        ],
    )

    assert result.exit_code == 0
    mock_func.assert_called_once_with("dummy.mp4", "in", "out")


def test_summarise_segments_command(mocker):
    mock_func = mocker.patch("main.segmentation.summarise_segments")

    result = runner.invoke(
        app,
        [
            "summarise-segments",
            "dummy.mp4",
            "--input-folder",
            "in",
            "--model-name",
            "test",
            "--caption-chunk-size",
            "50",
            "--prompt-folder",
            "prompts",
            "--output-folder",
            "out",
            "--backend",
            "api",
        ],
    )

    assert result.exit_code == 0
    mock_func.assert_called_once_with(
        "dummy.mp4", "in", "test", 50, "prompts", "out", "api"
    )


def test_classify_segments_command(mocker):
    mock_func = mocker.patch("main.segmentation.classify_segments")

    result = runner.invoke(
        app,
        [
            "classify-segments",
            "dummy.mp4",
            "--input-folder",
            "in",
            "--model-name",
            "test",
            "--prompt-folder",
            "prompts",
            "--output-folder",
            "out",
            "--backend",
            "api",
        ],
    )

    assert result.exit_code == 0
    mock_func.assert_called_once_with(
        "dummy.mp4", "in", "test", "prompts", "out", "api"
    )


def test_aggregate_metadata_command(mocker):
    mock_func = mocker.patch("components.metadata.aggregate_metadata")
    mock_func.return_value = {
        "collected": ["test"],
        "skipped": [],
        "output_path": "out",
    }

    result = runner.invoke(
        app,
        [
            "aggregate-metadata",
            "dummy.mp4",
            "--interim-folder",
            "interim",
            "--final-folder",
            "final",
            "--output-folder",
            "out",
        ],
    )

    assert result.exit_code == 0
    mock_func.assert_called_once_with("dummy.mp4", "interim", "final", "out")

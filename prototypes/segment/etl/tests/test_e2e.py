import gc
import shutil
from pathlib import Path

import pytest
import torch
from typer.testing import CliRunner

from main import app

runner = CliRunner()


@pytest.mark.e2e
def test_full_pipeline_e2e(tmp_path):
    """
    End-to-end test that exercises the actual ML models and CLI commands.
    This test is slow and requires compute/API access, so it is
    marked with @pytest.mark.e2e and should be run manually.

    Provide valid API keys in the environment variables for 'api' backend.
    """
    fixtures_dir = Path(__file__).parent / "fixtures"
    sample_video = fixtures_dir / "tiny_sample.mp4"

    if not sample_video.exists():
        pytest.skip("E2E test requires 'tests/fixtures/tiny_sample.mp4' to be present.")

    # Copy the video to a temp working directory to avoid polluting fixtures
    video_path = tmp_path / "tiny_sample.mp4"
    shutil.copy(sample_video, video_path)

    interim_folder = str(tmp_path / "1_interim")
    final_folder = str(tmp_path / "2_final")
    prompt_folder = Path(__file__).parent.parent.parent / "data" / "0_prompts"
    if not prompt_folder.exists():
        pytest.skip(f"E2E test requires prompts at {prompt_folder}")

    # 1. Extract Frames
    result = runner.invoke(
        app, ["extract-frames", str(video_path), "--output-folder", interim_folder]
    )
    assert result.exit_code == 0

    # 2. Extract Audio
    result = runner.invoke(
        app, ["extract-audio", str(video_path), "--output-folder", interim_folder]
    )
    assert result.exit_code == 0

    # 3. Caption Frames (Using local backend by default, beware memory requirements!)
    result = runner.invoke(
        app, ["caption-frames", str(video_path), "--output-folder", interim_folder]
    )
    assert result.exit_code == 0

    # Clear memory after Moondream
    gc.collect()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()

    # 4. Align
    result = runner.invoke(
        app,
        [
            "align",
            str(video_path),
            "--input-folder",
            interim_folder,
            "--output-folder",
            interim_folder,
        ],
    )
    assert result.exit_code == 0

    # 5. Detect Boundaries
    result = runner.invoke(
        app,
        [
            "detect-boundaries",
            str(video_path),
            "--input-folder",
            interim_folder,
            "--prompt-folder",
            str(prompt_folder),
            "--output-folder",
            final_folder,
        ],
    )
    assert result.exit_code == 0

    # Clear memory after first LLM pass
    gc.collect()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()

    # 6. Merge Segments
    result = runner.invoke(
        app,
        [
            "merge-segments",
            str(video_path),
            "--input-folder",
            final_folder,
            "--output-folder",
            final_folder,
        ],
    )
    assert result.exit_code == 0

    # 7. Summarise Segments
    result = runner.invoke(
        app,
        [
            "summarise-segments",
            str(video_path),
            "--input-folder",
            final_folder,
            "--prompt-folder",
            str(prompt_folder),
            "--output-folder",
            final_folder,
        ],
    )
    assert result.exit_code == 0

    # Clear memory after second LLM pass
    gc.collect()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()

    # 8. Classify Segments
    result = runner.invoke(
        app,
        [
            "classify-segments",
            str(video_path),
            "--input-folder",
            final_folder,
            "--prompt-folder",
            str(prompt_folder),
            "--output-folder",
            final_folder,
        ],
    )
    assert result.exit_code == 0

    # 9. Aggregate Metadata
    result = runner.invoke(
        app,
        [
            "aggregate-metadata",
            str(video_path),
            "--interim-folder",
            interim_folder,
            "--final-folder",
            final_folder,
            "--output-folder",
            final_folder,
        ],
    )
    assert result.exit_code == 0

    # Final assertions
    final_video_dir = tmp_path / "2_final" / "tiny_sample.mp4"
    assert (final_video_dir / "classifications.json").exists()
    assert (final_video_dir / "metadata_aggregated.json").exists()

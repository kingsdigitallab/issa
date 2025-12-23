import tempfile
from pathlib import Path
from unittest import mock

import torch

from components import utils


class TestCreateOutputPath:
    """Tests for create_output_path function."""

    def test_creates_basic_output_path(self):
        """Test that basic output path is created correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = "/path/to/video.mp4"
            output_path = utils.create_output_path(video_path, tmpdir)

            expected_path = Path(tmpdir) / "video.mp4"
            assert output_path == expected_path
            assert output_path.exists()
            assert output_path.is_dir()

    def test_creates_output_path_with_single_subfolder(self):
        """Test that output path with single subfolder is created correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = "/path/to/my_video.mp4"
            output_path = utils.create_output_path(video_path, tmpdir, "frames")

            expected_path = Path(tmpdir) / "my_video.mp4" / "frames"
            assert output_path == expected_path
            assert output_path.exists()
            assert output_path.is_dir()

    def test_creates_output_path_with_multiple_subfolders(self):
        """Test that output path with multiple subfolders is created correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = "/videos/test.mp4"
            output_path = utils.create_output_path(
                video_path, tmpdir, "processed", "frames", "hd"
            )

            expected_path = Path(tmpdir) / "test.mp4" / "processed" / "frames" / "hd"
            assert output_path == expected_path
            assert output_path.exists()
            assert output_path.is_dir()

    def test_handles_existing_directory(self):
        """Test that existing directories are handled gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = "/path/to/video.mp4"
            # Create the path first
            first_path = utils.create_output_path(video_path, tmpdir, "data")
            # Create it again
            second_path = utils.create_output_path(video_path, tmpdir, "data")

            assert first_path == second_path
            assert second_path.exists()

    def test_returns_pathlib_path(self):
        """Test that the function returns a Path object."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = "/path/to/video.mp4"
            output_path = utils.create_output_path(video_path, tmpdir)

            assert isinstance(output_path, Path)


class TestGetTorchDevice:
    """Tests for get_torch_device function."""

    def test_returns_cpu_when_no_accelerator_available(self, capsys):
        """Test that CPU is returned when no accelerator is available."""
        with mock.patch("torch.accelerator.is_available", return_value=False):
            device = utils.get_torch_device()

            assert device == "cpu"
            captured = capsys.readouterr()
            assert "Using device: cpu" in captured.out

    def test_returns_accelerator_when_available(self, capsys):
        """Test that accelerator type is returned when available."""
        mock_accelerator = mock.Mock()
        mock_accelerator.type = "cuda"

        with mock.patch("torch.accelerator.is_available", return_value=True):
            with mock.patch(
                "torch.accelerator.current_accelerator", return_value=mock_accelerator
            ):
                device = utils.get_torch_device()

                assert device == "cuda"
                captured = capsys.readouterr()
                assert "Using device: cuda" in captured.out

    def test_sets_float32_for_mps_device(self, capsys):
        """Test that default dtype is set to float32 for MPS devices."""
        mock_accelerator = mock.Mock()
        mock_accelerator.type = "mps"

        with mock.patch("torch.accelerator.is_available", return_value=True):
            with mock.patch(
                "torch.accelerator.current_accelerator", return_value=mock_accelerator
            ):
                with mock.patch("torch.set_default_dtype") as mock_set_dtype:
                    device = utils.get_torch_device()

                    assert device == "mps"
                    mock_set_dtype.assert_called_once_with(torch.float32)
                    captured = capsys.readouterr()
                    assert "Using device: mps" in captured.out

    def test_does_not_set_dtype_for_non_mps_device(self):
        """Test that dtype is not changed for non-MPS devices."""
        mock_accelerator = mock.Mock()
        mock_accelerator.type = "cuda"

        with mock.patch("torch.accelerator.is_available", return_value=True):
            with mock.patch(
                "torch.accelerator.current_accelerator", return_value=mock_accelerator
            ):
                with mock.patch("torch.set_default_dtype") as mock_set_dtype:
                    utils.get_torch_device()

                    mock_set_dtype.assert_not_called()


class TestGetTimestamp:
    """Tests for get_timestamp function."""

    def test_extracts_timestamp_from_standard_frame_path(self):
        """Test timestamp extraction from standard frame filename."""
        frame_path = "frame_001_123.456.png"
        timestamp = utils.get_timestamp(frame_path)

        assert timestamp == 123.456
        assert isinstance(timestamp, float)

    def test_extracts_timestamp_with_full_path(self):
        """Test timestamp extraction from full file path."""
        frame_path = "/path/to/frames/frame_042_567.89.png"
        timestamp = utils.get_timestamp(frame_path)

        assert timestamp == 567.89

    def test_extracts_integer_timestamp(self):
        """Test timestamp extraction when timestamp is an integer."""
        frame_path = "frame_000_100.png"
        timestamp = utils.get_timestamp(frame_path)

        assert timestamp == 100.0
        assert isinstance(timestamp, float)

    def test_extracts_zero_timestamp(self):
        """Test timestamp extraction for zero timestamp."""
        frame_path = "frame_001_0.0.png"
        timestamp = utils.get_timestamp(frame_path)

        assert timestamp == 0.0

    def test_extracts_large_timestamp(self):
        """Test timestamp extraction for large timestamp values."""
        frame_path = "frame_999_9999.999.png"
        timestamp = utils.get_timestamp(frame_path)

        assert timestamp == 9999.999

    def test_extracts_timestamp_with_many_decimal_places(self):
        """Test timestamp extraction with many decimal places."""
        frame_path = "frame_001_12.3456789.png"
        timestamp = utils.get_timestamp(frame_path)

        assert timestamp == 12.3456789

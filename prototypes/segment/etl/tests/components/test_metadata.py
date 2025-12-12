"""Tests for the metadata module."""

import os
import tempfile

from components import metadata


class TestGetGitHash:
    """Tests for get_git_hash function."""

    def test_returns_string_or_none(self):
        """Should return a string hash or None if not in git repo."""
        result = metadata.get_git_hash()
        assert result is None or isinstance(result, str)

    def test_hash_is_short_format(self):
        """If hash is returned, it should be short format (7-10 chars)."""
        result = metadata.get_git_hash()
        if result is not None:
            assert 7 <= len(result) <= 10


class TestGetPackageVersion:
    """Tests for get_package_version function."""

    def test_returns_string(self):
        """Should always return a string."""
        result = metadata.get_package_version()
        assert isinstance(result, str)

    def test_returns_valid_version_or_unknown(self):
        """Should return a version string or 'unknown'."""
        result = metadata.get_package_version()
        assert result == "unknown" or "." in result


class TestGetEnvironmentInfo:
    """Tests for get_environment_info function."""

    def test_returns_dict(self):
        """Should return a dictionary."""
        result = metadata.get_environment_info()
        assert isinstance(result, dict)

    def test_contains_required_keys(self):
        """Should contain python_version, platform, and hostname."""
        result = metadata.get_environment_info()
        assert "python_version" in result
        assert "platform" in result
        assert "hostname" in result

    def test_values_are_strings(self):
        """All values should be non-empty strings."""
        result = metadata.get_environment_info()
        for key, value in result.items():
            assert isinstance(value, str)
            assert len(value) > 0


class TestGetInputFileInfo:
    """Tests for get_input_file_info function."""

    def test_returns_dict(self):
        """Should return a dictionary."""
        result = metadata.get_input_file_info("/fake/path/video.mp4")
        assert isinstance(result, dict)

    def test_contains_required_keys(self):
        """Should contain input_file and input_file_size_bytes."""
        result = metadata.get_input_file_info("/fake/path/video.mp4")
        assert "input_file" in result
        assert "input_file_size_bytes" in result

    def test_extracts_filename(self):
        """Should extract just the filename from the path."""
        result = metadata.get_input_file_info("/some/long/path/my_video.mp4")
        assert result["input_file"] == "my_video.mp4"

    def test_size_is_none_for_nonexistent_file(self):
        """Should return None for size if file doesn't exist."""
        result = metadata.get_input_file_info("/nonexistent/video.mp4")
        assert result["input_file_size_bytes"] is None

    def test_size_is_correct_for_existing_file(self):
        """Should return correct size for existing file."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            temp_path = f.name

        try:
            result = metadata.get_input_file_info(temp_path)
            assert result["input_file_size_bytes"] == 12  # len("test content")
        finally:
            os.unlink(temp_path)


class TestCreateMetadata:
    """Tests for create_metadata function."""

    def test_returns_dict(self):
        """Should return a dictionary."""
        result = metadata.create_metadata(
            component="test_component",
            input_file="/path/to/video.mp4",
            items_processed=10,
            processing_time_seconds=5.5,
            parameters={"param1": "value1"},
        )
        assert isinstance(result, dict)

    def test_contains_all_required_fields(self):
        """Should contain all expected metadata fields."""
        result = metadata.create_metadata(
            component="test_component",
            input_file="/path/to/video.mp4",
            items_processed=10,
            processing_time_seconds=5.5,
            parameters={"param1": "value1"},
        )

        required_fields = [
            "component",
            "processed_at",
            "processing_time_seconds",
            "backend",
            "model_name",
            "device",
            "input_file",
            "input_file_size_bytes",
            "items_processed",
            "api_calls",
            "parameters",
            "package_version",
            "git_hash",
            "python_version",
            "platform",
            "hostname",
        ]

        for field in required_fields:
            assert field in result, f"Missing field: {field}"

    def test_component_is_set_correctly(self):
        """Should set the component name correctly."""
        result = metadata.create_metadata(
            component="frame_captioning",
            input_file="/path/to/video.mp4",
            items_processed=10,
            processing_time_seconds=5.5,
            parameters={},
        )
        assert result["component"] == "frame_captioning"

    def test_processing_time_is_rounded(self):
        """Should round processing time to 2 decimal places."""
        result = metadata.create_metadata(
            component="test",
            input_file="/path/to/video.mp4",
            items_processed=10,
            processing_time_seconds=5.555555,
            parameters={},
        )
        assert result["processing_time_seconds"] == 5.56

    def test_optional_fields_can_be_none(self):
        """Optional fields should default to None."""
        result = metadata.create_metadata(
            component="test",
            input_file="/path/to/video.mp4",
            items_processed=10,
            processing_time_seconds=5.5,
            parameters={},
        )
        assert result["backend"] is None
        assert result["model_name"] is None
        assert result["device"] is None
        assert result["api_calls"] is None

    def test_optional_fields_can_be_set(self):
        """Optional fields should be settable."""
        result = metadata.create_metadata(
            component="test",
            input_file="/path/to/video.mp4",
            items_processed=10,
            processing_time_seconds=5.5,
            parameters={},
            model_name="gpt-4o",
            backend="api",
            device="cuda",
            api_calls=50,
        )
        assert result["model_name"] == "gpt-4o"
        assert result["backend"] == "api"
        assert result["device"] == "cuda"
        assert result["api_calls"] == 50

    def test_processed_at_is_iso_format(self):
        """processed_at should be in ISO 8601 format."""
        result = metadata.create_metadata(
            component="test",
            input_file="/path/to/video.mp4",
            items_processed=10,
            processing_time_seconds=5.5,
            parameters={},
        )
        # ISO format contains 'T' separator and timezone info
        assert "T" in result["processed_at"]

    def test_parameters_are_preserved(self):
        """Parameters dict should be preserved in output."""
        params = {"remove_duplicates": True, "language": "en"}
        result = metadata.create_metadata(
            component="test",
            input_file="/path/to/video.mp4",
            items_processed=10,
            processing_time_seconds=5.5,
            parameters=params,
        )
        assert result["parameters"] == params

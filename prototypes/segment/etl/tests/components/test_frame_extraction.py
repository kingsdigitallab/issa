import os
from unittest.mock import MagicMock

import cv2
import pytest

from components import frame_extraction


def test_extract_frames(mocker, tmp_path):
    video_path = str(tmp_path / "dummy.mp4")
    output_folder = str(tmp_path / "out")

    # Mock VideoCapture
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True

    # Mock cap.get methods
    def mock_get(prop_id):
        if prop_id == cv2.CAP_PROP_FPS:
            return 30.0
        elif prop_id == cv2.CAP_PROP_FRAME_COUNT:
            return 90  # 3 seconds at 30fps
        return 0

    mock_cap.get.side_effect = mock_get

    # Mock cap.read: return True 90 times, then False
    read_returns = [(True, "fake_frame") for _ in range(90)] + [(False, None)]
    mock_cap.read.side_effect = read_returns

    mocker.patch("cv2.VideoCapture", return_value=mock_cap)

    # Mock cv2.imwrite to avoid actually writing images
    mock_imwrite = mocker.patch("cv2.imwrite")

    frame_extraction.extract_frames(
        video_path, sample_rate=1.0, output_folder=output_folder
    )

    # 90 frames, 30fps = 3 seconds. Sample rate 1.0 = 1 frame per second.
    # Therefore, we should extract 3 frames (at idx 0, 30, 60).
    assert mock_imwrite.call_count == 3
    mock_cap.release.assert_called_once()


def test_extract_frames_cannot_open(mocker, tmp_path):
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = False
    mocker.patch("cv2.VideoCapture", return_value=mock_cap)

    with pytest.raises(ValueError, match="Could not open video file"):
        frame_extraction.extract_frames("dummy.mp4", 1.0, str(tmp_path))

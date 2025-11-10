import os
from pathlib import Path

import torch


def create_output_path(video_path: str, base_folder: str, *subfolder: str) -> str:
    """
    Create an output directory path and ensure it exists.

    Args:
        video_path (str): The path to the video file.
        base_folder (str): The base output folder path.
        subfolder (str): The name of the subfolder to create.

    Returns:
        str: The full path to the created directory.
    """
    video_filename = Path(video_path).name
    output_path = Path(base_folder) / video_filename

    if subfolder:
        for folder in subfolder:
            output_path = output_path / folder

    output_path.mkdir(parents=True, exist_ok=True)

    return output_path


def get_torch_device():
    """
    Get the appropriate torch device (GPU if available, otherwise CPU).
    """
    device = (
        torch.accelerator.current_accelerator().type
        if torch.accelerator.is_available()
        else "cpu"
    )

    if device == "mps":
        # Ensure default dtype is float32 to avoid MPS float64 errors
        torch.set_default_dtype(torch.float32)

    print(f"Using device: {device}")

    return device


def get_timestamp(frame_path: str) -> float:
    """
    Extract the timestamp from a frame path.

    Args:
        frame_path (str): The path to the frame file.

    Returns:
        flota: The extracted timestamp.
    """
    return float(frame_path.split("_")[2].replace(".png", ""))

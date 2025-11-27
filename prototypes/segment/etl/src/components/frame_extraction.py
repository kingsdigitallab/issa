import os

import cv2
from tqdm import tqdm

from . import utils


def extract_frames(video_path: str, sample_rate: float, output_folder: str):
    """
    Extract frames from a video at a specified frame rate and save them to a folder.

    Args:
        video_path (str): Path to the input video file.
        sample_rate (float): The number of frames to sample per second.
        output_folder (str): Path to the output folder where frames will be saved.
    """
    output_path = utils.create_output_path(video_path, output_folder, "frames")

    print(f"Extracting frames from {video_path} and saving to {output_folder}...")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video file {video_path}")

    fps = int(cap.get(cv2.CAP_PROP_FPS))
    frame_interval = fps // sample_rate
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps

    frame_idx = 0

    print(f"Video: {duration:.1f}s, {fps:.1f} FPS, {frame_count} frames")

    with tqdm(total=frame_count, desc="Extracting frames", unit="frame") as pbar:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_interval == 0:
                timestamp = frame_idx / fps
                frame_filepath = os.path.join(
                    output_path, f"frame_{frame_idx:04d}_{timestamp:.2f}.png"
                )

                cv2.imwrite(frame_filepath, frame)

            frame_idx += 1
            pbar.update(1)

    cap.release()

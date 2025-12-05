import json
import os
from itertools import groupby

import torch
import tqdm

from . import utils

PROMPT_LARGE = """
You are an expert broadcast analyst. Your task is to analyze this frame from a broadcast
television recording and generate a structured caption. This caption will be used to
automatically identify and semantically segment different parts of the broadcast (e.g.,
separating news from commercials, or one news story from the next).

Provide your analysis in the following strict format:

**1. Segment Type:**
First, classify the frame's primary content. Choose one:
* **News Report:** (Anchor at a desk, on-location reporter, interview, news graphics)
* **Weather Report:** (Meteorologist with weather maps or graphics)
* **Commercial:** (Advertisement for a product, service, or brand)
* **Programme Content:** (A scene from a TV show, movie, documentary, or sports event)
* **Programme Intro/Outro:** (Opening title sequence, closing credits)
* **Station Ident/Branding:** (Channel logo, "coming up next" bumper, station promo)
* **Technical Card:** (Test pattern, "technical difficulties" slide, transmission info)

**2. On-Screen Text:**
Transcribe all visible text. **If no text is visible, state "None."** Otherwise, list
*only* the text categories you see:
* **Lower-Third/Chyron:** [Transcribe text]
* **Headline/Title:** [Transcribe text]
* **Logo/Ident:** [Transcribe text, e.g., channel name, brand]
* **Credits:** [Transcribe text]
* **Other:** [Transcribe any other text]
* *(If no text is visible, state "None.")*

**3. Scene Description:**
Concisely describe the visual elements.
* **People:** Describe the main individuals, their attire, and action (e.g., "A male
news anchor in a suit speaking to camera," "Two actors in a dramatic scene," "No people
visible").
* **Setting:** Describe the environment (e.g., "News studio," "Outdoor city street,"
"Kitchen set," "Abstract graphic background").
* **Key Objects:** List prominent objects relevant to the segment (e.g., "News desk,"
"Product bottle," "Weather map," "Microphone").
"""

PROMPT_SMALL = """
Describe this broadcast frame in detail. What text is visible? What type of segment is
it (news report, commercial, station ident, or show)? What is happening in the frame?
"""


def caption_frames(
    video_path: str,
    model_name: str,
    remove_duplicates: bool,
    output_folder: str,
    backend: str = "local",
):
    """
    Generate captions for frames of a video using a pre-trained vision model.

    Args:
        video_path (str): Path to the video file.
        model_name (str): Name of the pre-trained model vision model.
        remove_duplicates (bool): Whether to remove consecutive duplicate captions.
        output_folder (str): Path to the output folder.
        backend (str): The backend to use ("local" or "api").

    Returns:
        None
    """
    frames_path = utils.create_output_path(video_path, output_folder, "frames")
    frames = sorted(os.listdir(frames_path), key=utils.get_timestamp)

    if not frames:
        print(f"No frames found for {video_path}")
        return

    model, _, _ = utils.get_model_client(model_name, backend=backend)

    captions = []
    captions_path = utils.create_output_path(video_path, output_folder)

    prompt = PROMPT_SMALL

    with torch.inference_mode():
        for frame_path in tqdm.tqdm(frames, desc="Captioning frames"):
            full_frame_path = os.path.join(frames_path, frame_path)
            caption_text = utils.generate_caption(
                model, full_frame_path, prompt, model_name=model_name
            )
            timestamp = utils.get_timestamp(frame_path)

            captions.append(
                {
                    "frame_path": frame_path,
                    "timestamp": timestamp,
                    "caption": caption_text,
                }
            )

    if remove_duplicates:
        unique_captions = [
            next(group) for _, group in groupby(captions, key=lambda x: x["caption"])
        ]

        print(
            f"Reduced {len(captions)} captions to {len(unique_captions)} unique captions"
        )

    with open(os.path.join(captions_path, "captions.json"), "w") as f:
        json.dump(unique_captions, f, indent=4)

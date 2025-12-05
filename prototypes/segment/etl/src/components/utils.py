import base64
import os
from pathlib import Path

import torch
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image
from transformers import AutoModelForCausalLM, AutoProcessor

load_dotenv()


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


def get_model_client(model_name: str, backend: str = "local"):
    """
    Get the model client based on the backend.

    Args:
        model_name (str): The name of the model to load.
        backend (str): The backend to use ("local" or "api").

    Returns:
        tuple: A tuple containing the client/model, processor (if local), and device (if local).
    """
    if backend == "api":
        api_key = os.getenv("API_KEY")
        base_url = os.getenv("API_BASE_URL")
        if not base_url:
            base_url = None  # Use default OpenAI URL

        client = OpenAI(api_key=api_key, base_url=base_url)
        print(
            f"Initialized API client for {model_name} (Base URL: {base_url or 'Default'})"
        )
        return client, None, None

    device = get_torch_device()

    model = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True)
    model.to(device)
    model.eval()

    if device == "cuda":
        model.compile()

    try:
        processor = AutoProcessor.from_pretrained(model_name, use_fast=True)
    except Exception:
        processor = None

    print(f"Model {model_name} loaded on {device}")

    return model, processor, device


def generate_text_from_messages(
    client_or_model, processor, device, messages, model_name=None
):
    """
    Generates text from a list of messages using a causal language model or API.

    Args:
        client_or_model: The causal language model or API client.
        processor: The processor for the model (None if API).
        device: The device to run the model on (None if API).
        messages (list): A list of messages in the chat template format.
        model_name (str): The name of the model to use (required for API).

    Returns:
        str: The generated and decoded text.
    """
    if isinstance(client_or_model, OpenAI):
        response = client_or_model.chat.completions.create(
            model=model_name,
            messages=messages,
        )
        return response.choices[0].message.content

    inputs = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    ).to(device)
    input_len = inputs["input_ids"].shape[-1]

    with torch.inference_mode():
        generation = client_or_model.generate(
            **inputs, max_new_tokens=2048, do_sample=False
        )
        generation = generation[0][input_len:]

    decoded = processor.decode(generation, skip_special_tokens=True)
    return decoded


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def generate_caption(client_or_model, image_path, prompt, model_name=None):
    """
    Generate a caption for an image using a vision model or API.

    Args:
        client_or_model: The vision model or API client.
        image_path (str): Path to the image file.
        prompt (str): The prompt for captioning.
        model_name (str): The name of the model (required for API).

    Returns:
        str: The generated caption.
    """
    if isinstance(client_or_model, OpenAI):
        base64_image = encode_image(image_path)
        response = client_or_model.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
        )
        return response.choices[0].message.content

    # Local model inference (assuming Moondream or similar interface)
    image = Image.open(image_path)

    # Note: This assumes the local model has a .caption() method like Moondream
    # If using a different local model, this might need adjustment.
    # The original code used model.caption(image)
    caption = client_or_model.caption(image)

    # If the model returns a dict, extract the caption, otherwise assume string
    if isinstance(caption, dict) and "caption" in caption:
        return caption["caption"]

    return caption

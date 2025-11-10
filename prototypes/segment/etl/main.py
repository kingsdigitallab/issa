import typer

from components import (
    audio_extraction,
    frame_captioning,
    frame_extraction,
    segmentation,
)

app = typer.Typer(help="Semantically segment a video")


@app.command()
def extract_frames(
    video_path: str = typer.Argument(..., help="The path to the input video file"),
    sample_rate: float = typer.Option(
        1.0, help="The number of frames to sample per second"
    ),
    output_folder: str = typer.Option(
        "../data/1_interim", help="Path to the output folder"
    ),
):
    """Extract frames from a video"""
    try:
        frame_extraction.extract_frames(video_path, sample_rate, output_folder)
    except Exception as e:
        typer.echo(f"Error: {e}")


@app.command()
def extract_audio(
    video_path: str = typer.Argument(..., help="The path to the input video file"),
    language: str = typer.Option("en", help="The language of the audio"),
    model_size: str = typer.Option(
        "small", help="The size of the Whisper model to use"
    ),
    output_folder: str = typer.Option(
        "../data/1_interim", help="Path to the output folder"
    ),
):
    """Extract audio from a video"""
    try:
        audio_extraction.extract_audio(video_path, language, model_size, output_folder)
    except Exception as e:
        typer.echo(f"Error: {e}")


@app.command()
def caption_frames(
    video_path: str = typer.Argument(..., help="The path to the input video file"),
    model_name: str = typer.Option("vikhyatk/moondream2", help="Vision model to use"),
    remove_duplicates: bool = typer.Option(
        True, help="Remove consecutive duplicate captions"
    ),
    output_folder: str = typer.Option(
        "../data/1_interim", help="Path to the output folder"
    ),
):
    """Caption frames from a video"""
    try:
        frame_captioning.caption_frames(
            video_path, model_name, remove_duplicates, output_folder
        )
    except Exception as e:
        typer.echo(f"Error: {e}")


@app.command()
def segment(
    video_path: str = typer.Argument(..., help="The path to the input video file"),
    model_name: str = typer.Option("google/gemma-3-4b-it", help="LLM model to use"),
    input_folder: str = typer.Option(
        "../data/1_interim",
        help="Path to the input folder that contains the transcription and captioned frames",
    ),
    prompt_path: str = typer.Option(
        "../data/0_prompts/segmentation.md",
        help="Path to the systemprompt file for the LLM",
    ),
    output_folder: str = typer.Option(
        "../data/2_final", help="Path to the output folder"
    ),
):
    """Generate semantic segments for a video"""
    try:
        segmentation.generate_segments(
            video_path, input_folder, model_name, prompt_path, output_folder
        )
    except Exception as e:
        typer.echo(f"Error: {e}")


if __name__ == "__main__":
    app()

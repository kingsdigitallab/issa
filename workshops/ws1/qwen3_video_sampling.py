#!/usr/bin/env python3
# Script created by opencode:e-research/arc:apex
# Prompts: create a python script that calculates actual fps, number of frames and
# frame resolution from video duration (minutes), desired fps, max_frames and
# longest_edge, faithfully simulating how Qwen3.8 samples videos in vLLM
# (see docs/01-video_sampling_analysis.md); later add --video-tokens (in K) as an
# alternative way to set longest_edge (K * 1024 * 2048 pixels).

"""Simulate Qwen3VL video sampling as done by vLLM's video preprocessor.

Given a video's duration, desired sampling fps, processor frame limits and
pixel budget, reproduce the 3-stage pipeline from
docs/01-video_sampling_analysis.md:

1. Temporal sampling: num_frames = int(duration * fps), clamped to
   [min_frames, max_frames].
2. Spatial resize: HF smart_resize shrinks frames proportionally so the
   total pixel volume (frames x H x W) fits the longest_edge budget.
3. Token count: patches are merged (temporal_patch_size, merge_size) into
   vision tokens.

Outputs: actual/effective fps, sampled frame count, frame resolution,
vision-token grid and token count. The pixel budget can be given directly
(--longest-edge) or derived from a vision-token budget in K (--video-tokens).
"""

import argparse
import json
import math

# Qwen3VL video processor defaults (processor_config.json / video_preprocessor_config.json)
PATCH_SIZE = 16
TEMPORAL_PATCH_SIZE = 2
MERGE_SIZE = 2
MIN_FRAMES = 4
MAX_FRAMES = 768
DEFAULT_FPS = 2.0
DEFAULT_LONGEST_EDGE = 25165824  # 12K-token budget, model default
PIXELS_PER_K_TOKEN = 1024 * 2048  # longest_edge pixels per K of vision tokens (doc 01 tiers)
DEFAULT_WIDTH = 768
DEFAULT_HEIGHT = 576


def resolve_longest_edge(video_tokens: int | None, longest_edge: int) -> int:
    """Pixel budget: derived from --video-tokens (K) when given, else --longest-edge."""
    if video_tokens is not None:
        ret = video_tokens * PIXELS_PER_K_TOKEN
    else:
        ret = longest_edge
    return ret


def sample_frames(duration_seconds: float, fps: float, min_frames: int, max_frames: int) -> int:
    """Number of frames HF's sample_frames keeps: duration * fps, clamped."""
    ret = int(duration_seconds * fps)
    ret = min(max(ret, min_frames), max_frames)
    return ret


def smart_resize(height: int, width: int, num_frames: int, factor: int,
                 max_pixels: int, temporal_factor: int) -> tuple[int, int]:
    """HF's Qwen3VL video smart_resize: fit frames x H x W into max_pixels.

    Returns (resized_height, resized_width), multiples of `factor`.
    """
    h_bar = max(round(height / factor) * factor, factor)
    w_bar = max(round(width / factor) * factor, factor)
    t_bar = round(num_frames / temporal_factor) * temporal_factor

    if t_bar * h_bar * w_bar > max_pixels:
        beta = math.sqrt(num_frames * height * width / max_pixels)
        h_bar = max(factor, math.floor(height / beta / factor) * factor)
        w_bar = max(factor, math.floor(width / beta / factor) * factor)

    ret = (h_bar, w_bar)
    return ret


def count_tokens(resized_height: int, resized_width: int, num_frames: int,
                 patch_size: int, temporal_patch_size: int, merge_size: int) -> dict[str, int]:
    """Vision grid and token count of vLLM's _get_vision_info."""
    padded_frames = round_up(num_frames, temporal_patch_size)
    grid_t = max(padded_frames // temporal_patch_size, 1)
    grid_h = resized_height // patch_size
    grid_w = resized_width // patch_size
    num_patches = grid_t * grid_h * grid_w
    num_tokens = num_patches // (merge_size**2)
    ret = {
        "grid_t": grid_t,
        "grid_h": grid_h,
        "grid_w": grid_w,
        "tokens": num_tokens,
    }
    return ret


def round_up(value: int, multiple: int) -> int:
    """Round `value` up to the nearest multiple of `multiple`."""
    ret = -(-value // multiple) * multiple
    return ret


def simulate(duration_minutes: float, fps: float, max_frames: int,
             longest_edge: int, width: int, height: int,
             min_frames: int = MIN_FRAMES, patch_size: int = PATCH_SIZE,
             temporal_patch_size: int = TEMPORAL_PATCH_SIZE,
             merge_size: int = MERGE_SIZE) -> dict[str, object]:
    """Full pipeline result for one video, as a reportable dict."""
    duration_seconds = duration_minutes * 60
    num_frames = sample_frames(duration_seconds, fps, min_frames, max_frames)
    factor = patch_size * merge_size
    resized_height, resized_width = smart_resize(
        height, width, num_frames, factor, longest_edge, temporal_patch_size)
    token_info = count_tokens(resized_height, resized_width, num_frames,
                              patch_size, temporal_patch_size, merge_size)
    effective_fps = num_frames / duration_seconds if duration_seconds > 0 else float("inf")
    downscale = (height * width) / (resized_height * resized_width)
    ret = {
        "duration_minutes": duration_minutes,
        "frames": num_frames,
        "effective_fps": effective_fps,
        "resolution": f"{resized_width}x{resized_height}",
        "resized_width": resized_width,
        "resized_height": resized_height,
        "downscale": downscale,
        "longest_edge": longest_edge,
        **token_info,
    }
    return ret


def format_report(result: dict[str, object]) -> str:
    """Human-readable single-video report."""
    ret = (
        f"  duration:      {result['duration_minutes']} min\n"
        f"  frames:        {result['frames']}\n"
        f"  effective fps: {result['effective_fps']:.3f}\n"
        f"  resolution:    {result['resolution']} (WxH)\n"
        f"  downscale:     {result['downscale']:.1f}x\n"
        f"  pixel budget:  {result['longest_edge']}\n"
        f"  grid (TxHxW):  {result['grid_t']}x{result['grid_h']}x{result['grid_w']}\n"
        f"  vision tokens: {result['tokens']}\n"
    )
    return ret


def build_arg_parser() -> argparse.ArgumentParser:
    ret = argparse.ArgumentParser(
        description="Simulate Qwen3VL video sampling (vLLM preprocessor).")
    ret.add_argument("duration_minutes", type=float, nargs="+",
                     help="video duration(s) in minutes")
    ret.add_argument("--fps", type=float, default=DEFAULT_FPS,
                     help="desired sampling fps (default: %(default)s)")
    ret.add_argument("--max-frames", type=int, default=MAX_FRAMES,
                     help="hard cap on sampled frames (default: %(default)s)")
    budget_group = ret.add_mutually_exclusive_group()
    budget_group.add_argument("--longest-edge", type=int, default=DEFAULT_LONGEST_EDGE,
                              help="total pixel budget frames x H x W (default: %(default)s)")
    budget_group.add_argument("--video-tokens", type=int,
                              help="vision-token budget in K (e.g. 32 -> 32K tokens); "
                                   "derives longest_edge as K * 1024 * 2048")
    ret.add_argument("--width", type=int, default=DEFAULT_WIDTH,
                     help="source video width (default: %(default)s)")
    ret.add_argument("--height", type=int, default=DEFAULT_HEIGHT,
                     help="source video height (default: %(default)s)")
    ret.add_argument("--min-frames", type=int, default=MIN_FRAMES,
                     help="minimum sampled frames (default: %(default)s)")
    ret.add_argument("--patch-size", type=int, default=PATCH_SIZE,
                     help="vision patch size (default: %(default)s)")
    ret.add_argument("--temporal-patch-size", type=int, default=TEMPORAL_PATCH_SIZE,
                     help="temporal patch size (default: %(default)s)")
    ret.add_argument("--merge-size", type=int, default=MERGE_SIZE,
                     help="spatial merge size (default: %(default)s)")
    ret.add_argument("--json", action="store_true",
                     help="output results as JSON")
    return ret


def main() -> None:
    args = build_arg_parser().parse_args()
    longest_edge = resolve_longest_edge(args.video_tokens, args.longest_edge)
    results = [
        simulate(duration, args.fps, args.max_frames, longest_edge,
                 args.width, args.height, args.min_frames,
                 args.patch_size, args.temporal_patch_size, args.merge_size)
        for duration in args.duration_minutes
    ]
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for result in results:
            print(f"Video ({result['duration_minutes']} min):")
            print(format_report(result), end="")


if __name__ == "__main__":
    main()

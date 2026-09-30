"""issa_segments — review-only PoC project.

No live extraction is configured for this PoC: records come from the ISSA
pipeline's already-computed output (predictions CSV) plus NLS catalogue
ground truth (segments_true/*.json + sample-11.csv), converted by
../convert_records.py into paratext's "reviewing metadata you already have"
shape and packaged directly:

    paratext package records.jsonl -p issa-segments

`source=video_source()` is kept so this project *could* run a live
extraction later (e.g. an NLS-style workshop where attendees iterate on the
prompt) — it is never invoked by the package-only path above.
"""

from __future__ import annotations

from paratext.projects import Panel, Project, View, load_prompt
from paratext.sources import video_source

from .schema import Record

PROJECT = Project(
    name="issa-segments",
    schema_version="v1",
    prompt=load_prompt(__file__),
    schema=Record,
    source=video_source(),
    view=View(
        title="ISSA segmentation — model vs. NLS catalogue",
        id_label="Video / clip",
        panels=[
            Panel(
                source="ground_truth",
                title="NLS catalogue record",
                fields=["title", "year", "colour", "types"],
            ),
            Panel(
                source="model_output",
                title="Pipeline output (FrameSense + Qwen3.8-27B)",
                fields=["title", "year", "colour", "types", "summary"],
            ),
        ],
        table_label=("ground_truth", "title"),
    ),
)

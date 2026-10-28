"""issa_ws2 — WS2 deep-dive review project (NWFA, 10 sample videos).

Records come from ../convert_ws2.py; package with:

    paratext package records_ws2.jsonl -p issa-ws2
"""

from __future__ import annotations

from paratext.projects import Panel, Project, Verdict, View, load_prompt
from paratext.sources import video_source

from .schema import Record

PROJECT = Project(
    name="issa-ws2",
    schema_version="v1",
    prompt=load_prompt(__file__),
    schema=Record,
    source=video_source(),
    view=View(
        title="ISSA WS2 — pipeline vs. archive record vs. human annotators",
        id_label="Video",
        panels=[
            Panel(
                source="ground_truth",
                title="Archive record and human annotation",
                fields=["title", "year", "colour", "sound", "duration", "annotator_notes"],
            ),
            Panel(
                source="model_output",
                title="ISSA pipeline (FrameSense + Qwen3.8-27B)",
                fields=["types", "programmes", "label_matches"],
            ),
        ],
        verdicts=[
            Verdict("good_enough", "Good enough", "1"),
            Verdict("needs_tweaks", "Needs tweaking", "2", notes=True, warning=True),
            Verdict("not_accurate", "Incorrect", "3", notes=True, negative=True),
        ],
        notes_label="What happened?",
        notes_placeholder="Where did the pipeline and the annotators agree or part ways?",
        table_label=("ground_truth", "title"),
        collapsed=["label_matches"],
    ),
)

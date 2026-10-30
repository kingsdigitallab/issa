"""Output schema for issa_ws2: one record per NWFA video (WS2 deep dive).

Review-only, like issa_segments: describes the shape of what the pipeline
already produced (predictions-10.v3.xlsx) next to the NWFA catalogue record,
not a new extraction. Programme-level detail lives in the media tracks and in
the `programmes` / `label_matches` lists.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class Record(BaseModel):
    title: Optional[str] = Field(None, description="Title (catalogue) or tape label (Channel M)")
    year: Optional[str] = Field(None, description="Production year(s)")
    colour: Optional[str] = Field(None, description="colour | black-and-white")
    sound: Optional[str] = Field(None, description="sound | silent")
    duration: Optional[str] = Field(None, description="Running time, HH:MM:SS")
    types: Optional[list[str]] = Field(None, description="Category labels")
    programmes: Optional[list[str]] = Field(None, description="One line per programme: start, length, summary")
    label_matches: Optional[list[str]] = Field(None, description="Closest existing H22 labels to each programme summary")
    annotator_notes: Optional[list[str]] = Field(None, description="One line per human annotator")
    # Used by the patched review UI (ui/static/app.js); see ../ui/README.md
    compare: Optional[list[dict]] = Field(None, description="Mirrored rows: existing vs predicted, with a match status")
    extras: Optional[list[dict]] = Field(None, description="Fields only the pipeline produces")
    outline: Optional[list[dict]] = Field(None, description="Programmes, each with its segments")
    agreement: Optional[str] = Field(None, description="How far the annotators agree on programmes")
    collection: Optional[str] = Field(None, description="Archive and collection, e.g. NWFA ― Channel M")
    filename: Optional[str] = Field(None, description="File name of the video")
    file_duration: Optional[str] = Field(None, description="Duration of the video file, HH:MM:SS")

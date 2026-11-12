"""Output schema for issa_segments.

Review-only PoC: this schema describes the *shape* of what the ISSA pipeline
already produced (see ../../../notebooks/predictions_analysis.ipynb), not a
new extraction. No live model run is configured — records are converted from
existing predictions + NLS catalogue ground truth and packaged directly
(`paratext package records.jsonl -p issa-segments`; see review-views.md's
"Reviewing metadata you already have" recipe).

Keep each Field(description=...) short and structural — behaviour and edge
cases belong in prompt.md, which is *also* sent to the model, so a long
description here just restates the prompt in a second voice. Keep schema,
prompt, and view in step; the generated audit test guards it.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class Record(BaseModel):
    title: Optional[str] = Field(None, description="Programme title, if any")
    year: Optional[str] = Field(None, description="Release/production year, YYYY")
    colour: Optional[str] = Field(None, description="colour | black-and-white | colour-and-black-and-white")
    types: Optional[list[str]] = Field(None, description="Genre/type labels, e.g. ['tv news', 'documentary']")
    summary: Optional[str] = Field(None, description="One or two sentence summary")

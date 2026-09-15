Here's a structured review with concrete fixes, grounded in VLM prompt-engineering research:

## Core Issues

**1. No structured output format.** The prompt asks the model to "list" but never specifies *how*. VLMs produce far more reliable, parseable output when given an explicit JSON schema. Research on VLM video segmentation (NVIDIA VSS, Twelve Labs) consistently shows that schema-constrained JSON with `start_time` / `end_time` fields dramatically reduces hallucinated or ambiguous outputs.

**2. No timestamp requirement.** "List every separator" gives no temporal anchor. Without `start_time` and `end_time`, the model can't be validated against ground truth, and downstream systems can't act on the result.

**3. "Separators look completely different from surrounding programmes" is not operationalisable.** This is a subjective, holistic criterion that a VLM can't reliably evaluate. Fine-grained prompting research (ASK-Hint, 2025) shows that **concrete, action-centric cues outperform abstract descriptors by up to 30% AUC**. Replace it with specific visual signals.

**4. "Any other interstitial" is an open-ended catch-all.** This invites false positives (the model invents categories). The GPT-4o video-classification study (2025) found that **shortening and tightening policy prompts reduces false negatives** — counterintuitively, vagueness hurts recall more than precision.

**5. No abstention / "none found" instruction.** The note at the end ("a video may contain only one programme") is buried and phrased as a caveat, not a directive. The model needs an explicit "if none, return an empty list" instruction to avoid hallucinating a separator.

**6. No few-shot examples.** Even one or two example inputs/outputs (a video with a separator, one without) anchor the model's behaviour far better than description alone.

**7. The "ignore" clause is ambiguous.** "Ignore any other screen (title, chapter) that belong to a single programme" — the parenthetical examples (title, chapter) actually *overlap* with the positive examples (copyright or title slates). The model can't distinguish "a title slate that is a separator" from "a title card within a programme" without a clearer boundary rule.

---

## Suggested Rewrite

```
You are a broadcast video analyst. Identify every SEPARATOR between two
distinct programmes in this video.

A SEPARATOR is a brief visual interruption that marks the boundary
between one programme and the next. It typically lasts 1–30 seconds
and is visually distinct from the content on either side.

SEPARATORS include:
  - SMPTE colour bars / test cards
  - Station idents, logos, or branding sequences
  - Black or white screens (not part of a programme's own content)
  - Static, noise, or signal-loss frames
  - Countdown leaders (film countdown, digital countdown)
  - Copyright notices, legal slates, or "please stand by" slides
  - Network or channel bumper animations between programmes

NOT separators (do not report these):
  - Title cards, credits, or chapter markers *within* a single programme
  - Scene transitions (cuts, fades, dissolves) inside one programme
  - Intentional black screens that are part of a film's narrative
  - Watermarks, overlays, or persistent on-screen graphics

Rules:
  - A video may contain zero, one, or many separators.
  - If no separators are found, return an empty list.
  - Do not infer a separator from audio alone; it must be visible.
  - When in doubt whether a screen is a separator or part of a
    programme, prefer NOT reporting it (prioritise precision).

Output format — return ONLY valid JSON, no prose:
{
  "separators": [
    {
      "start_time": "HH:MM:SS",
      "end_time": "HH:MM:SS",
      "type": "<one of the categories above>",
      "description": "<one short sentence>"
    }
  ]
}
```

---

## Why Each Change Helps

| Change | Effect |
|---|---|
| Explicit JSON schema with timestamps | Parseable output; enables automated validation; reduces free-text hallucination |
| Concrete visual cues replacing "look completely different" | Fine-grained prompts improve detection accuracy by up to 30% (ASK-Hint) |
| Tightened category list + explicit "NOT" list | Reduces false positives from the open-ended "any other interstitial" |
| "Prefer NOT reporting it" tie-breaker | Directly targets precision; the study on GPT-4o video classification showed that shorter, tighter policies reduce FNs *and* FPs simultaneously |
| "Return an empty list" as a first-class instruction | Prevents the model from inventing a separator to satisfy the "list" imperative |
| "Do not infer from audio alone" | Eliminates a common VLM failure mode where audio cues (jingles, silence) are misread as visual separators |
| Duration hint (1–30 s) | Gives the model a prior that filters out long segments that are clearly programmes, not separators |

## Optional Further Improvements

- **Few-shot examples:** Append 1–2 short example videos (or frame sequences) with annotated JSON outputs. This is the single highest-leverage addition for VLM detection tasks.
- **Decomposition-aggregation:** If the video is long, split into overlapping chunks, run the prompt on each, then merge. The GPT-4o video study showed this outperforms a single-pass prompt for long videos.
- **Confidence field:** Add `"confidence": 0.0–1.0` to each separator so downstream filtering can drop low-confidence detections.
- **Reference images:** If your VLM API supports multimodal prompting (e.g., Twelve Labs Pegasus), attach reference images of known separator types (SMPTE bars, a specific station ident) to the prompt. This is a capability that text-only prompts can't match.

---

Good context — that changes several of my earlier recommendations. The open-ended nature of the task and the scale (100k+, decades, mixed sources) mean some of my previous suggestions were too rigid. Here's what I'd revise:

## What to keep from the original

- **The illustrative list is fine** — as long as it's framed as *examples*, not a closed taxonomy. The model needs those anchors to calibrate what "separator" means, but it must be explicitly told the list is non-exhaustive.
- **"Separators look completely different from surrounding programmes"** — this is actually the right *principle*. The problem wasn't that it's subjective; it's that it was the *only* criterion with no comparison instruction. It needs to be paired with an explicit "compare both sides" directive.

## Key revisions

### 1. Frame as boundary detection, not separator detection

The task is really "where does one programme end and another begin?" That's a more natural framing for a VLM and handles the open-ended case better. The separator is *evidence* of a boundary, not the boundary itself.

### 2. Add an explicit comparison instruction

This is the single most important fix for your use case. The model needs to be told to compare the content on **both sides** of a candidate segment:

> "For each candidate segment, compare the visual content immediately before it with the content immediately after. A separator sits between two *different* programmes. If both sides appear to be from the same programme (same setting, same people, same visual style, same narrative), the segment is part of that programme — not a separator."

This is essentially what **Scene-VLM** (2025) does with its context–focus window: it gives the model frames from both sides of each candidate boundary so it can make a comparative judgment. Without this, the model is pattern-matching on the separator itself in isolation, which is exactly why it misses unusual ones.

### 3. Make the list explicitly non-exhaustive + open-ended type field

> "Examples of separators include: SMPTE colour bars, test cards, station idents, black screens, static, countdown leaders, copyright slates, 'please stand by' slides, and many others. This list is **not exhaustive** — report any segment that meets the functional definition above, even if it doesn't match a known category."

And in the output schema, change the type field from a fixed enum to:
```json
"type": "<short descriptive label, e.g. 'SMPTE bars', 'station ident', 'unknown interstitial'>"
```

### 4. Invert the tie-breaker for your precision/recall balance

My earlier "prefer NOT reporting it" suggestion was wrong for your case. Since you're trying to **reduce false negatives**:

> "If you are uncertain whether a segment is a separator or part of a programme, **report it** and set confidence to a lower value. A missed boundary is worse than a false one."

Add a `confidence` field (0.0–1.0) to each output entry. This gives you a downstream knob: filter at 0.7 for high precision, at 0.4 for high recall. This mirrors Scene-VLM's approach of extracting confidence from token-level logits to enable controllable precision–recall trade-offs.

### 5. Minimize the "NOT" list to only the highest-impact false-positive sources

A long exclusion list backfires — the model starts second-guessing itself and misses real separators. Keep it to the 2–3 most common false positive sources:

> "Do NOT report:
> - Scene transitions (cuts, fades, dissolves) *within* a single programme
> - Title cards, credits, or chapter markers that are clearly part of the programme on at least one side
> - Persistent overlays (watermarks, timecodes, channel logos in a corner)"

### 6. Add era/format robustness

> "The video may be from any era (1950s–present), format (broadcast, VHS, digital, amateur recording), or source. Separators vary widely across eras and formats. Do not assume a separator must look like a modern broadcast element."

This matters for 100k+ videos spanning decades — a 1960s tape might have a hand-written slate or a different kind of test card that the model wouldn't expect.

### 7. Remove hard duration constraints

My earlier "1–30 seconds" hint is too narrow. Amateur tapes might have a 45-second "please wait" screen, and a quick 0.5s flash between programmes is still a separator. If you want a duration hint, make it very soft:

> "Separators are typically brief (seconds to a minute), but duration alone should not be the deciding factor."

---

## Revised core prompt

```
You are a broadcast video analyst. Identify every boundary between
two distinct programmes in this video.

A BOUNDARY is marked by a SEPARATOR: a brief visual segment that
does not belong to the programme on either side and marks the
transition from one programme to the next.

To identify a separator, compare the visual content immediately
BEFORE and AFTER the candidate segment:
  - If both sides are clearly different programmes (different
    setting, people, style, subject, or visual identity) AND the
    candidate segment is visually distinct from both → SEPARATOR.
  - If both sides appear to be from the same programme → NOT a
    separator, even if the segment looks unusual.

Examples of separators (NOT exhaustive — report anything that
meets the definition above):
  SMPTE colour bars, test cards, station idents, logos, branding
  sequences, black/white screens, static or noise, countdown
  leaders, copyright/legal slates, "please stand by" slides,
  network bumpers, hand-written slates, or any other interstitial.

Do NOT report:
  - Scene transitions (cuts, fades, dissolves) within one programme
  - Title cards, credits, or chapter markers that are part of the
    programme on at least one side
  - Persistent overlays (watermarks, timecodes, corner logos)

The video may be from any era, format, or source. Separators vary
widely across eras and formats.

If no separators are found, return an empty list.

Output — return ONLY valid JSON:
{
  "separators": [
    {
      "start_time": "HH:MM:SS",
      "end_time": "HH:MM:SS",
      "type": "<short descriptive label>",
      "confidence": 0.0,
      "description": "<one short sentence>"
    }
  ]
}
```

## What changed vs. my earlier version

| Earlier suggestion | Revised | Why |
|---|---|---|
| Closed category list in output | Open-ended `type` field | You can't enumerate separators across decades and formats |
| "Prefer NOT reporting it" | "Report it, lower confidence" | You're optimising for recall, not precision |
| Duration hint (1–30s) | Soft hint, duration not decisive | Amateur tapes and old broadcasts break this |
| Long "NOT" list | 3-item minimal list | Long exclusion lists cause the model to over-suppress |
| No comparison instruction | Explicit "compare both sides" | The key fix — mirrors Scene-VLM's context-focus approach |
| No era/format note | Explicit robustness instruction | 100k+ videos, decades of content |

The **compare-both-sides instruction** is the highest-leverage single change. It converts the task from "recognise a separator" (closed-set pattern matching, where unusual separators are missed) to "judge whether two adjacent segments are the same programme" (open-set comparison, where the model can generalise). That's the difference between a lookup table and a decision rule.

---

Refs:

https://developers.openai.com/cookbook/examples/gpt_with_vision_for_video_understanding

https://arxiv.org/html/2502.09573v1

https://arxiv.org/html/2512.21778v2

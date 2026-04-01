# Semantic Video Segmentation — Demonstrator

A [Slidev](https://sli.dev/) presentation for the ISSA Demonstrator Programme showcasing the video segmentation pipeline built at King's Digital Lab.

## Setup

```bash
pnpm install
```

## Development

```bash
pnpm dev
# visit http://localhost:3030
```

## Build & Export

```bash
pnpm build    # static site → dist/
pnpm export   # export to PDF (requires playwright-chromium)
```

## Content

Edit [`slides.md`](./slides.md) to modify the presentation. The slides cover:

1. **The problem** — undescribed digitised tapes from Heritage 2022
2. **The approach** — frame captioning + audio transcription + LLM boundary detection
3. **The output** — timestamps, summaries, topic labels, programme metadata
4. **Demo** — the `evaluation.html` verification interface (see `../../evaluation.html`)
5. **Other test cases** — documentary and rushes footage
6. **Observations** — what works, known limitations, no ground truth yet
7. **The precision question** — accuracy requirements by use case
8. **Feedback prompts** — questions for archive partners

### Assets

- `assets/SMPTE.svg` — cover slide background
- `assets/kings-logo-red.svg` — KDL logo
- `assets/demo.png` — screenshot for the demo slide
- `assets/frames-documentary.png` / `assets/frames-rushes.png` — other test case thumbnails
- `components/` — custom Vue components used in slides
- `pages/` — additional slide pages
- `snippets/` — code snippets embedded in slides

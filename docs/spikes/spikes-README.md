# Spikes

Small, time-boxed experiments that test whether an idea is feasible **before** it's committed to the [ISSA](https://github.com/kingsdigitallab/issa) roadmap.

A spike is throwaway by design. Its job is to answer a concrete question — usually *"do these pieces actually fit together?"* — as cheaply and honestly as possible, surface the real frictions early, and leave behind a runbook others can re-run or build from. A **green** spike graduates into scoped development; a **red** one saves a sprint. Nothing here is production code or a final architecture.

## What a spike doc should contain

- **Context** — enough for a fresh reader (including a coding assistant with no prior knowledge) to understand the idea in relation to the wider project and this codebase.
- **What it proves — and what it deliberately doesn't.** A spike is a narrow test; being explicit about its limits stops it being mistaken for the system.
- **Steps with checkpoints.** Concrete, ordered instructions, each with a pass/fail check so nobody advances on a broken foundation.
- **Honest flags.** Mark uncertainty and likely friction rather than papering over it — point at where to confirm, don't invent.
- **A status line** — Phase, scope, and what a green run graduates into.

## Current spikes

| Spike | Question it answers | Status |
|---|---|---|
| [`verdict-peertube-celluloid.md`](./verdict-peertube-celluloid.md) | Can a private self-hosted PeerTube + Celluloid let archivists view machine annotations on our own video and correct them — the seed of the MVP4 "archivist-in-the-loop" / cultivated-archive capability? | ✅ PeerTube proven ([replication recipe](./self_hosted_PeerTube.md)) · ❌ Celluloid abandoned — see verdict |

## Adding a spike

- One self-contained Markdown file per spike; name it for the thing it tests (`smoke-test-*`, `spike-*`).
- Keep it runnable end-to-end by someone who wasn't in the conversation that produced it.
- Add a row to the table above.
- When a spike graduates (or is abandoned), note the outcome and link to the follow-on spec or issue, so the folder stays a readable record of what was tried and why.

---

*See the [project wiki](https://github.com/kingsdigitallab/issa/wiki) for the wider ISSA context (Tech Review, Use Cases, DEERIN Prototypes).*

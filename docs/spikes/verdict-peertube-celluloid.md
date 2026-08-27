# Verdict: PeerTube + Celluloid Archivist-in-the-Loop Spike

**Date:** 2026-08-25  
**Status:** ✅ PeerTube ✅ | ❌ Celluloid  
**Replication recipe:** [`self_hosted_PeerTube.md`](./self_hosted_PeerTube.md) — the proven PeerTube half of this spike, condensed into a standalone runbook  
**Related:** `spikes-README.md`

---

## Goal

Prove, in 1–2 days, that three pieces fit together before committing more development time:

1. A **self-hosted, private PeerTube** serves archive video held in ISSA infrastructure (RDS / cluster storage).
2. A **self-hosted Celluloid** imports that PeerTube video and plays it in an annotation interface.
3. A **machine-proposed segment** and a **human correction** coexist in that interface — demonstrating, by hand, the "cultivation" loop (machine proposes → human corrects → record feeds next machine pass) that the full MVP4 "archivist-in-the-loop" / cultivated-archive capability automates.

If the checkpoints pass, the idea is proven and we scope the real build. If they don't, we've spent a day, not a sprint.

---

## Logic (the 3-piece test)

| Piece | What it proves | Expected Outcome |
|-------|----------------|----------------|
| **PeerTube** (private, self-hosted) | Serves an RDS tape over HTTPS on a private network; lockdown (registration/federation off, orig-res transcode, P2P off); programmatic upload as Unlisted; plays by URL. | Private video delivery substrate that keeps copyrighted archive material off the public internet. |
| **Celluloid** (self-hosted) | Imports a PeerTube video via its watch URL; resolves title/thumbnail/duration; plays inside Celluloid's annotation view. | Reuses a PeerTube-native, open-source annotation surface with existing chapter/timeline UI and a pluggable AI-processing pattern. |
| **Machine → Human round-trip** | Inject a machine `Chapter` (empty `lastEditedById` = machine-authored); human edits it in the UI → `lastEditedById` set to human user; record reads back out. | The single field `Chapter.lastEditedById` *is* the machine-proposes / human-corrects round-trip. This is the seed of the MVP4 cultivated-archive loop. |

**Deliberately out of scope:** Production privacy hardening (spike uses Unlisted + network isolation, not Internal+auth); the real Qwen3-VL / FrameSense pipeline; RDS-scale ingest; the two-level programme/atomic schema + three-source provenance + status/supersession fields; the UI reskin.

---

## Findings

### ✅ PeerTube — WORKS
| Checkpoint | Result |
|------------|--------|
| Private HTTPS + TLS (self-signed cert, SAN = floating IP) | ✅ |
| Registration closed, federation off, orig-res transcode only, P2P off | ✅ |
| Channel `issa_nls` created | ✅ |
| 2 test videos uploaded as Unlisted (privacy=2), playable by URL, not publicly listed | ✅ |
| Caddy reverse proxy terminates TLS, reverse-proxies to PeerTube `:9000` | ✅ |
| `curl --cacert` returns HTTP/2 200 with `via: 1.1 Caddy`, `x-powered-by: PeerTube` | ✅ |

**Key takeaway:** The private PeerTube video-serving layer **works end-to-end**. It keeps archive video on a private network, behind TLS, with programmatic upload and playback — a solid foundation for any downstream annotation interface.

### ❌ Celluloid — UNFEASIBLE IN SCOPE
| Blocker | Detail |
|---------|--------|
| **No pre-built images** | `stack.yml` references `celluloid-web:latest` / `celluloid-worker:latest` — images don't exist on Docker Hub (pull denied / require login). |
| **Dockerfile requires BuildKit** | The root `Dockerfile` uses `--mount=type=cache` (pnpm cache), which requires the `buildx`/BuildKit component. Legacy builder fails; `buildx` must be installed. |
| **`@celluloid/vision` build is broken** | (a) Requires **Node ≥22.18** (repo runs on v20). (b) `orval` codegen produces a **conflicting export**: `startDetectionAnalysePost` is imported in `src/index.ts` but not exported by the generated `endpoints.ts`. This persisted even after upgrading to Node 22. |
| **Fragile Node/pnpm/catalog matrix** | pnpm 11 needs Node 22+; pnpm 8 can't resolve the repo's `catalog:` dependencies; the lockfile is pnpm-10-specific. Even after Node 22 install, the vision codegen conflict persists. |
| **Vision is required at runtime** | `worker` imports `@celluloid/vision/env` at startup — no clean skip without forking/rebuilding the worker. |

**Net:** Celluloid's self-hosted build is too brittle to stand up in ISSA's scope/time. The annotation round-trip (the actual MVP4 idea) was never reached.

---

## Decision

| Outcome | Action |
|---------|--------|
| **PeerTube** | ✅ Keep as the private video-serving layer. It works, is reproducible, and isolates archive video on a private network. |
| **Celluloid** | ❌ Unfeasible in ISSA scope. Do not pursue further self-hosted builds in this phase. |
| **Annotation interface** | **Do not proceed with Celluloid.** Explore two paths forward (see below). |

---

## Paths Forward (open — need more research & UX discussion)

We did not reach the annotation round-trip. Two viable directions remain, and the next step is requirements gathering + UX discussion with the designer:

| Path | Description | Notes |
|-------|-------------|-----------------|
| **1. PeerTube-native chapters/comments API** | PeerTube exposes a **chapters API** and **comments/annotations API**. The "machine proposes → human corrects" loop may be implementable **directly on PeerTube** (create chapters via API, human edits via UI or API, read back via API). No extra app needed. | Reuses the one layer that already works; zero new infrastructure; PeerTube's chapter model (`lastEditedById`) already captures the machine→human transition. |
| **2. Custom lightweight web app** (React/Next.js) | A minimal app that: imports a PeerTube watch URL, plays the video, renders machine chapters (from FrameSense/Qwen3-VL output), captures human edits (start/end time, title, description), writes corrections back to a store (PostgreSQL), and exports the corrected record for the next machine pass. | Full control over UX (archivist workflows are specific); can integrate with FrameSense output directly; can implement the two-level (programme/atomic) schema and three-source provenance from day one. |

**Next step:** Review requirements with the team prior to workshop 1, involve the UX specialist + archivist partners to decide which path aligns best with the workshop's aims.

---

## Third-Party Components (links)

| Component | Repository / Docs | Version used |
|-----------|-------------------|--------------|
| **PeerTube** | <https://github.com/Chocobozzz/PeerTube> (docker: `support/docker/production/`) | `master` branch (docker-compose.yml, .env) |
| **Celluloid** | <https://github.com/celluloid-camp/celluloid> (monorepo, `stack.yml`, `Dockerfile`) | `develop` branch (at time of spike) |
| **Caddy** | <https://caddyserver.com/docs/> | v2 (via snap / binary) |
| **orval** | <https://orval.dev/> | v8.26.0 (used by Celluloid `vision` package) |
| **pnpm** | <https://pnpm.io/> | v9 (required for `catalog:` deps) |
| **turbo** | <https://turbo.build/repo> | v2.10.11 (used by Celluloid build) |
| **Prisma** | <https://www.prisma.io/> | v6.19.3 (Celluloid ORM) |
| **CREATE OpenStack** | <https://docs.er.kcl.ac.uk/CREATE/cloud/> | — |
| **CREATE VPN** | <https://docs.er.kcl.ac.uk/CREATE/tools/openvpn/> | — |
| **CREATE SSH keys** | <https://docs.er.kcl.ac.uk/CREATE/tools/ssh_clients/> | — |
| **CREATE VM creation** | <https://docs.er.kcl.ac.uk/CREATE/cloud/cloud_vm_create/> | — |

---

## Appendix: Exact Config Used (for replication)

### PeerTube `.env` (key overrides)
```bash
PEERTUBE_WEBSERVER_HOSTNAME=<floating-ip>
PEERTUBE_WEBSERVER_PORT=443
PEERTUBE_WEBSERVER_HTTPS=true
PEERTUBE_SIGNUP_ENABLED=false
PEERTUBE_FEDERATION_ENABLED=false
PEERTUBE_TRANSCODING_ALWAYS_TRANSCODE_ORIGINAL_RESOLUTION=true
PEERTUBE_DEFAULTS_P2P_WEBAPP_ENABLED=false
PEERTUBE_DEFAULTS_P2P_EMBED_ENABLED=false
POSTGRES_USER=peertube
POSTGRES_PASSWORD=<generated>
PEERTUBE_SECRET=<generated>
PEERTUBE_DB_USERNAME=$POSTGRES_USER
PEERTUBE_DB_PASSWORD=$POSTGRES_PASSWORD
PEERTUBE_DB_HOSTNAME=postgres
PEERTUBE_DB_PASSWORD=$POSTGRES_PASSWORD
PEERTUBE_DB_SSL=false
PEERTUBE_TRUST_PROXY='["127.0.0.1", "loopback", "172.28.0.0/16"]'
```

### PeerTube `docker-compose.yml` edits
- Comment out: `webserver`, `certbot`, `webserver-reloader` blocks
- Uncomment: `- "9000:9000"` under `peertube:` `ports:`
- (Optional) comment `- "1935:1935"`

### Caddyfile
```
:443 {
    tls /opt/ssl/peertube.crt /opt/ssl/peertube.key
    reverse_proxy 127.0.0.1:9000
}
```
---

## Reproducible Scripts
Full step-by-step recipe: [`self_hosted_PeerTube.md`](./self_hosted_PeerTube.md). Scripts:
- `docs/spikes/scripts/setup-peertube.sh` — end-to-end VM → PeerTube → Caddy → lockdown
- `docs/spikes/scripts/upload-to-peertube.py` — programmatic Unlisted upload to a channel

Both scripts use a single `PT_HOST` variable (auto-detected floating IP, overridable) and are designed to run **once, manually, after the VM is up and the floating IP is assigned**.
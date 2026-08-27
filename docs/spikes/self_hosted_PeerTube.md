# Self-Hosted PeerTube — Replication Recipe

**Status:** ✅ proven in the Phase 0 spike · **Scope:** the private video-serving layer only
**Scripts:** [`scripts/setup-peertube.sh`](./scripts/setup-peertube.sh), [`scripts/upload-to-peertube.py`](./scripts/upload-to-peertube.py)
**See also:** [verdict-peertube-celluloid.md](./verdict-peertube-celluloid.md) — full spike outcome, including why the paired annotation layer (Celluloid) was abandoned.

---

## Context

This recipe stands up the private, self-hosted PeerTube instance built for Phase 0 of ISSA's "archivist-in-the-loop" spike — a test of whether a private video layer could serve copyrighted archive tape (from KCL storage, e.g. RDS) to an annotation interface without ever exposing it publicly. This was done following the wider MVP4 "cultivated archive" capability (machine proposes an annotation → an archivist corrects it → the correction feeds the next machine pass; see the [project wiki](https://github.com/kingsdigitallab/issa/wiki) for the full ISSA context). PeerTube's role is narrow and worth restating: it is only the private, TLS-locked video-delivery substrate — not the annotation store or the processor — and it must never be reachable from a public URL. The annotation layer originally paired with it, Celluloid, did not survive the spike (its self-hosted build proved too brittle — see the verdict linked above); this PeerTube instance remains a working, reusable component for whatever annotation interface replaces it.

---

## Prerequisites

- A Linux host with **Docker + Compose**, tested with a CREATE OpenStack VM on a private network segment ([VM creation](https://docs.er.kcl.ac.uk/CREATE/cloud/cloud_vm_create/), [VPN](https://docs.er.kcl.ac.uk/CREATE/tools/openvpn/), [SSH keys](https://docs.er.kcl.ac.uk/CREATE/tools/ssh_clients/)).
- A floating/public IP for that host — the spike used a self-signed cert against the IP directly, not a DNS hostname.
- `ffprobe`, `openssl`, `git`, Python 3 with `requests`.
- Access to the RDS share (mounted, or a box to `scp`/`rsync` from) — see `workshops/ws1/copy-videos.bash` for the existing staging pattern.
- 2–3 sample tapes to test with (there is a short test video in `/spikes/issa_promo.mp4`).

---

## Recipe

### 1. Stage sample tapes and check their codecs

```bash
mkdir -p /opt/spike/videos
cp /mnt/rds/nls/<tape-id>.mp4 /opt/spike/videos/
ffprobe -v error -show_entries stream=codec_name,width,height:format=duration \
  -of default=nk=1 /opt/spike/videos/<tape-id>.mp4
```

H.264/MP4 sources barely get re-encoded by PeerTube; archival codecs (MPEG-2, ProRes, MXF) trigger a real transcode so we try to avoid this at scale.

**✅ Checkpoint:** 2–3 playable local files, codecs known.

### 2. Bring up PeerTube behind Caddy

```bash
PT_HOST=<your-floating-ip> ./scripts/setup-peertube.sh
```

This fetches PeerTube's official production `docker-compose.yml`, writes the `.env` overrides (hostname, HTTPS, registration/federation disabled, original-resolution-only transcoding, P2P off, generated DB/app secrets), removes PeerTube's bundled nginx/certbot services in favour of Caddy, generates a self-signed cert (SAN = your IP), starts the stack, and reverse-proxies `:443` to PeerTube's `:9000`. It prints the auto-generated root password at the end.

**✅ Checkpoint:**
```bash
curl --cacert /opt/ssl/peertube.crt -sI https://<your-floating-ip>
```
returns an HTTP/2 200 with `x-powered-by: PeerTube`.

### 2.1 Manual configuration (optional, the script above should do this automatically)
Log in at `https://<your-floating-ip>` with the root password from step 2, then in **Administration → Configuration**:

- Registration → **disabled**
- Federation → **off**
- Transcoding → **original resolution only**
- P2P / WebTorrent → **off**

### 3. Create a channel
Log in at `https://<your-floating-ip>` with the root password from step 2, then create a video channel (the spike used `issa_nls`).

**✅ Checkpoint:** admin login works; registration closed; channel exists.

### 4. Upload the tapes as Unlisted

```bash
PT_HOST=<your-floating-ip> PT_PASSWORD=<admin-pw> \
  python3 scripts/upload-to-peertube.py /opt/spike/videos --channel issa_nls
```

Prints each video's watch URL (`https://<host>/w/<shortUUID>`).

**✅ Checkpoint:** 2–3 videos in the channel, each playable by URL, not publicly listed, and only accessible behind the VPN.

---

## Troubleshooting

- **A downstream import/API call rejects the video:** almost always privacy — Private/Internal videos aren't readable by an anonymous API caller; Unlisted is.
- **Transcode is slow:** source isn't H.264 — expected, fine for a handful of files but not for batch processing.
- **`setup-peertube.sh` can't auto-detect `PT_HOST`:** pass it explicitly; the metadata-service fallback only works on OpenStack-style clouds.

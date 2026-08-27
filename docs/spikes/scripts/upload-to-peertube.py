#!/usr/bin/env python3
"""Upload a folder of videos to a PeerTube channel as Unlisted.

Used to stage RDS archive tapes onto the private PeerTube instance set up
by setup-peertube.sh — see ../self_hosted_PeerTube.md for the recipe.

Auth is OAuth2 password grant, single-request upload (fine for a handful
of spike files; switch to PeerTube's resumable upload endpoint at scale).

Usage:
    PT_HOST=1.2.3.4 PT_PASSWORD=<admin-pw> \
      python3 upload-to-peertube.py /opt/spike/videos [--channel issa_nls]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import requests

PRIVACY_UNLISTED = 2  # PeerTube privacy id: 1 public, 2 unlisted, 3 private, 4 internal


def peertube_url(host: str) -> str:
    return host if host.startswith("http") else f"https://{host}"


def get_token(base: str, username: str, password: str) -> str:
    client = requests.get(f"{base}/api/v1/oauth-clients/local").json()
    response = requests.post(
        f"{base}/api/v1/users/token",
        data={
            "client_id": client["client_id"],
            "client_secret": client["client_secret"],
            "grant_type": "password",
            "response_type": "code",
            "username": username,
            "password": password,
        },
    )
    response.raise_for_status()
    return response.json()["access_token"]


def get_or_create_channel_id(base: str, token: str, name: str) -> int:
    headers = {"Authorization": f"Bearer {token}"}
    me = requests.get(f"{base}/api/v1/users/me", headers=headers).json()
    for channel in me.get("videoChannels", []):
        if channel["name"] == name:
            return channel["id"]
    raise SystemExit(
        f"channel '{name}' not found — create it first in the admin UI "
        f"(Administration -> channels), per self_hosted_PeerTube.md"
    )


def upload(base: str, token: str, channel_id: int, path: Path) -> tuple[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    with open(path, "rb") as handle:
        response = requests.post(
            f"{base}/api/v1/videos/upload",
            headers=headers,
            data={"channelId": channel_id, "name": path.stem, "privacy": PRIVACY_UNLISTED},
            files={"videofile": handle},
        )
    response.raise_for_status()
    video = response.json()["video"]
    return video["uuid"], video["shortUUID"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help="folder of video files to upload")
    parser.add_argument("--channel", default="issa_nls")
    parser.add_argument("--username", default=os.environ.get("PT_USERNAME", "root"))
    args = parser.parse_args()

    host = os.environ.get("PT_HOST")
    password = os.environ.get("PT_PASSWORD")
    if not host or not password:
        sys.exit("Set PT_HOST and PT_PASSWORD environment variables.")

    base = peertube_url(host)
    token = get_token(base, args.username, password)
    channel_id = get_or_create_channel_id(base, token, args.channel)

    for video_path in sorted(args.folder.glob("*.*")):
        video_uuid, short_uuid = upload(base, token, channel_id, video_path)
        print(f"{video_path.name}  ->  {base}/w/{short_uuid}   (uuid {video_uuid})")


if __name__ == "__main__":
    main()

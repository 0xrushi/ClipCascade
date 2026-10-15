#!/usr/bin/env python3
"""Replay failed RAG dispatches from ClipCascade backend logs."""

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse


FAILURE_RE = re.compile(r"RAG ingest dispatch failed for (.+?) \(user=(.*?)\): ")


def link_type(url: str) -> str:
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    if host in {"x.com", "twitter.com", "fxtwitter.com"}:
        return "TWITTER"
    if host in {"instagram.com", "kkinstagram.com"}:
        return "INSTAGRAM"
    if host in {"tiktok.com", "vm.tiktok.com"}:
        return "TIKTOK"
    if host in {"youtube.com", "youtu.be"}:
        return "YOUTUBE"
    return "GENERIC_WEB"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("log_file", help="Backend log file, or - for stdin")
    parser.add_argument("--username", help="Replay failures for only this username")
    parser.add_argument("--sidecar-url", default="http://localhost:8090")
    parser.add_argument("--token", required=True, help="CCRAG_AUTH_TOKEN")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    source = sys.stdin if args.log_file == "-" else open(args.log_file, encoding="utf-8")
    seen: set[tuple[str, str]] = set()
    try:
        for line in source:
            match = FAILURE_RE.search(line)
            if not match:
                continue
            url, username = match.groups()
            if args.username and username != args.username:
                continue
            if (url, username) in seen:
                continue
            seen.add((url, username))

            payload = {
                "url": url,
                "link_type": link_type(url),
                "username": username,
                "timestamp": 0,
            }
            if args.dry_run:
                print(json.dumps(payload))
                continue

            request = urllib.request.Request(
                args.sidecar_url.rstrip("/") + "/ingest",
                data=json.dumps(payload).encode(),
                headers={
                    "Content-Type": "application/json",
                    "X-CCRAG-Token": args.token,
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    print(f"replayed user={username} status={response.status} url={url}")
            except urllib.error.HTTPError as error:
                print(f"failed user={username} status={error.code} url={url}", file=sys.stderr)
    finally:
        if args.log_file != "-":
            source.close()
    print(f"processed {len(seen)} unique failure(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

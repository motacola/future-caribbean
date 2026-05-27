#!/usr/bin/env python3
"""Telegram Sender — sends outbox/telegram_digest.md to a Telegram bot channel.

Credentials (set in .env or environment):
  TELEGRAM_BOT_TOKEN   — from @BotFather
  TELEGRAM_CHAT_ID     — channel/group chat ID (e.g. @mychannel or -100123456789)

Usage:
  python3 distributors/telegram_sender.py
  python3 distributors/telegram_sender.py --dry-run   # print message, don't send
  python3 distributors/telegram_sender.py --file outbox/telegram_digest.md

On success: appends a send receipt to outbox/live_send_log.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path for pipeline_util
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline_util import retry  # noqa: E402

DEFAULT_FILE = ROOT / "outbox" / "telegram_digest.md"
DISPATCH_LOG = ROOT / "outbox" / "live_send_log.md"

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

# Telegram message limit
MAX_CHARS = 4096


def load_env() -> None:
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def md_to_telegram(text: str) -> str:
    """Convert markdown to Telegram MarkdownV2 format."""
    # Telegram MarkdownV2 escapes: _ * [ ] ( ) ~ ` > # + - = | { } . !
    # Our digest uses *bold* and plain text — preserve *bold*, escape the rest
    import re

    # Split on *bold* spans, escape non-bold chunks
    def escape_plain(s: str) -> str:
        specials = r"\_[]()~`>#+-=|{}.!"
        for ch in specials:
            s = s.replace(ch, f"\\{ch}")
        return s

    parts = re.split(r"(\*[^*]+\*)", text)
    out = []
    for part in parts:
        if part.startswith("*") and part.endswith("*") and len(part) > 2:
            # Bold — keep the asterisks, escape inner content
            inner = escape_plain(part[1:-1])
            out.append(f"*{inner}*")
        else:
            out.append(escape_plain(part))
    return "".join(out)


@retry(max_attempts=3, delay=2.0, exceptions=(urllib.error.HTTPError, urllib.error.URLError))
def send_message(token: str, chat_id: str, text: str) -> dict:
    url = TELEGRAM_API.format(token=token)
    payload = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "MarkdownV2",
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def append_dispatch_log(channel: str, status: str, note: str, message_id: str = "") -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    entry = f"| {timestamp} | {channel} | {status} | {note} | {message_id} |\n"

    if not DISPATCH_LOG.exists():
        DISPATCH_LOG.write_text(
            "# Live Send Log\n\n"
            "Real delivery receipts from enabled delivery senders.\n\n"
            "| Timestamp | Channel | Status | Note | Message ID |\n"
            "|---|---|---|---|---|\n",
            encoding="utf-8",
        )
    with DISPATCH_LOG.open("a", encoding="utf-8") as f:
        f.write(entry)


def main() -> int:
    parser = argparse.ArgumentParser(description="Send telegram digest to Telegram channel.")
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE)
    parser.add_argument("--dry-run", action="store_true", help="Print message without sending")
    args = parser.parse_args()

    load_env()

    if not args.file.exists():
        print(f"ERROR: {args.file} not found. Run the pipeline first.", file=sys.stderr)
        return 1

    text = args.file.read_text(encoding="utf-8").strip()
    if not text:
        print("ERROR: digest file is empty.", file=sys.stderr)
        return 1

    # Truncate if over Telegram limit
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS - 20] + "\n\n…[truncated]"

    telegram_text = md_to_telegram(text)

    if args.dry_run:
        print("── DRY RUN ── Would send to Telegram:")
        print(telegram_text)
        append_dispatch_log("Telegram", "dry-run", f"from {args.file.name}")
        return 0

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        print(
            "ERROR: Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env\n"
            "  TELEGRAM_BOT_TOKEN=your_bot_token\n"
            "  TELEGRAM_CHAT_ID=@yourchannel_or_-100chatid",
            file=sys.stderr,
        )
        return 1

    print(f"Sending to Telegram chat {chat_id}...")
    try:
        result = send_message(token, chat_id, telegram_text)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"ERROR: Telegram API error {e.code}: {body}", file=sys.stderr)
        append_dispatch_log("Telegram", "failed", str(e))
        return 1
    except Exception as e:
        print(f"ERROR: Telegram send failed after retries: {e}", file=sys.stderr)
        append_dispatch_log("Telegram", "failed", str(e))
        return 1

    if result.get("ok"):
        message_id = str(result.get("result", {}).get("message_id", ""))
        print(f"Sent. Message ID: {message_id}")
        append_dispatch_log("Telegram", "sent", f"from {args.file.name}", message_id)
        return 0
    else:
        print(f"ERROR: Telegram returned: {result}", file=sys.stderr)
        append_dispatch_log("Telegram", "failed", str(result))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

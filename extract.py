#!/usr/bin/env python3
"""Print the user's own messages from local Claude Code + Codex transcripts, newest first."""
import argparse, glob, json, os, re

HOME = os.path.expanduser("~")
SKIP = re.compile(r"^\s*(<|\[Request interrupted|Caveat:|I hit my usage limit)")  # command tags, system injections


def claude():
    for f in glob.glob(f"{HOME}/.claude/projects/*/*.jsonl"):
        for line in open(f, errors="ignore"):
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("type") != "user" or d.get("isMeta") or d.get("isSidechain"):
                continue
            c = d.get("message", {}).get("content")
            if isinstance(c, list):  # tool results are not the user's writing
                c = "\n".join(x.get("text", "") for x in c if x.get("type") == "text")
            if c:
                yield d.get("timestamp", ""), c


def codex():
    for f in glob.glob(f"{HOME}/.codex/sessions/**/*.jsonl", recursive=True):
        for line in open(f, errors="ignore"):
            try:
                d = json.loads(line)
            except ValueError:
                continue
            p = d.get("payload") or {}
            if d.get("type") == "event_msg" and p.get("type") == "user_message":
                yield d.get("timestamp", ""), p.get("message", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["claude", "codex", "all"], default="all")
    ap.add_argument("--limit", type=int, default=400)
    ap.add_argument("--max-chars", type=int, default=1500, help="longer = probably a paste, not your writing")
    a = ap.parse_args()

    msgs = []
    if a.source in ("claude", "all"):
        msgs += claude()
    if a.source in ("codex", "all"):
        msgs += codex()

    seen, out = set(), []
    for ts, m in sorted(msgs, key=lambda x: x[0], reverse=True):
        m = m.strip()
        if len(m) < 3 or len(m) > a.max_chars or SKIP.match(m) or m.startswith("/") or m in seen:
            continue
        seen.add(m)
        out.append(m)
        if len(out) >= a.limit:
            break
    print(f"# {len(out)} messages\n")
    print("\n---\n".join(out))


if __name__ == "__main__":
    main()

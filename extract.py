#!/usr/bin/env python3
"""Print the user's own messages from local Claude Code + Codex transcripts, newest first."""
import argparse, glob, json, os, re

HOME = os.path.expanduser("~")
TAGS = re.compile(r"<([a-z][a-z_-]*)>[\s\S]*?</\1>")  # agent-injected blocks inside a message
SKIP = re.compile(r"^\s*(<|\[Request interrupted|Caveat:|I hit my usage limit)")  # command tags, system injections

# Redact, don't drop: the message's style survives, the secret doesn't.
SECRETS = [
    re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s:/@]+:[^\s@]+@\S+", re.I),  # scheme://user:pass@host
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\beyJ[\w-]{10,}\.[\w-]{10,}\.[\w-]{10,}"),  # JWT
    re.compile(r"\b(sk|pk|rk)[-_][\w-]{16,}|\bgh[pousr]_\w{20,}|\bgithub_pat_\w{20,}|\bxox[abprs]-[\w-]{10,}|\bAKIA[0-9A-Z]{16}\b|\bAIza[\w-]{30,}"),
    re.compile(r"(?i)\b(pass(word|wd)?|pwd|secret|token|api[_-]?key|private[_-]?key|auth)\b\s*[:=]\s*\S+"),
    re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),  # emails
    re.compile(r"(?<![\w/.-])(?=[\w-]*\d)(?=[\w-]*[A-Za-z])[\w-]{32,}={0,2}(?![\w/.])"),  # long random tokens outside paths/urls
]


def scrub(text):
    for rx in SECRETS:
        text = rx.sub("[redacted]", text)
    return text


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
        m = TAGS.sub("", m).strip()
        if len(m) < 3 or len(m) > a.max_chars or SKIP.match(m) or m.startswith("/") or m in seen:
            continue
        seen.add(m)
        out.append(scrub(m))
        if len(out) >= a.limit:
            break
    print(f"# {len(out)} messages\n")
    print("\n---\n".join(out))


def demo():
    cases = {
        "use postgresql://postgres.abc:Hunter2pass@aws-0.pooler.supabase.com:6543/postgres": "postgres.abc",
        "key is sk-proj-AbCdEf1234567890XyZ ok": "sk-proj",
        "gh token gho_abcdefghij1234567890ABCD": "gho_",
        "mail me at someone@example.com": "@example",
        "password: hunter2 pls": "hunter2",
        "pubkey 9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin": "9xQeW",
        "AKIAABCDEFGHIJKLMNOP is aws": "AKIA",
    }
    for raw, leak in cases.items():
        assert leak not in scrub(raw), (raw, scrub(raw))
    for path in ["see https://github.com/org/repo/blob/0123456789abcdef0123456789abcdef01234567/x.rs", "/Users/me/hoist-cli-0123456789abcdef0123456789abcdef/x"]:
        assert scrub(path) == path, scrub(path)
    keep = "bro why you created new fiolder bro, it is running ?"
    assert scrub(keep) == keep
    print("scrub ok")


if __name__ == "__main__":
    import sys
    demo() if "--test" in sys.argv else main()

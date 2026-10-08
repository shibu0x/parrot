#!/usr/bin/env python3
"""Print the user's own messages from local terminal AI agent transcripts, newest first."""
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


# Where each terminal agent keeps its transcripts. Most store user turns as JSON
# records, so one generic reader (user_text) handles all of them.
SOURCES = {
    "claude": ["~/.claude/projects/*/*.jsonl"],
    "codex": ["~/.codex/sessions/**/*.jsonl"],
    "gemini": ["~/.gemini/tmp/*/chats/*.json", "~/.gemini/tmp/*/logs.json"],
    "qwen": ["~/.qwen/tmp/*/chats/*.json", "~/.qwen/tmp/*/logs.json", "~/.qwen/projects/*/chats/*.jsonl"],
    "copilot": ["~/.copilot/session-state/**/*.jsonl"],
    "kiro": ["~/.kiro/sessions/**/*.jsonl"],
    "factory": ["~/.factory/sessions/**/*.jsonl"],
    "opencode": ["~/.local/share/opencode/storage/message/*/*.json"],
    "aider": ["~/*/.aider.input.history", "~/*/*/.aider.input.history", "~/*/*/*/.aider.input.history"],
}


def texts(c):
    """Text of a message body: a string, or a list of text parts in any agent's shape."""
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        out = []
        for x in c:
            if isinstance(x, str):
                out.append(x)
            elif isinstance(x, dict) and (x.get("type") or x.get("kind") or "text") == "text":
                t = x.get("text", x.get("data"))
                if isinstance(t, str):
                    out.append(t)
        return "\n".join(out)
    return ""


def user_text(d):
    """The user's text if this JSON record is a user turn, else ''. Tool results come out empty."""
    if not isinstance(d, dict) or d.get("isMeta") or d.get("isSidechain"):
        return ""
    if d.get("role") == "user":
        return texts(d.get("content"))
    if d.get("type") in ("user", "user_message", "user.message") or d.get("kind") == "Prompt":
        for k in ("message", "content", "data"):
            v = d.get(k)
            if isinstance(v, dict):
                v = v.get("content", v.get("message"))
            t = texts(v)
            if t:
                return t
        return ""
    for k in ("payload", "message"):  # codex / factory wrap the turn one level down
        if isinstance(d.get(k), dict):
            return user_text(d[k])
    return ""


def opencode_text(f, d):
    # message json has no text; it lives in storage/part/<messageID>/*.json
    parts = glob.glob(os.path.join(f.split("/storage/")[0], "storage/part", d.get("id", "-"), "*.json"))
    return "\n".join(texts([json.load(open(p))]) for p in sorted(parts))


def aider(f):
    # "# 2024-.. timestamp" starts an entry, "+line" lines are what the user typed
    entry = []
    for line in open(f, errors="ignore"):
        if line.startswith("#") and entry:
            yield "\n".join(entry)
            entry = []
        elif line.startswith("+"):
            entry.append(line[1:].rstrip("\n"))
    if entry:
        yield "\n".join(entry)


def read(name, f):
    if name == "aider":
        yield from aider(f)
        return
    if f.endswith(".jsonl"):
        records = []
        for line in open(f, errors="ignore"):
            try:
                records.append(json.loads(line))
            except ValueError:
                pass
    else:
        try:
            d = json.load(open(f, errors="ignore"))
        except ValueError:
            return
        records = d if isinstance(d, list) else d.get("messages", [d]) if isinstance(d, dict) else []
    for d in records:
        if name == "opencode":
            yield opencode_text(f, d) if isinstance(d, dict) and d.get("role") == "user" else ""
        else:
            yield user_text(d)


def collect(names):
    """(sort key, text) for every user message; newest file last, file order within."""
    for name in names:
        for pat in SOURCES[name]:
            for f in glob.glob(os.path.expanduser(pat), recursive=True):
                mtime = os.path.getmtime(f)
                for i, t in enumerate(read(name, f)):
                    if t:
                        yield (mtime, i), t


SAMPLES = os.path.expanduser("~/.writer/samples")


def samples(channel, base=SAMPLES):
    """Real writing the user dropped in <base>/<channel>/. One piece per file, or several split by a --- line."""
    for f in sorted(glob.glob(os.path.join(base, channel, "*"))):
        if os.path.isfile(f):
            for piece in re.split(r"\n---+\n", open(f, errors="ignore").read()):
                if piece.strip():
                    yield piece.strip()


def channels(base=SAMPLES):
    return sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))) if os.path.isdir(base) else []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="all", help="all, or comma list of: " + ", ".join(SOURCES))
    ap.add_argument("--limit", type=int, default=400)
    ap.add_argument("--max-chars", type=int, default=1500, help="longer = probably a paste, not your writing")
    ap.add_argument("--list", action="store_true", help="show how many messages each agent and sample channel has")
    ap.add_argument("--samples", metavar="CHANNEL", help=f"print real writing from {SAMPLES}/CHANNEL instead of agent chats")
    a = ap.parse_args()

    names = list(SOURCES) if a.source == "all" else a.source.split(",")
    bad = set(names) - set(SOURCES)
    if bad:
        ap.error(f"unknown source {', '.join(bad)}; pick from {', '.join(SOURCES)}")
    if a.list:
        for n in SOURCES:
            print(f"{n}: {sum(1 for _ in collect([n]))}")
        for c in channels():
            print(f"samples/{c}: {sum(1 for _ in samples(c))}")
        return
    if a.samples:
        out = [scrub(x) for x in samples(a.samples)]
        print(f"# {len(out)} messages\n")
        print("\n---\n".join(out))
        return

    seen, out = set(), []
    for _, m in sorted(collect(names), key=lambda x: x[0], reverse=True):
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
    shapes = [
        {"type": "user", "message": {"role": "user", "content": "claude str"}},
        {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "claude list"}]}},
        {"type": "event_msg", "payload": {"type": "user_message", "message": "codex"}},
        {"type": "user", "content": [{"text": "gemini parts"}]},
        {"type": "user", "message": "gemini log"},
        {"type": "user.message", "data": {"content": "copilot"}},
        {"kind": "Prompt", "data": {"content": [{"kind": "text", "data": "kiro"}]}},
        {"type": "message", "message": {"role": "user", "content": [{"type": "text", "text": "factory"}]}},
    ]
    for d in shapes:
        assert user_text(d), d
    not_user = [
        {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "content": "x"}]}},
        {"type": "assistant", "message": {"role": "assistant", "content": "hi"}},
        {"type": "user", "isMeta": True, "message": {"content": "meta"}},
        {"kind": "AssistantMessage", "data": {"content": [{"kind": "text", "data": "x"}]}},
    ]
    for d in not_user:
        assert not user_text(d), d
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(f"{d}/tweet")
        open(f"{d}/tweet/a.txt", "w").write("first post\n---\nsecond post")
        open(f"{d}/tweet/b.txt", "w").write("third")
        assert list(samples("tweet", d)) == ["first post", "second post", "third"]
        assert channels(d) == ["tweet"]
    keep = "bro why you created new fiolder bro, it is running ?"
    assert scrub(keep) == keep
    print("extract ok")


if __name__ == "__main__":
    import sys
    demo() if "--test" in sys.argv else main()

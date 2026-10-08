#!/usr/bin/env python3
"""Count writing habits in extract.py output, and score a draft's mechanics against them.

  python3 extract.py | python3 stats.py                 # habits of your messages
  python3 extract.py | python3 stats.py --draft "text"  # mechanics match of a draft
"""
import argparse, collections, re, statistics, sys

EMOJI = re.compile(r"[\U0001F300-\U0001FAFF☀-➿]")
APOS = {"dont": "don't", "cant": "can't", "wont": "won't", "didnt": "didn't", "doesnt": "doesn't",
        "isnt": "isn't", "im": "i'm", "ive": "i've", "lets": "let's", "whats": "what's", "thats": "that's"}
STOP = set("the a an to of and or in on for is it this that i you we be are with can so but if as at by not my me do just from what how why it's".split())

# Rate features: share of units (messages, or draft lines) showing the habit.
FEATURES = {
    "starts lowercase": lambda t: t[:1].islower(),
    "ends with full stop": lambda t: t.rstrip().endswith("."),
    "asks a question": lambda t: "?" in t,
    "space before ?": lambda t: " ?" in t,
    "exclamation": lambda t: "!" in t,
    "ellipsis": lambda t: "..." in t or "…" in t,
    "em dash": lambda t: "—" in t,
    "emoji": lambda t: bool(EMOJI.search(t)),
    "lowercase i": lambda t: bool(re.search(r"(^|\s)i(\s|$)", t)),
    "capital I": lambda t: bool(re.search(r"(^|\s)I(\s|')", t)),
}


def read_messages(text):
    parts = text.split("\n---\n")
    if parts and parts[0].startswith("# "):
        parts[0] = parts[0].split("\n", 1)[-1]
    return [p.strip() for p in parts if p.strip()]


def rates(units):
    return {k: sum(map(f, units)) / len(units) for k, f in FEATURES.items()}


def profile(msgs):
    words = [len(m.split()) for m in msgs]
    sents = [len(s.split()) for m in msgs for s in re.split(r"[.?!\n]+", m) if s.strip()]
    low = " ".join(msgs).lower()
    toks = re.findall(r"[a-z']+", low)
    count = collections.Counter(toks)
    out = [f"messages: {len(msgs)}",
           f"words per message: median {statistics.median(words):.0f}, avg {statistics.mean(words):.1f}",
           f"words per sentence: median {statistics.median(sents):.0f}"]
    out += [f"{k}: {v:.0%}" for k, v in rates(msgs).items()]
    pairs = [(c, count[c], count[APOS[c]]) for c in APOS if count[c] or count[APOS[c]]]
    out.append("no-apostrophe vs apostrophe: " + ", ".join(f"{c} {n}/{m}" for c, n, m in pairs))
    out.append("double ?? or more: %d" % len(re.findall(r"\?\?", low)))
    out.append("openers: " + ", ".join(f"{w} {n}" for w, n in collections.Counter(
        m.split()[0].lower().strip(",.!?") for m in msgs if m.split()).most_common(15)))
    top = [(w, n) for w, n in count.most_common(300) if w not in STOP and len(w) > 1][:40]
    out.append("top words: " + ", ".join(f"{w} {n}" for w, n in top))
    return "\n".join(out)


def match(msgs, draft):
    """Mechanics match 0-100: how close the draft's habit rates are to the user's."""
    lines = [l.strip() for l in draft.splitlines() if l.strip()]
    mine, theirs = rates(msgs), rates(lines)
    # ponytail: flat average over features, weight per feature if some matter more
    gaps = {k: abs(mine[k] - theirs[k]) for k in FEATURES}
    score = round(100 * (1 - sum(gaps.values()) / len(gaps)))
    worst = sorted(gaps.items(), key=lambda x: -x[1])[:3]
    return score, [f"{k}: you {mine[k]:.0%}, draft {theirs[k]:.0%}" for k, g in worst if g > 0.2]


def demo():
    msgs = ["bro is it running ?", "ok so lets push it", "why you removed the import ?"]
    assert match(msgs, "bro its done\nlets ship it ?")[0] > match(msgs, "I'm thrilled to announce this!\nIt's live — try it.")[0]
    assert "messages: 3" in profile(msgs)
    print("stats ok")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft", help="draft text to score")
    ap.add_argument("--test", action="store_true")
    a = ap.parse_args()
    if a.test:
        demo()
        sys.exit()
    msgs = read_messages(sys.stdin.read())
    if not msgs:
        sys.exit("no messages on stdin, pipe extract.py into this")
    if a.draft:
        score, notes = match(msgs, a.draft)
        print(f"mechanics match: {score}%")
        print("\n".join(notes))
    else:
        print(profile(msgs))

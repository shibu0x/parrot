#!/usr/bin/env python3
"""Count writing habits in extract.py output, and score a draft's mechanics against them.

  python3 scripts/extract.py | python3 stats.py                 # habits of your messages
  python3 scripts/extract.py | python3 stats.py --draft "text"  # mechanics match of a draft
"""
import argparse, collections, re, statistics, sys

EMOJI = re.compile(r"[\U0001F300-\U0001FAFF☀-➿]")
APOS = {"dont": "don't", "cant": "can't", "wont": "won't", "didnt": "didn't", "doesnt": "doesn't",
        "isnt": "isn't", "im": "i'm", "ive": "i've", "lets": "let's", "whats": "what's", "thats": "that's"}
STOP = set("the a an to of and or in on for is it this that i you we be are with can so but if as at by not my me do just from what how why it's".split())

# Phrases that read as AI. Only flagged when the user never uses them, so their real habits always win.
SLOP = [
    r"\bdelv(e|es|ing)\b", r"\bdive (deep )?into\b", r"\bunpack(ing)?\b", r"\bleverag(e|es|ing)\b", r"\butiliz(e|es|ing)\b",
    r"\bharness(ing)?\b", r"\bunlock(s|ing)?\b", r"\bempower(s|ing)?\b", r"\belevat(e|es|ing)\b", r"\bsupercharg(e|es|ing)\b",
    r"\bseamless(ly)?\b", r"\brobust\b", r"\bcutting[- ]edge\b", r"\bgame[- ]?chang(er|ing)\b", r"\brevolutioni[sz](e|es|ing)\b",
    r"\btapestry\b", r"\brealm\b", r"\blandscape\b", r"\bjourney\b", r"\bever[- ]evolving\b", r"\bfast[- ]paced\b",
    r"\b(excited|thrilled|proud|delighted) to (announce|share|introduce)\b", r"\bin today's\b", r"\bit'?s (important|worth) not(ing|e)\b",
    r"\bfurthermore\b", r"\bmoreover\b", r"\badditionally\b", r"\bmoving forward\b", r"\bat the end of the day\b",
    r"\blet that sink in\b", r"\bread that again\b", r"\bhere'?s the thing\b", r"\bthis changes everything\b",
    r"\bnobody (is talking|talks) about\b", r"\bwhat nobody tells you\b",
    r"\b(it'?s|this is) not (just )?(a |an |about )?\w+[^.\n]{0,30}[,.;] (it'?s|this is)\b",  # "it's not X, it's Y"
    r"(#\w+\s*){3,}",  # hashtag soup
]


def slop(msgs, draft):
    mine = " ".join(msgs)
    hits = []
    for rx in SLOP:
        m = re.search(rx, draft, re.I)
        if m and not re.search(rx, mine, re.I):
            hits.append(m.group(0).strip())
    return hits


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
    ai = "We're thrilled to announce our robust tool. It's not just a tool, it's a movement. #ai #dev #build"
    assert len(slop(msgs, ai)) == 4, slop(msgs, ai)
    assert slop(msgs, "bro its done lets ship it") == []
    assert slop(msgs + ["we leverage the pool"], "leverage it") == []  # user's own word is fine
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
        hits = slop(msgs, a.draft)
        print(f"ai phrases: {len(hits)}" + (" -> " + ", ".join(f'"{h}"' for h in hits) if hits else ""))
    else:
        print(profile(msgs))

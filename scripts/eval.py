#!/usr/bin/env python3
"""Check that the scorer can tell the user's real writing from generic AI text.

  python3 scripts/extract.py --limit 1000 | python3 eval.py
  python3 scripts/extract.py --samples tweet | python3 eval.py

Holds back 20% of the messages, builds the baseline from the rest, then scores
the held-back real messages and some generic AI text against it. Real ones
should score clearly higher and almost never be flagged as AI phrases.
"""
import random, statistics, sys

from stats import match, read_messages, slop

GENERIC_AI = [
    "I'm thrilled to announce the launch of my new project! It's been an incredible journey.",
    "In today's fast-paced world, developers need tools that work seamlessly. That's why I built this.",
    "Here's the thing: writing is hard. But it doesn't have to be. Let's dive into how this works.",
    "Excited to share what I've been working on. It's not just a tool, it's a whole new workflow.",
    "This changes everything for content creators. Unlock your full potential today. #AI #Writing #Productivity",
    "Furthermore, the robust architecture ensures a smooth experience. Moreover, it's completely free.",
]


def evaluate(msgs, seed=0):
    msgs = msgs[:]
    random.Random(seed).shuffle(msgs)
    cut = max(1, len(msgs) // 5)
    held, base = msgs[:cut], msgs[cut:]
    real = [match(base, m)[0] for m in held]
    ai = [match(base, t)[0] for t in GENERIC_AI]
    flagged = sum(1 for m in held if slop(base, m))
    return {
        "real": statistics.mean(real), "ai": statistics.mean(ai),
        "flagged": flagged, "held": len(held),
        "ai_phrases": statistics.mean(len(slop(base, t)) for t in GENERIC_AI),
    }


def report(r):
    gap = r["real"] - r["ai"]
    fp = r["flagged"] / r["held"]
    ok = gap >= 15 and fp <= 0.05
    return "\n".join([
        f"real you ({r['held']} held-back messages): mechanics {r['real']:.0f}%, flagged as AI {r['flagged']} ({fp:.0%})",
        f"generic AI text ({len(GENERIC_AI)} samples):   mechanics {r['ai']:.0f}%, ai phrases {r['ai_phrases']:.1f} each",
        f"gap: {gap:.0f} points -> {'PASS' if ok else 'FAIL'} (needs gap >= 15 and real flagged <= 5%)",
    ])


def demo():
    you = ["bro is it running ?", "ok so lets push it", "why you removed the import ?", "so whats next ?",
           "ok run it locally then", "bro why you pushing ??", "lets ship it now", "so is it done ?", "ok fix it", "no need"]
    r = evaluate(you * 3)
    assert r["real"] > r["ai"] + 15, r
    assert r["ai_phrases"] >= 1, r
    print("eval ok")


if __name__ == "__main__":
    if "--test" in sys.argv:
        demo()
        sys.exit()
    msgs = read_messages(sys.stdin.read())
    if len(msgs) < 20:
        sys.exit(f"need at least 20 messages to evaluate, got {len(msgs)}")
    print(report(evaluate(msgs)))

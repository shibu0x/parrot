---
name: writer
description: Writes tweets, posts, emails, blogs, replies in the USER'S OWN voice, learned from their past messages to Claude Code and Codex. Use when the user runs /writer, or says "write this like me", "in my voice", "how I would write it". `/writer profile` builds or shows their style profile; `/writer <type> <topic>` drafts content.
---

# writer

Learn how the user writes from their own messages to coding agents, then write in that voice.
Profile lives at `~/.writer/profile.md`. Raw messages never leave the machine except as the context you already have.

## Commands

- `/writer profile` : (re)build the profile and show it.
- `/writer <type> <what to write>` : type is tweet, thread, linkedin, blog, email, reply, docs, or anything else. Build the profile first if missing.

## 1. Build the profile

Run:

```bash
python3 ~/.claude/skills/writer/extract.py --limit 400
```

(`--source claude|codex` to restrict. Messages over 1500 chars are dropped as likely pastes.)

These are the user's messages ONLY. Analyze them and write `~/.writer/profile.md`:

```markdown
# Writing profile
updated: <date> | messages analyzed: <N>

## Scores (0-100)
casual, direct, technical, formal, humor, emotional

## Mechanics
- avg sentence length (words), fragments yes/no
- capitalization (lowercase starts? "i" lowercase?)
- punctuation habits (periods at end? question marks? "..."? em dashes? exclamation?)
- typos/spelling: real habits worth keeping (e.g. drops apostrophes) vs noise
- emoji use
- language mix (e.g. Hinglish), slang and filler words with examples ("bro", "tbh")

## Voice
- how they open and close a message
- how they explain, ask, push back
- words/phrases they use a lot (quote them)
- things they NEVER do (corporate tone, hedging, etc.)

## Samples
10-15 short verbatim messages that best show the voice. Skip anything with secrets, keys, emails, names of private people, or client data.
```

Be concrete. "Casual" is useless; "starts with 'bro', no capital letters, no period at the end" is useful. Count, don't guess.

Then show the profile to the user in a compact form.

## 2. Write

1. Read `~/.writer/profile.md`.
2. Note the gap: chat messages to an AI are not tweets. Keep the voice (word choice, rhythm, attitude, quirks) but fit the format (a tweet is under 280 chars, a blog has structure). Don't copy chat-only habits that make the piece unreadable, keep them if they're the user's signature.
3. Write 3 different drafts.
4. Score each against the profile (0-100): vocabulary, sentence rhythm, tone, mechanics (caps/punctuation/emoji), and "would they actually send this". Penalize anything that smells like AI: "delve", "excited to announce", "game-changer", tidy rule-of-three lists, em dashes if the user doesn't use them, emoji the user doesn't use, hashtag soup.
5. If the best scores under 85, rewrite it and score again (max 2 rounds).
6. Output:

```
<final text>

Style match: 91%  (vocab 90 · rhythm 93 · tone 92 · mechanics 88)
```

Add the other drafts below only if the user asks for options.

## Rules

- Never invent facts about the user's project. If the topic is thin, ask one question or keep it short.
- If the profile is older than ~2 weeks or the user says it's off, offer to rebuild.
- User edits to a draft ("no, I'd say it like X") are gold: append them under `## Corrections` in the profile so next time is better.

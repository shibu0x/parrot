---
name: writer
description: Writes tweets, posts, emails, blogs, replies in the USER'S OWN voice, learned from their past messages to terminal AI agents (Claude Code, Codex, Gemini CLI, Qwen Code, Copilot CLI, Kiro, Factory Droid, opencode, Aider). Use when the user runs /writer, or says "write this like me", "in my voice", "how I would write it". `/writer profile` builds or shows their style profile; `/writer <type> <topic>` drafts content.
---

# writer

Learn how the user writes from their own messages to coding agents, then write in that voice.
`<skill-dir>` below is the folder containing this SKILL.md (usually `~/.agents/skills/writer` or `~/.claude/skills/writer`).
Profile lives at `~/.writer/profile.md`. Raw messages never leave the machine except as the context you already have.

## Commands

- `/writer profile` : (re)build the profile and show it.
- `/writer <type> <what to write>` : type is tweet, thread, linkedin, blog, email, reply, docs, or anything else. Build the profile first if missing.

## 1. Build the profile

Run both:

```bash
python3 <skill-dir>/extract.py --limit 400
python3 <skill-dir>/extract.py --limit 400 | python3 <skill-dir>/stats.py
```

The first prints the user's own messages (`--source claude,codex,...` to restrict, `--list` to see message counts per agent; messages over 1500 chars are dropped as likely pastes; secrets, credentials and emails are already replaced with `[redacted]`). The second prints counted habits: lowercase starts, full stops, question marks, apostrophe drops, openers, top words.

Use the numbers from `stats.py` for Mechanics; don't estimate what was counted. Read the messages yourself for Voice and Samples. Write `~/.writer/profile.md`:

```markdown
# Writing profile
updated: <date> | messages analyzed: <N>

## Scores (0-100)
casual, direct, technical, formal, humor, emotional

## Mechanics
- avg sentence length (words), fragments yes/no
- capitalization (lowercase starts? "i" lowercase?)
- punctuation habits (periods at end? question marks? "..."? em dashes? exclamation?)
- emoji use
- language mix (e.g. Hinglish), slang and filler words with examples ("bro", "tbh")

## Signature (copy these)
Habits that are clearly the user's choice: consistent across many messages and kept even when they had time to write carefully. Lowercase starts at 86%, "bro" as an opener, no full stop at the end, dropping apostrophes in "dont"/"lets" are signature. Give the count next to each.

## Noise (never copy)
Things that come from typing fast to an AI, not from the voice:
- typos and misspellings ("becasue", "fiolder"), even frequent ones
- bare commands to the agent ("fix readme", "kill the process", "push it")
- pasted logs, code, error output, UI text
- fragments that only make sense mid-conversation ("done ??", "4000 is ok")

## Voice
- how they open and close a message
- how they explain, ask, push back
- words/phrases they use a lot (quote them)
- things they NEVER do (corporate tone, hedging, etc.)

## Samples
10-15 short verbatim messages that best show the voice. Skip anything with secrets, keys, emails, names of private people, or client data.
```

Be concrete. "Casual" is useless; "starts with 'bro', no capital letters, no period at the end" is useful. Count, don't guess.

When unsure whether a habit is signature or noise, ask: would they still do it in a post they reread before sending? If not, it's noise. A habit only goes in Signature if it shows up in at least ~20% of messages or is clearly deliberate (slang, a catchphrase).

Then show the profile to the user in a compact form.

## 2. Write

1. Read `~/.writer/profile.md`.
2. Note the gap: chat messages to an AI are not tweets. Copy everything under Signature, nothing under Noise. Fit the format (a tweet is under 280 chars, a blog has structure).
   Never add mistakes to look human: no planted typos, random fragments, or fake slang. Text sounds like the user because of their word choice and rhythm, not because it has errors.
3. Write 3 different drafts.
4. Get the mechanics score for each draft by counting, not judging:
   ```bash
   python3 <skill-dir>/extract.py --limit 400 | python3 <skill-dir>/stats.py --draft "<draft>"
   ```
   It prints a mechanics match % and the habits the draft gets most wrong. Then score the rest yourself (0-100): vocabulary, sentence rhythm, tone, and "would they actually send this". Penalize anything that smells like AI: "delve", "excited to announce", "game-changer", tidy rule-of-three lists, em dashes if the user doesn't use them, emoji the user doesn't use, hashtag soup.
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

# writer

A skill for terminal AI agents that learns how you write from your own messages to coding agents, then writes tweets, posts, emails and blogs in your voice.

Everything runs locally. `extract.py` reads only the messages you typed from your agents' local history, redacts secrets and emails, and `stats.py` counts your habits. Your profile is saved to `~/.writer/profile.md`.

Reads history from: Claude Code, Codex, Gemini CLI, Qwen Code, GitHub Copilot CLI, Kiro, Factory Droid, opencode, Aider.

## Install

```bash
git clone <this repo> ~/writer-skill && ~/writer-skill/install.sh
```

`install.sh` symlinks the skill into every agent it finds (`~/.agents`, `~/.claude`, `~/.codex`, `~/.gemini`, `~/.qwen`, `~/.copilot`, `~/.cursor`, `~/.factory`, `~/.kiro`, opencode, amp) and shows how many of your messages each agent has.

## Use

```
/writer profile                     # build and show your style profile
/writer tweet <what to write about> # also: thread, linkedin, blog, email, reply, docs
/writer rewrite [light|natural|strong] <text>  # put a draft in your voice
/writer check <text>                # how much it sounds like you, and what's off
```

## Better results: add real writing

Chat with an AI isn't how you tweet. Drop real posts into `~/.writer/samples/<channel>/` (`tweet/`, `email/`, `linkedin/`...), one per file or several split by a `---` line. For that channel they outrank your chat habits.

## Check

```bash
python3 extract.py --test && python3 stats.py --test && python3 eval.py --test
python3 extract.py --limit 1000 | python3 eval.py   # can the scorer tell you from generic AI text?
```

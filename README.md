# writer

A Claude Code / Codex skill that learns how you write from your own messages to coding agents, then writes tweets, posts, emails and blogs in your voice.

Everything runs locally. `extract.py` reads only the messages you typed from `~/.claude/projects` and `~/.codex/sessions`; your profile is saved to `~/.writer/profile.md`.

## Install

```bash
git clone <this repo> ~/writer-skill
ln -s ~/writer-skill ~/.claude/skills/writer
```

## Use

```
/writer profile                     # build and show your style profile
/writer tweet <what to write about> # also: thread, linkedin, blog, email, reply, docs
```

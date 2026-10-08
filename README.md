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

Everything happens in chat with your agent.

```
/writer profile                       learns your voice and shows you the stats
/writer tweet <what it's about>       also: thread, linkedin, blog, email, reply, docs
/writer rewrite <text>                puts a draft (yours or AI's) in your voice
/writer check <text>                  how much it sounds like you, and what's off
```

## Make it sharper with your real posts

How you talk to an AI isn't how you tweet. After showing your profile, `/writer` asks if you want to add your real writing. Just paste whatever you have in the chat:

> this is my writing https://medium.com/@you https://yourblog.dev
> here are some tweets https://x.com/you/status/123 https://x.com/you/status/456
> *(or paste the text of a few posts)*

It works out what each link is (a Medium or Substack profile, a blog, single tweets or LinkedIn posts), downloads your posts, and rebuilds your profile. Your real posts outrank your chat habits for that channel, so tweets come out like your tweets and blogs like your blogs.

Works with Medium, Substack, any blog with a feed, dev.to, Bluesky, single tweets and LinkedIn posts, and your X or LinkedIn data export if you want everything. X and LinkedIn profiles need a login, which this tool never uses, so for those you paste post links. Only add your own writing. Everything is saved on your machine in `~/.writer/`.

## Layout

```
SKILL.md            the skill: what the agent does for each /writer command
install.sh          links the skill into every agent on your machine
agents/openai.yaml  Codex UI metadata
scripts/
  extract.py        your messages from local agent history, secrets redacted
  stats.py          counts your habits, scores drafts, flags AI phrases
  eval.py           checks the scorer can tell you from generic AI text
  socials.py        pulls your posts from Medium, Substack, blogs, X/LinkedIn exports, links
```

Python 3 standard library only, nothing to install.

## For contributors

The agent runs these; you never need to. Self-checks, plus the eval on your own history:

```bash
python3 scripts/extract.py --test && python3 scripts/stats.py --test && python3 scripts/eval.py --test && python3 scripts/socials.py test
python3 scripts/extract.py --limit 1000 | python3 scripts/eval.py   # can the scorer tell you from generic AI text?
```

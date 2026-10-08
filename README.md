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

### Pull in your socials

The first `/writer profile` asks where you post and does this for you. Or just say it: `/writer set my profile, this is my writing https://medium.com/@you https://x.com/you/status/123`. By hand:

```bash
python3 scripts/socials.py set https://medium.com/@you https://yourblog.dev   # any link or export file, type detected
python3 scripts/socials.py add medium @you
python3 scripts/socials.py add substack you
python3 scripts/socials.py add x ~/Downloads/twitter-archive.zip      # X: Settings > Download an archive of your data
python3 scripts/socials.py add linkedin ~/Downloads/LinkedInExport.zip
python3 scripts/socials.py add link https://x.com/you/status/123 https://www.linkedin.com/posts/...   # single posts, any site
python3 scripts/socials.py sync                                       # later: fetch new posts only
```

Also: any blog RSS feed, dev.to, Bluesky. X and LinkedIn profiles need a login, which this tool never uses: give links to single posts (quick) or your data export (everything). Only add your own accounts; posts are saved to `~/.writer/samples/` on your machine.

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

## Check

```bash
python3 scripts/extract.py --test && python3 scripts/stats.py --test && python3 scripts/eval.py --test && python3 scripts/socials.py test
python3 scripts/extract.py --limit 1000 | python3 scripts/eval.py   # can the scorer tell you from generic AI text?
```

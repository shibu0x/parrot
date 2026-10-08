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

The first `/writer profile` asks where you post and does this for you. By hand:

```bash
python3 socials.py add medium @you
python3 socials.py add substack you
python3 socials.py add x ~/Downloads/twitter-archive.zip      # X: Settings > Download an archive of your data
python3 socials.py add linkedin ~/Downloads/LinkedInExport.zip
python3 socials.py add link https://x.com/you/status/123 https://www.linkedin.com/posts/...   # single posts, any site
python3 socials.py sync                                       # later: fetch new posts only
```

Also: any blog RSS feed, dev.to, Bluesky. X and LinkedIn profiles need a login, which this tool never uses: give links to single posts (quick) or your data export (everything). Only add your own accounts; posts are saved to `~/.writer/samples/` on your machine.

## Check

```bash
python3 extract.py --test && python3 stats.py --test && python3 eval.py --test && python3 socials.py test
python3 extract.py --limit 1000 | python3 eval.py   # can the scorer tell you from generic AI text?
```

#!/bin/sh
# Link this skill into every terminal AI agent installed on this machine.
# Symlinks, so `git pull` here updates every agent. Never touches a different
# skill that happens to be called `writer`.
src=$(cd "$(dirname "$0")" && pwd)
for dir in ~/.agents ~/.claude ~/.codex ~/.gemini ~/.qwen ~/.copilot ~/.cursor ~/.factory ~/.kiro ~/.config/opencode ~/.config/amp; do
  [ -d "$dir" ] || continue
  dest="$dir/skills/writer"
  if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$src" ]; then
    echo "ok      $dest"
  elif [ -e "$dest" ] || [ -L "$dest" ]; then
    echo "SKIPPED $dest already exists and is not this repo, remove it and re-run to replace it"
  else
    mkdir -p "$dir/skills" && ln -s "$src" "$dest" && echo "linked  $dest"
  fi
done
python3 "$src/extract.py" --list

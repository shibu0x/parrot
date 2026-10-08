#!/bin/sh
# Link this skill into every terminal AI agent installed on this machine.
# Symlinks, so `git pull` here updates every agent.
set -e
src=$(cd "$(dirname "$0")" && pwd)
for dir in ~/.agents ~/.claude ~/.codex ~/.gemini ~/.qwen ~/.copilot ~/.cursor ~/.factory ~/.kiro ~/.config/opencode ~/.config/amp; do
  [ -d "$dir" ] || continue
  mkdir -p "$dir/skills"
  ln -sfn "$src" "$dir/skills/writer"
  echo "linked $dir/skills/writer"
done
python3 "$src/extract.py" --list

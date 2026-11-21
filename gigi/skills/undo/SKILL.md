---
name: undo
description: Use when the person wants to undo what Claude changed, get a file back, "put it back", "what did you change", "I lost my work", or runs /gigi:undo. Shows what changed in the kit and puts back only the files they pick, on their yes.
allowed-tools: Bash(python3:*), Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git restore:*), Bash(git show:*)
---

# Undo

Their kit is saved with git, so anything since the last save can be put back.

1. Find the kit: `python3 "<base>/../../scripts/coach.py" kit`, where `<base>` is this skill's base directory (shown above as "Base directory for this skill"); with nothing, use the current folder. Run git with `-C "<kit>"`.
2. Show what changed since the last save: `git -C "<kit>" status --short` and `git -C "<kit>" diff --stat`. Say it in plain words: "Claude changed 3 files and added 2: ..." Group by folder when there are many. New files are listed as new; they are only removed if they ask.
3. Ask which to put back. Their reply naming files is the yes.
4. Put back exactly those: `git -C "<kit>" restore -- <files>` for changed or deleted files. For a new file they want gone, tell them it goes to the Trash from Finder; never delete files yourself.
5. An older version (before the last save): show `git -C "<kit>" log --oneline -10 -- <file>`, and on their yes `git -C "<kit>" restore --source <commit> -- <file>`.
6. Never commit, push, reset, or clean. Finish with what was put back.

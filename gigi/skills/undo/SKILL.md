---
name: undo
description: Use when the person wants to undo a change, get a file back, "put it back", "what changed", "I lost my work", or runs /gigi:undo. Shows what changed in the kit since the last save and puts back only the files they pick, on their yes, keeping a copy of what it replaces.
allowed-tools: Bash(python3:*)
---

# Undo

Their kit is saved with git, so anything since the last save can be put back. `<base>` below is this skill's base directory (shown above as "Base directory for this skill").

1. Run `python3 "<base>/../../scripts/coach.py" changes`. It prints JSON: `kit`, `last_save` (when, and its note), and `changed` (each `path` with `state`: changed, deleted or new).
2. Say it in plain words: "Since your last save (2 days ago), 3 files changed and 2 are new: ..." Group by folder when there are many. These are changes by Claude or by them; don't say Claude made them all.
3. Ask which to put back. Their reply naming files is the yes. "All of it" means you list them once more and ask again.
4. Run `python3 "<base>/../../scripts/coach.py" restore <path> <path> ...` with the paths as listed. It puts each back from the last save and first copies the current version to `.gigi-undo/<time>/` in the kit. New files are left as they are.
5. Tell them what came back, and that the versions they replaced are kept in `.gigi-undo` in their kit if they change their mind. For a new file they want gone: they move it to the Trash in Finder; you never delete files.
6. An older version, before the last save: tell them older versions need a person from the bootcamp team, so nothing is lost by guessing.

Never commit, push, reset, clean or delete.

---
name: fresh-start
description: Use when the thread is long, slow, nearly full, or the Gigi plugin says it is getting long; when the person says "start fresh", "new thread", "handoff", "this is slow"; or /gigi:fresh-start. Writes a handoff note and opens a new thread with it.
allowed-tools: Bash(python3:*), Bash(mkdir:*), Write
---

# Fresh start

A long thread makes every reply slower and costlier, and details get lost when Claude compacts it. A short note carries what matters into a new thread.

1. Run `python3 "<base>/../../scripts/coach.py" kit` with Bash, where `<base>` is this skill's base directory (shown above as "Base directory for this skill"). It prints their AgentOS kit folder, or nothing; with nothing, use the current folder.
2. Write the note from this conversation to `<kit>/handoffs/YYYY-MM-DD-<short-topic>.md` (make the folder if needed). Facts only, under 60 lines:
   - **Goal:** one or two lines.
   - **Where we are:** what works now.
   - **Decisions:** what was decided, and why in a few words.
   - **Files:** created or changed, by path.
   - **What's left:** a short checklist.
   - **Next step:** exactly what to do first.
   - **Watch out:** anything that bit us.
3. Run `python3 "<base>/../../scripts/coach.py" handoff-link "<full path of the note>"`. It prints the link, then `opened: yes` or `opened: no`. On a Mac it opens a new Claude thread in the kit with a short message in the box that points at the note.
4. `opened: yes`: "I wrote your handoff note and opened a new thread with it in the box. Press Return there. You can archive this one."
   `opened: no`: "I wrote your handoff note. Type /clear, then paste: Read handoffs/<file> and carry on from where it leaves off."

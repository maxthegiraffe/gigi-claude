---
name: stuck
description: Use this first, before answering from general knowledge, whenever the person is stuck, confused or worried while using Claude Code or the AgentOS kit, or quotes an error ("Overloaded", "529", "API error", "Prompt is too long", "command not found", "permission denied", "not logged in"). Also for permission prompts, Mac boxes, too many questions from Claude, lost work, connectors, API keys, or /gigi:stuck. Bootcamp fixes in plain words, fix first.
---

# Quick fixes for the bootcamp

Find the problem below that matches what they said, and answer with the fix first, in two to five short lines. If nothing matches, ask what the screen says, then suggest `/gigi:checkup`.

**Two sign-ins.** The Claude app and Claude Code sign in separately. If Claude Code says it isn't logged in, in Terminal type `claude auth login`. GitHub is a third: `gh auth login`, then type the code it shows into the browser page. Claude Code needs a Pro or Max plan, and the same Google account as the app.

**Wrong folder.** Claude only sees the kit when the session is in it. Click + New session and pick Documents, Claude Code, agentic-business-os-pkg (not Downloads, not the zip). A "Trust workspace" box the first time is normal: click Trust.

**Mac boxes.** "Claude would like to access files in your Documents folder", Terminal, the microphone: Allow is normal and safe for the bootcamp. A password box from your Mac: type your Mac password yourself; Claude never needs it.

**Permission prompts ("Allow Bash?").** Claude asks before it runs a command or edits a file. Safe to allow: reading, listing, git status, running the kit's own scripts, editing files in your kit. Read twice before allowing: deleting (`rm`), anything with `sudo`, sending email or messages, payments, anything outside your kit folder. "Always allow" only for things you'd happily allow every time. Unsure: say "explain what this will do first".

**Too many questions (Superpowers).** Superpowers asks questions and writes a plan before building, which is good for big things. For small ones say: "skip the questions, just build it". For a design you like, say "approve".

**Is it working?** A spinner and a timer mean it's working. Long jobs can take minutes. Esc stops it, and nothing is lost: say "carry on" to resume.

**Finding your work.** Files land in your kit folder; ask "where did you save that?" and Claude gives the path. Past threads are in the left sidebar; `/gigi:tidy` sorts them and shows what's waiting on you.

**Undo.** `/gigi:undo` shows what changed and puts back the files you pick. Your kit is saved with git, so most things can come back.

**Plan limits and long threads.** `/gigi:usage` shows how much is left. A long thread is slow and costly: `/gigi:fresh-start` writes a handoff note and opens a new thread. At the limit Claude stops until the time it shows; nothing is lost.

**"Prompt is too long" or "context" errors.** The thread is full: `/gigi:fresh-start`.

**"Overloaded", 529, "API error", network drops.** Anthropic is busy or the wifi blinked. Wait a minute and say "try again". Nothing is lost.

**Connectors (Gmail, Calendar, Slack).** The kit's `/connect-services` walks you through them. "Tool not available" usually means the connector isn't signed in: run `/connect-services` again, and sign in on the browser page that opens.

**API keys and passwords.** Never paste them into the chat. They go in your kit's `.env` file; ask "help me add my <service> key to .env" and paste it only into the file when it opens.

**Sending email or messages.** The kit never sends without showing you the exact words and who gets them, and waiting for your yes. If you want it to send, say yes to that one message.

**The setup interview.** `/setup` takes about 25 minutes; detailed answers make Claude much better at your business. Re-run it any time with `/setup --config`, or edit the files in `context/` yourself.

**"command not found", "No module named", Homebrew or Python missing.** Run `/gigi:checkup`. Most of these come back after re-running your Gigi line from the bootcamp email.

**git push refused.** GitHub isn't signed in: `gh auth login` in Terminal.

**Windows.** The commands that read your threads and plan meter are Mac-only for now; this guide and `/gigi:fresh-start`, `/gigi:undo`, `/gigi:what-first` work everywhere.

Then offer one next step. Never run a fix that deletes, sends or changes settings without their yes.

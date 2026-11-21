# Gigi for Claude Code

Your coach inside Claude Code, from the AgentOS bootcamp.

## Install

Open Terminal, paste this line, press Return:

```
claude plugin marketplace add maxthegiraffe/gigi-claude && claude plugin install gigi@gigi-claude
```

Then start a new Claude session (or quit and reopen the Claude app).

## What you can type

- `/gigi:checkup` when something isn't working: sign-ins, your kit folder, the setup interview, and the fix.
- `/gigi:usage` to see how much of your Claude plan is left and which threads are getting long.
- `/gigi:stuck` for quick fixes: errors, permission prompts, Mac boxes, connectors, too many questions.
- `/gigi:what-first` for three things to build for your business, with the sentence to type.
- `/gigi:fresh-start` when a thread is long or slow: a handoff note and a new thread with it.
- `/gigi:tidy` to clean up your thread sidebar (only what you say yes to).
- `/gigi:undo` to see what Claude changed in your kit and put back the files you pick.

You can also just describe the problem; Claude picks the right one.

Gigi also speaks up on her own, once, when it matters: when you've used 80% of your plan, when a thread gets long, and when your setup interview hasn't run yet. She never blocks anything or changes your settings.

## Update or remove

```
claude plugin marketplace update gigi-claude && claude plugin update gigi@gigi-claude
```

```
claude plugin uninstall gigi@gigi-claude
```

Made for Macs with the Claude app and the AgentOS kit. On Windows, the guide, fresh start, undo and what-first work; the usage and thread tools are Mac-only for now.

---
name: usage
description: Use when the person asks how much of their Claude plan is left, about usage, limits or tokens, why Claude got slow or stopped, "am I running out", or runs /gigi:usage. Shows the plan meter, their longest threads, and what to do.
allowed-tools: Bash(python3:*)
---

# How much of your plan is left

1. Run `python3 "<base>/../../scripts/coach.py" usage` with Bash, where `<base>` is this skill's base directory (shown above as "Base directory for this skill"). It prints JSON:
   - `meter`: `fh` (% of the 5-hour limit), `sd` (% of this week), `age_min` (how old the reading is), or `null`.
   - `threads`: their longest recent Claude Code threads: `title`, `tokens`, `window`, `pct` (how full), `last`.
2. Tell them in a few short lines, plain words:
   - The 5-hour and weekly numbers. If `age_min` is over 60, say the reading is that old; the Claude app refreshes it when they open Settings, then Usage.
   - `meter` is null and `platform` is `darwin`: "I can't see your plan meter yet. Open the Claude app's Settings, then Usage, once, and ask me again."
   - `meter` is null on another `platform`: "I can only read the plan meter on a Mac for now. In the Claude app, Settings, then Usage shows it."
   - The 5-hour number is stale once `age_min` is over 300: say so instead of quoting it.
   - Their two or three fullest threads with how full each is. Over 80%: suggest `/gigi:fresh-start` in that thread.
3. Then only the advice that applies:
   - 5-hour limit at 80% or more: it frees up on a rolling 5 hours. Do lighter work now (Sonnet is fine for everyday tasks; `/model` switches), and save heavy builds for later.
   - Week at 80% or more: spend what's left on what matters most this week; start fresh threads instead of stretching long ones.
   - Long threads cost the most: every reply re-reads the whole thread. A fresh thread with a handoff note is cheaper and faster.
   - If they hit the limit: Claude stops until the time in its message, nothing is lost, and Gigi Helper still works meanwhile.

Never change their model or settings yourself; tell them how. No tables, no jargon.
